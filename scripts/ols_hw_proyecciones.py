"""Tarea 5 (ronda 4), todo desde el DW (DATABASE_URL):
(a) recaudación anual PROGRAMAS 2023-2025 (suma de monto_ejecutado) y su diferencia con la tesis (8,03 / 9,98 / 12,90 M);
(b) OLS mensual N=36 (2023-01..2025-12) ajustado con toda la serie: proyección 2026-01..2026-06 con intervalo de predicción 95 % (t, gl=N-2);
(c) Holt-Winters aditivo (fact_marketing, N=33, 2023-09..2026-05): alfa, beta, gamma, RMSE de ajuste, AIC y proyección h=6.
Escribe docs/evidencias/ols_hw_proyecciones.json"""
import json, os, sys
import numpy as np, pandas as pd
from pathlib import Path
from scipy import stats
from sqlalchemy import create_engine, text
from statsmodels.tsa.holtwinters import ExponentialSmoothing as ES

ROOT = Path(__file__).resolve().parent.parent
eng = create_engine(os.environ["DATABASE_URL"])
Q = ("SELECT dt.periodo_mes, SUM(fr.monto_ejecutado)::float v FROM fact_rentabilidad fr JOIN dim_categoria_financiera c ON c.id_categoria=fr.id_categoria "
     "JOIN dim_tiempo dt ON dt.id_tiempo=fr.id_tiempo WHERE c.nombre_categoria='PROGRAMAS' AND fr.monto_ejecutado IS NOT NULL GROUP BY 1 ORDER BY 1")
m = pd.read_sql(text(Q), eng)
m["anio"] = m.periodo_mes.str[:4].astype(int)
anual = m[m.anio <= 2025].groupby("anio").v.sum()
tesis = {2023: 8.03e6, 2024: 9.98e6, 2025: 12.90e6}
csv = pd.read_csv(ROOT / "recaudacion.csv").set_index("anio").monto
a = {"DW_suma_monto_ejecutado": {int(k): round(float(v), 2) for k, v in anual.items()},
     "recaudacion_csv": {int(k): round(float(v), 2) for k, v in csv.items()},
     "tesis_millones": {k: v / 1e6 for k, v in tesis.items()},
     "diferencia_DW_menos_tesis_Bs": {k: round(float(anual[k] - tesis[k]), 2) for k in tesis},
     "diferencia_DW_menos_csv_Bs": {int(k): round(float(anual[k] - csv[k]), 2) for k in csv.index}}
with eng.connect() as c:
    a["marzo_2025_PROGRAMAS_DW"] = float(c.execute(text("SELECT r.monto_ejecutado FROM fact_rentabilidad r JOIN dim_tiempo t USING(id_tiempo) JOIN dim_categoria_financiera c USING(id_categoria) WHERE c.nombre_categoria='PROGRAMAS' AND t.periodo_mes='2025-03' AND r.monto_ejecutado IS NOT NULL")).scalar())
    a["conflictos_fuentes_en_log"] = [dict(r._mapping) for r in c.execute(text("SELECT id_documento, valor_recibido, valor_esperado, descripcion FROM log_inconsistencias WHERE tipo_regla='CONFLICTO_FUENTES' AND campo_afectado='fact_rentabilidad.monto_ejecutado' AND descripcion LIKE 'PROGRAMAS%'"))]


