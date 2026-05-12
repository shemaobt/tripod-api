"""Tests for the UploadConfirmedPayload schema used by the Inngest worker."""

from app.inngest.schemas import UploadConfirmedPayload


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
