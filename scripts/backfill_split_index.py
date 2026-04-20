"""One-shot backfill for split_index and split_segment_count on existing split children.

For each group of siblings (rows sharing a non-null split_from_id) that has any row
with a NULL split_index, assigns split_index in created_at+id order and sets
split_segment_count to the group size.

Safe to re-run — groups that are already fully populated are skipped.
"""

import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.db.models.oc_recording import OC_Recording


async def main() -> None:
    async with AsyncSessionLocal() as db:
        parent_ids_stmt = (
            select(OC_Recording.split_from_id)
            .where(OC_Recording.split_from_id.is_not(None))
            .distinct()
        )
        parent_ids_result = await db.execute(parent_ids_stmt)
        parent_ids = [row for row in parent_ids_result.scalars().all() if row]

        total_updated = 0
        total_groups = 0

        for parent_id in parent_ids:
            siblings_stmt = (
                select(OC_Recording)
                .where(OC_Recording.split_from_id == parent_id)
                .order_by(OC_Recording.created_at, OC_Recording.id)
            )
            siblings_result = await db.execute(siblings_stmt)
            siblings = list(siblings_result.scalars().all())

            if not siblings:
                continue

            needs_backfill = any(
                s.split_index is None or s.split_segment_count is None for s in siblings
            )
            if not needs_backfill:
                continue

            total_groups += 1
            segment_count = len(siblings)
            for i, sibling in enumerate(siblings):
                sibling.split_index = i
                sibling.split_segment_count = segment_count
                total_updated += 1

            await db.commit()
            print(f"Group {parent_id}: {segment_count} siblings backfilled")

        print(f"\nDone. Updated {total_updated} rows across {total_groups} split groups.")


if __name__ == "__main__":
    asyncio.run(main())
