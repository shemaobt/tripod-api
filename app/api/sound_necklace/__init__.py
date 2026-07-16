"""Sound Necklace API surface, mounted at ``/api/sound-necklace``.

Every route is a contract stub returning 501; they exist so the emitted OpenAPI
carries the full contract for the SPA to generate its TypeScript types.
"""

from fastapi import APIRouter

from app.api.sound_necklace import artifacts, audios, lock, resources, sessions

router = APIRouter()

for _sub in (sessions, lock, audios, resources, artifacts):
    for route in _sub.router.routes:
        router.routes.append(route)
