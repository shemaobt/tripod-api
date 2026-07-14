"""Artifact custody: bytes in, the same bytes out, forever.

The three artifacts are produced client-side and re-read by a downstream pipeline that
diffs them byte for byte against a golden reference (PRD §10.5). The API is only their
custodian. That makes one property load-bearing above all others: **nothing here may
parse a payload.** A `json.loads` + `json.dumps` round-trip is invisible to a shallow
assertion and fatal to the contract — it silently reorders keys, collapses whitespace,
re-escapes unicode and appends a newline.

So the payloads in these tests are deliberately ugly: keys out of alphabetical order,
two-space indents, a long float, en/em dashes, accented characters, no trailing newline.
A server that re-serialized any of them would still return valid, plausible JSON — and
every one of these tests would fail.
"""

from __future__ import annotations

import base64

import google_crc32c
import pytest

from app.db.models.sound_necklace import ArtifactKind
from app.services.oral_collector import gcs_utils
from tests.baker import make_language, make_project, make_project_user_access, make_user
from tests.test_sound_necklace.conftest import auth_header, grant_role

SN = "/api/sound-necklace"


# The bytes the golden harness would diff. Not built with json.dumps, on purpose.
MANIFEST_BYTES = (
    b'{"manifest_id":"fnv1a32:d31a8419",\n  "bead_sec": 0.30000000000000004,\n'
    b'  "zeta": 1, "alpha": 2,\n  "story": "A Hist\xc3\xb3ria de Rute \xe2\x80\x94 parte I"}'
)
ANCHORING_BYTES = (
    b'{"scenes":[{"id":"PT1","kind":"journey","confidence":"m\xc3\xa9dia"}],\n'
    b'  "phrases": [],  "seams":[]}'
)
# No trailing newline, en dash, em dash, curly quotes, accents, two-space indent. The
# dashes are escaped rather than written literally so that the linter's homoglyph check
# stays useful elsewhere — the bytes are the same, and they are the point: a report that
# came back with an ASCII hyphen would still read correctly and still break the diff.
REPORT_BYTES = (
    "# Relatório de Mapeamento\n\n"
    "## Cena PT1 \u2013 jornada\n\n"
    "  Resposta \u2014 nível 1: \u201co povo caminhou\u201d\n"
    "  Confiança: média"
).encode()

PAYLOADS = {
    "manifest": MANIFEST_BYTES,
    "anchoring": ANCHORING_BYTES,
    "report": REPORT_BYTES,
}


def crc32c_of(data: bytes) -> str:
    return base64.b64encode(google_crc32c.Checksum(data).digest()).decode()


@pytest.fixture()
def storage(monkeypatch):
    """A fake GCS: what was uploaded under a key, and what a signed URL points at.

    Real storage serves the bytes verbatim, so holding them in a dict is the honest
    model of it — and it lets a test read back exactly what the API handed over.
    """

    class FakeStorage:
        def __init__(self) -> None:
            self.objects: dict[str, bytes] = {}
            self.content_types: dict[str, str] = {}
            self.signed: list[dict] = []

        async def upload(
            self,
            bucket_name: str,
            blob_name: str,
            data: bytes,
            content_type: str,
            *,
            content_encoding: str | None = None,
        ) -> str:
            self.objects[blob_name] = data
            self.content_types[blob_name] = content_type
            return f"gs://{bucket_name}/{blob_name}"

        async def sign(
            self,
            bucket_name: str,
            blob_name: str,
            *,
            expiry_minutes: int = 15,
            response_content_type: str | None = None,
        ) -> str:
            self.signed.append({"bucket": bucket_name, "blob": blob_name, "ttl": expiry_minutes})
            return f"https://storage.googleapis.com/{bucket_name}/{blob_name}?X-Goog-Signature=d0d0"

        def fetch(self, url: str) -> bytes:
            """What a client following the redirect would actually receive."""
            key = url.split("?", 1)[0].split("/", 4)[4]
            return self.objects[key]

    fake = FakeStorage()
    monkeypatch.setattr(gcs_utils, "upload_gcs_object", fake.upload)
    monkeypatch.setattr(gcs_utils, "generate_signed_download_url", fake.sign)
    return fake


