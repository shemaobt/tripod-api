from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User
from app.db.models.language import Language
from app.db.models.oc_genre import OC_Genre, OC_Subcategory
from app.db.models.oc_project_user import OC_ProjectUser
from app.db.models.oc_recording import OC_Recording
from app.db.models.project import Project


async def get_genre_stats(db: AsyncSession, project_id: str) -> dict:
    """Return recording count and duration per genre and subcategory for a project."""

    # Genre-level aggregation
    genre_stmt = (
        select(
            OC_Recording.genre_id,
            OC_Genre.name.label("genre_name"),
            func.count(OC_Recording.id).label("recording_count"),
            func.coalesce(func.sum(OC_Recording.duration_seconds), 0.0).label(
                "duration_seconds"
            ),
        )
        .join(OC_Genre, OC_Genre.id == OC_Recording.genre_id)
        .where(OC_Recording.project_id == project_id)
        .where(OC_Recording.upload_status == "uploaded")
        .group_by(OC_Recording.genre_id, OC_Genre.name)
        .order_by(OC_Genre.name)
    )
    genre_result = await db.execute(genre_stmt)
    genres = [
        {
            "genre_id": row.genre_id,
            "genre_name": row.genre_name,
            "recording_count": row.recording_count,
            "duration_seconds": float(row.duration_seconds),
        }
        for row in genre_result.all()
    ]

    # Subcategory-level aggregation
    sub_stmt = (
        select(
            OC_Recording.subcategory_id,
            OC_Subcategory.name.label("subcategory_name"),
            OC_Recording.genre_id,
            func.count(OC_Recording.id).label("recording_count"),
            func.coalesce(func.sum(OC_Recording.duration_seconds), 0.0).label(
                "duration_seconds"
            ),
        )
        .join(OC_Subcategory, OC_Subcategory.id == OC_Recording.subcategory_id)
        .where(OC_Recording.project_id == project_id)
        .where(OC_Recording.upload_status == "uploaded")
        .group_by(
            OC_Recording.subcategory_id,
            OC_Subcategory.name,
            OC_Recording.genre_id,
        )
        .order_by(OC_Subcategory.name)
    )
    sub_result = await db.execute(sub_stmt)
    subcategories = [
        {
            "subcategory_id": row.subcategory_id,
            "subcategory_name": row.subcategory_name,
            "genre_id": row.genre_id,
            "recording_count": row.recording_count,
            "duration_seconds": float(row.duration_seconds),
        }
        for row in sub_result.all()
    ]

    return {
        "project_id": project_id,
        "genres": genres,
        "subcategories": subcategories,
    }


async def get_admin_stats(db: AsyncSession) -> dict:
    """Return system-wide totals: project count, language count, total hours, active users."""

    # Count projects that have OC recordings
    project_count_stmt = select(
        func.count(func.distinct(OC_Recording.project_id))
    )
    project_result = await db.execute(project_count_stmt)
    total_projects = project_result.scalar_one()

    # Count distinct languages across OC projects
    language_count_stmt = (
        select(func.count(func.distinct(Project.language_id)))
        .select_from(Project)
        .join(OC_ProjectUser, OC_ProjectUser.project_id == Project.id)
    )
    language_result = await db.execute(language_count_stmt)
    total_languages = language_result.scalar_one()

    # Total hours of recordings
    hours_stmt = select(
        func.coalesce(func.sum(OC_Recording.duration_seconds), 0.0)
    )
    hours_result = await db.execute(hours_stmt)
    total_seconds = float(hours_result.scalar_one())
    total_hours = total_seconds / 3600.0

    # Active users (distinct users who are OC project members)
    users_stmt = select(func.count(func.distinct(OC_ProjectUser.user_id)))
    users_result = await db.execute(users_stmt)
    active_users = users_result.scalar_one()

    return {
        "total_projects": total_projects,
        "total_languages": total_languages,
        "total_hours": round(total_hours, 2),
        "active_users": active_users,
    }
