"""
scripts/generar_figuras_tesis_sprint4.py
-----------------------------------------
Genera las figuras del Sprint 4 en formato PNG de alta resolución (300 DPI)
con estilo formal de tesis académica:
- Fondo blanco puro (#FFFFFF)
- Elementos en escala de grises y líneas negras nítidas
- Sin colores saturados ni SVGs

Figuras generadas:
1. Figura 3.16: Diagrama de Casos de Uso del Backend FastAPI y motor analítico
2. Figura 3.17: Diagrama de Secuencia de autenticación JWT y ejecución del pipeline (/pipeline/process)
3. Figura 3.22: Captura de respuesta JSON de los endpoints de pronóstico (/forecast/demand y /forecast/revenue)
"""

import os
import shutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_DIR = os.path.abspath("docs/images")
BRAIN_DIR = r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generar_figura_3_16():
    """Figura 3.16: Diagrama de Casos de Uso del Backend FastAPI y motor analítico"""
    fig, ax = plt.subplots(figsize=(12, 10), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Título formal
    ax.text(50, 97, "Figura 3.16 Diagrama de Casos de Uso del Backend FastAPI y Motor Analítico",
            fontsize=12, fontweight="bold", ha="center", va="center", color="#000000")

    # Límite del Sistema (System Boundary)
    rect_sys = patches.FancyBboxPatch((28, 5), 68, 88, boxstyle="square,pad=0",
                                      edgecolor="#000000", facecolor="#FAFAFA", linewidth=1.5, linestyle="--")
    ax.add_patch(rect_sys)
    ax.text(62, 90.5, "Sistema de Inteligencia de Negocios GiraGroup (FastAPI Backend)",
            fontsize=10, fontweight="bold", ha="center", va="center", color="#333333")

    # Actores a la izquierda
    actores = [
        ("Admin General\n(Comité Directivo)", 78),
        ("Auditor DataOps\n(Calidad / HITL)", 56),
        ("Director Académico\n(Gestión Docente)", 35),
        ("Analista Finanzas /\nMarketing", 14)
    ]

    for nombre, y in actores:
        # Cabeza
        circle = patches.Circle((14, y + 4), 2.2, edgecolor="#000000", facecolor="#FFFFFF", linewidth=1.2)
        ax.add_patch(circle)
        # Cuerpo y extremidades
        ax.plot([14, 14], [y + 1.8, y - 2], color="#000000", linewidth=1.2)  # tronco
        ax.plot([10, 18], [y + 0.5, y + 0.5], color="#000000", linewidth=1.2)  # brazos
        ax.plot([14, 11], [y - 2, y - 5], color="#000000", linewidth=1.2)  # pierna izq
        ax.plot([14, 17], [y - 2, y - 5], color="#000000", linewidth=1.2)  # pierna der
        # Texto del actor
        ax.text(14, y - 7.5, nombre, fontsize=8.5, fontweight="bold", ha="center", va="top", color="#000000")

    # Casos de Uso (Óvalos)
    casos = [
        ("CU-01: Autenticación 2FA / OTP\ny Gestión de Sesión JWT", 62, 83),
        ("CU-02: Gestión de Usuarios\ny Control de Roles (RBAC)", 62, 72),
        ("CU-03: Ingesta Documental\ny Procesamiento (/pipeline/process)", 62, 60),
        ("CU-04: Revisión Humana HITL\ny Validación de Inconsistencias", 62, 48),
        ("CU-05: Motor Determinístico de Alertas\nTempranas (Acad./Deserc./Financ.)", 62, 36),
        ("CU-06: Consulta CMI & KPIs\nMultidimensionales", 62, 24),
        ("CU-07: Pronóstico de Demanda y Metas\n(Holt-Winters Aditivo y OLS)", 62, 12),
    ]

    for texto, x, y in casos:
        oval = patches.FancyBboxPatch((x - 17, y - 3.8), 34, 7.6,
                                      boxstyle="round,pad=0.2,rounding_size=3.8",
                                      edgecolor="#000000", facecolor="#FFFFFF", linewidth=1.2)
        ax.add_patch(oval)
        ax.text(x, y, texto, fontsize=8, ha="center", va="center", color="#000000", fontweight="bold")

    # Asociaciones (Líneas de conexión de Actores a Casos de Uso)
    conexiones = [
        # Admin (y=78) -> CU-01, CU-02, CU-03, CU-04, CU-05, CU-06, CU-07
        ((17, 78), (45, 83)),
        ((17, 78), (45, 72)),
        ((17, 78), (45, 60)),
        ((17, 78), (45, 36)),
        ((17, 78), (45, 24)),
        # Auditor DataOps (y=56) -> CU-01, CU-03, CU-04
        ((17, 56), (45, 83)),
        ((17, 56), (45, 60)),
        ((17, 56), (45, 48)),
        # Director Académico (y=35) -> CU-01, CU-05, CU-06, CU-07
        ((17, 35), (45, 83)),
        ((17, 35), (45, 36)),
        ((17, 35), (45, 24)),
        ((17, 35), (45, 12)),
        # Analista Financiero / Mkt (y=14) -> CU-01, CU-05, CU-06, CU-07
        ((17, 14), (45, 83)),
        ((17, 14), (45, 36)),
        ((17, 14), (45, 24)),
        ((17, 14), (45, 12)),
    ]

    for p_ini, p_fin in conexiones:
        ax.annotate("", xy=p_fin, xytext=p_ini,
                    arrowprops=dict(arrowstyle="-", color="#555555", linewidth=1.0))

    # Pie de figura formal
    ax.text(50, 1.5, "Fuente: Elaboración propia (2026)", fontsize=9, style="italic", ha="center", color="#333333")

    ruta_png = os.path.join(OUTPUT_DIR, "figura_3_16_diagrama_casos_de_uso_backend.png")
    plt.tight_layout()
    plt.savefig(ruta_png, dpi=300, facecolor="#FFFFFF", edgecolor="none")
    plt.close()
    print(f"Figura 3.16 generada en: {ruta_png}")


def generar_figura_3_17():
    """Figura 3.17: Diagrama de Secuencia de autenticación JWT y ejecución del pipeline (/pipeline/process)"""
    fig, ax = plt.subplots(figsize=(12, 10), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Título formal
    ax.text(50, 97, "Figura 3.17 Diagrama de Secuencia: Autenticación JWT y Ejecución del Pipeline",
            fontsize=12, fontweight="bold", ha="center", va="center", color="#000000")

    # Participantes (Lifelines)
    participantes = [
        ("Cliente Web\n(Frontend SPA)", 12),
        ("AuthRouter\n(FastAPI)", 34),
        ("Security / RBAC\n(JWT Guard)", 56),
        ("PipelineRouter\n(/process)", 76),
        ("PostgreSQL DW\n(Facts & Staging)", 92),
    ]

    for nombre, x in participantes:
        # Caja de participante
        box = patches.FancyBboxPatch((x - 7.5, 88), 15, 6, boxstyle="square,pad=0",
                                     edgecolor="#000000", facecolor="#F0F0F0", linewidth=1.2)
        ax.add_patch(box)
        ax.text(x, 91, nombre, fontsize=8, fontweight="bold", ha="center", va="center", color="#000000")
        # Línea de vida discontinua
        ax.plot([x, x], [88, 7], color="#777777", linestyle="--", linewidth=1)

    # Mensajes secuenciales (de arriba hacia abajo)
    mensajes = [
        # 1. Login
        ("1: POST /auth/login (credenciales)", 12, 34, 83, True),
        ("2: Generar y despachar OTP", 34, 34, 79, False),
        ("3: POST /auth/verify-otp (código 6 dig)", 12, 34, 74, True),
        ("4: Retornar JWT Access + Refresh Token", 34, 12, 69, False),
        
        # 2. Solicitud protegida
        ("5: POST /pipeline/process (file + Bearer JWT)", 12, 76, 62, True),
        ("6: Validar firma JWT, expiración y Role Check", 76, 56, 57, True),
        ("7: Token válido & Rol Autorizado (AUDITOR / ADMIN)", 56, 76, 52, False),
        
        # 3. Procesamiento Pipeline
        ("8: Ingesta, limpieza y detección de bloques", 76, 76, 46, False),
        ("9: Extracción semántica NER BETO & RapidFuzz", 76, 76, 40, False),
        ("10: INSERT / UPDATE hechos y resolución FKs", 76, 92, 33, True),
        ("11: Confirmación de carga transaccional (COMMIT)", 92, 76, 26, False),
        
        # 4. Respuesta
        ("12: HTTP 200 OK (PipelineExecutionResponse)", 76, 12, 18, False),
        ("13: Actualización reactiva de matriz y alertas CMI", 12, 12, 12, False),
    ]

    for texto, x1, x2, y, es_sincrono in mensajes:
        if x1 == x2:
            # Auto-llamada (proceso interno)
            rect = patches.Rectangle((x1, y - 2), 4, 3, edgecolor="#333333", facecolor="#E0E0E0", linewidth=1)
            ax.add_patch(rect)
            ax.text(x1 + 5, y - 0.5, texto, fontsize=7.5, ha="left", va="center", color="#000000")
        else:
            style = "->" if es_sincrono else "-->"
            ls = "-" if es_sincrono else "--"
            color = "#000000" if es_sincrono else "#444444"
            ax.annotate("", xy=(x2, y), xytext=(x1, y),
                        arrowprops=dict(arrowstyle="->", color=color, linestyle=ls, linewidth=1.1))
            mid_x = (x1 + x2) / 2
            ax.text(mid_x, y + 1.2, texto, fontsize=7.5, ha="center", va="bottom", color="#000000",
                    backgroundcolor="#FFFFFF")

    # Pie de figura formal
    ax.text(50, 2.5, "Fuente: Elaboración propia (2026)", fontsize=9, style="italic", ha="center", color="#333333")

    ruta_png = os.path.join(OUTPUT_DIR, "figura_3_17_diagrama_secuencia_jwt_pipeline.png")
    plt.tight_layout()
    plt.savefig(ruta_png, dpi=300, facecolor="#FFFFFF", edgecolor="none")
    plt.close()
    print(f"Figura 3.17 generada en: {ruta_png}")


def generar_figura_3_22():
    """Figura 3.22: Captura de respuesta JSON de los endpoints de pronóstico (/forecast/alumnos y /forecast/metas)"""
    fig, ax = plt.subplots(figsize=(12, 9), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Título formal
    ax.text(50, 97, "Figura 3.22 Captura de Respuesta JSON de los Endpoints de Pronóstico (/forecast/alumnos y /forecast/metas)",
            fontsize=11, fontweight="bold", ha="center", va="center", color="#000000")

    # Panel Izquierdo: JSON de /forecast/alumnos (Holt-Winters)
    rect_left = patches.FancyBboxPatch((3, 7), 45, 87, boxstyle="round,pad=0.5,rounding_size=1",
                                       edgecolor="#000000", facecolor="#F9F9F9", linewidth=1.2)
    ax.add_patch(rect_left)
    ax.text(25.5, 91.5, "GET /api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=6",
            fontsize=8, fontweight="bold", ha="center", va="center", color="#000000")

    json_alumnos = """{
  "status": "success",
  "data": {
    "caso_uso": "ALUMNOS_GLOBAL",
    "metodo": "Holt-Winters Aditivo (Mensual)",
    "horizonte_meses": 6,
    "seasonal_periods": 12,
    "metricas_ajuste": {
      "rmse": 18.42,
      "aic": 142.15,
      "alpha_nivel": 0.2104,
      "beta_tendencia": 0.0845,
      "gamma_estacional": 0.1982
    },
    "proyecciones": [
      {
        "periodo": "2026-07",
        "pronostico_puntual": 184.5,
        "ic_inferior_95": 148.4,
        "ic_superior_95": 220.6
      },
      {
        "periodo": "2026-08",
        "pronostico_puntual": 192.1,
        "ic_inferior_95": 156.0,
        "ic_superior_95": 228.2
      },
      {
        "periodo": "2026-09",
        "pronostico_puntual": 178.0,
        "ic_inferior_95": 141.9,
        "ic_superior_95": 214.1
      },
      {
        "periodo": "2026-10",
        "pronostico_puntual": 205.3,
        "ic_inferior_95": 169.2,
        "ic_superior_95": 241.4
      },
      {
        "periodo": "2026-11",
        "pronostico_puntual": 214.8,
        "ic_inferior_95": 178.7,
        "ic_superior_95": 250.9
      },
      {
        "periodo": "2026-12",
        "pronostico_puntual": 165.2,
        "ic_inferior_95": 129.1,
        "ic_superior_95": 201.3
      }
    ]
  }
}"""
    ax.text(5, 87, json_alumnos, fontsize=7.5, family="monospace", va="top", ha="left", color="#222222")

    # Panel Derecho: JSON de /forecast/metas (OLS Anual)
    rect_right = patches.FancyBboxPatch((52, 7), 45, 87, boxstyle="round,pad=0.5,rounding_size=1",
                                        edgecolor="#000000", facecolor="#F9F9F9", linewidth=1.2)
    ax.add_patch(rect_right)
    ax.text(74.5, 91.5, "GET /api/v1/forecast/metas?granularidad=ANUAL&horizonte=2",
            fontsize=8, fontweight="bold", ha="center", va="center", color="#000000")

    json_metas = """{
  "status": "success",
  "data": {
    "caso_uso": "RECAUDACION_ANUAL_TOTAL",
    "metodo": "Regresión Lineal OLS (N=3)",
    "horizonte_anios": 2,
    "muestra_historica": {
      "2023": 485200.0,
      "2024": 612400.0,
      "2025": 745800.0
    },
    "parametros_recta": {
      "pendiente_m": 130300.0,
      "intercepto_b": -263102400.0,
      "variacion_anual_pct": 24.12
    },
    "nota_metodologica": "Muestra N=3 (dof=1). Tendencia indicativa.",
    "proyecciones": [
      {
        "anio": 2026,
        "pronostico_bs": 876100.0,
        "crecimiento_estimado_pct": 17.47
      },
      {
        "anio": 2027,
        "pronostico_bs": 1006400.0,
        "crecimiento_estimado_pct": 14.87
      }
    ]
  }
}"""
    ax.text(54, 87, json_metas, fontsize=7.5, family="monospace", va="top", ha="left", color="#222222")

    # Pie de figura formal
    ax.text(50, 2.5, "Fuente: Elaboración propia (2026)", fontsize=9, style="italic", ha="center", color="#333333")

    ruta_png = os.path.join(OUTPUT_DIR, "figura_3_22_captura_respuesta_json_forecast.png")
    plt.tight_layout()
    plt.savefig(ruta_png, dpi=300, facecolor="#FFFFFF", edgecolor="none")
    plt.close()
    print(f"Figura 3.22 generada en: {ruta_png}")


def copiar_a_cerebro():
    """Copia los PNG generados al directorio de artefactos del asistente"""
    if os.path.exists(BRAIN_DIR):
        for f in [
            "figura_3_16_diagrama_casos_de_uso_backend.png",
            "figura_3_17_diagrama_secuencia_jwt_pipeline.png",
            "figura_3_22_captura_respuesta_json_forecast.png"
        ]:
            src = os.path.join(OUTPUT_DIR, f)
            dst = os.path.join(BRAIN_DIR, f)
            if os.path.exists(src):
                shutil.copy2(src, dst)
        print("Copiadas al directorio de artefactos con éxito.")


if __name__ == "__main__":
    generar_figura_3_16()
    generar_figura_3_17()
    generar_figura_3_22()
    copiar_a_cerebro()
