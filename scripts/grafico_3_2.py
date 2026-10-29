import pandas as pd
import matplotlib.pyplot as plt

# Datos extraidos directamente de PostgreSQL (giragroup_db) excluyendo fact_situacion_financiera con fk_estado = 'A' (DEFAULT 1.0)
data = [
    {"rango": "Consolidado (≥ 0,85)", "n": 1046, "pct": 75.4},
    {"rango": "Revisión HITL (0,60 – 0,84)", "n": 200, "pct": 14.4},
    {"rango": "Retenido en Staging (< 0,60)", "n": 141, "pct": 10.2},
]
df = pd.DataFrame(data)
df.to_csv("confianza.csv", index=False)

plt.rcParams.update({
    "font.family": "serif",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

fig, ax = plt.subplots(figsize=(7.5, 4.2), facecolor="white")
bars = ax.bar(
    df["rango"],
    df["pct"],
    width=0.52,
    color=["#333333", "#888888", "#cccccc"],
    edgecolor="#111111",
    hatch=["", "//", ".."],
    linewidth=1.0,
)

for bar, row in zip(bars, df.itertuples()):
    h = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2.0,
        h + 1.8,
        f"{row.pct:.1f}% (n = {row.n:,})",
        ha="center",
        va="bottom",
        fontsize=9.5,
        fontweight="bold",
        color="#111111",
    )

ax.set_ylim(0, 90)
ax.set_ylabel("Proporción de registros (%)", fontsize=10)
ax.set_xlabel("Nivel de confianza probabilística e índice híbrido (c)", fontsize=10)
ax.grid(axis="y", linestyle=":", color="#bbbbbb", alpha=0.8)
ax.set_axisbelow(True)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

fig.tight_layout()
fig.savefig("grafico_3_2.png", dpi=300, facecolor="white")
fig.savefig("docs/images/grafico_3_2_distribucion_confianza_probabilistica.png", dpi=300, facecolor="white")
print("Gráfico 3.2 generado exitosamente: N =", df["n"].sum(), "| Suma pct =", df["pct"].sum())
