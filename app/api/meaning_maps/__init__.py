from fastapi import APIRouter

from app.api.meaning_maps import crud, export, feedback, generation

router = APIRouter()

for _sub in (generation, crud, export, feedback):
    for route in _sub.router.routes:
        router.routes.append(route)
