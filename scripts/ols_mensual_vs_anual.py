"""Tarea 4: OLS sobre la serie mensual META_MENSUAL_PROGRAMAS del DW (N >= 36), hold-out de 6 meses, frente al OLS anual (N=3)."""
import json, os, sys
import numpy as np, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT)]
from sqlalchemy import create_engine
from pipeline.analytics.time_series_extractor import extraer_serie_temporal
from pipeline.analytics.forecasting_ols import estimar_tendencia_anual_ols
eng = create_engine(os.environ["DATABASE_URL"])
m = extraer_serie_temporal("META_MENSUAL_PROGRAMAS", engine=eng)
m = m.groupby(level=0).sum() if m.index.duplicated().any() else m
serie48 = m.astype(float)
# 2026 de META_MENSUAL_PROGRAMAS son METAS (monto_ejecutado vacío => COALESCE a monto_meta): la recaudación ejecutada es 2023-01..2025-12 (N=36)
y_all = serie48[serie48.index.astype(str) < '2026-01']; n = len(y_all)
def ols(y):
    t = np.arange(len(y)); b, a = np.polyfit(t, y, 1); fit = a + b * t
    ss_res = float(((y - fit) ** 2).sum()); ss_tot = float(((y - y.mean()) ** 2).sum())
    return a, b, 1 - ss_res / ss_tot, float(np.sqrt(ss_res / len(y)))
h = 6
tr, te = y_all.values[:-h], y_all.values[-h:]
a, b, r2, rmse_aj = ols(tr)
pred = a + b * np.arange(len(tr), len(tr) + h)
nz = te != 0
rmse = float(np.sqrt(((te - pred) ** 2).mean())); mape = float((abs(te[nz] - pred[nz]) / abs(te[nz])).mean() * 100)
a2, b2, r22, rmse2 = ols(y_all.values)
anual = extraer_serie_temporal("META_ANUAL", engine=eng)
ra = estimar_tendencia_anual_ols(anual, horizonte_anios=2)
x_a = np.array(anual.index, dtype=float); y_a = anual.values.astype(float); ca = np.polyfit(x_a, y_a, 1); fa = np.polyval(ca, x_a)
r2_a = 1 - ((y_a - fa) ** 2).sum() / ((y_a - y_a.mean()) ** 2).sum(); rmse_a = float(np.sqrt(((y_a - fa) ** 2).mean()))
res = {"serie": "META_MENSUAL_PROGRAMAS ejecutado (fact_rentabilidad, categoria PROGRAMAS), 2023-01..2025-12", "nota_2026": "los 12 meses de 2026 del extractor son metas (suma 15.960.170,68), no recaudación; se excluyen", "N": n, "desde": str(y_all.index[0]), "hasta": str(y_all.index[-1]),
       "hold_out_6m": {"entrenamiento_N": len(tr), "pendiente_Bs_por_mes": round(b, 2), "R2_entrenamiento": round(r2, 4), "RMSE_holdout": round(rmse, 2), "MAPE_holdout_pct": round(mape, 2), "media_holdout": round(float(te.mean()), 2)},
       "serie_completa": {"pendiente_Bs_por_mes": round(b2, 2), "incremento_anual_implicito_del_total_Bs": round(b2 * 144, 2), "R2": round(r22, 4), "RMSE_ajuste": round(rmse2, 2)},
       "OLS_anual_N3": {"N": len(y_a), "pendiente_Bs_por_anio": round(float(ca[0]), 2), "R2": round(float(r2_a), 4), "RMSE_ajuste": round(rmse_a, 2), "proyeccion_2_anios": ra.get("proyecciones") or ra.get("proyeccion"), "claves_devueltas": list(ra)},
       "serie_anual": {int(k): float(v) for k, v in anual.items()}}
(ROOT / "docs/evidencias/ols_mensual_vs_anual.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
