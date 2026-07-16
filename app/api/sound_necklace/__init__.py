"""Sound Necklace API surface, mounted at ``/api/sound-necklace``.

Sessions are implemented. The remaining resources are still contract stubs
returning 501; they exist so the emitted OpenAPI carries the full contract for the
SPA to generate its TypeScript types. The 501 is declared on the stubs only — a
blanket declaration would keep advertising it for routes that now answer for real.
"""

from typing import Any

from fastapi import APIRouter, status

from app.api.sound_necklace import artifacts, audios, lock, resources, sessions

STUB_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_501_NOT_IMPLEMENTED: {"description": "Not implemented yet"}
}

router = APIRouter()
router.include_router(sessions.router)

for _sub in (lock, audios, resources, artifacts):
    router.include_router(_sub.router, responses=STUB_RESPONSES)
