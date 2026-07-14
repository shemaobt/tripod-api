"""Session persistence: create, autosave under a version guard, lifecycle, resume, list.

The state document is produced and validated by the SPA (it re-reads it with a
strict schema), so the API is only its custodian: what comes in as bytes goes out
as the same bytes. These tests send deliberately ugly JSON — keys out of order,
odd whitespace, a long float — because a server that re-serializes the document
would silently normalize all three and still look correct to a shallow assertion.
"""

from __future__ import annotations

import pytest

from tests.baker import make_language, make_project, make_project_user_access, make_user
from tests.test_sound_necklace.conftest import auth_header, grant_role

SN = "/api/sound-necklace"


def state_bytes(*, mode: str = "escuta", confirmed: bool = False) -> str:
    """A state envelope whose exact bytes matter. Not built with json.dumps on purpose."""
    return (
        '{"schema_version": 1,  "mode":"' + mode + '",\n'
        '  "beadSec": 0.30000000000000004, "whole": {"confirmed": '
        + ("true" if confirmed else "false")
        + ', "id":"S1"},\n  "zeta": 1, "alpha": 2}'
    )


JSON_HEADERS = {"content-type": "application/json"}


async def new_session(client, headers, project_id: str, *, name: str = "O Conto do Boto") -> str:
    res = await client.post(
        f"{SN}/sessions",
        headers=headers,
        json={
            "audio_id": "aud_1",
            "project_id": project_id,
            "story_name": name,
            "story_slug": "conto-do-boto",
            "granularity_level": "media",
            "bead_sec": 0.5,
            "manifest_id": "fnv1a32:d31a8419",
            "pipeline_consent": True,
        },
    )
    assert res.status_code == 201, res.text
    return str(res.json()["id"])


@pytest.fixture()
async def facilitator(db_session, sound_necklace_app):
    """A sound-necklace facilitator with access to one project."""
    user = await make_user(db_session, email="facilitator@example.com")
    await grant_role(db_session, sound_necklace_app.id, user.id, "facilitator")
    language = await make_language(db_session, name="Nheengatu", code="yrl")
    project = await make_project(db_session, language.id, name="Projeto A")
    await make_project_user_access(db_session, project.id, user.id)
    headers = await auth_header(db_session, user)
    return user, project, headers


# ── Creation ─────────────────────────────────────────────────────────────────


async def test_create_opens_the_session_at_the_first_station(client, facilitator):
    _user, project, headers = facilitator

    res = await client.post(
        f"{SN}/sessions",
        headers=headers,
        json={
            "audio_id": "aud_1",
            "project_id": project.id,
            "story_name": "O Conto do Boto",
            "story_slug": "conto-do-boto",
            "granularity_level": "media",
            "bead_sec": 0.5,
            "manifest_id": "fnv1a32:d31a8419",
            "pipeline_consent": True,
        },
    )

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "em_progresso"
    assert body["progress"]["current_step"] == "ouvir"
    assert body["story_slug"] == "conto-do-boto"
    assert body["project_id"] == project.id


async def test_create_in_a_project_the_user_cannot_reach_is_forbidden(
    client, db_session, facilitator, sound_necklace_app
):
    _user, _project, headers = facilitator
    language = await make_language(db_session, name="Outra", code="oth")
    foreign = await make_project(db_session, language.id, name="Projeto B")

    res = await client.post(
        f"{SN}/sessions",
        headers=headers,
        json={
            "audio_id": "aud_1",
            "project_id": foreign.id,
            "story_name": "Alheia",
            "story_slug": "alheia",
            "granularity_level": "media",
            "bead_sec": 0.5,
            "manifest_id": "fnv1a32:d31a8419",
            "pipeline_consent": True,
        },
    )

    assert res.status_code == 403


# ── Autosave + resume: the bytes are the contract ────────────────────────────


async def test_state_is_absent_until_the_first_autosave(client, facilitator):
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)

    res = await client.get(f"{SN}/sessions/{session_id}/state", headers=headers)

    assert res.status_code == 404


async def test_resume_returns_the_saved_document_byte_for_byte(client, facilitator):
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)
    raw = state_bytes(mode="triagem")

    saved = await client.put(
        f"{SN}/sessions/{session_id}/state",
        headers={**headers, **JSON_HEADERS},
        content=raw,
    )
    assert saved.status_code == 200, saved.text

    resumed = await client.get(f"{SN}/sessions/{session_id}/state", headers=headers)

    assert resumed.status_code == 200
    assert resumed.content == raw.encode(), "the stored document must come back as the same bytes"


async def test_progress_follows_the_saved_state(client, facilitator):
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)

    await client.put(
        f"{SN}/sessions/{session_id}/state",
        headers={**headers, **JSON_HEADERS},
        content=state_bytes(mode="mapeamento"),
    )

    res = await client.get(f"{SN}/sessions/{session_id}", headers=headers)
    assert res.json()["progress"]["current_step"] == "conversa"


async def test_progress_reaches_the_cutting_station_once_the_whole_is_confirmed(
    client, facilitator
):
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)

    await client.put(
        f"{SN}/sessions/{session_id}/state",
        headers={**headers, **JSON_HEADERS},
        content=state_bytes(mode="escuta", confirmed=True),
    )

    res = await client.get(f"{SN}/sessions/{session_id}", headers=headers)
    assert res.json()["progress"]["current_step"] == "cortar"


# ── The version guard ────────────────────────────────────────────────────────


