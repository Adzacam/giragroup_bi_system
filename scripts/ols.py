import shutil, os
import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

d = pd.read_csv('recaudacion.csv')
x = d.anio - 2024
m, b = np.polyfit(x, d.monto, 1)
xf = np.arange(x.min(), x.max() + 3)
yf = m * xf + b

print(f'pendiente={m:,.2f} Bs/año  intercepto(2024)={b:,.2f} Bs  var_media={d.monto.pct_change().mean()*100:.2f}%')
print('Proyección 2026:', f'{m*(2026-2024)+b:,.2f} Bs', '| Proyección 2027:', f'{m*(2027-2024)+b:,.2f} Bs')

f, a = plt.subplots(figsize=(7, 4))
a.scatter(d.anio, d.monto / 1e6, c='k', s=45, zorder=3, label='Observado (2023–2025)')
a.plot(xf + 2024, yf / 1e6, 'k--', label='Tendencia OLS (centrada en 2024)')
a.fill_between(xf + 2024, (yf * .95) / 1e6, (yf * 1.05) / 1e6, color='#ddd', label='Banda operativa ±5 %')
a.set(xlabel='Gestión', ylabel='Recaudación (Millones de Bs)', xticks=(xf + 2024).astype(int))
a.grid(True, linestyle=':', alpha=0.5, color='#888')
a.legend(loc='upper left')
f.tight_layout()
f.savefig('grafico_3_5.png', dpi=300, facecolor='white')
os.makedirs('docs/images', exist_ok=True)
shutil.copy2('grafico_3_5.png', 'docs/images/grafico_3_5_tendencia_lineal_ols.png')
brain_dir = r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0"
if os.path.exists(brain_dir):
    shutil.copy2('grafico_3_5.png', os.path.join(brain_dir, 'grafico_3_5_tendencia_lineal_ols.png'))
