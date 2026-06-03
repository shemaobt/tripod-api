"""GCS configuration for annotation-studio audio + export bundles.

Reuses the same GCP project/bucket as oral-collector, isolated under the
``annotation-studio/`` key prefix so the two apps never collide. Storage keys
persisted in the DB are the *logical* keys built by ``naming.py`` (e.g.
``ter/tier_a/raw/<id>.wav``); the storage adapter prepends the prefix when it
talks to GCS, keeping ``naming.py`` a pure reflection of the in-zip layout.
"""

GCS_AS_BUCKET = "tripod-image-uploads"
GCS_AS_PROJECT = "gen-lang-client-0886209230"
AS_BLOB_PREFIX = "annotation-studio"

SIGNED_PUT_EXPIRY_SECONDS = 600
SIGNED_GET_EXPIRY_SECONDS = 3600
