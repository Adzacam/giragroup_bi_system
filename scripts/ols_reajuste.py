"""Tarea 5 (ronda 5): OLS mensual de la recaudación PROGRAMAS (monto_ejecutado) del DW.
(1) Reajuste con 2023-01..2026-04 (N=40; mayo de 2026 parcial excluido), proyección 2026-06..2026-11 con IC 95 % de predicción.
(2) Hold-out de los últimos 6 meses (2025-11..2026-04), modelo entrenado en los 34 anteriores.
(3) Modelo entrenado hasta 2025-12 (N=36) frente al ejecutado real de enero a abril de 2026.
Uso: DATABASE_URL=... python scripts/ols_reajuste.py -> docs/evidencias/ols_reajuste.json"""
import json, os
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
Q = ("SELECT dt.periodo_mes, SUM(fr.monto_ejecutado)::float v FROM fact_rentabilidad fr JOIN dim_categoria_financiera c ON c.id_categoria=fr.id_categoria "
     "JOIN dim_tiempo dt ON dt.id_tiempo=fr.id_tiempo WHERE c.nombre_categoria='PROGRAMAS' AND fr.monto_ejecutado IS NOT NULL GROUP BY 1 ORDER BY 1")
m = pd.read_sql(text(Q), create_engine(os.environ["DATABASE_URL"])).set_index("periodo_mes").v
y = m[m.index <= "2026-04"]
assert len(y) == 40 and y.index[0] == "2023-01"


def ajustar(v):
    t = np.arange(len(v)); b, a = np.polyfit(t, v, 1); f = a + b * t
    return a, b, t, f


def pred(v, ts, nivel=0.95):
    a, b, t, f = ajustar(v); n = len(v)
    s2 = ((v - f) ** 2).sum() / (n - 2); sxx = ((t - t.mean()) ** 2).sum(); tc = stats.t.ppf(0.5 + nivel / 2, n - 2)
    mu = a + b * ts; se = np.sqrt(s2 * (1 + 1 / n + (ts - t.mean()) ** 2 / sxx))
    return mu, mu - tc * se, mu + tc * se


def mape(real, p):
    return float((abs(real - p) / abs(real)).mean() * 100)


a, b, t, f = ajustar(y.values)
r2 = 1 - ((y.values - f) ** 2).sum() / ((y.values - y.values.mean()) ** 2).sum()
ts = np.arange(41, 47)  # junio..noviembre de 2026 (mayo = índice 40, excluido)
mu, lo, hi = pred(y.values, ts)
meses = [f"2026-{k:02d}" for k in range(6, 12)]
res = {"serie": "PROGRAMAS monto_ejecutado, 2023-01..2026-04 (N=40); 2026-05 excluido por parcial",
       "ajuste_N40": {"pendiente_Bs_mes": round(float(b), 2), "intercepto": round(float(a), 2), "R2": round(float(r2), 4),
                      "RMSE_ajuste": round(float(np.sqrt(((y.values - f) ** 2).mean())), 2)},
       "proyeccion_2026-06_a_2026-11": [{"mes": k, "pronostico": round(float(u), 2), "ic95_inf": round(float(l), 2), "ic95_sup": round(float(h), 2)}
                                          for k, u, l, h in zip(meses, mu, lo, hi)]}
tr, te = y.values[:-6], y.values[-6:]
mu_h, _, _ = pred(tr, np.arange(34, 40))
res["holdout_ultimos_6_meses_2025-11_a_2026-04"] = {"entrenamiento_N": len(tr), "MAPE_pct": round(mape(te, mu_h), 2),
                                                    "RMSE": round(float(np.sqrt(((te - mu_h) ** 2).mean())), 2),
                                                    "por_mes": {k: [round(float(r), 2), round(float(p), 2)] for k, r, p in zip(y.index[-6:], te, mu_h)}}
y36 = y[y.index <= "2025-12"]
mu_f, _, _ = pred(y36.values, np.arange(36, 40))
real = y[y.index >= "2026-01"].values
a36, b36, _, f36 = ajustar(y36.values)
res["modelo_hasta_2025-12_vs_ejecutado_ene_abr_2026"] = {"N_entrenamiento": 36, "pendiente_Bs_mes": round(float(b36), 2),
    "R2": round(1 - float(((y36.values - f36) ** 2).sum() / ((y36.values - y36.values.mean()) ** 2).sum()), 4),
    "MAPE_pct": round(mape(real, mu_f), 2), "por_mes": {k: [round(float(r), 2), round(float(p), 2)] for k, r, p in zip(y.index[-4:], real, mu_f)}}
(ROOT / "docs" / "evidencias" / "ols_reajuste.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
