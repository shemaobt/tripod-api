from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User
from app.db.models.book_context import BCDApproval
from app.services.book_context.approve_bcd import SPECIALIST_ROLES


async def get_approval_status(db: AsyncSession, bcd_id: str) -> dict:
    """Return the current approval progress for a BCD."""
    result = await db.execute(select(BCDApproval).where(BCDApproval.bcd_id == bcd_id))
    approvals = list(result.scalars().all())

    user_ids = {a.user_id for a in approvals}
    user_names: dict[str, str] = {}
    if user_ids:
        users_result = await db.execute(
            select(User.id, User.display_name, User.email).where(User.id.in_(user_ids))
        )
        for uid, display_name, email in users_result:
            user_names[uid] = display_name or email.split("@")[0]

    approval_entries = []
    covered = set()
    for a in approvals:
        roles = a.roles_at_approval or [a.role_at_approval]
        specialties = [r for r in roles if r in SPECIALIST_ROLES]
        covered.update(specialties)
        approval_entries.append(
            {
                "id": a.id,
                "user_id": a.user_id,
                "user_name": user_names.get(a.user_id, "Unknown"),
                "role_at_approval": a.role_at_approval,
                "roles_at_approval": roles,
                "approved_at": a.approved_at.isoformat() if a.approved_at else None,
            }
        )

    missing = sorted(SPECIALIST_ROLES - covered)
    distinct_users = len({a.user_id for a in approvals})

    return {
        "approvals": approval_entries,
        "covered_specialties": sorted(covered),
        "missing_specialties": missing,
        "distinct_reviewers": distinct_users,
        "is_complete": distinct_users >= 2 and len(covered) >= 2,
    }
