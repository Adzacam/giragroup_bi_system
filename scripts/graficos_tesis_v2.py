# -*- coding: utf-8 -*-
"""
scripts/graficos_tesis_v2.py
============================
Script unificado y versionado para la regeneración de gráficos académicos
de la tesis del Proyecto de Grado - Sistema BI GiraGroup S.R.L.

Reglas y Estándares:
- Fuente única: docs/fuente_verdad_tesis.md (SFV v2, snapshot_dw_20261110_1201).
- Formato numérico boliviano: coma decimal (,) y punto de miles (.) en textos, etiquetas y ejes.
- Resolución: PNG a 300 DPI, ancho exacto 16 cm (6,3 pulgadas / 1.890 px).
- Tipografía: Fuente serif académica de 10 pt.
- Paleta: Escala de grises con tramas (hatching) para lectura impresa en blanco y negro.
- Sin título interno en la imagen: títulos y fuentes se gestionan en Word.
- Valores rotulados sobre barras y elementos de datos.
- Salida oficial: docs/evidencias/graficos_v2/
"""

import os
import shutil
import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import statsmodels.api as sm
from statsmodels.tsa.holtwinters import ExponentialSmoothing as ES

# Configuración global tipográfica y de estilo
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['DejaVu Serif', 'Times New Roman', 'Cambria', 'Georgia']
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['axes.labelsize'] = 9.5
plt.rcParams['xtick.labelsize'] = 8.5
plt.rcParams['ytick.labelsize'] = 8.5
plt.rcParams['legend.fontsize'] = 8.5
plt.rcParams['figure.titlesize'] = 11

OUTPUT_DIR = pathlib.Path("docs/evidencias/graficos_v2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Ancho estándar de 16 cm en pulgadas para 300 DPI
ANCHO_16CM = 16.0 / 2.54  # 6.2992 pulgadas


# -----------------------------------------------------------------------------
# Formateadores numéricos estándar boliviano
# -----------------------------------------------------------------------------
def fmt_miles(val):
    """Formatea enteros con punto de miles boliviano."""
    return f"{int(round(val)):,}".replace(',', '.')

def fmt_decimal(val, dec=2):
    """Formatea float con coma decimal y punto de miles."""
    fmt = f"{{:,.{dec}f}}"
    txt = fmt.format(val)
    return txt.replace(',', 'X').replace('.', ',').replace('X', '.')

def formatter_coma_fn(x, pos):
    """Formateador de ejes numéricos."""
    if abs(x - int(round(x))) < 1e-5:
        return fmt_miles(x)
    return fmt_decimal(x, dec=1)

def formatter_pct_fn(x, pos):
    """Formateador de ejes porcentuales."""
    if abs(x - int(round(x))) < 1e-5:
        return f"{int(round(x))} %"
    return f"{fmt_decimal(x, dec=1)} %"

formatter_bo = ticker.FuncFormatter(formatter_coma_fn)
formatter_pct = ticker.FuncFormatter(formatter_pct_fn)

def guardar_figura_exacta(fig, nombre_archivo):
    """Guarda la figura a 300 DPI garantizando 16 cm de ancho."""
    ruta = OUTPUT_DIR / nombre_archivo
    fig.savefig(ruta, dpi=300, facecolor='#FFFFFF', edgecolor='none')
    plt.close(fig)
    print(f"[OK] Generado: {ruta}")


# =============================================================================
# G3.2: Lote de 1.387 por resultado (Barras horizontales)
# =============================================================================
def generar_g3_2():
    """
    G3.2: Lote de 1.387 por resultado:
    - Directo: 1.353 (97,55 %)
    - HITL: 34 (2,45 %)
    - Staging: 0 (0,00 %)
    Barras horizontales.
    """
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 2.7), dpi=300)
    fig.subplots_adjust(left=0.38, right=0.94, top=0.92, bottom=0.20)
    
    categorias = [
        "Consolidación directa (≥ 0,85)",
        "Revisión humana HITL (0,60 – 0,85)",
        "Retenido en Staging (< 0,60)"
    ]
    valores = [1353, 34, 0]
    porcentajes = [97.55, 2.45, 0.00]
    
    y_pos = np.arange(len(categorias))
    colores = ['#4A4A4A', '#8C8C8C', '#D9D9D9']
    tramas = ['///', '...', 'xxx']
    
    barras = ax.barh(y_pos, valores, color=colores, edgecolor='#111111',
                     height=0.52, hatch=tramas, linewidth=1.1)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categorias)
    ax.set_xlabel("Cantidad de registros evaluados (Total = 1.387)")
    ax.set_xlim(0, 1650)
    ax.xaxis.set_major_formatter(formatter_bo)
    ax.grid(axis='x', linestyle=':', alpha=0.6, color='#888888')
    
    for bar, val, pct in zip(barras, valores, porcentajes):
        txt = f"{fmt_miles(val)} ({fmt_decimal(pct, 2)} %)"
        ax.text(val + 30, bar.get_y() + bar.get_height() / 2, txt,
                va='center', ha='left', fontsize=8.5, color='#111111')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.invert_yaxis()
    
    guardar_figura_exacta(fig, "grafico_3_2_distribucion_lote_1387.png")


