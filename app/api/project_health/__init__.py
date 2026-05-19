from fastapi import APIRouter

from app.api.project_health import admin, interviews, prompts, reports, voice

router = APIRouter()

for _sub in (interviews, reports, admin, prompts, voice):
    for route in _sub.router.routes:
        router.routes.append(route)
