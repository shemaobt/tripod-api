"""The emitted OpenAPI schema is what the SPA generates its TypeScript from, so
the stub reality — every route answers 501 — has to be visible in the contract,
not just in the code.
"""

from __future__ import annotations

PREFIX = "/api/sound-necklace"
METHODS = {"get", "post", "put", "delete", "patch"}


def _operations() -> list[tuple[str, str, dict]]:
    from app.main import app

    schema = app.openapi()
    return [
        (path, method, operation)
        for path, item in schema["paths"].items()
        if path.startswith(PREFIX)
        for method, operation in item.items()
        if method in METHODS
    ]


def test_every_route_advertises_501():
    operations = _operations()
    assert operations, "no sound-necklace operations in the schema"
    missing = [
        f"{method.upper()} {path}"
        for path, method, operation in operations
        if "501" not in operation["responses"]
    ]
    assert not missing, f"operations that hide their stub status: {missing}"


def test_artifact_download_declares_a_redirect_not_an_empty_body():
    """Bytes are served by storage, never proxied — the schema must say redirect."""
    operations = {(path, method): operation for path, method, operation in _operations()}
    download = operations[(f"{PREFIX}/sessions/{{session_id}}/artifacts/{{kind}}", "get")]
    assert "307" in download["responses"]
    assert "200" not in download["responses"]


def test_artifact_upload_takes_raw_multipart_bytes():
    """A JSON body would put the payload through a parser — §10.5 forbids that."""
    operations = {(path, method): operation for path, method, operation in _operations()}
    upload = operations[(f"{PREFIX}/sessions/{{session_id}}/artifacts", "post")]
    assert list(upload["requestBody"]["content"]) == ["multipart/form-data"]
