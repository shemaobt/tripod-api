"""Camada `platform`: o que não é de nenhum app.

**Não há `_deps.py` com `APP_KEY` aqui, e isso é a declaração.** Os pacotes de app gateiam
por `require_app_access(APP_KEY)`; a plataforma serve qualquer usuário autenticado, de
qualquer app — o precedente é `app/api/uploads.py`, que usa só `get_current_user`.

`common/` = helpers sem dependência externa (`get_or_raise`).
`platform/` = serviços agnósticos de app apoiados num provedor externo ou em infra (TTS,
storage). Inquilinos naturais em PRs futuras: `common/email.py`, `services/storage/upload.py`
e `api/uploads.py`.
"""

from fastapi import APIRouter

from app.api.platform.tts import router as tts_router

router = APIRouter()
router.include_router(tts_router)

__all__ = ["router"]
