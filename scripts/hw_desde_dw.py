"""Tarea 7: Holt-Winters con la serie de fact_marketing (DW) vs inscritos.csv, misma ventana (N=33, 2023-09 a 2026-05, hold-out 6)."""
import json, os, sys
import numpy as np, pandas as pd
from sqlalchemy import create_engine, text
from statsmodels.tsa.holtwinters import ExponentialSmoothing as ES

url = os.environ["DATABASE_URL"]
df = pd.read_sql(text("SELECT dt.periodo_mes, SUM(fm.inscritos)::float AS valor FROM dim_tiempo dt JOIN fact_marketing fm "
                      "ON dt.id_tiempo=fm.id_tiempo GROUP BY dt.periodo_mes HAVING SUM(fm.inscritos)>0 ORDER BY 1"), create_engine(url))
dw = pd.Series(df.valor.values, index=pd.PeriodIndex(df.periodo_mes, freq="M").to_timestamp(), name="inscritos").asfreq("MS", fill_value=0)
csv = pd.read_csv("inscritos.csv", parse_dates=["mes"], index_col="mes")["inscritos"].asfreq("MS", fill_value=0).astype(float)
h = 6
fit = lambda x: ES(x, trend="add", seasonal="add", seasonal_periods=12, initialization_method="heuristic").fit()

def evaluar(s_full):
    s = s_full.iloc[-33:]
    m = fit(s[:-h]); fc = m.forecast(h); te = s[-h:]; nz = te != 0
    M = fit(s); F = M.forecast(h)
    return {"N": len(s), "desde": str(s.index[0].date()), "hasta": str(s.index[-1].date()),
            "RMSE_holdout": round(float(np.sqrt(((te - fc) ** 2).mean())), 2),
            "MAPE_holdout_pct": round(float((abs(te[nz] - fc[nz]) / te[nz]).mean() * 100), 2),
            "AIC": round(float(M.aic), 2), "suma_ventana": int(s.sum()),
            "pronostico_h6": {k.strftime("%Y-%m"): round(float(v), 1) for k, v in F.items()},
            "serie": {k.strftime("%Y-%m"): int(v) for k, v in s.items()}}

res = {"DW_fact_marketing": evaluar(dw), "inscritos_csv": evaluar(csv)}
res["series_identicas_en_ventana"] = bool((dw.iloc[-33:].values == csv.iloc[-33:].values).all())
open("docs/evidencias/holtwinters_dw_vs_csv.json", "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=2))
print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk not in ("serie", "pronostico_h6")} if isinstance(v, dict) else v) for k, v in res.items()}, indent=1))
