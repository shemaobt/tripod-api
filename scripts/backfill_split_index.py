"""One-shot backfill for split_index and split_segment_count on existing split children.

Delegates to app.services.oral_collector.split_service.backfill_split_indices so the
logic is covered by the backend test suite. Safe to re-run — already-populated groups
are skipped.
"""

import asyncio

from app.core.database import AsyncSessionLocal
from app.services.oral_collector.split_service import backfill_split_indices


async def main() -> None:
    async with AsyncSessionLocal() as db:
        total_updated, total_groups = await backfill_split_indices(db)
        print(f"Done. Updated {total_updated} rows across {total_groups} split groups.")


if __name__ == "__main__":
    asyncio.run(main())