def ols_pred(y, h, nivel=0.95):
    n = len(y); t = np.arange(n); b, a0 = np.polyfit(t, y, 1); fit = a0 + b * t
    s2 = ((y - fit) ** 2).sum() / (n - 2); sxx = ((t - t.mean()) ** 2).sum(); tc = stats.t.ppf(0.5 + nivel / 2, n - 2)
    x0 = np.arange(n, n + h); mu = a0 + b * x0; se = np.sqrt(s2 * (1 + 1 / n + (x0 - t.mean()) ** 2 / sxx))
    r2 = 1 - ((y - fit) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return {"N": n, "pendiente_Bs_mes": round(float(b), 2), "intercepto": round(float(a0), 2), "R2": round(float(r2), 4), "RMSE_ajuste": round(float(np.sqrt(((y - fit) ** 2).mean())), 2),
            "t_critico": round(float(tc), 4), "proyeccion": [{"mes": f"2026-{i + 1:02d}", "pronostico": round(float(mu[i]), 2), "ic95_inf": round(float(mu[i] - tc * se[i]), 2), "ic95_sup": round(float(mu[i] + tc * se[i]), 2)} for i in range(h)]}


y = m[m.periodo_mes < "2026-01"].set_index("periodo_mes").v
assert len(y) == 36
res = {"a_recaudacion_anual": a, "b_OLS_mensual_h6": {"serie": "PROGRAMAS monto_ejecutado, 2023-01..2025-12 (valores del DW)", **ols_pred(y.values, 6)}}
y2 = y.copy(); y2["2025-03"] = float(csv[2025] - anual[2025] + y["2025-03"])  # sensibilidad: marzo 2025 con la cifra de EJECUTADO VS META
res["b_OLS_mensual_h6_sensibilidad_marzo_2025_de_EJECUTADO_VS_META"] = {"marzo_2025": round(float(y2["2025-03"]), 2), **ols_pred(y2.values, 6)}
real26 = m[m.periodo_mes >= "2026-01"][["periodo_mes", "v"]]
res["b_ejecutado_2026_en_DW"] = {r.periodo_mes: round(float(r.v), 2) for r in real26.itertuples()}

pp = {x["mes"]: x["pronostico"] for x in res["b_OLS_mensual_h6"]["proyeccion"]}
ab = [abs(res["b_ejecutado_2026_en_DW"][k] - pp[k]) / res["b_ejecutado_2026_en_DW"][k] * 100 for k in ("2026-01", "2026-02", "2026-03", "2026-04")]
res["b_validacion_con_ejecutado_2026"] = {"meses": "2026-01..2026-04 (2026-05 excluido: mes parcial, 252.233,32)", "error_abs_pct_por_mes": [round(x, 2) for x in ab], "MAPE_pct": round(float(np.mean(ab)), 2)}

df = pd.read_sql(text("SELECT dt.periodo_mes, SUM(fm.inscritos)::float AS valor FROM dim_tiempo dt JOIN fact_marketing fm ON dt.id_tiempo=fm.id_tiempo GROUP BY dt.periodo_mes HAVING SUM(fm.inscritos)>0 ORDER BY 1"), eng)
s = pd.Series(df.valor.values, index=pd.PeriodIndex(df.periodo_mes, freq="M").to_timestamp()).asfreq("MS", fill_value=0).iloc[-33:]
h = 6
fit = lambda x: ES(x, trend="add", seasonal="add", seasonal_periods=12, initialization_method="heuristic").fit()
mod = fit(s[:-h]); fc = mod.forecast(h); te = s[-h:]; nz = te != 0
M = fit(s); F = M.forecast(h); ri = float(np.sqrt(M.sse / len(s)))
p = M.params
res["c_HoltWinters_DW"] = {"N": len(s), "desde": str(s.index[0].date()), "hasta": str(s.index[-1].date()),
    "alpha": round(float(p["smoothing_level"]), 4), "beta": round(float(p["smoothing_trend"]), 4), "gamma": round(float(p["smoothing_seasonal"]), 4),
    "RMSE_ajuste": round(ri, 2), "AIC": round(float(M.aic), 2), "RMSE_holdout6": round(float(np.sqrt(((te - fc) ** 2).mean())), 2),
    "MAPE_holdout6_pct": round(float((abs(te[nz] - fc[nz]) / te[nz]).mean() * 100), 2),
    "parametros_modelo_hold_out_(entrenado_en_27)": {k: round(float(mod.params[k]), 4) for k in ("smoothing_level", "smoothing_trend", "smoothing_seasonal")},
    "proyeccion_h6": [{"mes": k.strftime("%Y-%m"), "pronostico": round(float(v), 1), "ic95_inf": round(float(max(0, v - 1.96 * ri)), 1), "ic95_sup": round(float(v + 1.96 * ri), 1)} for k, v in F.items()]}
(ROOT / "docs" / "evidencias" / "ols_hw_proyecciones.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
