from fastapi import APIRouter

from app.api.book_context import analysis, crud, feedback, sections, translate, workflow

router = APIRouter()

for _sub in (analysis, crud, workflow, sections, feedback, translate):
    for route in _sub.router.routes:
        router.routes.append(route)
