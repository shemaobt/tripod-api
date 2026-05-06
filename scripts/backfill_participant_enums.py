"""One-shot backfill for participant_register enum normalization on existing BCDs.

Delegates to app.services.book_context.participant_backfill.backfill_participant_enums.
Idempotent — already-normalized participants are skipped. Pass --dry-run to preview
without persisting.
"""

import argparse
import asyncio

from app.core.database import AsyncSessionLocal
from app.services.book_context.participant_backfill import backfill_participant_enums


async def main(dry_run: bool) -> None:
    async with AsyncSessionLocal() as db:
        rows_updated, docs_visited = await backfill_participant_enums(db, dry_run=dry_run)
        prefix = "[dry-run] Would update" if dry_run else "Done. Updated"
        print(f"{prefix} {rows_updated} rows across {docs_visited} docs.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without persisting.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
