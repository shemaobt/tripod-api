import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.bhsa import router as bhsa_router
from app.api.health import router as health_router
from app.api.languages import router as languages_router
from app.api.organizations import router as organizations_router
from app.api.phases import router as phases_router
from app.api.projects import router as projects_router
from app.api.rag import router as rag_router
from app.api.roles import router as roles_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.exceptions import register_exception_handlers
from app.core.qdrant import close_qdrant, init_qdrant
from app.services.bhsa import loader


def _load_bhsa_background() -> None:
    """Load BHSA data in a background thread."""
    try:
        print("[STARTUP] Loading BHSA data in background...")
        loader.load()
        print("[STARTUP] BHSA data loaded successfully!")
    except Exception as e:
        print(f"[STARTUP] Failed to load BHSA data: {e}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    await init_qdrant()
    threading.Thread(target=_load_bhsa_background, daemon=True).start()
    try:
        yield
    finally:
        await close_qdrant()
        await close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Tripod Backend", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(roles_router, prefix="/api/roles", tags=["roles"])
    app.include_router(languages_router, prefix="/api/languages", tags=["languages"])
    app.include_router(organizations_router, prefix="/api/organizations", tags=["organizations"])
    app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
    app.include_router(phases_router, prefix="/api/phases", tags=["phases"])
    app.include_router(rag_router, prefix="/api/rag", tags=["rag"])
    app.include_router(bhsa_router, prefix="/api/bhsa", tags=["bhsa"])

    register_exception_handlers(app)

    return app


app = create_app()
