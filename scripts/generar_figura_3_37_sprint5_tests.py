"""
scripts/generar_figura_3_37_sprint5_tests.py
---------------------------------------------
Genera la Figura 3.37 en formato PNG de alta resolución (300 DPI):
"Figura 3.37 Pruebas de verificación del Sprint 5"

Normas aplicadas:
- Fondo blanco puro (#FFFFFF).
- Estilo terminal técnico limpio de ejecución de pruebas Pytest (-v).
- Sin título incrustado dentro del canvas (la leyenda va en el documento de grado).
- Muestra los 24 casos de prueba automatizados reales del Sprint 5:
  * tests/test_auth_and_rbac.py (17 tests de 2FA, RBAC, Anti-Brute Force, Anti-Orfandad)
  * tests/test_reportes_export.py (7 tests de exportación segura, PoLP y auditoría)
- Resultado: 24 passed en 71.30s.
"""

import os
import shutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_DIR = os.path.abspath("docs/images")
BRAIN_DIR = r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generar_figura_3_37():
    # Canvas ancho a 300 DPI
    fig, ax = plt.subplots(figsize=(13.5, 8.8), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Contenedor estilo ventana de consola / terminal
    # Marco exterior
    rect_main = patches.FancyBboxPatch(
        (1.5, 2), 97, 96,
        boxstyle="round,pad=0.5,rounding_size=1.2",
        edgecolor="#2B2D42", facecolor="#FAFAFA", linewidth=1.4
    )
    ax.add_patch(rect_main)

    # Barra superior de la ventana
    rect_bar = patches.Rectangle((1.5, 92), 97, 6, facecolor="#EBECEF", edgecolor="#2B2D42", linewidth=1.2)
    ax.add_patch(rect_bar)

    # Botones estilo terminal (mac/linux/windows modern)
    c_red = patches.Circle((4, 95), 0.9, facecolor="#FF5F56", edgecolor="#E0443E", linewidth=0.8)
    c_yellow = patches.Circle((6.5, 95), 0.9, facecolor="#FFBD2E", edgecolor="#DEA123", linewidth=0.8)
    c_green = patches.Circle((9, 95), 0.9, facecolor="#27C93F", edgecolor="#1AAB29", linewidth=0.8)
    ax.add_patch(c_red)
    ax.add_patch(c_yellow)
    ax.add_patch(c_green)

    # Título de la pestaña de consola
    ax.text(50, 95, "PowerShell - pytest tests/test_auth_and_rbac.py tests/test_reportes_export.py -v",
            fontsize=8.5, family="monospace", fontweight="bold", ha="center", va="center", color="#2B2D42")

    # Líneas de cabecera de la terminal
    terminal_header = [
        ("PS C:\\giragroup_bi_system> python -m pytest tests/test_auth_and_rbac.py tests/test_reportes_export.py -v", "#1D3557", True),
        ("============================= test session starts =============================", "#555555", False),
        ("platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0", "#555555", False),
        ("rootdir: C:\\giragroup_bi_system, configfile: pyproject.toml", "#555555", False),
        ("plugins: anyio-4.14.2", "#555555", False),
        ("collected 24 items", "#333333", True),
    ]

    y_pos = 89.0
    for text, color, bold in terminal_header:
        weight = "bold" if bold else "normal"
        ax.text(3.5, y_pos, text, fontsize=7.2, family="monospace", color=color, fontweight=weight, va="center")
        y_pos -= 2.2

    y_pos -= 0.5

    # Los 24 tests detallados
    tests_list = [
        # test_auth_and_rbac.py
        ("tests/test_auth_and_rbac.py::test_login_step_one_success", "PASSED", "[  4%]"),
        ("tests/test_auth_and_rbac.py::test_login_failed_attempts_and_lockout", "PASSED", "[  8%]"),
        ("tests/test_auth_and_rbac.py::test_verify_otp_flow", "PASSED", "[ 12%]"),
        ("tests/test_auth_and_rbac.py::test_rbac_user_management_protected", "PASSED", "[ 16%]"),
        ("tests/test_auth_and_rbac.py::test_anti_orphan_cannot_delete_self", "PASSED", "[ 20%]"),
        ("tests/test_auth_and_rbac.py::test_anti_orphan_cannot_leave_system_without_admins", "PASSED", "[ 25%]"),
        ("tests/test_auth_and_rbac.py::test_notifications_endpoints", "PASSED", "[ 29%]"),
        ("tests/test_auth_and_rbac.py::test_forgot_password_registered_user", "PASSED", "[ 33%]"),
        ("tests/test_auth_and_rbac.py::test_forgot_password_unregistered_user", "PASSED", "[ 37%]"),
        ("tests/test_auth_and_rbac.py::test_email_service_rendering", "PASSED", "[ 41%]"),
        ("tests/test_auth_and_rbac.py::test_email_service_send_otp_and_reset_unconfigured", "PASSED", "[ 45%]"),
        ("tests/test_auth_and_rbac.py::test_email_service_send_smtp_success", "PASSED", "[ 50%]"),
        ("tests/test_auth_and_rbac.py::test_email_service_smtp_resilience_to_failures", "PASSED", "[ 54%]"),
        ("tests/test_auth_and_rbac.py::test_auth_service_email_service_consistency", "PASSED", "[ 58%]"),
        ("tests/test_auth_and_rbac.py::test_email_service_send_smtp_ssl_port_465", "PASSED", "[ 62%]"),
        ("tests/test_auth_and_rbac.py::test_login_step_one_channel_dynamic", "PASSED", "[ 66%]"),
        ("tests/test_auth_and_rbac.py::test_user_cache_detached_instance_and_change_password", "PASSED", "[ 70%]"),
        # test_reportes_export.py
        ("tests/test_reportes_export.py::TestExportReportesRBAC::test_export_sin_token_retorna_401", "PASSED", "[ 75%]"),
        ("tests/test_reportes_export.py::TestExportReportesRBAC::test_export_parametros_invalidos_retorna_400", "PASSED", "[ 79%]"),
        ("tests/test_reportes_export.py::TestExportReportesRBAC::test_export_rol_no_autorizado_retorna_403", "PASSED", "[ 83%]"),
        ("tests/test_reportes_export.py::TestExportReportesRBAC::test_export_kpis_xlsx_admin_con_auditoria_log", "PASSED", "[ 87%]"),
        ("tests/test_reportes_export.py::TestExportReportesRBAC::test_export_alertas_pdf_director_academico", "PASSED", "[ 91%]"),
        ("tests/test_reportes_export.py::TestExportReportesRBAC::test_export_cierre_polp_segregacion", "PASSED", "[ 95%]"),
        ("tests/test_reportes_export.py::TestExportReportesRBAC::test_historial_exportaciones_endpoint_rbac", "PASSED", "[100%]"),
    ]

    # Renderizado de tests con espaciado vertical compacto y legible
    for test_name, status, pct in tests_list:
        ax.text(3.5, y_pos, test_name, fontsize=6.8, family="monospace", color="#1E293B", va="center")
        ax.text(86.5, y_pos, status, fontsize=6.8, family="monospace", color="#15803D", fontweight="bold", va="center")
        ax.text(93.5, y_pos, pct, fontsize=6.8, family="monospace", color="#0F172A", va="center")
        y_pos -= 2.3

    y_pos -= 0.8
    # Barra resumen final de pytest
    rect_summary = patches.Rectangle((3.5, y_pos - 1.2), 93, 3.2, facecolor="#DCFCE7", edgecolor="#86EFAC", linewidth=1.1)
    ax.add_patch(rect_summary)

    ax.text(50, y_pos + 0.4, "======================== 24 passed, 3 warnings in 71.30s (0:01:11) ========================",
            fontsize=7.4, family="monospace", fontweight="bold", ha="center", va="center", color="#166534")

    # Guardado de la figura
    img_filename = "figura_3_37_pruebas_verificacion_sprint5.png"
    out_path = os.path.join(OUTPUT_DIR, img_filename)
    plt.tight_layout(pad=0.2)
    plt.savefig(out_path, dpi=300, facecolor="#FFFFFF", edgecolor="none")
    plt.close()
    print(f"Figura 3.37 generada exitosamente en: {out_path}")

    # Copia al brain de artefactos
    if os.path.isdir(BRAIN_DIR):
        brain_path = os.path.join(BRAIN_DIR, img_filename)
        shutil.copyfile(out_path, brain_path)
        print(f"Copiada a artefactos: {brain_path}")

if __name__ == "__main__":
    generar_figura_3_37()
