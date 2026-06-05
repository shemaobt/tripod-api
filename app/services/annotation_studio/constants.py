"""GCS configuration for annotation-studio audio + export bundles.

A dedicated bucket (separate from oral-collector's ``tripod-image-uploads``)
so the experiment's audio is isolated and its CORS is managed independently.
Storage keys are the *logical* keys built by ``naming.py`` (e.g.
``ter/tier_a/raw/<id>.wav``) and are used verbatim as object names.
"""

GCS_AS_BUCKET = "annotation-studio-audio"
GCS_AS_PROJECT = "gen-lang-client-0886209230"

SIGNED_PUT_EXPIRY_SECONDS = 600
SIGNED_GET_EXPIRY_SECONDS = 3600
