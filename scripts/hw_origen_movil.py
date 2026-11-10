"""Ronda 10, tarea 2b/2c: validacion con origen movil sobre la serie mensual de inscritos de fact_marketing (DW real).
Origenes: los ultimos 12 meses (se entrena con todo lo anterior al origen); h = 1..6 truncado a los meses con dato real.
Modelos: actual (pipeline.analytics.forecasting_holtwinters), HW amortiguado, HW sobre log(1+y) y SARIMA pequeno elegido por AIC en cada origen.
Escribe docs/evidencias/holtwinters_origen_movil.json. Uso: DATABASE_URL=... python scripts/hw_origen_movil.py"""
import itertools, json, os, sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
from sqlalchemy import create_engine, text
from statsmodels.tsa.holtwinters import ExponentialSmoothing as ES
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from pipeline.analytics.forecasting_holtwinters import entrenar_y_proyectar_hw  # noqa: E402

H, ORIGENES = 6, 12
df = pd.read_sql(text("SELECT dt.periodo_mes, SUM(fm.inscritos)::float AS v FROM dim_tiempo dt JOIN fact_marketing fm ON dt.id_tiempo=fm.id_tiempo "
                      "GROUP BY 1 ORDER BY 1"), create_engine(os.environ["DATABASE_URL"]))
y = pd.Series(df.v.values, index=pd.PeriodIndex(df.periodo_mes, freq="M").to_timestamp()).asfreq("MS", fill_value=0.0)
n = len(y)


def actual(tr):
    return np.array(entrenar_y_proyectar_hw(tr, "ALUMNOS_GLOBAL", horizonte=H)["forecast"])


def amortiguado(tr):
    return np.maximum(ES(tr, trend="add", damped_trend=True, seasonal="add", seasonal_periods=12, initialization_method="estimated").fit().forecast(H).values, 0)


def logaritmico(tr):
    f = ES(np.log1p(tr), trend="add", seasonal="add", seasonal_periods=12, initialization_method="estimated").fit().forecast(H).values
    return np.maximum(np.expm1(f), 0)


GRILLA = [(p, d, q, P, D, Q) for p, d, q, P, D, Q in itertools.product((0, 1), (0, 1), (0, 1), (0, 1), (0, 1), (0, 1)) if d + D <= 1]


def sarima(tr):
    mejor = None
    for p, d, q, P, D, Q in GRILLA:
        try:
            r = SARIMAX(tr, order=(p, d, q), seasonal_order=(P, D, Q, 12), trend="c" if d + D == 0 else None,
                        enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=100)
            if np.isfinite(r.aic) and (mejor is None or r.aic < mejor[0]):
                mejor = (r.aic, r, (p, d, q, P, D, Q))
        except Exception:
            continue
    sarima.ordenes.append(list(mejor[2]))
    return np.maximum(mejor[1].forecast(H).values, 0)


sarima.ordenes = []
naive = lambda tr: np.array([tr.values[-12 + (i % 12)] for i in range(H)])  # referencia: naive estacional
MODELOS = {"actual_HW_aditivo": actual, "HW_amortiguado": amortiguado, "HW_log": logaritmico, "SARIMA_AIC": sarima, "referencia_naive_estacional": naive}

res = {k: {"por_origen": [], "ape_por_h": {h: [] for h in range(1, H + 1)}} for k in MODELOS}
for t in range(n - ORIGENES, n):  # t = observaciones de entrenamiento
    tr, real = y.iloc[:t], y.iloc[t:t + H]
    for k, f in MODELOS.items():
        fc = f(tr)[:len(real)]
        ape = np.abs(real.values - fc) / real.values * 100
        res[k]["por_origen"].append({"origen": str(real.index[0].date()), "n_entrenamiento": t, "h_disponibles": len(real), "mape": round(float(ape.mean()), 2)})
        for i, a in enumerate(ape, 1):
            res[k]["ape_por_h"][i].append(float(a))

salida = {"serie": {"fuente": "fact_marketing.inscritos por mes (DW real)", "n": n, "desde": str(y.index[0].date()), "hasta": str(y.index[-1].date()),
                    "nota": "2022-11 y 2022-12 son meses de arranque con pocos inscritos"},
          "diseno": {"origenes": ORIGENES, "h": "1..6, truncado a los meses con dato real (los ultimos 5 origenes tienen menos de 6)", "sarima_grilla": len(GRILLA)}, "modelos": {}}
for k, v in res.items():
    m = [o["mape"] for o in v["por_origen"]]
    todos = [a for l in v["ape_por_h"].values() for a in l]
    salida["modelos"][k] = {"mape_medio_origenes": round(float(np.mean(m)), 2), "de_origenes": round(float(np.std(m, ddof=1)), 2),
                            "mape_agrupado_todos_los_pasos": round(float(np.mean(todos)), 2), "pasos_evaluados": len(todos),
                            "mape_por_h": {h: round(float(np.mean(l)), 2) for h, l in v["ape_por_h"].items() if l}, "por_origen": v["por_origen"]}
salida["sarima_ordenes_elegidos"] = sarima.ordenes
gan = min((k for k in MODELOS if not k.startswith("referencia")), key=lambda k: salida["modelos"][k]["mape_medio_origenes"])
salida["mejor_mape_medio"] = gan
salida["adoptar_distinto_del_actual"] = gan != "actual_HW_aditivo"
(RAIZ / "docs" / "evidencias" / "holtwinters_origen_movil.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
for k, v in salida["modelos"].items():
    print(f"{k:30s} MAPE {v['mape_medio_origenes']:6.2f} ± {v['de_origenes']:5.2f}  agrupado {v['mape_agrupado_todos_los_pasos']:6.2f}  por h {v['mape_por_h']}")
print("mejor:", gan, "| ordenes SARIMA:", sarima.ordenes)
