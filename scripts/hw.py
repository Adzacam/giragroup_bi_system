import shutil, os
import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from statsmodels.tsa.holtwinters import ExponentialSmoothing as ES

plt.rcParams.update({
    "font.family": "serif",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

s_full = pd.read_csv('inscritos.csv', parse_dates=['mes'], index_col='mes')['inscritos'].asfreq('MS', fill_value=0)
# Ventana consolidada N = 33 meses (2023-09 a 2026-05): 27 meses de entrenamiento (>= 24 requeridos por s=12) + 6 meses holdout
s = s_full.iloc[-33:]
h = 6
fit = lambda x: ES(x, trend='add', seasonal='add', seasonal_periods=12, initialization_method='heuristic').fit() if len(x) >= 24 else ES(x, trend='add', initialization_method='heuristic').fit()

m = fit(s[:-h])
fc = m.forecast(h)
te = s[-h:]
nz = te != 0
rmse = float(np.sqrt(((te - fc) ** 2).mean()))
mape = float((abs(te[nz] - fc[nz]) / te[nz]).mean() * 100)

M = fit(s)
F = M.forecast(h)
ri = float(np.sqrt(M.sse / len(s)))
lo, hi = (F - 1.96 * ri).clip(lower=0), F + 1.96 * ri

print(
    {k: round(float(M.params[k]), 4) for k in ('smoothing_level', 'smoothing_trend', 'smoothing_seasonal') if M.params.get(k) is not None},
    f'N={len(s)} train={len(s)-h} holdout={h} RMSE_holdout={rmse:.2f} MAPE={mape:.1f}% RMSE_ajuste={ri:.2f} AIC={M.aic:.2f}'
)
print('Pronóstico h=6:', {k.strftime('%Y-%m'): round(float(v), 1) for k, v in F.items()})

f, a = plt.subplots(figsize=(8, 4.2), facecolor='white')
a.plot(s.index, s.values, 'k-o', ms=3.5, lw=1.2, label='Histórico observado (N = 33 meses)')
a.axvline(s.index[-h], color='#555555', linestyle=':', lw=1.0, label='Corte validación hold-out (h = 6)')
a.plot(fc.index, fc.values, color='#666666', linestyle='-.', marker='^', ms=3.5, lw=1.1, label=f'Validación hold-out (MAPE = {mape:.1f} %)')
a.plot(F.index, F.values, 'k--', marker='s', ms=3.8, lw=1.4, label='Pronóstico Holt-Winters (h = 6)')
a.fill_between(F.index, lo, hi, color='#cccccc', alpha=0.85, label='IC 95 % (±1,96 RMSE)')
a.set(xlabel='Periodo mensual', ylabel='Matrículas / Inscritos')
a.grid(True, linestyle=':', alpha=0.6, color='#888888')
a.spines['top'].set_visible(False)
a.spines['right'].set_visible(False)
a.legend(loc='upper left', frameon=False, fontsize=8.5)
f.tight_layout()
f.savefig('grafico_3_4.png', dpi=300, facecolor='white')
os.makedirs('docs/images', exist_ok=True)
shutil.copy2('grafico_3_4.png', 'docs/images/grafico_3_4_serie_temporal_holt_winters.png')
brain_dir = r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0"
if os.path.exists(brain_dir):
    shutil.copy2('grafico_3_4.png', os.path.join(brain_dir, 'grafico_3_4_serie_temporal_holt_winters.png'))