@pytest.fixture()
async def facilitator(db_session, sound_necklace_app):
    user = await make_user(db_session, email="facilitator@example.com")
    await grant_role(db_session, sound_necklace_app.id, user.id, "facilitator")
    language = await make_language(db_session, name="Terena", code="ter")
    project = await make_project(db_session, language.id, name="Projeto A")
    await make_project_user_access(db_session, project.id, user.id)
    headers = await auth_header(db_session, user)
    return user, project, headers


@pytest.fixture()
async def other_project(db_session):
    language = await make_language(db_session, name="Nheengatu", code="yrl")
    return await make_project(db_session, language.id, name="Projeto B")


async def new_session(client, headers, project_id: str) -> str:
    res = await client.post(
        f"{SN}/sessions",
        headers=headers,
        json={
            "audio_id": "ruth-a-historia-de-rute",
            "project_id": project_id,
            "story_name": "A História de Rute",
            "story_slug": "a-historia-de-rute",
            "granularity_level": "medium",
            "bead_sec": 0.5,
            "manifest_id": "fnv1a32:d31a8419",
            "pipeline_consent": True,
        },
    )
    assert res.status_code == 201, res.text
    return str(res.json()["id"])


def upload_files(payloads: dict[str, bytes] | None = None) -> dict:
    p = payloads or PAYLOADS
    return {
        "manifest": ("manifesto-contas.json", p["manifest"], "application/json"),
        "anchoring": ("retorno-ancoragem.json", p["anchoring"], "application/json"),
        "report": ("relatorio-mapeamento.md", p["report"], "text/markdown"),
    }


# ── The rule this issue exists for ───────────────────────────────────────────


async def test_the_bytes_that_come_back_are_the_bytes_that_went_in(client, facilitator, storage):
    """The whole issue, in one test. A json round-trip anywhere on this path would
    reorder the keys, normalize the whitespace, re-escape the accents and add a newline
    — and every payload here is shaped to make that visible."""
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)

    upload = await client.post(
        f"{SN}/sessions/{session_id}/artifacts", headers=headers, files=upload_files()
    )
    assert upload.status_code == 201, upload.text

    for kind, expected in (
        ("manifest", MANIFEST_BYTES),
        ("anchoring", ANCHORING_BYTES),
        ("report", REPORT_BYTES),
    ):
        res = await client.get(
            f"{SN}/sessions/{session_id}/artifacts/{kind}",
            headers=headers,
            follow_redirects=False,
        )
        assert res.status_code == 307, f"{kind}: {res.text}"
        served = storage.fetch(res.headers["location"])
        assert served == expected, f"{kind} did not survive custody"


def test_no_artifact_payload_is_ever_deserialized():
    """A guard for the rule the test above proves, at the level §10.5 states it:

        "must NOT deserialize an artifact into a Pydantic model and re-serialize it"

    The byte-identity test catches a round-trip on the payloads it happens to carry.
    This catches the reach for the parser itself, on any payload, in the whole path.
    """
    import importlib
    import inspect

    path = "app.services.sound_necklace"
    source = "\n".join(
        inspect.getsource(importlib.import_module(f"{path}.{name}"))
        for name in ("store_artifacts", "artifact_download_url")
    )
    for parser in ("json.loads", "json.dumps", "model_validate", "model_dump", ".json()"):
        assert parser not in source, (
            f"the artifact path reaches for {parser!r} — payloads must stay opaque bytes"
        )


async def test_an_empty_artifact_is_rejected_rather_than_stored(client, facilitator, storage):
    """An empty upload is a client bug, and storing it would hand the pipeline a
    zero-byte artifact that diffs as 'present but wrong'."""
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)

    res = await client.post(
        f"{SN}/sessions/{session_id}/artifacts",
        headers=headers,
        files=upload_files({**PAYLOADS, "report": b""}),
    )

    assert res.status_code == 400, res.text
    assert storage.objects == {}, "an artifact was stored before the envelope was validated"


# ── Checksums ────────────────────────────────────────────────────────────────


async def test_the_checksums_describe_the_bytes_actually_stored(client, facilitator, storage):
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)

    res = await client.post(
        f"{SN}/sessions/{session_id}/artifacts", headers=headers, files=upload_files()
    )

    assert res.status_code == 201, res.text
    by_kind = {a["kind"]: a for a in res.json()}
    assert by_kind["manifest"]["size"] == len(MANIFEST_BYTES)
    assert by_kind["manifest"]["crc32c"] == crc32c_of(MANIFEST_BYTES)
    assert by_kind["report"]["size"] == len(REPORT_BYTES)
    assert by_kind["report"]["crc32c"] == crc32c_of(REPORT_BYTES)


