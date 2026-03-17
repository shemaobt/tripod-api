import inngest

from app.core.config import get_settings

settings = get_settings()

inngest_client = inngest.Inngest(
    app_id="tripod-backend",
    event_key=settings.inngest_event_key or None,
    signing_key=settings.inngest_signing_key or None,
)
