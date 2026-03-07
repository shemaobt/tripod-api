from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError
from app.db.models.book_context import BCDApproval, BCDStatus, BookContextDocument
from app.services.book_context.get_bcd import get_bcd_or_404

SPECIALIST_ROLES = {"exegete", "biblical_language_specialist", "translation_specialist"}
APPROVE_CAPABLE = {"admin", "facilitator", *SPECIALIST_ROLES}


async def approve_bcd(
    db: AsyncSession,
    bcd_id: str,
    user_id: str,
    user_roles: list[str],
) -> BookContextDocument:
    """Approve a BCD using multi-specialist workflow."""
    capable_roles = [r for r in user_roles if r in APPROVE_CAPABLE]
    if not capable_roles:
        raise AuthorizationError(
            "You need an admin, facilitator, or specialist role to approve."
        )

    bcd = await get_bcd_or_404(db, bcd_id)

    if bcd.status not in (BCDStatus.DRAFT, BCDStatus.REVIEW):
        if bcd.status == BCDStatus.APPROVED:
            raise ConflictError("This document is already approved.")
        raise ConflictError("Only draft or in-review documents can be approved.")

    existing = await db.execute(
        select(BCDApproval).where(BCDApproval.bcd_id == bcd_id)
    )
    approvals = list(existing.scalars().all())

    if any(a.user_id == user_id for a in approvals):
        raise ConflictError("You have already approved this document.")

    approval = BCDApproval(
        bcd_id=bcd_id,
        user_id=user_id,
        role_at_approval=capable_roles[0],
        roles_at_approval=capable_roles,
    )
    db.add(approval)

    is_admin = "admin" in capable_roles
    has_prior_admin = any(
        "admin" in (a.roles_at_approval or [a.role_at_approval])
        for a in approvals
    )

    if is_admin or has_prior_admin:
        bcd.status = BCDStatus.APPROVED
    else:
        all_approvals = [*approvals, approval]
        distinct_users = len({a.user_id for a in all_approvals})

        covered_specialties = set()
        for a in all_approvals:
            roles = a.roles_at_approval or [a.role_at_approval]
            covered_specialties.update(r for r in roles if r in SPECIALIST_ROLES)

        if distinct_users >= 2 and len(covered_specialties) >= 2:
            bcd.status = BCDStatus.APPROVED
        else:
            bcd.status = BCDStatus.REVIEW

    if bcd.status == BCDStatus.APPROVED:
        has_active = await db.execute(
            select(BookContextDocument.id)
            .where(
                BookContextDocument.book_id == bcd.book_id,
                BookContextDocument.is_active == True,
            )
            .limit(1)
        )
        if has_active.scalar_one_or_none() is None:
            bcd.is_active = True

    await db.commit()
    await db.refresh(bcd)
    return bcd
