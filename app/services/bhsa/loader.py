from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.services.bhsa.passage import extract_passage

logger = logging.getLogger(__name__)

_tf_api: Any = None
_is_loaded: bool = False
_is_loading: bool = False
_message: str = "Not loaded"


def get_status() -> dict[str, Any]:
    return {
        "is_loaded": _is_loaded,
        "is_loading": _is_loading,
        "message": _message,
    }


def load(*, settings: Settings | None = None, force: bool = False) -> None:
    from tf.app import use

    global _tf_api, _is_loaded, _is_loading, _message

    if _is_loaded and not force:
        _message = "Data already loaded"
        return

    if _is_loading:
        return

    _is_loading = True
    settings = settings or get_settings()

    try:
        _message = "Initializing BHSA data load..."

        bucket = settings.gcs_bucket_name
        if bucket:
            _download_from_gcs(bucket)

        data_path = settings.bhsa_data_path
        if data_path:
            _message = f"Loading Text-Fabric from {data_path}..."
            _tf_api = use(data_path, silent=False)
        else:
            _message = "Loading Text-Fabric (ETCBC/bhsa)..."
            _tf_api = use("ETCBC/bhsa", silent=False)

        _is_loaded = True
        _message = "BHSA Data Ready"
    except Exception as exc:
        _message = f"Error loading data: {exc}"
        raise RuntimeError(f"Failed to load BHSA: {exc}") from exc
    finally:
        _is_loading = False


def _download_from_gcs(bucket_name: str) -> None:
    global _message

    try:
        from google.cloud import storage  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("google-cloud-storage not installed, skipping GCS")
        return

    tf_data_dir = Path(os.path.expanduser("~/text-fabric-data"))
    github_dir = tf_data_dir / "github"

    if github_dir.exists():
        logger.info("Local BHSA data found at %s, skipping download", github_dir)
        return

    _message = f"Downloading from GCS ({bucket_name})..."
    tf_data_dir.mkdir(parents=True, exist_ok=True)

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix="text-fabric-data/"))

    count = 0
    for blob in blobs:
        rel_path = blob.name.replace("text-fabric-data/", "", 1)
        if not rel_path or rel_path.endswith("/"):
            continue
        dest = tf_data_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(dest))
        count += 1
        if count % 50 == 0:
            _message = f"Downloading: {count}/{len(blobs)} files..."

    logger.info("Downloaded %d files from GCS", count)
    _message = "GCS download complete, initializing TF..."


def fetch_passage(ref: str) -> dict[str, Any]:
    if not _is_loaded or _tf_api is None:
        raise RuntimeError("BHSA not loaded — call /api/bhsa/load first")
    return extract_passage(_tf_api, ref)


def get_verse_counts(book: str) -> dict[int, int]:
    """Return {chapter_number: verse_count} for every chapter of *book*."""
    if not _is_loaded or _tf_api is None:
        raise RuntimeError("BHSA not loaded — call /api/bhsa/load first")

    from app.services.bhsa.reference import normalize_book_name

    bhsa_book = normalize_book_name(book)
    T = _tf_api.api.T
    L = _tf_api.api.L
    F = _tf_api.api.F

    counts: dict[int, int] = {}
    for node in F.otype.s("book"):
        if T.sectionFromNode(node)[0] == bhsa_book:
            for ch_node in L.d(node, otype="chapter"):
                ch_num = T.sectionFromNode(ch_node)[1]
                verse_count = len(L.d(ch_node, otype="verse"))
                counts[ch_num] = verse_count
            break
    return counts
