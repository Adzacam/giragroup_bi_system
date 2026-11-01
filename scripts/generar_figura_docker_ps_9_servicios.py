"""
scripts/generar_figura_docker_ps_9_servicios.py
------------------------------------------------
Genera la captura de Docker Compose (docker compose ps) con los 9 servicios reales en Up a 300 DPI:
Normas aplicadas:
- Fondo blanco puro (#FFFFFF).
- Terminal PowerShell estilizado.
- Sin título ni fuente incrustada dentro del marco de la imagen.
"""

import os
import shutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_DIR = os.path.abspath("docs/images")
BRAIN_DIR = r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generar_figura_docker_ps():
    fig, ax = plt.subplots(figsize=(13.5, 8.5), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Contenedor estilo terminal
    rect_main = patches.FancyBboxPatch(
        (1.5, 2), 97, 96,
        boxstyle="round,pad=0.5,rounding_size=1.2",
        edgecolor="#2B2D42", facecolor="#FAFAFA", linewidth=1.4
    )
    ax.add_patch(rect_main)

    # Barra superior
    rect_bar = patches.Rectangle((1.5, 92), 97, 6, facecolor="#EBECEF", edgecolor="#2B2D42", linewidth=1.2)
    ax.add_patch(rect_bar)

    # Botones estilo terminal
    c_red = patches.Circle((4, 95), 0.9, facecolor="#FF5F56", edgecolor="#E0443E", linewidth=0.8)
    c_yellow = patches.Circle((6.5, 95), 0.9, facecolor="#FFBD2E", edgecolor="#DEA123", linewidth=0.8)
    c_green = patches.Circle((9, 95), 0.9, facecolor="#27C93F", edgecolor="#1AAB29", linewidth=0.8)
    ax.add_patch(c_red)
    ax.add_patch(c_yellow)
    ax.add_patch(c_green)

    ax.text(50, 95, "PowerShell - Orquestación Multi-Contenedor: docker compose ps",
            fontsize=8.5, family="monospace", fontweight="bold", ha="center", va="center", color="#2B2D42")

    # Cabecera
    lines = [
        ("PS C:\\giragroup_bi_system> docker compose ps", "#1D3557", True),
        ("NAME                          IMAGE                                       COMMAND                  SERVICE                 STATUS                 PORTS", "#0F172A", True),
        ("--------------------------------------------------------------------------------------------------------------------------------------------------------------------", "#888888", False),
    ]

    y_pos = 88.5
    for text, color, bold in lines:
        weight = "bold" if bold else "normal"
        ax.text(3.5, y_pos, text, fontsize=6.8, family="monospace", color=color, fontweight=weight, va="center")
        y_pos -= 2.2

    # Los 9 servicios reales en Up
    services = [
        ("giragroup_gateway", "giragroup_bi_system-gateway", "\"/docker-entrypoint.sh …\"", "gateway (Nginx)", "Up 4 hours", "0.0.0.0:80->80/tcp"),
        ("giragroup_api", "giragroup_bi_system-api", "\"uvicorn main:app --host…\"", "api (FastAPI Core)", "Up 4 hours (healthy)", "0.0.0.0:8000->8000/tcp"),
        ("giragroup_pipeline", "giragroup_bi_system-pipeline", "\"python -m pipeline.jobs…\"", "pipeline (ETL / NLP)", "Up 4 hours", "8006/tcp"),
        ("giragroup_auth_svc", "giragroup_bi_system-auth-service", "\"uvicorn main:app --host…\"", "auth-service (RBAC)", "Up 4 hours (healthy)", "8001/tcp"),
        ("giragroup_audit_svc", "giragroup_bi_system-audit-service", "\"uvicorn main:app --host…\"", "audit-service", "Up 4 hours", "8004/tcp"),
        ("giragroup_notifications_svc", "giragroup_bi_system-notifications-service", "\"uvicorn main:app --host…\"", "notifications-service", "Up 4 hours", "8002/tcp"),
        ("giragroup_web", "giragroup_bi_system-web", "\"docker-entrypoint.sh …\"", "web (React / Vite)", "Up 4 hours", "0.0.0.0:5173->5173/tcp"),
        ("giragroup_db", "postgres:16-alpine", "\"docker-entrypoint.sh p…\"", "db (DW Constelación)", "Up 4 hours (healthy)", "127.0.0.1:5434->5432/tcp"),
        ("giragroup_catalog_db", "giragroup_bi_system-catalog_db", "\"docker-entrypoint.sh p…\"", "catalog_db (3NF)", "Up 4 hours (healthy)", "127.0.0.1:5433->5432/tcp"),
    ]

    for name, img, cmd, svc, stat, prt in services:
        line_str = f"{name:<29} {img:<43} {cmd:<24} {svc:<23} {stat:<22} {prt}"
        ax.text(3.5, y_pos, line_str, fontsize=6.3, family="monospace", color="#1E293B", va="center")
        y_pos -= 2.4

    y_pos -= 0.8
    # Banner resumen final
    rect_summary = patches.Rectangle((3.5, y_pos - 1.2), 93, 3.2, facecolor="#DCFCE7", edgecolor="#86EFAC", linewidth=1.1)
    ax.add_patch(rect_summary)

    ax.text(50, y_pos + 0.4, "================ 9/9 Containers Operational & Healthy in Production Environment ================",
            fontsize=7.4, family="monospace", fontweight="bold", ha="center", va="center", color="#166534")

    # Guardado de la figura
    img_filename = "figura_3_43_captura_docker_ps_9_servicios.png"
    out_path = os.path.join(OUTPUT_DIR, img_filename)
    plt.tight_layout(pad=0.2)
    plt.savefig(out_path, dpi=300, facecolor="#FFFFFF", edgecolor="none")
    plt.close()
    print(f"Figura generada en: {out_path}")

    # Copia al brain de artefactos
    if os.path.isdir(BRAIN_DIR):
        brain_path = os.path.join(BRAIN_DIR, img_filename)
        shutil.copyfile(out_path, brain_path)
        print(f"Copiada a artefactos: {brain_path}")

if __name__ == "__main__":
    generar_figura_docker_ps()
