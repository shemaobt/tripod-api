from fastapi import APIRouter

from app.api.project_health import admin, interviews, reports

router = APIRouter()

for _sub in (interviews, reports, admin):
    for route in _sub.router.routes:
        router.routes.append(route)
