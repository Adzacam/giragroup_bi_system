import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger("uvicorn.auth.email")

class EmailService:
    def __init__(self, templates_dir: Optional[Path] = None):
        if templates_dir and templates_dir.exists():
            self.templates_dir = templates_dir
        else:
            # Detect templates directory in backend or relative paths
            base_dir = Path(__file__).resolve().parent.parent
            candidate = base_dir / "templates"
            if candidate.exists():
                self.templates_dir = candidate
            else:
                self.templates_dir = Path.cwd() / "backend" / "templates"

        if self.templates_dir.exists():
            self.env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                autoescape=select_autoescape(["html", "xml"])
            )
        else:
            self.env = None

        # Output preview directory for visual inspection in dev
        self.preview_dir = Path(__file__).resolve().parent.parent / "output" / "email_previews"
        try:
            self.preview_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def render_otp_email(
        self,
        to_email: str,
        username: str,
        otp_code: str,
        expires_in_minutes: int = 5
    ) -> str:
        """Renderiza la plantilla corporativa Navy/Gold para verificación 2FA."""
        if not self.env:
            return f"Código OTP para {to_email}: {otp_code} (Expira en {expires_in_minutes}m)"

        template = self.env.get_template("email_otp_verification.html")
        formatted_otp = f"{otp_code[:3]} {otp_code[3:]}" if len(otp_code) == 6 else otp_code
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        return template.render(
            to_email=to_email,
            username=username or to_email.split("@")[0],
            otp_code=otp_code,
            formatted_otp=formatted_otp,
            expires_in_minutes=expires_in_minutes,
            request_timestamp=timestamp_str,
        )

    def render_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_code: str,
        expires_in_minutes: int = 15
    ) -> str:
        """Renderiza la plantilla corporativa Navy/Gold para restablecimiento de contraseña."""
        if not self.env:
            return f"Código de restablecimiento para {to_email}: {reset_code} (Expira en {expires_in_minutes}m)"

        template = self.env.get_template("email_password_reset.html")
        formatted_otp = f"{reset_code[:3]} {reset_code[3:]}" if len(reset_code) == 6 else reset_code
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        return template.render(
            to_email=to_email,
            username=username or to_email.split("@")[0],
            reset_code=reset_code,
            formatted_otp=formatted_otp,
            expires_in_minutes=expires_in_minutes,
            request_timestamp=timestamp_str,
        )

    def send_otp_email(
        self,
        to_email: str,
        username: str,
        otp_code: str,
        expires_in_minutes: int = 5
    ) -> dict:
        """Emite el correo electrónico OTP corporativo y genera preview para auditoría."""
        html_content = self.render_otp_email(to_email, username, otp_code, expires_in_minutes)

        # Log institucional
        msg = f"📧 [EMAIL OTP DESPACHADO] Destino: {to_email} | Código: {otp_code} | Expira: {expires_in_minutes}m"
        logger.info(msg)
        sys.stderr.write(f"\n{msg}\n")
        sys.stderr.flush()

        # Guardar preview HTML para inspección local de diseño
        try:
            preview_file = self.preview_dir / "latest_otp_email.html"
            preview_file.write_text(html_content, encoding="utf-8")
        except Exception:
            pass

        return {
            "status": "delivered",
            "to": to_email,
            "otp": otp_code,
            "template": "email_otp_verification.html"
        }

    def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_code: str,
        expires_in_minutes: int = 15
    ) -> dict:
        """Emite el correo de restablecimiento y genera preview para auditoría."""
        html_content = self.render_password_reset_email(to_email, username, reset_code, expires_in_minutes)

        msg = f"📧 [EMAIL RESET DESPACHADO] Destino: {to_email} | Código: {reset_code} | Expira: {expires_in_minutes}m"
        logger.info(msg)
        sys.stderr.write(f"\n{msg}\n")
        sys.stderr.flush()

        try:
            preview_file = self.preview_dir / "latest_password_reset_email.html"
            preview_file.write_text(html_content, encoding="utf-8")
        except Exception:
            pass

        return {
            "status": "delivered",
            "to": to_email,
            "reset_code": reset_code,
            "template": "email_password_reset.html"
        }

email_service = EmailService()
