# -*- coding: utf-8 -*-
"""
Regeneración del Gráfico 3.2 (Lote de 1.387 registros) en escala de grises y tramas para el docx.
Resolución: 300 DPI
"""

from pathlib import Path
import matplotlib.pyplot as plt

OUT = Path("docs/evidencias/grafico_3_2_bandas_lote_1387.png")
OUT.parent.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

fig, ax = plt.subplots(figsize=(8.2, 3.0), dpi=300)

etiquetas = [
    "Retenido en Staging (< 0,60)",
    "Revisión humana HITL (0,60 - 0,85)",
    "Consolidación directa (≥ 0,85 y personas)",
]
valores = [0, 31, 1356]
total = 1387
colores = ["#9CA3AF", "#6B7280", "#4B5563"]
tramas = ["", "..", "//"]

bars = ax.barh(etiquetas, valores, height=0.52, color=colores, edgecolor="#111827", linewidth=1.0)
for bar, hatch in zip(bars, tramas):
    bar.set_hatch(hatch)
    w = bar.get_width()
    pct = (w / total) * 100
    txt = f"{int(w):,}".replace(",", ".") + f" ({pct:.2f} %)".replace(".", ",")
    ax.text(w + 22, bar.get_y() + bar.get_height() / 2, txt,
            va="center", ha="left", fontsize=9.5, color="#111827")

ax.set_xlim(0, 1720)
ax.set_xticks([0, 200, 400, 600, 800, 1000, 1200, 1400, 1600])
ax.set_xticklabels(["0", "200", "400", "600", "800", "1.000", "1.200", "1.400", "1.600"], fontsize=9)
ax.tick_params(axis="y", labelsize=9.5)
ax.set_xlabel("Cantidad de registros evaluados (Total N = 1.387)", fontsize=10, labelpad=6)
ax.grid(axis="x", linestyle=":", alpha=0.6, color="#6B7280")
ax.set_axisbelow(True)

plt.tight_layout()
fig.savefig(OUT, dpi=300)
plt.close(fig)
print("Gráfico 3.2 guardado en:", OUT.resolve())
