from fastapi import APIRouter

from app.api.projects import access, core, phases

router = APIRouter()

for _sub in (core, access, phases):
    for route in _sub.router.routes:
        router.routes.append(route)
