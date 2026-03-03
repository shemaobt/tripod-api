from app.services import (
    auth,
    authorization,
    language,
    meaning_map,
    org,
    phase,
    project,
    rag,
)

# Expose sub-packages under backward-compatible names
auth_service = auth
authorization_service = authorization
language_service = language
meaning_map_service = meaning_map
organization_service = org
phase_service = phase
project_service = project
rag_service = rag

__all__ = [
    "auth",
    "auth_service",
    "authorization",
    "authorization_service",
    "language",
    "language_service",
    "meaning_map",
    "meaning_map_service",
    "org",
    "organization_service",
    "phase",
    "phase_service",
    "project",
    "project_service",
    "rag",
    "rag_service",
]
