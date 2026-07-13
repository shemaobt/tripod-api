"""Sound Necklace (Colar de Sons) API surface, mounted at ``/api/colar``.

Every route is a contract stub returning 501; they exist so the emitted OpenAPI
carries the full contract for the SPA to generate its TypeScript types.
"""

from fastapi import APIRouter

from app.api.colar import artifacts, audios, lock, resources, sessions

router = APIRouter()

for _sub in (sessions, lock, audios, resources, artifacts):
    for route in _sub.router.routes:
        router.routes.append(route)
