"""
scripts/generar_figura_3_25_json.py
------------------------------------
Genera la Figura 3.25 en formato PNG de alta resolución (300 DPI, ancho >= 2000 px):
"Figura 3.25 Captura de respuesta JSON de los endpoints de pronóstico (/forecast/alumnos y /forecast/metas)"

Normas aplicadas:
- Fondo blanco puro (#FFFFFF).
- Estilo dos paneles lado a lado con sintaxis JSON limpia y monoespaciada.
- Sin título incrustado dentro del canvas (el título va en la leyenda de Word).
- Datos reales y exactos devueltos por el motor predictivo de FastAPI:
  * GET /api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=6 (Holt-Winters Aditivo con IC)
  * GET /api/v1/forecast/metas?granularidad=ANUAL&horizonte=2 (Regresión Lineal OLS N=3)
"""

import os
import shutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_DIR = os.path.abspath("docs/images")
BRAIN_DIR = r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generar_figura_3_25():
    fig, ax = plt.subplots(figsize=(12, 7.8), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # ── PANEL IZQUIERDO: GET /api/v1/forecast/alumnos (Holt-Winters) ───────
    rect_left = patches.FancyBboxPatch(
        (2, 2.5), 46.5, 95,
        boxstyle="round,pad=0.5,rounding_size=1.2",
        edgecolor="#222222", facecolor="#FAFAFA", linewidth=1.2
    )
    ax.add_patch(rect_left)

    rect_left_bar = patches.Rectangle((2, 91.5), 46.5, 6, facecolor="#EBEBEB", edgecolor="#222222", linewidth=1.1)
    ax.add_patch(rect_left_bar)
    ax.text(25.25, 94.5, "GET /api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=6",
            fontsize=7.8, family="monospace", fontweight="bold", ha="center", va="center", color="#000000")

    json_alumnos = """{
  "status": "success",
  "data": {
    "caso_uso": "ALUMNOS_GLOBAL",
    "tipo_solicitado": "GLOBAL",
    "metodo": "HoltWinters",
    "parametros": {
      "damped_trend": true,
      "phi": 0.9072,
      "m": 12
    },
    "n_observaciones": 43,
    "rmse": 59.57,
    "mape_pct": 15.67,
    "horizonte_meses": 6,
    "proyecciones": [
      {
        "periodo": "2026-06",
        "valor_forecast": 396.44,
        "ic_lower": 279.68,
        "ic_upper": 513.19
      },
      {
        "periodo": "2026-07",
        "valor_forecast": 423.55,
        "ic_lower": 306.80,
        "ic_upper": 540.30
      },
      {
        "periodo": "2026-08",
        "valor_forecast": 479.38,
        "ic_lower": 362.63,
        "ic_upper": 596.13
      },
      {
        "periodo": "2026-09",
        "valor_forecast": 440.72,
        "ic_lower": 323.96,
        "ic_upper": 557.47
      },
      {
        "periodo": "2026-10",
        "valor_forecast": 416.17,
        "ic_lower": 299.42,
        "ic_upper": 532.92
      },
      {
        "periodo": "2026-11",
        "valor_forecast": 402.81,
        "ic_lower": 286.05,
        "ic_upper": 519.56
      }
    ]
  }
}"""
    ax.text(3.5, 89.5, json_alumnos, fontsize=7.4, family="monospace", va="top", ha="left", color="#111111")

    # ── PANEL DERECHO: GET /api/v1/forecast/metas (OLS Anual) ─────────────
    rect_right = patches.FancyBboxPatch(
        (51.5, 2.5), 46.5, 95,
        boxstyle="round,pad=0.5,rounding_size=1.2",
        edgecolor="#222222", facecolor="#FAFAFA", linewidth=1.2
    )
    ax.add_patch(rect_right)

    rect_right_bar = patches.Rectangle((51.5, 91.5), 46.5, 6, facecolor="#EBEBEB", edgecolor="#222222", linewidth=1.1)
    ax.add_patch(rect_right_bar)
    ax.text(74.75, 94.5, "GET /api/v1/forecast/metas?granularidad=ANUAL&horizonte=2",
            fontsize=7.8, family="monospace", fontweight="bold", ha="center", va="center", color="#000000")

    json_metas = """{
  "caso_uso": "META_ANUAL",
  "granularidad": "ANUAL",
  "metodo": "OLS",
  "tipo_estimacion": "Proyección indicativa lineal",
  "pendiente_anual_bs": 2436141.68,
  "cagr_historico_pct": 26.76,
  "nota_metodologica": "Muestra N=3 (dof=1).
    Tendencia lineal indicativa sin IC 95%
    por reducida muestra longitudinal.",
  "proyecciones": [
    {
      "periodo": "2026",
      "monto_proyectado_bs": 15183417.34,
      "ic_lower": null,
      "ic_upper": null
    },
    {
      "periodo": "2027",
      "monto_proyectado_bs": 17619559.02,
      "ic_lower": null,
      "ic_upper": null
    }
  ]
}"""
    ax.text(53.0, 89.5, json_metas, fontsize=7.4, family="monospace", va="top", ha="left", color="#111111")

    out_file = os.path.join(OUTPUT_DIR, "figura_3_25_captura_respuesta_json_forecast.png")
    plt.tight_layout()
    plt.savefig(out_file, dpi=300, facecolor="#FFFFFF", bbox_inches="tight")
    plt.close()
    print(f"Figura 3.25 generada exitosamente en: {out_file}")

    v2_dir = os.path.abspath("docs/evidencias/graficos_v2")
    os.makedirs(v2_dir, exist_ok=True)
    dst_v2 = os.path.join(v2_dir, "figura_3_25_captura_respuesta_json_forecast.png")
    shutil.copy2(out_file, dst_v2)
    print(f"Copiada a: {dst_v2}")

    if os.path.exists(BRAIN_DIR):
        dst = os.path.join(BRAIN_DIR, "figura_3_25_captura_respuesta_json_forecast.png")
        shutil.copy2(out_file, dst)
        print(f"Copiada a artefactos del asistente: {dst}")

if __name__ == "__main__":
    generar_figura_3_25()
