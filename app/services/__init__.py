from app.services import (
    access_request,
    app,
    auth,
    authorization,
    language,
    meaning_map,
    notifications,
    org,
    phase,
    project,
    rag,
    user,
)

access_request_service = access_request
app_service = app
auth_service = auth
authorization_service = authorization
language_service = language
meaning_map_service = meaning_map
notification_service = notifications
organization_service = org
phase_service = phase
project_service = project
rag_service = rag
user_service = user

__all__ = [
    "access_request",
    "access_request_service",
    "app",
    "app_service",
    "auth",
    "auth_service",
    "authorization",
    "authorization_service",
    "language",
    "language_service",
    "meaning_map",
    "meaning_map_service",
    "notification_service",
    "notifications",
    "org",
    "organization_service",
    "phase",
    "phase_service",
    "project",
    "project_service",
    "rag",
    "rag_service",
    "user",
    "user_service",
]
