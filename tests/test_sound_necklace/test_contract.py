"""The emitted OpenAPI schema is what the SPA generates its TypeScript from, so it
has to tell the truth about which resources are real and which are still stubs.
"""

from __future__ import annotations

PREFIX = "/api/sound-necklace"
METHODS = {"get", "post", "put", "delete", "patch"}

# Implemented (ENG-260 sessions, ENG-261 audios). Everything else still answers 501.
IMPLEMENTED_OPERATIONS = {
    ("/sessions", "post"),
    ("/sessions", "get"),
    ("/sessions/{session_id}", "get"),
    ("/sessions/{session_id}/state", "get"),
    ("/sessions/{session_id}/state", "put"),
    ("/sessions/{session_id}/complete", "post"),
    ("/sessions/{session_id}/reopen", "post"),
    ("/projects/{project_id}/audios", "get"),
    ("/audios/{audio_id}/url", "get"),
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
