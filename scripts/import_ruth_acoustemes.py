"""Import the Terena "ruth" acousteme corpus into the backend for Beads.

Reads the corpus JSON produced by
``tripod-lab/backend/scripts/tokenize_ruth_pilot.py`` (keyed by audio basename
-> {units, timestamps, duration_sec, num_frames, source_object}), converts each
per-frame ``units`` array into RLE ``segments`` (what the Beads frontend
consumes), and stores one acousteme artifact per audio via
``acousteme_service.store_artifact`` — gzipping + uploading the stream to the
terena-pilot bucket and upserting the pointer row.

    uv run python scripts/import_ruth_acoustemes.py \
        --corpus gs://terena-pilot/acoustemes-raw/ruth_corpus.json

The audios themselves are already in gs://terena-pilot/ruth/; this only writes
the acousteme streams + DB rows. After it runs, Beads can consume the pilot via
GET /api/oc/acoustemes?collection=terena-ruth.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import unicodedata
from typing import Any

from google.cloud import storage

from app.core.database import AsyncSessionLocal
from app.services.oral_collector import acousteme_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("import_ruth_acoustemes")

CODEBOOK_VERSION = "terena-xlsr53-k100-v1"
COLLECTION = "terena-ruth"
AUDIO_BUCKET = "terena-pilot"
HOP_SEC = acousteme_service.ACOUSTEME_HOP_SEC


def slugify(name: str, prefix: str = "ruth") -> str:
    """Stable ascii slug for an audio basename (handles spaces/accents)."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    ascii_name = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_name).strip("-").lower()
    return f"{prefix}-{ascii_name}" if ascii_name else prefix


def units_to_segments(units: list[int], duration_sec: float | None) -> list[dict[str, Any]]:
    """RLE-encode per-frame unit ids into contiguous {start, end, unit_id} runs.

    Frame duration is derived from the audio length (duration / num_frames) so
    the last segment ends exactly at duration_sec — no end-of-file drift when
    Beads seeks the audio. Falls back to the fixed 20 ms hop if duration is
    unknown.
    """
    segments: list[dict[str, Any]] = []
    if not units:
        return segments
    dt = (duration_sec / len(units)) if duration_sec else HOP_SEC
    run_start = 0
    for i in range(1, len(units) + 1):
        if i == len(units) or units[i] != units[run_start]:
            segments.append(
                {
                    "start": round(run_start * dt, 4),
                    "end": round(i * dt, 4),
                    "unit_id": int(units[run_start]),
                }
            )
            run_start = i
    return segments


def load_corpus(corpus_uri: str) -> dict[str, Any]:
    if corpus_uri.startswith("gs://"):
        bucket_name, obj = corpus_uri[len("gs://") :].split("/", 1)
        data = storage.Client().bucket(bucket_name).blob(obj).download_as_bytes()
        corpus: dict[str, Any] = json.loads(data)
        return corpus
    with open(corpus_uri) as f:
        loaded: dict[str, Any] = json.load(f)
        return loaded


async def import_corpus(corpus_uri: str, dry_run: bool, limit: int | None) -> None:
    corpus = load_corpus(corpus_uri)
    entries = list(corpus.items())
    if limit is not None:
        entries = entries[:limit]
    logger.info("Loaded %d corpus entries from %s", len(entries), corpus_uri)

    async with AsyncSessionLocal() as db:
        for name, entry in entries:
            audio_id = slugify(name)
            segments = units_to_segments(entry.get("units") or [], entry.get("duration_sec"))
            audio_object = entry.get("source_object") or f"ruth/{name}.mp3"
            stream = {
                "duration_sec": entry.get("duration_sec"),
                "num_frames": entry.get("num_frames"),
                "segments": segments,
            }
            logger.info(
                "%s -> %s (%d frames, %d segments)%s",
                name,
                audio_id,
                entry.get("num_frames") or 0,
                len(segments),
                " [dry-run]" if dry_run else "",
            )
            if dry_run:
                continue
            await acousteme_service.store_artifact(
                db,
                audio_id=audio_id,
                codebook_version=CODEBOOK_VERSION,
                stream=stream,
                bucket=AUDIO_BUCKET,
                audio_bucket=AUDIO_BUCKET,
                audio_object=audio_object,
                title=name,
                collection=COLLECTION,
            )
    logger.info("Done (%d entries)", len(entries))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus",
        default="gs://terena-pilot/acoustemes-raw/ruth_corpus.json",
        help="Corpus JSON URI (gs:// or local path)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Log only; no uploads/DB writes")
    parser.add_argument("--limit", type=int, default=None, help="Only import the first N entries")
    args = parser.parse_args()
    asyncio.run(import_corpus(args.corpus, args.dry_run, args.limit))


if __name__ == "__main__":
    main()