# =============================================================================
# G3.3: Ablación A/B/C (Barras agrupadas)
# =============================================================================
def generar_g3_3():
    """
    G3.3: Ablación A/B/C.
    Barras agrupadas con:
    - F1 estricto en gold_510: A 100,00, B 100,00, C 97,57
    - F1 relajado en layouts_5: A 28,57; B 71,64; C 69,23
    """
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 3.6), dpi=300)
    fig.subplots_adjust(left=0.12, right=0.96, top=0.94, bottom=0.16)
    
    escenarios = [
        "Dataset estándar (gold_510)\nF1 micro estricto",
        "Layouts adversos (layouts_5)\nF1 micro relajado"
    ]
    
    modo_a = [100.00, 28.57]
    modo_b = [100.00, 71.64]
    modo_c = [97.57, 69.23]
    
    x = np.arange(len(escenarios))
    ancho = 0.22
    
    b1 = ax.bar(x - ancho, modo_a, ancho, label='Modo A (Determinístico puro)',
                color='#E0E0E0', edgecolor='#111111', hatch='///', linewidth=1.1)
    b2 = ax.bar(x, modo_b, ancho, label='Modo B (Híbrido implementado)',
                color='#666666', edgecolor='#111111', hatch='...', linewidth=1.1)
    b3 = ax.bar(x + ancho, modo_c, ancho, label='Modo C (BETO puro)',
                color='#B0B0B0', edgecolor='#111111', hatch='xxx', linewidth=1.1)
    
    ax.set_ylabel("Puntuación F1 (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(escenarios)
    ax.set_ylim(0, 118)
    ax.yaxis.set_major_formatter(formatter_pct)
    ax.grid(axis='y', linestyle=':', alpha=0.6, color='#888888')
    
    def rotular(barras, vals):
        for bar, v in zip(barras, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2.5,
                    f"{fmt_decimal(v, 2)} %", ha='center', va='bottom', fontsize=8.5)
            
    rotular(b1, modo_a)
    rotular(b2, modo_b)
    rotular(b3, modo_c)
    
    ax.legend(loc='upper right', frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=8.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    guardar_figura_exacta(fig, "grafico_3_3_ablacion_modelos_ner.png")


# =============================================================================
# G3.4: Serie de matrícula y pronóstico Holt-Winters (33 meses)
# =============================================================================
def generar_g3_4():
    """
    G3.4: Serie de matrícula (fact_marketing.inscritos, sep-2023 a may-2026, 33 meses):
    (a) Valores reales;
    (b) Ajuste HW amortiguado de 27 meses y su pronóstico en hold-out dic-2025 a may-2026;
    (c) Naive estacional (y_t = y_t-12) en el hold-out;
    (d) Proyección jun a nov 2026 del ajuste de 33 meses, con banda ±94,79 (1,96 × RMSE in-sample),
        rotulada «IC aprox. con RMSE de ajuste».
    Leyenda fuera abajo con MAPE: HW 13,89 %, naive 10,32 %.
    Eje X formateado en español (sep-23, ene-24, etc.).
    """
    s_full = pd.read_csv('inscritos.csv', parse_dates=['mes'], index_col='mes')['inscritos'].asfreq('MS', fill_value=0)
    s = s_full.iloc[-33:]
    
    h = 6
    train = s.iloc[:27]
    test = s.iloc[27:]
    
    # 1. Ajuste validación 27 meses
    m27 = ES(train, trend='add', damped_trend=True, seasonal='add', seasonal_periods=12,
             initialization_method='estimated').fit(optimized=True)
    fc_test = m27.forecast(h)
    mape_hw = np.mean(np.abs((test.values - fc_test.values) / test.values)) * 100
    
    # 2. Naive estacional (y_t = y_t-12)
    naive_vals = s.iloc[27-12:33-12].values
    mape_naive = np.mean(np.abs((test.values - naive_vals) / test.values)) * 100
    
    # Verificación estricta con SFV v2
    if abs(mape_hw - 13.89) >= 0.05 or abs(mape_naive - 10.32) >= 0.05:
        raise ValueError(f"Falla de validación SFV: HW={mape_hw:.2f}% (esperado 13,89%), Naive={mape_naive:.2f}% (esperado 10,32%)")
    
    # 3. Ajuste de producción 33 meses
    m33 = ES(s, trend='add', damped_trend=True, seasonal='add', seasonal_periods=12,
             initialization_method='estimated').fit(optimized=True)
    fc_fut = m33.forecast(h)
    rmse_in33 = np.sqrt(np.mean(m33.resid**2))
    banda = 1.96 * rmse_in33
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.2), dpi=300)
    fig.subplots_adjust(left=0.12, right=0.96, top=0.95, bottom=0.30)
    
    # (a) Valores reales
    ax.plot(s.index, s.values, 'k-o', ms=3.5, lw=1.2, label='Observado real (sep-2023 a may-2026)')
    
    # (b) Ajuste HW amortiguado 27 meses (in-sample) y pronóstico hold-out
    ax.plot(train.index, m27.fittedvalues, color='#777777', linestyle=':', lw=1.0,
            label='Ajuste HW 27m in-sample')
    ax.axvline(s.index[27], color='#555555', linestyle='--', lw=1.0,
               label='Corte hold-out (dic-2025)')
    ax.plot(test.index, fc_test.values, color='#333333', linestyle='--', marker='^', ms=4.2, lw=1.3,
            label=f'Pronóstico HW hold-out (MAPE = {fmt_decimal(mape_hw, 2)} %)')
    
    # (c) Naive estacional hold-out
    ax.plot(test.index, naive_vals, color='#888888', linestyle='-.', marker='s', ms=3.8, lw=1.2,
            label=f'Naive estacional hold-out (MAPE = {fmt_decimal(mape_naive, 2)} %)')
    
    # (d) Proyección jun a nov 2026
    ax.plot(fc_fut.index, fc_fut.values, color='#000000', linestyle='-', marker='D', ms=3.8, lw=1.4,
            label='Proyección modelo 33m (jun-nov 2026)')
    
    lo = fc_fut.values - banda
    hi = fc_fut.values + banda
    ax.fill_between(fc_fut.index, lo, hi, color='#B8B8B8', alpha=0.55,
                    label='IC aprox. con RMSE de ajuste (±94,79)')
    
    ax.set_ylabel("Inscritos mensuales")
    ax.set_xlabel("Periodo mensual")
    ax.yaxis.set_major_formatter(formatter_bo)
    
    import matplotlib.dates as mdates
    meses_es = {
        1: 'ene', 2: 'feb', 3: 'mar', 4: 'abr', 5: 'may', 6: 'jun',
        7: 'jul', 8: 'ago', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dic'
    }
    def date_formatter_es(x, pos):
        dt = mdates.num2date(x)
        return f"{meses_es[dt.month]}-{str(dt.year)[2:]}"
    
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(date_formatter_es))
    
    ax.grid(True, linestyle=':', alpha=0.5, color='#888888')
    ax.set_ylim(40, 720)
    
    # Leyenda colocada fuera abajo en dos columnas
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.22), ncol=2,
              frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=7.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    guardar_figura_exacta(fig, "grafico_3_4_serie_temporal_holt_winters.png")


