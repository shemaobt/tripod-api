import logging
import time

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_graph_token_cache: dict[str, object] | None = None


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

    if settings.email_provider == "microsoft_graph":
        await _send_via_graph(to_email, greeting, reset_url, app_name)
        return

    logger.warning("Unknown email_provider=%s — reset email not sent", settings.email_provider)


def _build_html(greeting: str, reset_url: str, app_name: str) -> str:
    return (
        "<div style=\"font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', "
        'Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">'
        '<div style="text-align: center; margin-bottom: 24px;">'
        f'<h2 style="color: #1a1a1a; margin: 0;">{app_name}</h2>'
        "</div>"
        f'<p style="color: #333; font-size: 16px; line-height: 1.5;">Hi {greeting},</p>'
        '<p style="color: #333; font-size: 16px; line-height: 1.5;">'
        "We received a request to reset your password. "
        "Click the button below to choose a new password:"
        "</p>"
        '<div style="text-align: center; margin: 32px 0;">'
        f'<a href="{reset_url}" style="background-color: #c2410c; color: white; '
        "padding: 12px 32px; border-radius: 8px; text-decoration: none; "
        'font-size: 16px; font-weight: 600; display: inline-block;">'
        "Reset Password</a>"
        "</div>"
        '<p style="color: #666; font-size: 14px; line-height: 1.5;">'
        "Or copy and paste this link into your browser:<br/>"
        f'<a href="{reset_url}" style="color: #c2410c; word-break: break-all;">'
        f"{reset_url}</a>"
        "</p>"
        '<p style="color: #666; font-size: 14px; line-height: 1.5;">'
        "This link expires in 1 hour. If you did not request a password reset, "
        "you can safely ignore this email."
        "</p>"
        '<hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />'
        '<p style="color: #999; font-size: 12px; text-align: center;">'
        f"{app_name} by Shema YWAM"
        "</p>"
        "</div>"
    )


async def _get_graph_token() -> str:
    global _graph_token_cache

    if _graph_token_cache and time.time() < _graph_token_cache["expires_at"] - 60:  # type: ignore[operator]
        return _graph_token_cache["value"]  # type: ignore[return-value]

    import httpx

    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://login.microsoftonline.com/{settings.azure_tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.azure_client_id,
                "client_secret": settings.azure_client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
        )
        resp.raise_for_status()

    data = resp.json()
    _graph_token_cache = {
        "value": data["access_token"],
        "expires_at": time.time() + data["expires_in"],
    }
    token: str = data["access_token"]
    return token


async def _send_via_graph(
    to_email: str,
    greeting: str,
    reset_url: str,
    app_name: str,
) -> None:
    import httpx

    settings = get_settings()
    token = await _get_graph_token()
    html = _build_html(greeting, reset_url, app_name)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://graph.microsoft.com/v1.0/users/{settings.email_from_address}/sendMail",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "message": {
                    "subject": f"Reset your password — {app_name}",
                    "body": {"contentType": "HTML", "content": html},
                    "toRecipients": [
                        {"emailAddress": {"address": to_email}},
                    ],
                },
                "saveToSentItems": False,
            },
        )
        resp.raise_for_status()
    logger.info("[PASSWORD RESET] Sent via Microsoft Graph to=%s", to_email)


async def _send_via_resend(
    to_email: str,
    greeting: str,
    reset_url: str,
    app_name: str,
    api_key: str,
) -> None:
    import httpx

    html = _build_html(greeting, reset_url, app_name)

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
