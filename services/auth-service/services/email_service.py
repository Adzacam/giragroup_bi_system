import os
import sys
import logging
import socket
import smtplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.utils import formataddr, formatdate, make_msgid
from email.header import Header
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


def mask_email(email: str) -> str:
    """
    Enmascara el correo del destinatario protegiendo su privacidad en comunicaciones institucionales.
    Ejemplo: 'dazaadrian012@gmail.com' -> 'daz********@gmail.com'
    """
    if not email or "@" not in email:
        return email or ""
    local_part, domain = email.split("@", 1)
    if len(local_part) <= 2:
        masked_local = local_part[0] + "****"
    elif len(local_part) <= 4:
        masked_local = local_part[:2] + "****"
    else:
        masked_local = local_part[:3] + "********"
    return f"{masked_local}@{domain}"


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
                self.templates_dir = Path.cwd() / "backend" / "templates"

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
        if (password.startswith('"') and password.endswith('"')) or (password.startswith("'") and password.endswith("'")):
            password = password[1:-1]

        if "gmail" in host.lower() and len(password.replace(" ", "")) == 16:
            password = password.replace(" ", "")

        from_email = os.getenv("SMTP_FROM_EMAIL", "").strip() or user or "noreply@giragroup.bo"
        from_name = os.getenv("SMTP_FROM_NAME", "GiraGroup BI").strip()
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

    def get_logo_bytes(self) -> Optional[bytes]:
        """Recupera los bytes del logo institucional de GiraGroup para embeber en correos."""
        candidates = [
            self.templates_dir / "assets" / "giragroup_logo.jpg",
            Path(__file__).resolve().parent.parent / "templates" / "assets" / "giragroup_logo.jpg",
            Path.cwd() / "frontend" / "public" / "giragroup_logo.jpg",
        ]
        for candidate in candidates:
            if candidate and candidate.exists():
                try:
                    return candidate.read_bytes()
                except Exception:
                    pass
        return None

    def get_logo_base64(self) -> Optional[str]:
        """Obtiene la data URI Base64 del logo para previsualización HTML y clientes web."""
        data = self.get_logo_bytes()
        if data:
            encoded = base64.b64encode(data).decode("ascii")
            return f"data:image/jpeg;base64,{encoded}"
        return None

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
        """
        cfg = self.smtp_config
        host = cfg["host"]

        if not host:
            logger.info("ℹ️ [SMTP OMITIDO] SMTP_HOST no configurado. Operando en modo consola/local.")
            return {"sent": False, "reason": "not_configured"}

        email_backend = os.getenv("EMAIL_BACKEND", "smtp").strip().lower()
        if email_backend in ("console", "memory", "dummy"):
            logger.info(f"ℹ️ [EMAIL_BACKEND={email_backend.upper()}] Envío SMTP omitido hacia {to_email}. Operando en modo hermético/consola.")
            return {"sent": False, "reason": f"backend_{email_backend}"}

        smtp_enabled = os.getenv("SMTP_ENABLED", "true").strip().lower() in ("true", "1", "yes", "t")
        real_smtp_enabled = os.getenv("ENABLE_REAL_SMTP", "true").strip().lower() in ("true", "1", "yes", "t")
        if not smtp_enabled or not real_smtp_enabled:
            logger.info("ℹ️ [SMTP OMITIDO] SMTP deshabilitado por configuración (SMTP_ENABLED o ENABLE_REAL_SMTP en false).")
            return {"sent": False, "reason": "disabled_by_config"}

        port = cfg["port"]
        user = cfg["user"]
        password = cfg["password"]
        from_email = cfg["from_email"]
        from_name = cfg["from_name"]
        use_tls = cfg["use_tls"]
        use_ssl = cfg["use_ssl"]
        timeout = cfg["timeout"]

        msg = MIMEMultipart("related")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr((from_name, from_email)) if from_name else from_email
        msg["To"] = to_email
        msg["Reply-To"] = from_email
        msg["Date"] = formatdate(localtime=True)
        domain_part = host if ("." in host and not host.replace(".", "").isdigit()) else "giragroup.bo"
        msg["Message-ID"] = make_msgid(domain=domain_part)
        msg["X-Mailer"] = "GiraGroup-BI-Security/1.0"
        msg["Auto-Submitted"] = "auto-generated"
        msg["X-Auto-Response-Suppress"] = "All"

        msg_alt = MIMEMultipart("alternative")
        msg.attach(msg_alt)

        if not text_content:
            text_content = f"{subject}\n\nNotificación institucional de GiraGroup BI System para {to_email}."

        msg_alt.attach(MIMEText(text_content, "plain", "utf-8"))
        msg_alt.attach(MIMEText(html_content, "html", "utf-8"))

        # Adjuntar logo corporativo como recurso inline CID
        logo_bytes = self.get_logo_bytes()
        if logo_bytes:
            try:
                img_part = MIMEImage(logo_bytes, _subtype="jpeg")
                img_part.add_header("Content-ID", "<giragroup_logo>")
                img_part.add_header("Content-Disposition", "inline", filename="giragroup_logo.jpg")
                msg.attach(img_part)
            except Exception as e:
                logger.warning(f"No se pudo adjuntar el logo CID en el correo: {e}")

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
        expires_in_minutes: int = 5,
        logo_src: Optional[str] = None
    ) -> str:
        """Renderiza la plantilla corporativa Navy/Gold para verificación 2FA."""
        if not self.env:
            return f"Código OTP para {to_email}: {otp_code} (Expira en {expires_in_minutes}m)"

        template = self.env.get_template("email_otp_verification.html")
        formatted_otp = f"{otp_code[:3]} {otp_code[3:]}" if len(otp_code) == 6 else otp_code
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        masked = mask_email(to_email)
        logo_data = logo_src or self.get_logo_base64() or "cid:giragroup_logo"

        return template.render(
            to_email=to_email,
            masked_email=masked,
            to_email_masked=masked,
            username=username or to_email.split("@")[0],
            otp_code=otp_code,
            formatted_otp=formatted_otp,
            expires_in_minutes=expires_in_minutes,
            request_timestamp=timestamp_str,
            logo_src=logo_data,
        )

    def render_password_reset_email(
        self,
        to_email: str,
        username: str,
        temp_password: Optional[str] = None,
        reset_code: Optional[str] = None,
        expires_in_minutes: int = 15,
        logo_src: Optional[str] = None
    ) -> str:
        """Renderiza la plantilla corporativa Navy/Gold para restablecimiento con contraseña temporal."""
        if not self.env:
            pwd = temp_password or reset_code or "Clave temporal"
            return f"Contraseña temporal para {to_email}: {pwd}"

        template = self.env.get_template("email_password_reset.html")
        pwd = temp_password or reset_code or "Gira#123456"
        formatted_otp = f"{pwd[:3]} {pwd[3:]}" if (len(pwd) == 6 and pwd.isdigit()) else pwd
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        masked = mask_email(to_email)
        logo_data = logo_src or self.get_logo_base64() or "cid:giragroup_logo"

        return template.render(
            to_email=to_email,
            masked_email=masked,
            to_email_masked=masked,
            username=username or to_email.split("@")[0],
            temp_password=pwd,
            reset_code=pwd,
            formatted_otp=formatted_otp,
            expires_in_minutes=expires_in_minutes,
            request_timestamp=timestamp_str,
            logo_src=logo_data,
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
        html_preview = self.render_otp_email(to_email, username, otp_code, expires_in_minutes, logo_src=self.get_logo_base64())
        html_smtp = self.render_otp_email(to_email, username, otp_code, expires_in_minutes, logo_src="cid:giragroup_logo")
        masked = mask_email(to_email)

        text_content = (
            f"GiraGroup BI System - Verificación de Identidad (2FA)\n\n"
            f"Hola {username or to_email.split('@')[0]},\n"
            f"Se ha solicitado iniciar sesión en tu cuenta asociada a {masked}.\n"
            f"Código de seguridad: {otp_code}\n"
            f"Vigencia: {expires_in_minutes} minutos.\n\n"
            f"No compartas este código con nadie.\n"
            f"«Este mensaje fue generado automáticamente. No respondas a este correo»."
        )

        banner = (
            f"\n"
            f"╔════════════════════════════════════════════════════════════════╗\n"
            f"║                GIRAGROUP BI SYSTEM - CÓDIGO OTP                ║\n"
            f"╠════════════════════════════════════════════════════════════════╣\n"
            f"║ Destino   : {masked:<50} ║\n"
            f"║ Código OTP: {otp_code:<50} ║\n"
            f"║ Vigencia  : {expires_in_minutes} minutos{' ':<39} ║\n"
            f"╚════════════════════════════════════════════════════════════════╝\n"
        )
        sys.stderr.write(banner)
        sys.stderr.flush()
        logger.info(f"📧 [EMAIL OTP DESPACHADO] Destino: {masked} | Código: {otp_code} | Expira: {expires_in_minutes}m")

        try:
            preview_file = self.preview_dir / "latest_otp_email.html"
            preview_file.write_text(html_preview, encoding="utf-8")
        except Exception:
            pass

        # Asunto discreto y seguro que no expone el OTP en las notificaciones
        subject = "[GiraGroup BI] Código de seguridad para iniciar sesión"
        smtp_res = self._send_smtp(
            to_email=to_email,
            subject=subject,
            html_content=html_smtp,
            text_content=text_content
        )

        return {
            "status": "delivered",
            "to": to_email,
            "masked_to": masked,
            "otp": otp_code,
            "template": "email_otp_verification.html",
            "smtp": smtp_res
        }

    def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        temp_password: Optional[str] = None,
        reset_code: Optional[str] = None,
        expires_in_minutes: int = 15
    ) -> Dict[str, Any]:
        """
        Emite el correo de restablecimiento con la nueva contraseña temporal vía SMTP
        y garantiza SIEMPRE la impresión destacada en terminal para auditoría y desarrollo rápido.
        """
        pwd = temp_password or reset_code or "Gira#123456"
        html_preview = self.render_password_reset_email(
            to_email, username, temp_password=pwd, expires_in_minutes=expires_in_minutes, logo_src=self.get_logo_base64()
        )
        html_smtp = self.render_password_reset_email(
            to_email, username, temp_password=pwd, expires_in_minutes=expires_in_minutes, logo_src="cid:giragroup_logo"
        )
        masked = mask_email(to_email)

        text_content = (
            f"GiraGroup BI System - Contraseña Temporal de Inicio de Sesión\n\n"
            f"Hola {username or to_email.split('@')[0]},\n"
            f"Se ha generado una nueva contraseña temporal para su cuenta institucional ({masked}):\n\n"
            f"Contraseña temporal: {pwd}\n\n"
            f"Úsela para iniciar sesión en la plataforma y proceda a actualizarla inmediatamente desde su perfil de usuario.\n\n"
            f"«Este mensaje fue generado automáticamente. No respondas a este correo»."
        )

        banner = (
            f"\n"
            f"╔════════════════════════════════════════════════════════════════╗\n"
            f"║         GIRAGROUP BI SYSTEM - CONTRASEÑA TEMPORAL              ║\n"
            f"╠════════════════════════════════════════════════════════════════╣\n"
            f"║ Destino   : {masked:<50} ║\n"
            f"║ Temporal  : {pwd:<50} ║\n"
            f"║ Acción    : Iniciar sesión y cambiar clave en perfil           ║\n"
            f"╚════════════════════════════════════════════════════════════════╝\n"
        )
        sys.stderr.write(banner)
        sys.stderr.flush()
        logger.info(f"📧 [EMAIL RESET DESPACHADO] Destino: {masked} | Temporal: {pwd}")

        try:
            preview_file = self.preview_dir / "latest_password_reset_email.html"
            preview_file.write_text(html_preview, encoding="utf-8")
        except Exception:
            pass

        subject = "[GiraGroup BI] Contraseña temporal para iniciar sesión"
        smtp_res = self._send_smtp(
            to_email=to_email,
            subject=subject,
            html_content=html_smtp,
            text_content=text_content
        )

        return {
            "status": "delivered",
            "to": to_email,
            "masked_to": masked,
            "temp_password": pwd,
            "reset_code": pwd,
            "template": "email_password_reset.html",
            "smtp": smtp_res
        }


email_service = EmailService()
