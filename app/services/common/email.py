import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def send_password_reset_email(
    to_email: str,
    display_name: str | None,
    reset_url: str,
    app_name: str,
) -> None:
    """Send a password reset email. Provider is configured via settings.email_provider."""
    settings = get_settings()
    greeting = display_name or to_email

    if settings.email_provider == "log":
        logger.info(
            "[PASSWORD RESET] app=%s to=%s name=%s url=%s",
            app_name,
            to_email,
            greeting,
            reset_url,
        )
        return

    if settings.email_provider == "resend":
        await _send_via_resend(to_email, greeting, reset_url, app_name, settings.resend_api_key)
        return

    logger.warning("Unknown email_provider=%s — reset email not sent", settings.email_provider)


async def _send_via_resend(
    to_email: str,
    greeting: str,
    reset_url: str,
    app_name: str,
    api_key: str,
) -> None:
    import httpx

    html = (
        f"<p>Hi {greeting},</p>"
        f"<p>You requested a password reset for your <strong>{app_name}</strong> account.</p>"
        f'<p><a href="{reset_url}" style="display:inline-block;padding:10px 20px;'
        f'background:#BE4A01;color:#fff;border-radius:6px;text-decoration:none">'
        f"Reset Password</a></p>"
        f"<p>Or copy this link: {reset_url}</p>"
        f"<p>This link expires in 1 hour. If you did not request this, "
        f"you can ignore this email.</p>"
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": f"{app_name} <noreply@shemaywam.com>",
                "to": [to_email],
                "subject": f"Password Reset — {app_name}",
                "html": html,
            },
        )
        resp.raise_for_status()
        logger.info("[PASSWORD RESET] Sent via Resend to=%s", to_email)
