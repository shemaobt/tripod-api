from fastapi import APIRouter

from app.api.translation_helper import agents, audio, chats, prompts

router = APIRouter()

for _sub in (agents, chats, prompts, audio):
    for route in _sub.router.routes:
        router.routes.append(route)
