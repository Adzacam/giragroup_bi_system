# -*- coding: utf-8 -*-
"""
Generación de gráficas para Defensa (.pptx) y Tesis (.docx)
Paleta institucional: Univalle Guindo + Azul Marino + Dorado
Resolución: 300 DPI
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

OUT = Path("docs/evidencias/graficas_defensa")
OUT.mkdir(parents=True, exist_ok=True)

# Paleta institucional (Univalle Guindo + Azul Marino + Dorado)
NAVY = "#1B365D"
WINE = "#8B1538"
GOLD = "#C8963E"
TEAL = "#2A7B6F"
GRAY = "#64748B"
LIGHT = "#E2E8F0"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# ==============================================================================
# 1. GANTT DE SPRINTS (Diapositiva 11 - Izquierda)
# ==============================================================================
fig, ax = plt.subplots(figsize=(7.5, 3.6), dpi=300)
sprints = [
    ("S1 · Docker y DW Constelación", 0, 2, NAVY),
    ("S2 · Ingesta Multiarchivo", 2, 2, NAVY),
    ("S3 · Modelo BETO + RapidFuzz", 4, 2, GOLD),
    ("S4 · API 2FA, Alertas y HW/OLS", 6, 2, NAVY),
    ("S5 · Web React y CMI (23 KPI)", 8, 2, NAVY),
    ("S6 · SQA, Carga y Despliegue", 10, 2, TEAL),
    ("F9–F12 · Estabilización y HITL", 12, 2, WINE),
]
fechas = [
    "01/06–15/06", "15/06–29/06", "29/06–13/07", "13/07–27/07",
    "27/07–10/08", "10/08–24/08", "Sep–Nov"
]

y_pos = np.arange(len(sprints))[::-1]
for i, ((label, start, dur, color), f_txt) in enumerate(zip(sprints, fechas)):
    y = y_pos[i]
    ax.barh(y, dur, left=start, height=0.58, color=color, alpha=0.92, edgecolor="white")
    ax.text(start + dur / 2, y, f_txt, ha="center", va="center",
            color="white", fontsize=8, fontweight="bold")

ax.set_yticks(y_pos)
ax.set_yticklabels([s[0] for s in sprints], fontsize=8.5, fontweight="bold", color="#1E293B")
ax.set_xticks([0, 2, 4, 6, 8, 10, 12, 14])
ax.set_xticklabels(["Jun", "15/06", "Jul", "13/07", "27/07", "Ago", "24/08", "Nov"], fontsize=8)
ax.grid(axis="x", linestyle="--", alpha=0.45, color="#94A3B8")
ax.set_title("Cronograma de Sprints (Jira GCB) y Estabilización", fontsize=10, fontweight="bold", color=NAVY, pad=10)
plt.tight_layout()
fig.savefig(OUT / "01_scrum_gantt.png", dpi=300)
plt.close(fig)

# ==============================================================================
# 2. VELOCIDAD Y QUEMADO DEL BACKLOG (Diapositiva 11 - Derecha)
# ==============================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.2, 3.3), dpi=300)
s_labels = ["S1", "S2", "S3", "S4", "S5", "S6"]
vel = [55, 55, 68, 76, 76, 63]
col_vel = [NAVY, NAVY, GOLD, NAVY, NAVY, TEAL]

bars = ax1.bar(s_labels, vel, color=col_vel, width=0.58)
for b in bars:
    ax1.text(b.get_x() + b.get_width()/2, b.get_height() + 2, f"{int(b.get_height())}",
             ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#1E293B")
ax1.set_ylim(0, 92)
ax1.set_ylabel("Puntos de historia (PH)", fontsize=8.5)
ax1.set_title("Velocidad por sprint (Total: 393 PH)", fontsize=9.5, fontweight="bold", color=NAVY)
ax1.grid(axis="y", linestyle="--", alpha=0.4)

x_burn = ["Inicio", "S1", "S2", "S3", "S4", "S5", "S6"]
real_burn = [393, 338, 283, 215, 139, 63, 0]
ideal_burn = np.linspace(393, 0, len(x_burn))

ax2.plot(x_burn, ideal_burn, linestyle="--", color=GRAY, linewidth=1.4, label="Ritmo ideal")
ax2.plot(x_burn, real_burn, marker="o", color=WINE, linewidth=2.2, markersize=6,
         markerfacecolor="white", markeredgewidth=2, label="Restante real")
for x, y in zip(x_burn, real_burn):
    ax2.text(x, y + 14, f"{y}", ha="center", va="bottom", fontsize=8, fontweight="bold", color=WINE)
ax2.set_ylim(0, 445)
ax2.set_title("Quemado del Backlog (PH restantes)", fontsize=9.5, fontweight="bold", color=NAVY)
ax2.grid(axis="y", linestyle="--", alpha=0.4)
ax2.legend(frameon=False, fontsize=8, loc="upper right")
plt.tight_layout()
fig.savefig(OUT / "02_scrum_velocidad_quemado.png", dpi=300)
plt.close(fig)

# ==============================================================================
# 3. DATOS Y PARTICIÓN CRISP-DM (Diapositiva 14 - Derecha)
# ==============================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.8, 3.6), dpi=300)

# 3A: Entidades en Conjunto de Prueba de Referencia (510 entidades)
tipos = ["PER_DOCENTE", "PER_ESTUDIANTE", "MODULO", "PROGRAMA"]
cant = [50, 130, 150, 180]
bars1 = ax1.barh(tipos, cant, color=[GRAY, TEAL, GOLD, NAVY], height=0.55)
for b in bars1:
    w = b.get_width()
    ax1.text(w + 4, b.get_y() + b.get_height()/2, f"{int(w)} ({w/510*100:.1f} %)",
             va="center", fontsize=8, fontweight="bold", color="#1E293B")
ax1.set_xlim(0, 245)
ax1.set_xlabel("Cantidad de entidades", fontsize=8.5)
ax1.set_title("Entidades en prueba de referencia\n(Total = 510 entidades)", fontsize=9.5, fontweight="bold", color=NAVY)
ax1.grid(axis="x", linestyle="--", alpha=0.4)

# 3B: Partición del corpus etiquetado (líneas + personas únicas, fuga = 0)
conj = ["Entrenamiento\n(2.447 pers.)", "Validación\n(597 pers.)", "Prueba ref.\n(83 pers.)"]
lineas = [1400, 350, 180]
pcts = [l / sum(lineas) * 100 for l in lineas]
bars2 = ax2.bar(conj, lineas, color=[NAVY, GOLD, TEAL], width=0.55)
for b, p in zip(bars2, pcts):
    h = b.get_height()
    ax2.text(b.get_x() + b.get_width()/2, h + 30, f"{int(h):,}".replace(",", ".") + f"\n({p:.1f} %)",
             ha="center", va="bottom", fontsize=8, fontweight="bold", color="#1E293B")
ax2.set_ylim(0, 1720)
ax2.set_ylabel("Líneas etiquetadas (IOB2)", fontsize=8.5)
ax2.set_title("Partición por persona (fuga = 0)\n(Total = 1.930 líneas)", fontsize=9.5, fontweight="bold", color=NAVY)
ax2.grid(axis="y", linestyle="--", alpha=0.4)

plt.tight_layout()
fig.savefig(OUT / "03_corpus_entidades_particion.png", dpi=300)
plt.close(fig)

# ==============================================================================
# 4. GRÁFICO 3.2 ACTUALIZADO — BANDAS LOTE 1.387 (Tesis Cap. III)
# ==============================================================================
fig, ax = plt.subplots(figsize=(7.6, 3.0), dpi=300)
bandas = [
    "Retenido en Staging (< 0,60)",
    "Revisión humana HITL (0,60–0,85)",
    "Consolidación directa (≥ 0,85 y personas)",
]
vals = [0, 31, 1356]
col_b = [WINE, GOLD, NAVY]
bars = ax.barh(bandas, vals, color=col_b, height=0.52)
for b in bars:
    w = b.get_width()
    pct = w / 1387 * 100
    lbl = f"{int(w):,}".replace(",", ".") + f" ({pct:.2f} %)".replace(".", ",")
    ax.text(w + 22, b.get_y() + b.get_height()/2, lbl,
            va="center", fontsize=8.8, fontweight="bold", color="#1E293B")
ax.set_xlim(0, 1720)
ax.set_xlabel("Cantidad de registros evaluados (Total N = 1.387)", fontsize=8.8)
ax.grid(axis="x", linestyle="--", alpha=0.4)
plt.tight_layout()
fig.savefig(OUT / "04_grafico_3_2_bandas_lote_1387.png", dpi=300)
plt.close(fig)

# ==============================================================================
# 5. GRÁFICO 3.3 ACTUALIZADO — ABLACIÓN A/B/C CON NOMBRES LIMPIOS (Cap. III y Diap. 15)
# ==============================================================================
fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=300)
grupos = [
    "Prueba de referencia (510 ent.)\nF1 micro estricto",
    "Formatos no vistos (5 planillas)\nF1 micro relajado"
]
modo_a = [100.00, 28.57]
modo_b = [100.00, 73.76]
modo_c = [97.96, 72.06]

x = np.arange(len(grupos))
w = 0.24
b1 = ax.bar(x - w, modo_a, w, label="Modo A (Reglas puras)", color=LIGHT, edgecolor=NAVY, hatch="//")
b2 = ax.bar(x,     modo_b, w, label="Modo B (Híbrido implementado)", color=NAVY)
b3 = ax.bar(x + w, modo_c, w, label="Modo C (BETO puro)", color=GOLD)

for bars_grp in (b1, b2, b3):
    for b in bars_grp:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width()/2, h + 1.8, f"{h:.2f} %".replace(".", ","),
                ha="center", va="bottom", fontsize=8.2, fontweight="bold", color="#1E293B")

ax.set_xticks(x)
ax.set_xticklabels(grupos, fontsize=9, fontweight="bold")
ax.set_ylim(0, 118)
ax.set_ylabel("Puntuación F1 (%)", fontsize=9)
ax.grid(axis="y", linestyle="--", alpha=0.4)
ax.legend(frameon=True, facecolor="white", edgecolor=LIGHT, fontsize=8.2, loc="upper right")
plt.tight_layout()
fig.savefig(OUT / "05_grafico_3_3_ablacion_abc.png", dpi=300)
plt.close(fig)

# ==============================================================================
# 6. GRÁFICO 4.5 ACTUALIZADO — TIEMPOS PRETEST VS POSTEST (Cap. IV y Diap. 18)
# ==============================================================================
fig, ax = plt.subplots(figsize=(6.8, 3.6), dpi=300)
escenarios = [
    "Pretest\n(Manual reconstruido)",
    "Postest ciclo + KLM\n(caché llena, f3_base)",
    "Postest solo máquina\n(carga fría, F9)",
]
minutos = [600.0, 20.52, 10.93]
col_t = [WINE, GOLD, TEAL]

bars = ax.bar(escenarios, minutos, color=col_t, width=0.5)
ax.set_yscale("log")
ax.set_ylim(5, 1400)
ax.axhline(15, color=NAVY, linestyle="--", linewidth=1.3, label="Meta RNF-03 (15 min)")

for b in bars:
    h = b.get_height()
    txt = f"{h:.2f} min".replace(".", ",") if h < 100 else f"{h:.0f} min"
    ax.text(b.get_x() + b.get_width()/2, h * 1.15, txt,
            ha="center", va="bottom", fontsize=8.8, fontweight="bold", color="#1E293B")

ax.set_ylabel("Tiempo por ciclo (minutos, escala log)", fontsize=8.5)
ax.set_title("Reducción del tiempo de consolidación (Pretest vs. Postest)", fontsize=9.8, fontweight="bold", color=NAVY)
ax.grid(axis="y", linestyle="--", alpha=0.4, which="both")
ax.legend(frameon=False, fontsize=8.5, loc="upper right")
plt.tight_layout()
fig.savefig(OUT / "06_grafico_4_5_tiempos_pre_post.png", dpi=300)
plt.close(fig)

print("Listo. 6 gráficas generadas en:", OUT.resolve())
