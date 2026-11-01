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

os.makedirs("output", exist_ok=True)
os.makedirs("docs/images", exist_ok=True)
brain_dir = r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0"

# ==============================================================================
# 1. GRÁFICO 3.1: MATRIZ DE CONFUSIÓN
# ==============================================================================
# Clases: Módulo, Docente, Estudiante, Programa
# Datos exactos auditados:
# Módulo:     Soporte 150 -> TP = 150, FP = 0,  FN = 0
# Docente:    Soporte 50  -> TP = 50,  FP = 0,  FN = 0
# Estudiante: Soporte 130 -> TP = 128, FP = 0,  FN = 2 (confundidos con Programa)
# Programa:   Soporte 180 -> TP = 173, FP = 17, FN = 7 (7 no detectados / O)
# FP de Programa: 17 (2 de Estudiante + 15 de tokens espurios/O)

clases = ["Módulo", "Docente", "Estudiante", "Programa"]

# Matriz absoluta de confusión (4x4)
cm_abs = np.array([
    [150,   0,   0,   0],
    [  0,  50,   0,   0],
    [  0,   0, 128,   2],
    [  0,   0,   0, 173]
])

# Normalización por fila (Recall por clase)
cm_norm = cm_abs.astype(float) / cm_abs.sum(axis=1)[:, np.newaxis]

fig1, ax1 = plt.subplots(figsize=(6.5, 5.5), dpi=300)
im = ax1.imshow(cm_norm, cmap="Blues", interpolation="nearest", vmin=0, vmax=1)
cbar = fig1.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
cbar.ax.set_ylabel("Proporción Normalizada (Recall)", rotation=-90, va="bottom", fontsize=9)

ax1.set_xticks(range(len(clases)))
ax1.set_yticks(range(len(clases)))
ax1.set_xticklabels(clases, fontsize=9.5, fontweight="medium")
ax1.set_yticklabels(clases, fontsize=9.5, fontweight="medium")
ax1.set_xlabel("Clase Predicha por el Modelo BETO", fontsize=10, fontweight="bold", labelpad=8)
ax1.set_ylabel("Clase Real en Documento", fontsize=10, fontweight="bold", labelpad=8)
ax1.set_title("Gráfico 3.1 Matriz de Confusión del Reconocimiento de Entidades Nombradas (BETO)",
              fontsize=10.5, fontweight="bold", pad=12)

for i in range(len(clases)):
    for j in range(len(clases)):
        val_norm = cm_norm[i, j]
        val_abs = cm_abs[i, j]
        color = "white" if val_norm > 0.5 else "#111111"
        if val_abs > 0:
            texto = f"{val_norm:.3f}\n(n={val_abs})"
        else:
            texto = "0.000\n(n=0)"
        ax1.text(j, i, texto, ha="center", va="center", color=color, fontsize=8.5, fontweight="bold")

fig1.tight_layout()
p1 = "output/grafico_3_1_matriz_confusion_beto.png"
fig1.savefig(p1, dpi=300, facecolor="white")
fig1.savefig("docs/images/grafico_3_1_matriz_confusion_beto.png", dpi=300, facecolor="white")
if os.path.exists(brain_dir):
    shutil.copy2(p1, os.path.join(brain_dir, "grafico_3_1_matriz_confusion_beto.png"))
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
p2 = "output/grafico_3_3_desempeno_metricas_beto.png"
fig2.savefig(p2, dpi=300, facecolor="white")
fig2.savefig("docs/images/grafico_3_3_desempeno_metricas_beto.png", dpi=300, facecolor="white")
if os.path.exists(brain_dir):
    shutil.copy2(p2, os.path.join(brain_dir, "grafico_3_3_desempeno_metricas_beto.png"))
plt.close(fig2)
print(f"Generado: {p2}")