# =============================================================================
# G3.5: OLS mensual de matrícula (N = 33)
# =============================================================================
def generar_g3_5():
    """
    G3.5: OLS mensual de matrícula (N = 33): puntos y recta.
    En el gráfico: pendiente +3,6541 est./mes; intercepto 329,72 (t=0 en sep-2023); R² 0,1921; p 0,0107.
    Leyenda fuera del área de datos.
    """
    s_full = pd.read_csv('inscritos.csv', parse_dates=['mes'], index_col='mes')['inscritos'].asfreq('MS', fill_value=0)
    s = s_full.iloc[-33:]
    
    t = np.arange(len(s))
    y = s.values
    
    X = sm.add_constant(t)
    modelo_ols = sm.OLS(y, X).fit()
    
    pendiente = modelo_ols.params[1]
    intercepto = modelo_ols.params[0]
    r2 = modelo_ols.rsquared
    p_val = modelo_ols.pvalues[1]
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.0), dpi=300)
    fig.subplots_adjust(left=0.12, right=0.96, top=0.95, bottom=0.25)
    
    ax.scatter(t, y, color='#444444', edgecolor='#111111', s=34, zorder=3,
               label='Observaciones mensuales ($y_t$, N = 33)')
    
    y_pred = intercepto + pendiente * t
    ax.plot(t, y_pred, color='#111111', lw=1.6, linestyle='-', zorder=2,
            label='Recta de tendencia OLS')
    
    cuadro_texto = (
        f"Regresión lineal OLS (N = 33 meses):\n"
        f"• Pendiente (β₁): +{fmt_decimal(pendiente, 4)} est./mes\n"
        f"• Intercepto (β₀): {fmt_decimal(intercepto, 2)} (en t = 0)\n"
        f"• Coef. determinación R²: {fmt_decimal(r2, 4)}\n"
        f"• Significancia valor-p: {fmt_decimal(p_val, 4)}\n"
        f"• Referencia: t = 0 (sep-2023) a t = 32 (may-2026)"
    )
    ax.text(0.04, 0.94, cuadro_texto, transform=ax.transAxes,
            va='top', ha='left', fontsize=8.2,
            bbox=dict(boxstyle='square,pad=0.5', facecolor='#F8F8F8', edgecolor='#666666', lw=0.9))
    
    ax.set_xlabel("Índice de mes ($t = 0, \\dots, 32$ | sep-2023 a may-2026)")
    ax.set_ylabel("Inscritos mensuales")
    ax.yaxis.set_major_formatter(formatter_bo)
    ax.set_xlim(-1, 33)
    ax.set_ylim(100, 620)
    ax.grid(True, linestyle=':', alpha=0.5, color='#888888')
    
    # Leyenda colocada fuera abajo
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=2,
              frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=8.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    guardar_figura_exacta(fig, "grafico_3_5_ols_matricula.png")


