from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, RoleError
from app.db.models.auth import AccessRequest, App, User
from app.services.authorization.assign_role import assign_role


async def review_access_request(
    db: AsyncSession,
    actor: User,
    request_id: str,
    status: str,
    reason: str | None = None,
) -> AccessRequest:

    if status not in ("approved", "rejected"):
        raise RoleError("Status must be 'approved' or 'rejected'")

    stmt: Select[tuple[AccessRequest]] = select(AccessRequest).where(AccessRequest.id == request_id)
    result = await db.execute(stmt)
    request = result.scalar_one_or_none()
    if not request:
        raise NotFoundError("Access request not found")

    if request.status != "pending":
        raise RoleError(f"Request already {request.status}")

    request.status = status
    request.reviewed_by = actor.id
    request.reviewed_at = datetime.now(UTC)
    request.review_reason = reason

    if status == "approved":
        app_stmt: Select[tuple[App]] = select(App).where(App.id == request.app_id)
        app_result = await db.execute(app_stmt)
        app = app_result.scalar_one()

        await assign_role(db, actor, request.user_id, app.app_key, "analyst")
    else:
        await db.commit()
        await db.refresh(request)

    return request
