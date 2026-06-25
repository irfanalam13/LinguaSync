"""SMTP email delivery for auth verification and password reset links."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from urllib.parse import urlencode

from app.core.config import get_settings
from shared.logging import get_logger

log = get_logger("services.email")


def _is_configured() -> bool:
    settings = get_settings()
    return bool(settings.smtp_username and settings.smtp_password and settings.email_from)


def _build_url(path: str, token: str) -> str:
    base = get_settings().app_base_url.rstrip("/")
    return f"{base}{path}?{urlencode({'token': token})}"


def _send(to_email: str, subject: str, text: str, html: str) -> bool:
    settings = get_settings()
    if not _is_configured():
        log.warning("SMTP email skipped; VC_SMTP_USERNAME, VC_SMTP_PASSWORD, or VC_EMAIL_FROM is missing.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.email_from_name, settings.email_from or ""))
    msg["To"] = to_email
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
    except Exception:
        log.exception("SMTP email delivery failed for %s", to_email)
        return False

    return True


def send_email_verification(to_email: str, token: str) -> bool:
    url = _build_url("/verify-email", token)
    return _send(
        to_email=to_email,
        subject="Verify your Voice Converter email",
        text=f"Verify your email by opening this link: {url}",
        html=f"""
            <p>Welcome to Voice Converter.</p>
            <p><a href="{url}">Verify your email</a></p>
            <p>This link expires in 24 hours.</p>
        """,
    )


def send_password_reset(to_email: str, token: str) -> bool:
    url = _build_url("/reset-password", token)
    return _send(
        to_email=to_email,
        subject="Reset your Voice Converter password",
        text=f"Reset your password by opening this link: {url}",
        html=f"""
            <p>We received a request to reset your Voice Converter password.</p>
            <p><a href="{url}">Reset your password</a></p>
            <p>This link expires in 30 minutes.</p>
        """,
    )