async def test_autosave_without_a_version_overwrites(client, facilitator):
    """The SPA's autosaver sends no version. An unconditional write must keep working."""
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)
    last = state_bytes(mode="mapeamento")

    for raw in (state_bytes(mode="escuta"), state_bytes(mode="triagem"), last):
        res = await client.put(
            f"{SN}/sessions/{session_id}/state",
            headers={**headers, **JSON_HEADERS},
            content=raw,
        )
        assert res.status_code == 200, res.text

    resumed = await client.get(f"{SN}/sessions/{session_id}/state", headers=headers)
    assert resumed.text == last


async def test_a_stale_if_match_that_is_not_a_version_is_refused_not_crashed(client, facilitator):
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)

    res = await client.put(
        f"{SN}/sessions/{session_id}/state",
        headers={**headers, **JSON_HEADERS, "If-Match": "not-a-version"},
        content=state_bytes(),
    )

    assert res.status_code == 400


async def test_a_body_that_is_not_utf8_is_refused_not_crashed(client, facilitator):
    """`json.loads` accepts UTF-16, so a body can validate and still not be UTF-8 text."""
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)

    res = await client.put(
        f"{SN}/sessions/{session_id}/state",
        headers={**headers, **JSON_HEADERS},
        content=state_bytes().encode("utf-16"),
    )

    assert res.status_code == 400


async def test_the_second_writer_of_a_version_is_refused_and_told_the_current_one(
    client, facilitator
):
    """Two machines resume the same session and both write from version 1.

    The first wins; the loser must be refused with the version it needs to reload,
    rather than silently clobbering work it never saw.
    """
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)

    first_save = await client.put(
        f"{SN}/sessions/{session_id}/state",
        headers={**headers, **JSON_HEADERS},
        content=state_bytes(mode="escuta"),
    )
    version = first_save.headers["etag"]

    winner = await client.put(
        f"{SN}/sessions/{session_id}/state",
        headers={**headers, **JSON_HEADERS, "If-Match": version},
        content=state_bytes(mode="triagem"),
    )
    loser = await client.put(
        f"{SN}/sessions/{session_id}/state",
        headers={**headers, **JSON_HEADERS, "If-Match": version},
        content=state_bytes(mode="mapeamento"),
    )

    assert winner.status_code == 200
    assert loser.status_code == 409
    assert loser.json()["current_version"] == 2

    kept = await client.get(f"{SN}/sessions/{session_id}/state", headers=headers)
    assert kept.text == state_bytes(mode="triagem"), "the refused write must not have landed"


# ── Lifecycle ────────────────────────────────────────────────────────────────


async def test_complete_then_reopen_preserves_the_document(client, facilitator):
    _user, project, headers = facilitator
    session_id = await new_session(client, headers, project.id)
    raw = state_bytes(mode="mapeamento")
    await client.put(
        f"{SN}/sessions/{session_id}/state",
        headers={**headers, **JSON_HEADERS},
        content=raw,
    )

    done = await client.post(f"{SN}/sessions/{session_id}/complete", headers=headers)
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "concluida"
    assert done.json()["progress"]["current_step"] == "guardar"

    reopened = await client.post(f"{SN}/sessions/{session_id}/reopen", headers=headers)
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "em_progresso"
    assert reopened.json()["progress"]["current_step"] == "conversa", (
        "reopening must restore the station the state was left at, not the completion one"
    )

    resumed = await client.get(f"{SN}/sessions/{session_id}/state", headers=headers)
    assert resumed.content == raw.encode(), "a completed-then-reopened session must resume intact"


# ── Listing ──────────────────────────────────────────────────────────────────


async def test_the_list_only_shows_sessions_of_projects_the_user_can_reach(
    client, db_session, facilitator, sound_necklace_app
):
    _user, project, headers = facilitator
    await new_session(client, headers, project.id, name="Minha")

    stranger = await make_user(db_session, email="stranger@example.com")
    await grant_role(db_session, sound_necklace_app.id, stranger.id, "facilitator")
    other_language = await make_language(db_session, name="Outra", code="oth")
    other_project = await make_project(db_session, other_language.id, name="Projeto B")
    await make_project_user_access(db_session, other_project.id, stranger.id)
    stranger_headers = await auth_header(db_session, stranger)
    await new_session(client, stranger_headers, other_project.id, name="Alheia")

    mine = await client.get(f"{SN}/sessions", headers=headers)
    theirs = await client.get(f"{SN}/sessions", headers=stranger_headers)

    assert [s["story_name"] for s in mine.json()["sessions"]] == ["Minha"]
    assert [s["story_name"] for s in theirs.json()["sessions"]] == ["Alheia"]


async def test_reading_a_session_of_another_project_is_forbidden(
    client, db_session, facilitator, sound_necklace_app
):
    _user, _project, headers = facilitator
    stranger = await make_user(db_session, email="stranger@example.com")
    await grant_role(db_session, sound_necklace_app.id, stranger.id, "facilitator")
    other_language = await make_language(db_session, name="Outra", code="oth")
    other_project = await make_project(db_session, other_language.id, name="Projeto B")
    await make_project_user_access(db_session, other_project.id, stranger.id)
    stranger_headers = await auth_header(db_session, stranger)
    foreign_id = await new_session(client, stranger_headers, other_project.id, name="Alheia")

    res = await client.get(f"{SN}/sessions/{foreign_id}", headers=headers)

    assert res.status_code == 403


async def test_an_unknown_session_is_not_found(client, facilitator):
    _user, _project, headers = facilitator

    res = await client.get(f"{SN}/sessions/does-not-exist", headers=headers)

    assert res.status_code == 404
