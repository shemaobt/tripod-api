"""Tests for the UploadConfirmedPayload schema and `verify_gcs_blob` used by
the Inngest worker."""

from unittest.mock import MagicMock, patch

import inngest
import pytest

from app.inngest.schemas import UploadConfirmedPayload
from app.inngest.upload_processing import verify_gcs_blob


def _base_kwargs() -> dict[str, str | int]:
    return {
        "recording_id": "rec-1",
        "expected_blob_path": "oral-collector/proj/genre/rec-1.wav",
        "expected_size_bytes": 1024,
    }


def test_payload_accepts_crc32c_only() -> None:
    payload = UploadConfirmedPayload(**_base_kwargs(), expected_crc32c="Nks/tw==")
    assert payload.expected_crc32c == "Nks/tw=="
    assert payload.expected_md5_hash is None


def test_payload_accepts_md5_only() -> None:
    """Backward compat: legacy clients only sending md5 still validate."""
    payload = UploadConfirmedPayload(**_base_kwargs(), expected_md5_hash="abc")
    assert payload.expected_md5_hash == "abc"
    assert payload.expected_crc32c is None


def test_payload_accepts_both_hashes() -> None:
    payload = UploadConfirmedPayload(
        **_base_kwargs(),
        expected_md5_hash="abc",
        expected_crc32c="Nks/tw==",
    )
    assert payload.expected_md5_hash == "abc"
    assert payload.expected_crc32c == "Nks/tw=="


def test_payload_optional_hashes_default_to_none() -> None:
    payload = UploadConfirmedPayload(**_base_kwargs())
    assert payload.expected_md5_hash is None
    assert payload.expected_crc32c is None


def test_payload_round_trips_through_model_dump() -> None:
    """Inngest sends `payload.model_dump()` over the wire — make sure the new
    field survives serialization/deserialization."""
    original = UploadConfirmedPayload(
        **_base_kwargs(),
        expected_crc32c="Nks/tw==",
    )
    rehydrated = UploadConfirmedPayload.model_validate(original.model_dump())
    assert rehydrated.expected_crc32c == "Nks/tw=="


def _make_blob_mock(
    *,
    exists: bool = True,
    size: int = 1024,
    crc32c: str | None = None,
    md5_hash: str | None = None,
) -> MagicMock:
    blob = MagicMock()
    blob.exists.return_value = exists
    blob.size = size
    blob.crc32c = crc32c
    blob.md5_hash = md5_hash
    return blob


def _patch_storage(blob: MagicMock):
    client = MagicMock()
    client.bucket.return_value.blob.return_value = blob
    return patch(
        "app.inngest.upload_processing.storage.Client", return_value=client
    )


def test_verify_blob_missing_raises() -> None:
    payload = UploadConfirmedPayload(**_base_kwargs())
    with (
        _patch_storage(_make_blob_mock(exists=False)),
        pytest.raises(inngest.NonRetriableError, match="does not exist"),
    ):
        verify_gcs_blob(payload)


def test_verify_blob_size_mismatch_raises() -> None:
    payload = UploadConfirmedPayload(**_base_kwargs())
    with (
        _patch_storage(_make_blob_mock(size=999)),
        pytest.raises(inngest.NonRetriableError, match="Size mismatch"),
    ):
        verify_gcs_blob(payload)


def test_verify_blob_size_match_returns_size() -> None:
    payload = UploadConfirmedPayload(**_base_kwargs())
    with _patch_storage(_make_blob_mock(size=1024)):
        result = verify_gcs_blob(payload)
    assert result.size == 1024


def test_verify_blob_crc32c_match_succeeds() -> None:
    payload = UploadConfirmedPayload(**_base_kwargs(), expected_crc32c="Nks/tw==")
    with _patch_storage(_make_blob_mock(crc32c="Nks/tw==")):
        result = verify_gcs_blob(payload)
    assert result.size == 1024


def test_verify_blob_crc32c_mismatch_raises() -> None:
    payload = UploadConfirmedPayload(**_base_kwargs(), expected_crc32c="Nks/tw==")
    with (
        _patch_storage(_make_blob_mock(crc32c="ZZZZZZ==")),
        pytest.raises(inngest.NonRetriableError, match="CRC32C mismatch"),
    ):
        verify_gcs_blob(payload)


def test_verify_blob_crc32c_skipped_when_gcs_missing() -> None:
    """If GCS does not return crc32c metadata, we skip the comparison rather
    than fail — preserves forward-compatibility."""
    payload = UploadConfirmedPayload(**_base_kwargs(), expected_crc32c="Nks/tw==")
    with _patch_storage(_make_blob_mock(crc32c=None)):
        result = verify_gcs_blob(payload)
    assert result.size == 1024


def test_verify_blob_crc32c_skipped_when_client_did_not_send() -> None:
    """When the client never sent a crc32c, the GCS-side value is ignored."""
    payload = UploadConfirmedPayload(**_base_kwargs())
    with _patch_storage(_make_blob_mock(crc32c="anything")):
        result = verify_gcs_blob(payload)
    assert result.size == 1024


def test_verify_blob_md5_match_succeeds() -> None:
    """Legacy MD5 path still works for old clients."""
    payload = UploadConfirmedPayload(
        **_base_kwargs(), expected_md5_hash="0cc175b9c0f1b6a831c399e269772661"
    )
    with _patch_storage(_make_blob_mock(md5_hash="DMF1ucDxtqgxw5niaXcmYQ==")):
        result = verify_gcs_blob(payload)
    assert result.size == 1024


def test_verify_blob_md5_mismatch_raises() -> None:
    payload = UploadConfirmedPayload(
        **_base_kwargs(), expected_md5_hash="ffffffffffffffffffffffffffffffff"
    )
    with (
        _patch_storage(_make_blob_mock(md5_hash="DMF1ucDxtqgxw5niaXcmYQ==")),
        pytest.raises(inngest.NonRetriableError, match="MD5 mismatch"),
    ):
        verify_gcs_blob(payload)


def test_verify_blob_both_hashes_validated() -> None:
    payload = UploadConfirmedPayload(
        **_base_kwargs(),
        expected_md5_hash="0cc175b9c0f1b6a831c399e269772661",
        expected_crc32c="Nks/tw==",
    )
    with _patch_storage(
        _make_blob_mock(md5_hash="DMF1ucDxtqgxw5niaXcmYQ==", crc32c="Nks/tw==")
    ):
        result = verify_gcs_blob(payload)
    assert result.size == 1024
