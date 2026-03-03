from app.services import (
    auth,
    authorization,
    language,
    org,
    phase,
    project,
    rag,
)

# Expose sub-packages under backward-compatible names
auth_service = auth
authorization_service = authorization
language_service = language
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
    "org",
    "organization_service",
    "phase",
    "phase_service",
    "project",
    "project_service",
    "rag",
    "rag_service",
]