# =============================================================================
# G4.1: Calidad del corpus (Dos paneles)
# =============================================================================
def generar_g4_1():
    """
    G4.1: Calidad del corpus en dos paneles:
    (a) Staging pendiente, 1.044: CI_NOMBRE_DISCORDANTE 756 y BAJA_CONFIANZA_IA 288.
    (b) Excepciones interceptadas, 562: Likert 283, correo 139, comentario 87,
        sin forma de nombre 48, sin coincidencia 5;
        con la anotación «0 de 562 ingresaron al DW sin control».
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(ANCHO_16CM, 4.6), dpi=300,
                                   gridspec_kw={'height_ratios': [1, 1.8], 'hspace': 0.60})
    fig.subplots_adjust(left=0.38, right=0.94, top=0.93, bottom=0.12)
    
    # ---------------- Panel (a): Staging pendiente ----------------
    cat_a = [
        "CI_NOMBRE_DISCORDANTE",
        "BAJA_CONFIANZA_IA"
    ]
    val_a = [756, 288]
    pct_a = [756 / 1044 * 100, 288 / 1044 * 100]
    
    y_a = np.arange(len(cat_a))
    b_a = ax1.barh(y_a, val_a, color=['#555555', '#AAAAAA'], edgecolor='#111111',
                   height=0.45, hatch=['///', '...'], linewidth=1.1)
    
    ax1.set_yticks(y_a)
    ax1.set_yticklabels(cat_a, fontsize=8.5)
    ax1.set_xlabel("Registros pendientes en Staging (Total = 1.044)", fontsize=8.5)
    ax1.set_xlim(0, 950)
    ax1.xaxis.set_major_formatter(formatter_bo)
    ax1.grid(axis='x', linestyle=':', alpha=0.5, color='#888888')
    ax1.invert_yaxis()
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    for bar, val, pct in zip(b_a, val_a, pct_a):
        txt = f"{fmt_miles(val)} ({fmt_decimal(pct, 2)} %)"
        ax1.text(val + 18, bar.get_y() + bar.get_height() / 2, txt,
                 va='center', ha='left', fontsize=8.5)
    
    ax1.text(-0.62, 1.15, "(a) Staging pendiente por causa técnica (n = 1.044)",
             transform=ax1.transAxes, fontsize=9.5, weight='bold')
    
    # ---------------- Panel (b): Excepciones interceptadas ----------------
    cat_b = [
        "Likert (escala numérica)",
        "Correo electrónico en celda",
        "Comentario de texto libre",
        "Sin forma de nombre",
        "Sin coincidencia catálogo"
    ]
    val_b = [283, 139, 87, 48, 5]
    pct_b = [v / 562 * 100 for v in val_b]
    
    y_b = np.arange(len(cat_b))
    colores_b = ['#444444', '#777777', '#999999', '#CCCCCC', '#EAEAEA']
    tramas_b = ['///', '...', 'xxx', '\\\\\\', '+++']
    
    b_b = ax2.barh(y_b, val_b, color=colores_b, edgecolor='#111111',
                   height=0.55, hatch=tramas_b, linewidth=1.1)
    
    ax2.set_yticks(y_b)
    ax2.set_yticklabels(cat_b, fontsize=8.5)
    ax2.set_xlabel("Entidades anómalas interceptadas (Total = 562)", fontsize=8.5)
    ax2.set_xlim(0, 360)
    ax2.xaxis.set_major_formatter(formatter_bo)
    ax2.grid(axis='x', linestyle=':', alpha=0.5, color='#888888')
    ax2.invert_yaxis()
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    for bar, val, pct in zip(b_b, val_b, pct_b):
        txt = f"{fmt_miles(val)} ({fmt_decimal(pct, 2)} %)"
        ax2.text(val + 6, bar.get_y() + bar.get_height() / 2, txt,
                 va='center', ha='left', fontsize=8.5)
        
    ax2.text(0.98, 0.16, "0 de 562 ingresaron al DW sin control", transform=ax2.transAxes,
             ha='right', va='center', fontsize=8.5, weight='bold',
             bbox=dict(boxstyle='square,pad=0.4', facecolor='#FFFFFF', edgecolor='#222222', lw=1.0))
    
    ax2.text(-0.62, 1.10, "(b) Excepciones de calidad interceptadas en preprocesamiento (n = 562)",
             transform=ax2.transAxes, fontsize=9.5, weight='bold')
    
    guardar_figura_exacta(fig, "grafico_4_1_calidad_corpus.png")
    shutil.copy2(OUTPUT_DIR / "grafico_4_1_calidad_corpus.png",
                 OUTPUT_DIR / "grafico_4_1_inconsistencias_corpus.png")


# =============================================================================
# G4.2: Resoluciones por etapa de la cascada jerárquica (N = 11.426)
# =============================================================================
def generar_g4_2():
    """
    G4.2: Resoluciones por etapa de la cascada (N = 11.426):
    - CI: 1.850 (16,19 %)
    - Encabezado: 3.079 (26,95 %)
    - Regex: 3.103 (27,16 %)
    - BETO: 3.248 (28,43 %)
    - Fuzzy: 146 (1,28 %)
    """
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 3.2), dpi=300)
    fig.subplots_adjust(left=0.38, right=0.94, top=0.92, bottom=0.18)
    
    etapas = [
        "1. Documento de identidad (CI exacta)",
        "2. Encabezado posicional",
        "3. Expresiones regulares (Regex)",
        "4. Modelo del lenguaje BETO (NLP)",
        "5. Coincidencia difusa (RapidFuzz)"
    ]
    valores = [1850, 3079, 3103, 3248, 146]
    porcentajes = [16.19, 26.95, 27.16, 28.43, 1.28]
    
    y_pos = np.arange(len(etapas))
    colores = ['#444444', '#777777', '#999999', '#555555', '#CCCCCC']
    tramas = ['///', '...', '\\\\\\', 'xxx', '+++']
    
    barras = ax.barh(y_pos, valores, color=colores, edgecolor='#111111',
                     height=0.55, hatch=tramas, linewidth=1.1)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(etapas)
    ax.set_xlabel("Resoluciones exitosas por etapa (Total N = 11.426)")
    ax.set_xlim(0, 3950)
    ax.xaxis.set_major_formatter(formatter_bo)
    ax.grid(axis='x', linestyle=':', alpha=0.5, color='#888888')
    ax.invert_yaxis()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    for bar, val, pct in zip(barras, valores, porcentajes):
        txt = f"{fmt_miles(val)} ({fmt_decimal(pct, 2)} %)"
        ax.text(val + 50, bar.get_y() + bar.get_height() / 2, txt,
                va='center', ha='left', fontsize=8.5)
        
    guardar_figura_exacta(fig, "grafico_4_2_resoluciones_cascada.png")
    shutil.copy2(OUTPUT_DIR / "grafico_4_2_resoluciones_cascada.png",
                 OUTPUT_DIR / "grafico_4_2_confianza_probabilistica.png")


# =============================================================================
# G4.3: Vinculación por archivo (Barras apiladas directo/HITL)
# =============================================================================
def generar_g4_3():
    """
    G4.3: Vinculación por archivo, barras apiladas directo/HITL:
    - ARCA: 448 / 2
    - Cobranzas: 349 / 1
    - Inscritos: 248 / 2
    - Eval. Docente (Institución A): 137 / 13
    - Exp. Docente: 95 / 15
    - Egresos: 53 / 0
    - Ejecutado vs Meta: 23 / 1
    Límite xlim=(0, 580) para evitar cortes de texto; leyenda fuera abajo.
    Sin motivos por archivo (son N/D).
    """
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.0), dpi=300)
    fig.subplots_adjust(left=0.38, right=0.96, top=0.95, bottom=0.22)
    
    archivos = [
        "ARCA",
        "Cobranzas",
        "Inscritos",
        "Eval. Docente (Institución A)",
        "Exp. Docente",
        "Egresos",
        "Ejecutado vs Meta"
    ]
    directo = [448, 349, 248, 137, 95, 53, 23]
    hitl = [2, 1, 2, 13, 15, 0, 1]
    totales = [d + h for d, h in zip(directo, hitl)]
    
    y_pos = np.arange(len(archivos))
    
    b1 = ax.barh(y_pos, directo, color='#666666', edgecolor='#111111',
                 height=0.55, hatch='///', label='Consolidación directa (≥ 0,85)')
    b2 = ax.barh(y_pos, hitl, left=directo, color='#CCCCCC', edgecolor='#111111',
                 height=0.55, hatch='...', label='Revisión humana HITL (0,60 – 0,85)')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(archivos)
    ax.set_xlabel("Cantidad de registros evaluados")
    ax.set_xlim(0, 580)
    ax.xaxis.set_major_formatter(formatter_bo)
    ax.grid(axis='x', linestyle=':', alpha=0.5, color='#888888')
    ax.invert_yaxis()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    for i, (d, h, tot) in enumerate(zip(directo, hitl, totales)):
        rotulo = f"{fmt_miles(d)} dir. / {h} HITL (Total {tot})"
        ax.text(tot + 8, i, rotulo, va='center', ha='left', fontsize=8.2)
        
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=2,
              frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=8.2)
    
    guardar_figura_exacta(fig, "grafico_4_3_vinculacion_por_archivo.png")
    shutil.copy2(OUTPUT_DIR / "grafico_4_3_vinculacion_por_archivo.png",
                 OUTPUT_DIR / "grafico_4_3_distribucion_archivo_lote_1387.png")


# =============================================================================
# G4.4: KPIs por perspectiva del CMI (Gráfico analítico Pretest vs Postest)
# =============================================================================
def generar_g4_4():
    """
    G4.4: Disponibilidad de KPI por perspectiva estratégica de Kaplan y Norton (Pretest vs Postest).
    Estructurado en las 4 perspectivas oficiales:
    - Financiera (5 KPI operativos): KPI-01 a KPI-05
    - Clientes / Estudiantes y mercado (0 evaluados + 1 N/D*): KPI-06
    - Procesos Internos (2 KPI operativos): KPI-10 y KPI-11
    - Aprendizaje y Crecimiento (3 KPI operativos): KPI-07 a KPI-09
    Total: 10 KPI operativos (+ 1 N/D) = 11 KPI de la tesis.
    Escala de grises con tramas, tipografía serif 10 pt, sin título interno, leyenda fuera abajo.
    """
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.3), dpi=300)
    fig.subplots_adjust(left=0.10, right=0.96, top=0.94, bottom=0.28)
    
    perspectivas = [
        "1. Perspectiva\nFinanciera",
        "2. Clientes\n(Estudiantes y mercado)",
        "3. Procesos\nInternos",
        "4. Aprendizaje\ny Crecimiento"
    ]
    x = np.arange(len(perspectivas))
    width = 0.32
    
    pretest = [0, 0, 0, 0]
    postest_op = [5, 0, 2, 3]
    postest_nd = [0, 1, 0, 0]
    
    b_pre = ax.bar(x - width/2, pretest, width,
                   label='Pretest (Línea base: sistemas aislados, 0 KPI centralizados)',
                   color='#E5E5E5', edgecolor='#222222', hatch='..', linewidth=1.1)
    
    b_post_op = ax.bar(x + width/2, postest_op, width,
                       label='Postest (KPI operativos en CMI / DW - Gestión 2025)',
                       color='#555555', edgecolor='#111111', hatch='///', linewidth=1.1)
    
    b_post_nd = ax.bar(x + width/2, postest_nd, width, bottom=postest_op,
                       label='Postest (KPI no determinado: KPI-06 N/D*)',
                       color='#B0B0B0', edgecolor='#111111', hatch='xxx', linewidth=1.1)
    
    ax.set_ylabel("Cantidad de KPI estratégicos disponibles")
    ax.set_xticks(x)
    ax.set_xticklabels(perspectivas, fontsize=8.8)
    ax.set_ylim(0, 6.5)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.yaxis.set_major_formatter(formatter_bo)
    ax.grid(axis='y', linestyle=':', alpha=0.6, color='#888888')
    
    # Anotar pretest
    for r in b_pre:
        ax.text(r.get_x() + r.get_width()/2, 0.15, "0", ha='center', va='bottom', fontsize=8.5, color='#444444')
        
    # Anotar postest
    labels_post = [
        "5 KPI\n(KPI-01 a 05)",
        "0 (+1 N/D*)\n(KPI-06)",
        "2 KPI\n(KPI-10 y 11)",
        "3 KPI\n(KPI-07 a 09)"
    ]
    totales_post = [5, 1, 2, 3]
    for r, tot, lbl in zip(b_post_op, totales_post, labels_post):
        ax.text(r.get_x() + r.get_width()/2, tot + 0.18, lbl,
                ha='center', va='bottom', fontsize=8.2, weight='bold', color='#111111')
        
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.20), ncol=2,
              frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=7.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    guardar_figura_exacta(fig, "grafico_4_4_kpi_cmi_perspectivas.png")
    shutil.copy2(OUTPUT_DIR / "grafico_4_4_kpi_cmi_perspectivas.png",
                 OUTPUT_DIR / "grafico_4_4_kpis_cmi.png")


# =============================================================================
# G4.5: Tiempo de consolidación semilogarítmico (Pretest vs Postest)
# =============================================================================
def generar_g4_5():
    """
    G4.5: Tiempo de consolidación en escala semilogarítmica:
    - Pretest: 600,0 min
    - Postest: 9,2 min (60,0 s de máquina + 490,5 s de KLM)
    Margen izquierdo left=0.18 para evitar cortes en eje Y.
    Flecha sin solaparse y rótulo «Reducción del −98,5 % (Δ = −590,8 min)».
    Leyenda fuera abajo.
    """
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.0), dpi=300)
    fig.subplots_adjust(left=0.18, right=0.96, top=0.95, bottom=0.24)
    
    escenarios = [
        "Pretest: Consolidación manual\n(Línea base: 8 a 12 horas)",
        "Postest: Pipeline analítico\n(Automatizado + HITL)"
    ]
    x = np.arange(len(escenarios))
    
    # Barra pretest
    ax.bar(x[0], 600.0, width=0.42, color='#666666', edgecolor='#111111',
           hatch='///', linewidth=1.1)
    ax.errorbar([x[0]], [600.0], yerr=[[120.0], [120.0]], fmt='none',
                ecolor='#111111', elinewidth=1.3, capsize=5)
    
    # Barra postest apilada (máquina 1,0 min + KLM 8,175 min = 9,175 min ~ 9,2 min)
    t_maquina = 60.0 / 60.0    # 1,0 min
    t_klm = 490.5 / 60.0       # 8,175 min
    ax.bar(x[1], t_maquina, width=0.42, color='#333333', edgecolor='#111111',
           hatch='\\\\\\', linewidth=1.1, label='Tiempo de máquina (60,0 s)')
    ax.bar(x[1], t_klm, bottom=t_maquina, width=0.42, color='#D0D0D0', edgecolor='#111111',
           hatch='...', linewidth=1.1, label='Revisión humana estimada (KLM: 490,5 s)')
    
    ax.set_yscale('log')
    ax.set_ylabel("Tiempo de consolidación (minutos, escala logarítmica)")
    ax.set_xticks(x)
    ax.set_xticklabels(escenarios)
    ax.set_ylim(0.5, 2400)
    
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: fmt_miles(y)))
    ax.grid(axis='y', linestyle=':', alpha=0.5, color='#888888', which='both')
    
    ax.text(x[0], 850, "600,0 min\n(media de 10,0 h)", ha='center', va='bottom', fontsize=8.5, weight='bold')
    ax.text(x[1], 12.0, "9,2 min total\n(revisión humana estimada (KLM))",
            ha='center', va='bottom', fontsize=8.5, weight='bold')
    
    ax.annotate(
        "Reducción del −98,5 %\n(Δ = −590,8 min)",
        xy=(x[1], 20), xytext=(0.48, 120),
        arrowprops=dict(facecolor='#111111', shrink=0.08, width=1.1, headwidth=5),
        ha='center', va='center', fontsize=8.5,
        bbox=dict(boxstyle="square,pad=0.35", fc="#FFFFFF", ec="#333333", lw=0.9)
    )
    
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=2,
              frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=8.0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    guardar_figura_exacta(fig, "grafico_4_5_tiempo_consolidacion_semilog.png")


# =============================================================================
# G4.6: Evaluación comparativa Likert (Pretest vs Postest, N = 10)
# =============================================================================
def generar_g4_6():
    """
    G4.6: Evaluación comparativa de usabilidad por dimensión Likert (Pretest vs Postest, N = 10).
    Tipografía serif de 10 pt, escala de grises con tramas, recortando barras de error en 5,0
    para respetar la escala ordinal máxima (1 a 5). Leyenda fuera abajo.
    """
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.4), dpi=300)
    fig.subplots_adjust(left=0.36, right=0.96, top=0.95, bottom=0.20)
    
    items = [
        "1. Disponibilidad oportuna",
        "2. Confiabilidad y gobierno",
        "3. Detección temprana mora",
        "4. Facilidad de consulta",
        "5. Trazabilidad documental",
        "6. Capacidad prospectiva",
        "7. Soporte a decisiones",
        "8. Autonomía frente a TI",
        "9. Satisfacción global"
    ]
    
    medias_pre = np.array([1.80, 1.90, 1.70, 2.10, 1.60, 1.40, 2.30, 2.40, 2.00])
    desv_pre =   np.array([0.63, 0.57, 0.48, 0.74, 0.52, 0.52, 0.67, 0.70, 0.67])
    
    medias_post = np.array([4.60, 4.50, 4.70, 4.80, 4.40, 4.50, 4.60, 4.30, 4.70])
    desv_post =   np.array([0.52, 0.53, 0.48, 0.42, 0.52, 0.53, 0.52, 0.67, 0.48])
    
    # Recorte asimétrico de error en 5,0 para postest (escala Likert acotada [1, 5])
    err_sup_post = np.minimum(desv_post, 5.0 - medias_post)
    xerr_post = [desv_post, err_sup_post]
    
    y = np.arange(len(items))
    height = 0.36
    
    b1 = ax.barh(y - height/2, medias_pre, height, label='Pretest (Línea base manual)',
                 color='#D0D0D0', edgecolor='#222222', hatch='..', xerr=desv_pre, capsize=3,
                 error_kw={'ecolor': '#333333', 'elinewidth': 1.0})
    b2 = ax.barh(y + height/2, medias_post, height, label='Postest (Sistema BI implementado)',
                 color='#555555', edgecolor='#111111', hatch='///', xerr=xerr_post, capsize=3,
                 error_kw={'ecolor': '#111111', 'elinewidth': 1.0})
    
    ax.set_yticks(y)
    ax.set_yticklabels(items, fontsize=8.5)
    ax.set_xlabel("Puntuación media en escala Likert (1: Muy deficiente a 5: Excelente)")
    ax.set_xlim(0, 5.2)
    ax.set_xticks([0, 1, 2, 3, 4, 5])
    ax.xaxis.set_major_formatter(formatter_bo)
    ax.grid(axis='x', linestyle=':', alpha=0.5, color='#888888')
    
    # Línea neutral en 3,0
    ax.axvline(3.0, color='#666666', linestyle='--', linewidth=1.0)
    
    # Leyenda colocada fuera abajo
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2,
              frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=8.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.invert_yaxis()
    
    guardar_figura_exacta(fig, "grafico_4_6_evaluacion_likert_pre_post.png")


# =============================================================================
# Ejecución consolidada
# =============================================================================
def main():
    print("Iniciando regeneración de gráficos oficiales v2 (snapshot_dw_20261110_1201)...")
    generar_g3_2()
    generar_g3_3()
    generar_g3_4()
    generar_g3_5()
    generar_g4_1()
    generar_g4_2()
    generar_g4_3()
    generar_g4_4()
    generar_g4_5()
    generar_g4_6()
    print("\n¡Todos los gráficos fueron generados exitosamente en docs/evidencias/graficos_v2/ con 16 cm y 300 DPI!")


if __name__ == '__main__':
    main()
