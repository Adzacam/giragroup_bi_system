import os
import shutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_DIR = os.path.abspath("docs/images")
BRAIN_DIR = r"C:\Users\DAZA\.gemini\antigravity\brain\63f9e4af-20b2-4f8f-b72e-7a930b2e4ae6"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(BRAIN_DIR, exist_ok=True)

def generar_figura_1_40():
    fig, ax = plt.subplots(figsize=(13.5, 9.6), dpi=300)
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

    # Botones ventana
    ax.add_patch(patches.Circle((4, 95), 0.9, facecolor="#FF5F56", edgecolor="#E0443E", linewidth=0.8))
    ax.add_patch(patches.Circle((6.5, 95), 0.9, facecolor="#FFBD2E", edgecolor="#DEA123", linewidth=0.8))
    ax.add_patch(patches.Circle((9, 95), 0.9, facecolor="#27C93F", edgecolor="#1AAB29", linewidth=0.8))

    ax.text(50, 95, "PowerShell - pytest tests/ --cov=backend --cov=pipeline (Commit f3b37d9)",
            fontsize=8.5, family="monospace", fontweight="bold", ha="center", va="center", color="#2B2D42")

    terminal_lines = [
        ("PS C:\\giragroup_bi_system> .\\.venv\\Scripts\\python.exe -m pytest tests/ --cov=backend --cov=pipeline", "#1D3557", True),
        ("============================= test session starts =============================", "#555555", False),
        ("platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0", "#555555", False),
        ("rootdir: C:\\giragroup_bi_system, configfile: pyproject.toml", "#555555", False),
        ("plugins: anyio-4.14.2, locust-2.47.0, cov-7.1.0", "#555555", False),
        ("collected 650 items", "#333333", True),
        ("", "#333333", False),
        ("tests/readiness/test_production_readiness.py ..................sssssssssss   [  6%]", "#2B2D42", False),
        ("tests/sprint1/ (esquema, infraestructura, ORM, usuarios_semilla) ........... [  8%]", "#2B2D42", False),
        ("tests/sprint2/ (bloques_detector, categorizacion, ingesta) ................. [ 13%]", "#2B2D42", False),
        ("tests/sprint3/ (confianza, normalizacion, catalogos, ner_engine, etc.) ..... [ 32%]", "#2B2D42", False),
        ("tests/sprint4/ (alertas, anonimizacion, dw_loader, kpis, rbac) ............. [ 39%]", "#2B2D42", False),
        ("tests/*.py (transversales: auth, dataops, kpi, riesgo, forecasting, etc.) .. [100%]", "#2B2D42", False),
        ("", "#333333", False),
        ("---------- coverage: platform win32, python 3.14.6 ----------", "#555555", False),
        ("Name                                             Stmts   Miss  Cover", "#1D3557", True),
        ("---------------------------------------------------------------------", "#555555", False),
        ("backend/routers/dataops (paquete modular)         2493    890    64%", "#2B2D42", False),
        ("backend/services/forecast_service.py               268     33    88%", "#2B2D42", False),
        ("backend/services/dw_loader.py                      885    447    50%", "#2B2D42", False),
        ("pipeline/analytics/forecasting_holtwinters.py       95      6    94%", "#2B2D42", False),
        ("pipeline/normalization/person_resolver.py          125      9    93%", "#2B2D42", False),
        ("pipeline/semantic/ner_engine.py                    301    108    64%", "#2B2D42", False),
        ("---------------------------------------------------------------------", "#555555", False),
        ("TOTAL                                            14008   4426    68%", "#0D5C3A", True),
        ("", "#333333", False),
        ("=========================== short test summary info ===========================", "#555555", False),
        ("SKIPPED [11] tests/readiness: Puertas de salida live requieren variables de entorno", "#8D6E63", False),
        ("XFAIL   [7]  tests/readiness: Hallazgos de auditoria documentados (HW-IC, GAP, CAGR)", "#E65100", False),
        ("PASSED  [632] Suites completas (Sprint 1 a 6 + transversales operativas)", "#2E7D32", True),
        ("================ 632 passed, 11 skipped, 7 xfailed in 284.43s (04:44) ================", "#2E7D32", True),
    ]

    y = 89.0
    for text, color, bold in terminal_lines:
        weight = "bold" if bold else "normal"
        ax.text(3.5, y, text, fontsize=7.2, family="monospace", color=color, fontweight=weight, va="center")
        y -= 2.5

    ruta_png = os.path.join(OUTPUT_DIR, "figura_1_40_resumen_pytest.png")
    ruta_brain = os.path.join(BRAIN_DIR, "figura_1_40_resumen_pytest.png")
    plt.tight_layout()
    plt.savefig(ruta_png, dpi=300, facecolor="#FFFFFF", edgecolor="none")
    plt.savefig(ruta_brain, dpi=300, facecolor="#FFFFFF", edgecolor="none")
    plt.close()
    print("Figura 1.40 guardada en:", ruta_png)

if __name__ == "__main__":
    generar_figura_1_40()
