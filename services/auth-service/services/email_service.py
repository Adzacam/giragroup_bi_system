import os
import sys
import logging
import socket
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Cargar .env de forma segura si no ha sido cargado
try:
    from dotenv import load_dotenv, find_dotenv
    dotenv_file = find_dotenv(usecwd=True)
    if dotenv_file:
        load_dotenv(dotenv_file)
    else:
        load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("uvicorn.auth.email")


class EmailService:
    def __init__(self, templates_dir: Optional[Path] = None):
        if templates_dir and templates_dir.exists():
            self.templates_dir = templates_dir
        else:
            base_dir = Path(__file__).resolve().parent.parent
            candidate = base_dir / "templates"
            if candidate.exists():
                self.templates_dir = candidate
            else:
                self.templates_dir = Path.cwd() / "services" / "auth-service" / "templates"

        if self.templates_dir.exists():
            self.env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                autoescape=select_autoescape(["html", "xml"])
            )
        else:
            self.env = None

        # Directorio de preview HTML para inspección visual y auditoría local
        self.preview_dir = Path(__file__).resolve().parent.parent / "output" / "email_previews"
        try:
            self.preview_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    @property
    def is_smtp_configured(self) -> bool:
        """Verifica si SMTP_HOST está configurado con valor no vacío."""
        return bool(os.getenv("SMTP_HOST", "").strip())

    def _is_smtp_configured(self) -> bool:
        """Alias para compatibilidad interna."""
        return self.is_smtp_configured

    @property
    def smtp_config(self) -> Dict[str, Any]:
        """Obtiene y normaliza la configuración SMTP actual desde variables de entorno."""
        host = os.getenv("SMTP_HOST", "").strip()
        try:
            port = int(os.getenv("SMTP_PORT", "587").strip())
        except (ValueError, TypeError):
            port = 587

        user = os.getenv("SMTP_USER", "").strip()
        password = os.getenv("SMTP_PASSWORD", "")
        # Despojar comillas accidentales en el archivo .env
        if (password.startswith('"') and password.endswith('"')) or (password.startswith("'") and password.endswith("'")):
            password = password[1:-1]

        # Normalizar App Password de Gmail (16 caracteres agrupados con espacios)
        if "gmail" in host.lower() and len(password.replace(" ", "")) == 16:
            password = password.replace(" ", "")

        from_email = os.getenv("SMTP_FROM_EMAIL", "").strip() or user or "noreply@giragroup.com"
        from_name = os.getenv("SMTP_FROM_NAME", "GiraGroup BI System").strip()
        if (from_name.startswith('"') and from_name.endswith('"')) or (from_name.startswith("'") and from_name.endswith("'")):
            from_name = from_name[1:-1]

        use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in ("true", "1", "yes", "t")
        use_ssl = (os.getenv("SMTP_USE_SSL", "false").strip().lower() in ("true", "1", "yes", "t")) or (port == 465)

        try:
            timeout = float(os.getenv("SMTP_TIMEOUT", "5.0").strip())
        except (ValueError, TypeError):
            timeout = 5.0

        return {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "from_email": from_email,
            "from_name": from_name,
            "use_tls": use_tls,
            "use_ssl": use_ssl,
            "timeout": timeout,
        }

    def _send_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía un correo mediante smtplib de la biblioteca estándar de Python.
        Soporta STARTTLS (puerto 587) y SSL directo (puerto 465).
        Aplica timeout defensivo (5s) y manejo de excepciones robusto para que la
        aplicación nunca se bloquee si el servidor SMTP falla o la red no responde.
        """
        cfg = self.smtp_config
        host = cfg["host"]

        if not host:
            logger.info("ℹ️ [SMTP OMITIDO] SMTP_HOST no configurado. Operando en modo consola/local.")
            return {"sent": False, "reason": "not_configured"}

        port = cfg["port"]
        user = cfg["user"]
        password = cfg["password"]
        from_email = cfg["from_email"]
        from_name = cfg["from_name"]
        use_tls = cfg["use_tls"]
        use_ssl = cfg["use_ssl"]
        timeout = cfg["timeout"]

        # Construcción del mensaje MIME multipart (HTML + PlainText fallback)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((from_name, from_email)) if from_name else from_email
        msg["To"] = to_email
        msg["Date"] = formatdate(localtime=True)
        domain_part = host if ("." in host and not host.replace(".", "").isdigit()) else None
        msg["Message-ID"] = make_msgid(domain=domain_part)

        if not text_content:
            text_content = f"{subject}\n\nNotificación institucional de GiraGroup BI System para {to_email}."

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        server = None
        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(host, port, timeout=timeout)
                server.ehlo()
            else:
                server = smtplib.SMTP(host, port, timeout=timeout)
                server.ehlo()
                if use_tls:
                    server.starttls()
                    server.ehlo()

            if user and password:
                server.login(user, password)

            server.send_message(msg)
            logger.info(f"✅ [SMTP ENVIADO] Correo despachado con éxito a {to_email} vía {host}:{port}")
            return {"sent": True, "host": host, "port": port}

        except smtplib.SMTPAuthenticationError as e:
            err = f"Credenciales SMTP erróneas para {user} en {host}:{port}: {e}"
            logger.error(f"❌ [SMTP ERROR AUTENTICACIÓN] {err}")
            return {"sent": False, "error": err, "error_type": "AuthenticationError"}
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, socket.timeout, OSError) as e:
            err = f"Fallo de conexión o timeout ({timeout}s) contactando {host}:{port}: {e}"
            logger.warning(f"⚠️ [SMTP TIMEOUT/CONEXIÓN] {err}")
            return {"sent": False, "error": err, "error_type": "ConnectionTimeoutError"}
        except Exception as e:
            err = f"Error inesperado al enviar correo por SMTP ({host}:{port}): {e}"
            logger.warning(f"⚠️ [SMTP ERROR GENERAL] {err}")
            return {"sent": False, "error": err, "error_type": type(e).__name__}
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    try:
                        server.close()
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
    ) -> Dict[str, Any]:
        """
        Emite el correo electrónico OTP corporativo vía SMTP y garantiza SIEMPRE
        la impresión destacada en terminal para flujos rápidos por comando.
        """
        html_content = self.render_otp_email(to_email, username, otp_code, expires_in_minutes)
        text_content = (
            f"GiraGroup BI System - Verificación 2FA\n\n"
            f"Hola {username or to_email.split('@')[0]},\n"
            f"Su código de verificación temporal es: {otp_code}\n"
            f"Vigencia: {expires_in_minutes} minutos.\n\n"
            f"Si no solicitó este código, ignore este mensaje o contacte al administrador de seguridad."
        )

        # 1. SIEMPRE imprimir en consola/terminal para pruebas ágiles por comando
        banner = (
            f"\n"
            f"╔════════════════════════════════════════════════════════════════╗\n"
            f"║                GIRAGROUP BI SYSTEM - CÓDIGO OTP                ║\n"
            f"╠════════════════════════════════════════════════════════════════╣\n"
            f"║ Destino   : {to_email:<50} ║\n"
            f"║ Código OTP: {otp_code:<50} ║\n"
            f"║ Vigencia  : {expires_in_minutes} minutos{' ':<39} ║\n"
            f"╚════════════════════════════════════════════════════════════════╝\n"
        )
        sys.stderr.write(banner)
        sys.stderr.flush()
        logger.info(f"📧 [EMAIL OTP DESPACHADO] Destino: {to_email} | Código: {otp_code} | Expira: {expires_in_minutes}m")

        # 2. Guardar preview HTML para auditoría local
        try:
            preview_file = self.preview_dir / "latest_otp_email.html"
            preview_file.write_text(html_content, encoding="utf-8")
        except Exception:
            pass

        # 3. Despachar vía SMTP real (con fallback defensivo)
        subject = f"{otp_code} es tu código de verificación de GiraGroup BI"
        smtp_res = self._send_smtp(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

        return {
            "status": "delivered",
            "to": to_email,
            "otp": otp_code,
            "template": "email_otp_verification.html",
            "smtp": smtp_res
        }

    def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_code: str,
        expires_in_minutes: int = 15
    ) -> Dict[str, Any]:
        """
        Emite el correo de restablecimiento vía SMTP y garantiza SIEMPRE
        la impresión destacada en terminal para auditoría y desarrollo rápido.
        """
        html_content = self.render_password_reset_email(to_email, username, reset_code, expires_in_minutes)
        text_content = (
            f"GiraGroup BI System - Restablecimiento de Contraseña\n\n"
            f"Hola {username or to_email.split('@')[0]},\n"
            f"Su código para restablecer la contraseña es: {reset_code}\n"
            f"Vigencia: {expires_in_minutes} minutos.\n\n"
            f"Si no solicitó restablecer su clave, ignore este mensaje de inmediato."
        )

        # 1. SIEMPRE imprimir en consola/terminal
        banner = (
            f"\n"
            f"╔════════════════════════════════════════════════════════════════╗\n"
            f"║         GIRAGROUP BI SYSTEM - RESTABLECIMIENTO DE CLAVE        ║\n"
            f"╠════════════════════════════════════════════════════════════════╣\n"
            f"║ Destino   : {to_email:<50} ║\n"
            f"║ Código    : {reset_code:<50} ║\n"
            f"║ Vigencia  : {expires_in_minutes} minutos{' ':<39} ║\n"
            f"╚════════════════════════════════════════════════════════════════╝\n"
        )
        sys.stderr.write(banner)
        sys.stderr.flush()
        logger.info(f"📧 [EMAIL RESET DESPACHADO] Destino: {to_email} | Código: {reset_code} | Expira: {expires_in_minutes}m")

        # 2. Guardar preview HTML
        try:
            preview_file = self.preview_dir / "latest_password_reset_email.html"
            preview_file.write_text(html_content, encoding="utf-8")
        except Exception:
            pass

        # 3. Despachar vía SMTP real
        subject = "Código para restablecer su contraseña - GiraGroup BI"
        smtp_res = self._send_smtp(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

        return {
            "status": "delivered",
            "to": to_email,
            "reset_code": reset_code,
            "template": "email_password_reset.html",
            "smtp": smtp_res
        }


email_service = EmailService()
