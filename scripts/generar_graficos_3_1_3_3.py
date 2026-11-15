import os
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "serif",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

os.makedirs("docs/evidencias/graficos_v2", exist_ok=True)


# ==============================================================================
# 1. GRÁFICO 3.1: MATRIZ DE CONFUSIÓN (calculada, no escrita a mano)
# ==============================================================================
# Se alimenta de docs/evidencias/matriz_confusion_ner.json, que genera
# scripts/matriz_confusion_ner.py desde y_true/y_pred reales sobre test_gold_real.jsonl
# (token a token, con la clase O). Si el JSON no existe, el gráfico NO se regenera.
import json as _json
from pathlib import Path as _Path

_CM_JSON = _Path("docs/evidencias/matriz_confusion_ner.json")
if not _CM_JSON.exists():
    print(f"OMITIDO gráfico 3.1: falta {_CM_JSON}. Ejecute el entrenamiento/evaluación y "
          "scripts/matriz_confusion_ner.py antes de regenerarlo.")
else:
    _cm = _json.loads(_CM_JSON.read_text(encoding="utf-8"))
    clases = _cm["clases"]
    cm_abs = np.array(_cm["matriz"])
    _sumas = cm_abs.sum(axis=1)[:, np.newaxis]
    cm_norm = np.divide(cm_abs.astype(float), _sumas, out=np.zeros(cm_abs.shape), where=_sumas > 0)

    fig1, ax1 = plt.subplots(figsize=(7, 6), dpi=300)
    im = ax1.imshow(cm_norm, cmap="Blues", interpolation="nearest", vmin=0, vmax=1)
    cbar = fig1.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel("Proporción Normalizada (Recall)", rotation=-90, va="bottom", fontsize=9)
    ax1.set_xticks(range(len(clases)))
    ax1.set_yticks(range(len(clases)))
    ax1.set_xticklabels(clases, fontsize=8.5, rotation=20)
    ax1.set_yticklabels(clases, fontsize=8.5)
    ax1.set_xlabel("Predicho")
    ax1.set_ylabel("Real")
    ax1.set_title("Gráfico 3.1 Matriz de Confusión (token a token, incl. O) — test_gold_real", fontsize=10)
    for i in range(len(clases)):
        for j in range(len(clases)):
            color = "white" if cm_norm[i, j] > 0.5 else "#111111"
            ax1.text(j, i, f"{cm_norm[i, j]:.3f}\n(n={cm_abs[i, j]})", ha="center", va="center",
                     color=color, fontsize=7.5, fontweight="bold")
    fig1.tight_layout()
    p1 = "docs/evidencias/graficos_v2/grafico_3_1_matriz_confusion_beto.png"
    fig1.savefig(p1, dpi=300, facecolor="white")
    plt.close(fig1)
    print(f"Generado: {p1}")

# ==============================================================================
# 2. GRÁFICO 3.3: MÉTRICAS PRECISION, RECALL Y F1-SCORE POR ENTIDAD
# ==============================================================================
# Datos exactos auditados:
# Módulo:     P = 1.0000, R = 1.0000, F1 = 1.0000 (Soporte = 150)
# Docente:    P = 1.0000, R = 1.0000, F1 = 1.0000 (Soporte = 50)
# Estudiante: P = 1.0000, R = 0.9846, F1 = 0.9922 (Soporte = 130)
# Programa:   P = 0.9105, R = 0.9611, F1 = 0.9351 (Soporte = 180)

clases = ["Módulo", "Docente", "Estudiante", "Programa"]
precision = [1.0000, 1.0000, 1.0000, 0.9105]
recall    = [1.0000, 1.0000, 0.9846, 0.9611]
f1        = [1.0000, 1.0000, 0.9922, 0.9351]

x = np.arange(len(clases))
width = 0.25

fig2, ax2 = plt.subplots(figsize=(7.5, 4.4), dpi=300)

r1 = ax2.bar(x - width, precision, width, label="Precision", color="#333333", edgecolor="#111111")
r2 = ax2.bar(x, recall, width, label="Recall", color="#777777", edgecolor="#111111", hatch="//")
r3 = ax2.bar(x + width, f1, width, label="F1-Score", color="#CCCCCC", edgecolor="#111111", hatch="..")

ax2.set_ylabel("Puntaje de Rendimiento (0.00 - 1.00)", fontsize=9.5, fontweight="bold")
ax2.set_title("Gráfico 3.3 Desempeño de Métricas Precision, Recall y F1-Score por Tipo de Entidad (BETO)",
              fontsize=10.5, fontweight="bold", pad=12)
ax2.set_xticks(x)
ax2.set_xticklabels([f"{c}\n(n={s})" for c, s in zip(clases, [150, 50, 130, 180])], fontsize=9)
ax2.set_ylim(0.80, 1.03)
ax2.grid(axis="y", linestyle=":", alpha=0.6, color="#888888")
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)
ax2.legend(loc="lower right", frameon=False, fontsize=9)

def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax2.annotate(f"{height:.3f}",
                     xy=(rect.get_x() + rect.get_width() / 2, height),
                     xytext=(0, 3),
                     textcoords="offset points",
                     ha="center", va="bottom", fontsize=7.5, fontweight="bold")

autolabel(r1)
autolabel(r2)
autolabel(r3)

fig2.tight_layout()
p2 = "docs/evidencias/graficos_v2/grafico_3_3_desempeno_metricas_beto.png"
fig2.savefig(p2, dpi=300, facecolor="white")
plt.close(fig2)
print(f"Generado: {p2}")