# ── Re-completion ────────────────────────────────────────────────────────────


async def test_reuploading_replaces_the_artifact_rather_than_accumulating(
    client, facilitator, storage
):
    """A facilitator who reopens a session and completes it again must not leave the
    pipeline choosing between two manifests."""
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)
    await client.post(
        f"{SN}/sessions/{session_id}/artifacts", headers=headers, files=upload_files()
    )

    revised = b'{"manifest_id":"fnv1a32:d31a8419", "revised": true}'
    second = await client.post(
        f"{SN}/sessions/{session_id}/artifacts",
        headers=headers,
        files=upload_files({**PAYLOADS, "manifest": revised}),
    )

    assert second.status_code == 201, second.text
    res = await client.get(
        f"{SN}/sessions/{session_id}/artifacts/manifest", headers=headers, follow_redirects=False
    )
    assert storage.fetch(res.headers["location"]) == revised
    assert len(storage.objects) == 3, "a stale artifact object was left behind"


# ── The gate (this download is an audit point — ENG-266 hooks here) ──────────


async def test_uploading_into_another_projects_session_is_denied(
    client, facilitator, other_project, db_session, sound_necklace_app, storage
):
    _user, _project, headers = facilitator
    outsider = await make_user(db_session, email="outsider@example.com")
    await grant_role(db_session, sound_necklace_app.id, outsider.id, "facilitator")
    await make_project_user_access(db_session, other_project.id, outsider.id)
    theirs = await new_session(client, await auth_header(db_session, outsider), other_project.id)

    res = await client.post(
        f"{SN}/sessions/{theirs}/artifacts", headers=headers, files=upload_files()
    )

    assert res.status_code == 403
    assert storage.objects == {}, "bytes were stored before the gate rejected the caller"


async def test_downloading_another_projects_artifact_is_denied(
    client, facilitator, other_project, db_session, sound_necklace_app, storage
):
    _user, _project, headers = facilitator
    outsider = await make_user(db_session, email="outsider@example.com")
    await grant_role(db_session, sound_necklace_app.id, outsider.id, "facilitator")
    await make_project_user_access(db_session, other_project.id, outsider.id)
    their_headers = await auth_header(db_session, outsider)
    theirs = await new_session(client, their_headers, other_project.id)
    await client.post(
        f"{SN}/sessions/{theirs}/artifacts", headers=their_headers, files=upload_files()
    )

    res = await client.get(
        f"{SN}/sessions/{theirs}/artifacts/manifest", headers=headers, follow_redirects=False
    )

    assert res.status_code == 403
    assert storage.signed == [], "a URL was minted before the gate rejected the caller"


async def test_an_artifact_never_uploaded_is_a_miss(client, facilitator, storage):
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)

    res = await client.get(
        f"{SN}/sessions/{session_id}/artifacts/manifest", headers=headers, follow_redirects=False
    )

    assert res.status_code == 404
    assert storage.signed == []


async def test_the_download_url_is_short_lived_and_names_the_frozen_filename(
    client, facilitator, storage
):
    """PRD §10 freezes the artifact filenames. They ride in the object key, so the
    browser saves the file the pipeline expects without the API proxying a byte."""
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)
    await client.post(
        f"{SN}/sessions/{session_id}/artifacts", headers=headers, files=upload_files()
    )

    res = await client.get(
        f"{SN}/sessions/{session_id}/artifacts/anchoring",
        headers=headers,
        follow_redirects=False,
    )

    assert res.status_code == 307
    (call,) = storage.signed
    assert call["bucket"] == "sound-necklace-private"
    assert call["blob"].endswith("a-historia-de-rute-retorno-ancoragem.json")
    assert call["ttl"] == 15


async def test_every_kind_of_artifact_is_reachable(client, facilitator, storage):
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)
    await client.post(
        f"{SN}/sessions/{session_id}/artifacts", headers=headers, files=upload_files()
    )

    for kind in ArtifactKind:
        res = await client.get(
            f"{SN}/sessions/{session_id}/artifacts/{kind.value}",
            headers=headers,
            follow_redirects=False,
        )
        assert res.status_code == 307, f"{kind.value} is not reachable: {res.text}"
