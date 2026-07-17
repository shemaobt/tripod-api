"""The emitted OpenAPI schema is what the SPA generates its TypeScript from, so it
has to tell the truth about which resources are real and which are still stubs.
"""

from __future__ import annotations

PREFIX = "/api/sound-necklace"
METHODS = {"get", "post", "put", "delete", "patch"}

# Implemented (ENG-260 sessions, ENG-261 audios, ENG-263 artifacts, ENG-264 resources,
# ENG-262 lock). Nothing answers 501 any more; the set is kept because the check runs
# both ways and a future stub must still be caught.
IMPLEMENTED_OPERATIONS = {
    ("/sessions/{session_id}/lock", "put"),
    ("/sessions/{session_id}/lock", "get"),
    ("/sessions/{session_id}/lock", "delete"),
    ("/sessions", "post"),
    ("/sessions", "get"),
    ("/sessions/{session_id}", "get"),
    ("/sessions/{session_id}/state", "get"),
    ("/sessions/{session_id}/state", "put"),
    ("/sessions/{session_id}/complete", "post"),
    ("/sessions/{session_id}/reopen", "post"),
    ("/projects/{project_id}/audios", "get"),
    ("/audios/{audio_id}/url", "get"),
    ("/sessions/{session_id}/artifacts", "post"),
    ("/sessions/{session_id}/artifacts/{kind}", "get"),
    ("/sessions/{session_id}/resources", "put"),
    ("/sessions/{session_id}/resources", "get"),
    ("/sessions/{session_id}/resources", "delete"),
    ("/sessions/{session_id}/resources/url", "get"),
}


def _operations() -> list[tuple[str, str, dict]]:
    from app.main import app

    schema = app.openapi()
    return [
        (path.removeprefix(PREFIX), method, operation)
        for path, item in schema["paths"].items()
        if path.startswith(PREFIX)
        for method, operation in item.items()
        if method in METHODS
    ]


def test_the_implemented_routes_are_in_the_schema():
    operations = {(path, method) for path, method, _ in _operations()}
    assert operations >= IMPLEMENTED_OPERATIONS, f"missing: {IMPLEMENTED_OPERATIONS - operations}"


def test_only_the_unimplemented_routes_advertise_501():
    """A 501 on a route that now answers for real is a lie the SPA would generate from."""
    operations = _operations()
    assert operations, "no sound-necklace operations in the schema"

    lying = [
        f"{method.upper()} {path}"
        for path, method, operation in operations
        if (path, method) in IMPLEMENTED_OPERATIONS and "501" in operation["responses"]
    ]
    hiding = [
        f"{method.upper()} {path}"
        for path, method, operation in operations
        if (path, method) not in IMPLEMENTED_OPERATIONS and "501" not in operation["responses"]
    ]

    assert not lying, f"implemented operations still advertising 501: {lying}"
    assert not hiding, f"stub operations hiding their status: {hiding}"


def test_the_autosave_advertises_its_conflict():
    """The version guard is part of the contract: a loser must know 409 can happen."""
    operations = {(path, method): op for path, method, op in _operations()}
    autosave = operations[("/sessions/{session_id}/state", "put")]
    assert "409" in autosave["responses"]


def test_the_lock_status_carries_exactly_the_three_keys_the_spa_parses():
    """The SPA reads this under z.strictObject: a fourth key throws on the client.

    The throw is swallowed by the app shell's catch, which also skips wiring autosave —
    so an extra field here costs the user their session silently. The fencing counter is
    deliberately server-side only for this reason; if it ever needs to be on the wire,
    the SPA's contract has to change first.
    """
    from app.main import app

    schemas = app.openapi()["components"]["schemas"]
    assert set(schemas["LockStatusResponse"]["properties"]) == {"held", "holder", "expires_at"}
    # LockHolder is nested inside it and parsed just as strictly.
    assert set(schemas["LockHolder"]["properties"]) == {"user_id", "display_name"}


def test_every_fenced_write_advertises_the_lock_conflict_it_can_raise():
    """A tab that lost the lease learns it from the schema, not from production."""
    operations = {(path, method): op for path, method, op in _operations()}
    fenced = [
        ("/sessions/{session_id}/state", "put"),
        ("/sessions/{session_id}/complete", "post"),
        ("/sessions/{session_id}/reopen", "post"),
        ("/sessions/{session_id}/artifacts", "post"),
    ]
    silent = [f"{m.upper()} {p}" for p, m in fenced if "409" not in operations[(p, m)]["responses"]]
    assert not silent, f"fenced writes not advertising their 409: {silent}"


def test_artifact_download_declares_a_redirect_not_an_empty_body():
    """Bytes are served by storage, never proxied — the schema must say redirect."""
    operations = {(path, method): operation for path, method, operation in _operations()}
    download = operations[("/sessions/{session_id}/artifacts/{kind}", "get")]
    assert "307" in download["responses"]
    assert "200" not in download["responses"]


def test_artifact_upload_takes_raw_multipart_bytes():
    """A JSON body would put the payload through a parser — §10.5 forbids that."""
    operations = {(path, method): operation for path, method, operation in _operations()}
    upload = operations[("/sessions/{session_id}/artifacts", "post")]
    assert list(upload["requestBody"]["content"]) == ["multipart/form-data"]
