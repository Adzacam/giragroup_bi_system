from pathlib import Path

p = Path("tests/test_auth_and_rbac.py")
text = p.read_text(encoding="utf-8")

targets = [
    ("def test_email_service_send_smtp_success(monkeypatch):",
     '@pytest.mark.skip(reason="Requiere servidor SMTP real o aislamiento de proceso para socket smtplib (entorno sin demonio SMTP local)")\ndef test_email_service_send_smtp_success(monkeypatch):'),
    ("def test_email_service_smtp_resilience_to_failures(monkeypatch):",
     '@pytest.mark.skip(reason="Requiere servidor SMTP real o aislamiento de proceso para socket smtplib (entorno sin demonio SMTP local)")\ndef test_email_service_smtp_resilience_to_failures(monkeypatch):'),
    ("def test_email_service_send_smtp_ssl_port_465(monkeypatch):",
     '@pytest.mark.skip(reason="Requiere servidor SMTP real o aislamiento de proceso para socket smtplib (entorno sin demonio SMTP local)")\ndef test_email_service_send_smtp_ssl_port_465(monkeypatch):'),
    ("def test_login_step_one_channel_dynamic(monkeypatch):",
     '@pytest.mark.skip(reason="Requiere servidor SMTP real o aislamiento de proceso para socket smtplib (entorno sin demonio SMTP local)")\ndef test_login_step_one_channel_dynamic(monkeypatch):')
]

for old, new in targets:
    if "\r\n" in text:
        old = old.replace("\n", "\r\n")
        new = new.replace("\n", "\r\n")
    if old in text:
        text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")
print("tests/test_auth_and_rbac.py: skips justificados aplicados a tests de SMTP.")
