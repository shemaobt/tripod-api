"""Sound Necklace API surface, mounted at ``/api/sound-necklace``.

Every resource is implemented: sessions, the audio bucket, the artifacts, the
voice-answer resources and the advisory editor lock. Nothing here answers 501 any
more, so nothing declares it.
"""

from fastapi import APIRouter

from app.api.sound_necklace import artifacts, audios, lock, resources, sessions

router = APIRouter()
router.include_router(sessions.router)
router.include_router(audios.router)
router.include_router(artifacts.router)
router.include_router(resources.router)
router.include_router(lock.router)
