from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UploadStatus
from app.core.exceptions import AuthorizationError, NotFoundError
from app.db.models.oc_genre import OC_Genre, OC_Subcategory
from app.db.models.oc_recording import OC_Recording
from app.db.models.project import ProjectUserAccess
from app.models.oc_recording import (
    ConfirmUploadRequest,
    RecordingCreate,
    RecordingUpdate,
    ResumableUploadUrlRequest,
    ResumableUploadUrlResponse,
)
from tests.baker import make_language, make_project, make_user

pytest.importorskip("app.inngest")


async def _seed_genre(db: AsyncSession) -> tuple[OC_Genre, OC_Subcategory]:
    genre = OC_Genre(name="narrative", sort_order=0)
    db.add(genre)
    await db.flush()

    sub = OC_Subcategory(genre_id=genre.id, name="folktale", sort_order=0)
    db.add(sub)
    await db.commit()
    await db.refresh(genre)
    await db.refresh(sub)
    return genre, sub


async def _seed_project(db: AsyncSession) -> str:
    lang = await make_language(db)
    project = await make_project(db, lang.id)
    return project.id


async def _seed_recording(
    db: AsyncSession,
    user_id: str,
    project_id: str,
    genre_id: str,
    subcategory_id: str,
    *,
    upload_status: str = UploadStatus.LOCAL,
    file_size_bytes: int = 1024,
) -> OC_Recording:
    rec = OC_Recording(
        project_id=project_id,
        genre_id=genre_id,
        subcategory_id=subcategory_id,
        user_id=user_id,
        title="test recording",
        duration_seconds=10.0,
        file_size_bytes=file_size_bytes,
        format="m4a",
        upload_status=upload_status,
        recorded_at=datetime.now(UTC),
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec


def _import_service():
    from app.services.oral_collector import recording_service
    return recording_service


@pytest.mark.asyncio
async def test_create_recording(db_session: AsyncSession) -> None:
    rs = _import_service()
    user = await make_user(db_session)
    project_id = await _seed_project(db_session)
    genre, sub = await _seed_genre(db_session)

    data = RecordingCreate(
        project_id=project_id,
        genre_id=genre.id,
        subcategory_id=sub.id,
        title="My Recording",
        duration_seconds=30.5,
        file_size_bytes=2048,
        format="m4a",
        recorded_at=datetime.now(UTC),
    )
    rec = await rs.create_recording(db_session, data, user.id)

    assert rec.id is not None
    assert rec.project_id == project_id
    assert rec.user_id == user.id
    assert rec.title == "My Recording"
    assert rec.duration_seconds == 30.5
    assert rec.file_size_bytes == 2048
    assert rec.format == "m4a"
    assert rec.upload_status == UploadStatus.LOCAL


@pytest.mark.asyncio
async def test_get_recording(db_session: AsyncSession) -> None:
    rs = _import_service()
    user = await make_user(db_session)
    project_id = await _seed_project(db_session)
    genre, sub = await _seed_genre(db_session)

    rec = await _seed_recording(db_session, user.id, project_id, genre.id, sub.id)
    fetched = await rs.get_recording(db_session, rec.id)

    assert fetched.id == rec.id
    assert fetched.title == "test recording"


@pytest.mark.asyncio
async def test_get_recording_not_found(db_session: AsyncSession) -> None:
    rs = _import_service()
    with pytest.raises(NotFoundError):
        await rs.get_recording(db_session, "nonexistent-id")


@pytest.mark.asyncio
async def test_update_recording(db_session: AsyncSession) -> None:
    rs = _import_service()
    user = await make_user(db_session)
    project_id = await _seed_project(db_session)
    genre, sub = await _seed_genre(db_session)

    rec = await _seed_recording(db_session, user.id, project_id, genre.id, sub.id)
    updated = await rs.update_recording(
        db_session, rec.id, RecordingUpdate(title="Updated Title")
    )

    assert updated.title == "Updated Title"


@pytest.mark.asyncio
async def test_delete_recording(db_session: AsyncSession) -> None:
    rs = _import_service()
    user = await make_user(db_session)
    project_id = await _seed_project(db_session)
    genre, sub = await _seed_genre(db_session)

    rec = await _seed_recording(db_session, user.id, project_id, genre.id, sub.id)
    await rs.delete_recording(db_session, rec.id)

    with pytest.raises(NotFoundError):
        await rs.get_recording(db_session, rec.id)


@pytest.mark.asyncio
async def test_list_recordings(db_session: AsyncSession) -> None:
    rs = _import_service()
    user = await make_user(db_session)
    project_id = await _seed_project(db_session)
    genre, sub = await _seed_genre(db_session)

    await _seed_recording(
        db_session, user.id, project_id, genre.id, sub.id,
        upload_status=UploadStatus.UPLOADED,
    )
    await _seed_recording(
        db_session, user.id, project_id, genre.id, sub.id,
        upload_status=UploadStatus.VERIFIED,
    )

    recordings = await rs.list_recordings(db_session, project_id)
    assert len(recordings) == 2


@pytest.mark.asyncio
async def test_list_recordings_filter_by_status(db_session: AsyncSession) -> None:
    rs = _import_service()
    user = await make_user(db_session)
    project_id = await _seed_project(db_session)
    genre, sub = await _seed_genre(db_session)

    await _seed_recording(
        db_session, user.id, project_id, genre.id, sub.id,
        upload_status=UploadStatus.UPLOADED,
    )
    await _seed_recording(
        db_session, user.id, project_id, genre.id, sub.id,
        upload_status=UploadStatus.LOCAL,
    )

    uploaded = await rs.list_recordings(
        db_session, project_id, upload_status=UploadStatus.UPLOADED
    )
    assert len(uploaded) == 1
    assert uploaded[0].upload_status == UploadStatus.UPLOADED


@pytest.mark.asyncio
async def test_check_recording_access_owner(db_session: AsyncSession) -> None:
    rs = _import_service()
    user = await make_user(db_session)
    project_id = await _seed_project(db_session)
    genre, sub = await _seed_genre(db_session)

    rec = await _seed_recording(db_session, user.id, project_id, genre.id, sub.id)
    await rs.check_recording_access(db_session, rec, user.id)


@pytest.mark.asyncio
async def test_check_recording_access_denied(db_session: AsyncSession) -> None:
    rs = _import_service()
    user = await make_user(db_session, email="owner@test.com")
    other = await make_user(db_session, email="other@test.com")
    project_id = await _seed_project(db_session)
    genre, sub = await _seed_genre(db_session)

    rec = await _seed_recording(db_session, user.id, project_id, genre.id, sub.id)
    with pytest.raises(AuthorizationError):
        await rs.check_recording_access(db_session, rec, other.id)


@pytest.mark.asyncio
async def test_check_recording_access_manager(db_session: AsyncSession) -> None:
    rs = _import_service()
    user = await make_user(db_session, email="owner@test.com")
    manager = await make_user(db_session, email="manager@test.com")
    project_id = await _seed_project(db_session)
    genre, sub = await _seed_genre(db_session)

    access = ProjectUserAccess(project_id=project_id, user_id=manager.id, role="manager")
    db_session.add(access)
    await db_session.commit()

    rec = await _seed_recording(db_session, user.id, project_id, genre.id, sub.id)
    await rs.check_recording_access(db_session, rec, manager.id)


def test_gcs_blob_path() -> None:
    rs = _import_service()
    path = rs._gcs_blob_path("proj-1", "genre-1", "rec-1", "m4a")
    assert path == "oral-collector/proj-1/genre-1/rec-1.m4a"


def test_gcs_blob_path_wav() -> None:
    rs = _import_service()
    path = rs._gcs_blob_path("proj-1", "genre-1", "rec-1", "wav")
    assert path == "oral-collector/proj-1/genre-1/rec-1.wav"


def test_confirm_upload_request_model() -> None:
    req = ConfirmUploadRequest(md5_hash="abc123")
    assert req.md5_hash == "abc123"

    req_none = ConfirmUploadRequest()
    assert req_none.md5_hash is None


def test_resumable_upload_url_request_model() -> None:
    req = ResumableUploadUrlRequest(recording_id="rec-1", format="m4a")
    assert req.recording_id == "rec-1"
    assert req.format == "m4a"


def test_resumable_upload_url_response_model() -> None:
    resp = ResumableUploadUrlResponse(
        recording_id="rec-1",
        session_uri="https://example.com/upload",
        chunk_size_bytes=8388608,
        content_type="audio/mp4",
    )
    assert resp.session_uri == "https://example.com/upload"
    assert resp.chunk_size_bytes == 8388608
