# -*- coding: utf-8 -*-
"""
scripts/generar_figuras_f3_congelado.py
=======================================
Generación integral de figuras y gráficos académicos para la fase F3 CONGELADO (18-nov-2026).
Proyecto de Grado - Sistema BI GiraGroup S.R.L.

Normas técnicas aplicadas:
- Fuente única estricta: docs/fuente_verdad_tesis.md y archivos de docs/mediciones/
- Formato numérico boliviano: coma (,) decimal y punto (.) de miles
- Resolución: 300 DPI, fondo blanco puro (#FFFFFF), paleta en escala de grises con tramas (hatching) APA/IEEE
- Tipografía serif académica de alta legibilidad
- Invariantes F3V (DECISIÓN 3 F3V): 51 tablas base, 10 vistas bi, 10 hechos, 7 dimensiones, 1 puente, 23 KPI
- Flujo DataOps oficial: 3 pasos (① Carga -> ② Lectura de BETO -> ③ Revisión HITL)
- Destinos de salida: docs/figuras/f3/ y docs/evidencias/graficos_v2/
"""

import os
import json
import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as patches

# Configuración tipográfica y de estilo
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['DejaVu Serif', 'Times New Roman', 'Cambria', 'Georgia']
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['axes.labelsize'] = 9.5
plt.rcParams['xtick.labelsize'] = 8.5
plt.rcParams['ytick.labelsize'] = 8.5
plt.rcParams['legend.fontsize'] = 8.5
plt.rcParams['figure.titlesize'] = 11

DIR_FIGURAS_F3 = pathlib.Path("docs/figuras/f3")
DIR_EVIDENCIAS = pathlib.Path("docs/evidencias/graficos_v2")
DIR_FIGURAS_F3.mkdir(parents=True, exist_ok=True)
DIR_EVIDENCIAS.mkdir(parents=True, exist_ok=True)

ANCHO_16CM = 16.0 / 2.54  # 6.2992 pulgadas

# -----------------------------------------------------------------------------
# Formateadores numéricos estándar boliviano
# -----------------------------------------------------------------------------
def fmt_miles(val):
    return f"{int(round(val)):,}".replace(',', '.')

def fmt_decimal(val, dec=2):
    fmt = f"{{:,.{dec}f}}"
    txt = fmt.format(val)
    return txt.replace(',', 'X').replace('.', ',').replace('X', '.')

def formatter_bo(x, pos):
    if abs(x - int(round(x))) < 1e-5:
        return fmt_miles(x)
    return fmt_decimal(x, dec=1)

def formatter_pct(x, pos):
    return f"{fmt_decimal(x, 1)} %"

formatter_coma = ticker.FuncFormatter(formatter_bo)
formatter_pct_axis = ticker.FuncFormatter(formatter_pct)

def guardar_figura(fig, nombre_archivo):
    """Guarda en docs/figuras/f3/ y copia a docs/evidencias/graficos_v2/."""
    p1 = DIR_FIGURAS_F3 / nombre_archivo
    p2 = DIR_EVIDENCIAS / nombre_archivo
    fig.savefig(p1, dpi=300, bbox_inches='tight', facecolor='#FFFFFF', edgecolor='none')
    fig.savefig(p2, dpi=300, bbox_inches='tight', facecolor='#FFFFFF', edgecolor='none')
    plt.close(fig)
    print(f"[OK] Generado a 300 DPI: {nombre_archivo}")


# =============================================================================
# 1. Gráfico 3.1: Matriz de confusión NER BETO (gold_510, Modo C estricto)
# =============================================================================
def generar_grafico_3_1():
    p_json = pathlib.Path("docs/mediciones/f3r_matriz_confusion.json")
    data = json.loads(p_json.read_text(encoding="utf-8"))
    
    clases = ["MODULO", "PER_DOCENTE", "PER_ESTUDIANTE", "PROGRAMA"]
    # Soporte: MODULO=150, PER_DOCENTE=50, PER_ESTUDIANTE=130, PROGRAMA=180 (Total 510)
    # TP: MODULO=150, PER_DOCENTE=50, PER_ESTUDIANTE=129, PROGRAMA=174 (Total 503 TP estricto)
    # FN: MODULO=0, PER_DOCENTE=0, PER_ESTUDIANTE=1, PROGRAMA=6 (Total 7)
    # FP: MODULO=0, PER_DOCENTE=0, PER_ESTUDIANTE=1, PROGRAMA=13 (Total 14)
    cm_abs = np.array([
        [150,   0,   0,   0],
        [  0,  50,   0,   0],
        [  0,   0, 129,   1],
        [  0,   0,   6, 174]
    ])
    sumas = cm_abs.sum(axis=1)[:, np.newaxis]
    cm_norm = np.divide(cm_abs.astype(float), sumas, out=np.zeros(cm_abs.shape), where=sumas > 0)
    
    fig, ax = plt.subplots(figsize=(6.5, 5.2), dpi=300)
    fig.subplots_adjust(left=0.20, right=0.92, top=0.92, bottom=0.18)
    
    im = ax.imshow(cm_norm, cmap="Blues", interpolation="nearest", vmin=0, vmax=1)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel("Proporción normalizada (Recall)", rotation=-90, va="bottom", fontsize=9)
    cbar.ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: fmt_decimal(y, 1)))
    
    ax.set_xticks(range(len(clases)))
    ax.set_yticks(range(len(clases)))
    ax.set_xticklabels(clases, fontsize=8.5, rotation=15)
    ax.set_yticklabels(clases, fontsize=8.5)
    ax.set_xlabel("Clase predicha (Inferencia BETO NLP)")
    ax.set_ylabel("Clase real (Gold Standard)")
    
    for i in range(len(clases)):
        for j in range(len(clases)):
            val_norm = cm_norm[i, j]
            val_abs = cm_abs[i, j]
            color = "white" if val_norm > 0.55 else "#111111"
            ax.text(j, i, f"{fmt_decimal(val_norm, 3)}\n(n = {fmt_miles(val_abs)})",
                    ha="center", va="center", color=color, fontsize=7.8, weight="bold")
            
    fig.text(0.12, 0.04, "Fuente: Elaboración propia a partir de docs/mediciones/f3r_matriz_confusion.json (503 TP estricto / 510 soporte)",
             fontsize=7.8, style='italic', color='#333333')
    guardar_figura(fig, "grafico_3_1_matriz_confusion_beto.png")


# =============================================================================
# 2. Gráfico 3.2: Distribución del lote de validación controlado 1.387
# =============================================================================
def generar_grafico_3_2():
    p_json = pathlib.Path("docs/mediciones/f3v_lote_1387_r1.json")
    data = json.loads(p_json.read_text(encoding="utf-8"))
    
    # 1.360 directo (98,05 %), 27 HITL (1,95 %), 0 staging (0,00 %)
    categorias = [
        "Consolidación directa (≥ 0,85 y personas)",
        "Revisión humana HITL (0,60 – 0,85)",
        "Retenido en Staging (< 0,60)"
    ]
    valores = [1360, 27, 0]
    porcentajes = [98.05, 1.95, 0.00]
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 2.7), dpi=300)
    fig.subplots_adjust(left=0.38, right=0.94, top=0.92, bottom=0.20)
    
    y_pos = np.arange(len(categorias))
    colores = ['#4A4A4A', '#8C8C8C', '#D9D9D9']
    tramas = ['///', '...', 'xxx']
    
    barras = ax.barh(y_pos, valores, color=colores, edgecolor='#111111',
                     height=0.52, hatch=tramas, linewidth=1.1)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categorias)
    ax.set_xlabel("Cantidad de registros evaluados (Total N = 1.387)")
    ax.set_xlim(0, 1650)
    ax.xaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='x', linestyle=':', alpha=0.6, color='#888888')
    
    for bar, val, pct in zip(barras, valores, porcentajes):
        txt = f"{fmt_miles(val)} ({fmt_decimal(pct, 2)} %)"
        ax.text(val + 30, bar.get_y() + bar.get_height() / 2, txt,
                va='center', ha='left', fontsize=8.5, color='#111111', weight='medium')
        
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.invert_yaxis()
    
    guardar_figura(fig, "grafico_3_2_distribucion_lote_1387.png")


# =============================================================================
# 3. Gráfico 3.3: Ablación A/B/C del modelo BETO (gold_510 y layouts_5)
# =============================================================================
def generar_grafico_3_3():
    p_json = pathlib.Path("docs/mediciones/f3r_ablacion.json")
    data = json.loads(p_json.read_text(encoding="utf-8"))
    
    # Valores exactos de Tabla C.1 (docs/fuente_verdad_tesis.md):
    # gold_510 (F1 micro estricto): A 100,00 %, B 100,00 %, C 97,96 %
    # layouts_5 (F1 micro relajado): A 28,57 %, B 73,76 %, C 72,06 %
    escenarios = [
        "Dataset estándar (gold_510)\nF1 micro estricto",
        "Layouts adversarios (layouts_5)\nF1 micro relajado"
    ]
    modo_a = [100.00, 28.57]
    modo_b = [100.00, 73.76]
    modo_c = [97.96, 72.06]
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 3.6), dpi=300)
    fig.subplots_adjust(left=0.12, right=0.96, top=0.94, bottom=0.16)
    
    x = np.arange(len(escenarios))
    ancho = 0.22
    
    b1 = ax.bar(x - ancho, modo_a, ancho, label='Modo A (Reglas puras)',
                color='#E0E0E0', edgecolor='#111111', hatch='///', linewidth=1.1)
    b2 = ax.bar(x, modo_b, ancho, label='Modo B (Híbrido implementado)',
                color='#555555', edgecolor='#111111', hatch='...', linewidth=1.1)
    b3 = ax.bar(x + ancho, modo_c, ancho, label='Modo C (BETO puro)',
                color='#A0A0A0', edgecolor='#111111', hatch='xxx', linewidth=1.1)
    
    ax.set_ylabel("Puntuación F1 (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(escenarios)
    ax.set_ylim(0, 118)
    ax.yaxis.set_major_formatter(formatter_pct_axis)
    ax.grid(axis='y', linestyle=':', alpha=0.6, color='#888888')
    
    for barras, vals in [(b1, modo_a), (b2, modo_b), (b3, modo_c)]:
        for bar, v in zip(barras, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2.5,
                    f"{fmt_decimal(v, 2)} %", ha='center', va='bottom', fontsize=8.2, weight='medium')
            
    ax.legend(loc='upper right', frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=8.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    guardar_figura(fig, "grafico_3_3_ablacion_modelos_ner.png")


# =============================================================================
# 4. Gráfico 3.4: Serie de matrícula histórica y pronóstico Holt-Winters amortiguado
# =============================================================================
def generar_grafico_3_4():
    p_json = pathlib.Path("docs/mediciones/f3r_hw_matricula.json")
    data = json.loads(p_json.read_text(encoding="utf-8"))
    
    serie_obs = data["serie_observada"]
    meses_hist = list(serie_obs.keys())
    valores_hist = list(serie_obs.values())
    
    periodos_fut = data["periodos_proyectados"]
    forecast_fut = data["forecast"]
    ic_lower = data["ic_legacy_95"]["lower"]
    ic_upper = data["ic_legacy_95"]["upper"]
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.2), dpi=300)
    fig.subplots_adjust(left=0.12, right=0.96, top=0.95, bottom=0.28)
    
    # Eje X unificado
    todos_meses = meses_hist + periodos_fut
    x_hist = np.arange(len(meses_hist))
    x_fut = np.arange(len(meses_hist), len(todos_meses))
    
    # 1. Histórico observado
    ax.plot(x_hist, valores_hist, 'k-o', ms=3.5, lw=1.2, label=f'Matrícula observada (N = {len(meses_hist)} meses: nov-22 a may-26)')
    
    # 2. Línea divisoria de pronóstico
    ax.axvline(x_hist[-1], color='#555555', linestyle='--', lw=1.0, label='Corte histórico (mayo 2026)')
    
    # 3. Proyección futura
    # Conectar último punto observado con primer proyectado
    x_conn = [x_hist[-1], x_fut[0]]
    y_conn = [valores_hist[-1], forecast_fut[0]]
    ax.plot(x_conn, y_conn, color='#222222', linestyle=':', lw=1.2)
    
    ax.plot(x_fut, forecast_fut, color='#111111', linestyle='-', marker='D', ms=4.0, lw=1.4,
            label='Proyección Holt-Winters amortiguado (jun-nov 2026)')
    
    # 4. Intervalo de confianza al 95 %
    ax.fill_between(x_fut, ic_lower, ic_upper, color='#B8B8B8', alpha=0.55,
                    label='Banda de incertidumbre IC 95 % (RMSE = 59,57)')
    
    ax.set_ylabel("Inscritos mensuales (Alumnos)")
    ax.set_xlabel("Periodo mensual (Aaaa-mm)")
    ax.yaxis.set_major_formatter(formatter_coma)
    
    # Muestreo de etiquetas en eje X
    step = 4
    indices = list(range(0, len(todos_meses), step))
    if (len(todos_meses) - 1) not in indices:
        indices.append(len(todos_meses) - 1)
    ax.set_xticks(indices)
    ax.set_xticklabels([todos_meses[i] for i in indices], rotation=25, fontsize=8.0)
    
    ax.grid(True, linestyle=':', alpha=0.5, color='#888888')
    ax.set_ylim(0, 680)
    
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.22), ncol=2,
              frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=8.0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    guardar_figura(fig, "grafico_3_4_serie_temporal_holt_winters.png")


# =============================================================================
# 5. Gráfico 3.5: Regresión lineal OLS mensual de matrícula (N = 33)
# =============================================================================
def generar_grafico_3_5():
    p_json = pathlib.Path("docs/mediciones/f3r_hw_matricula.json")
    data = json.loads(p_json.read_text(encoding="utf-8"))
    serie_obs = data["serie_observada"]
    
    # Tomar los últimos 33 meses (sep-2023 a may-2026) que componen la ventana formal de OLS
    items = list(serie_obs.items())[-33:]
    meses = [k for k, v in items]
    y = np.array([v for k, v in items])
    t = np.arange(len(y))
    
    # Cifras exactas de SFV Tabla J.1 (E-14):
    # Pendiente: +3,6541 est./mes, Intercepto: 329,72, R² = 0,1921, p = 0,0107
    pendiente = 3.6541
    intercepto = 329.72
    r2 = 0.1921
    p_val = 0.0107
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.0), dpi=300)
    fig.subplots_adjust(left=0.12, right=0.96, top=0.95, bottom=0.25)
    
    ax.scatter(t, y, color='#444444', edgecolor='#111111', s=34, zorder=3,
               label=f'Observaciones mensuales ($y_t$, N = 33)')
    
    y_pred = intercepto + pendiente * t
    ax.plot(t, y_pred, color='#111111', lw=1.6, linestyle='-', zorder=2,
            label='Recta de tendencia OLS')
    
    cuadro_texto = (
        f"Regresión lineal OLS mensual (N = 33 meses):\n"
        f"• Pendiente (β₁): +{fmt_decimal(pendiente, 4)} est./mes\n"
        f"• Intercepto (β₀): {fmt_decimal(intercepto, 2)} (en t = 0)\n"
        f"• Coef. determinación R²: {fmt_decimal(r2, 4)}\n"
        f"• Significancia valor-p: {fmt_decimal(p_val, 4)}\n"
        f"• Periodo: t = 0 (sep-2023) a t = 32 (may-2026)"
    )
    ax.text(0.04, 0.94, cuadro_texto, transform=ax.transAxes,
            va='top', ha='left', fontsize=8.2,
            bbox=dict(boxstyle='square,pad=0.5', facecolor='#F8F8F8', edgecolor='#666666', lw=0.9))
    
    ax.set_xlabel("Índice de mes ($t = 0, \\dots, 32$ | sep-2023 a may-2026)")
    ax.set_ylabel("Inscritos mensuales")
    ax.yaxis.set_major_formatter(formatter_coma)
    ax.set_xlim(-1, 33)
    ax.set_ylim(100, 620)
    ax.grid(True, linestyle=':', alpha=0.5, color='#888888')
    
    ax.legend(loc='lower right', frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=8.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    guardar_figura(fig, "grafico_3_5_ols_matricula.png")


# =============================================================================
# 6. Gráfico 4.1: Calidad de corpus, staging y excepciones de preprocesamiento
# =============================================================================
def generar_grafico_4_1():
    p_lote = pathlib.Path("docs/mediciones/f3v_lote_1387_r1.json")
    d_lote = json.loads(p_lote.read_text(encoding="utf-8"))
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(ANCHO_16CM, 4.6), dpi=300,
                                   gridspec_kw={'height_ratios': [1, 1.8], 'hspace': 0.60})
    fig.subplots_adjust(left=0.38, right=0.94, top=0.93, bottom=0.12)
    
    # ---------------- Panel (a): Staging en f3_base (N = 1.044 pendientes) ----------------
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
    ax1.xaxis.set_major_formatter(formatter_coma)
    ax1.grid(axis='x', linestyle=':', alpha=0.5, color='#888888')
    ax1.invert_yaxis()
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    for bar, val, pct in zip(b_a, val_a, pct_a):
        txt = f"{fmt_miles(val)} ({fmt_decimal(pct, 2)} %)"
        ax1.text(val + 18, bar.get_y() + bar.get_height() / 2, txt,
                 va='center', ha='left', fontsize=8.5)
    
    ax1.text(-0.62, 1.15, "(a) Staging pendiente por causa técnica en ciclo mensual (n = 1.044)",
             transform=ax1.transAxes, fontsize=9.2, weight='bold')
    
    # ---------------- Panel (b): Excepciones interceptadas en lote 1.387 (Total 550) ----------------
    cat_b = [
        "Likert (escala numérica)",
        "Correo electrónico en celda",
        "Comentario de texto libre",
        "Sin forma de nombre",
        "Sin coincidencia catálogo"
    ]
    val_b = [283, 154, 87, 21, 5]
    pct_b = [v / 550 * 100 for v in val_b]
    
    y_b = np.arange(len(cat_b))
    colores_b = ['#444444', '#666666', '#888888', '#AAAAAA', '#CCCCCC']
    tramas_b = ['///', '...', 'xxx', '\\\\\\', '+++']
    
    b_b = ax2.barh(y_b, val_b, color=colores_b, edgecolor='#111111',
                   height=0.55, hatch=tramas_b, linewidth=1.1)
    
    ax2.set_yticks(y_b)
    ax2.set_yticklabels(cat_b, fontsize=8.5)
    ax2.set_xlabel("Entidades anómalas interceptadas en lote controlado (Total = 550)", fontsize=8.5)
    ax2.set_xlim(0, 360)
    ax2.xaxis.set_major_formatter(formatter_coma)
    ax2.grid(axis='x', linestyle=':', alpha=0.5, color='#888888')
    ax2.invert_yaxis()
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    for bar, val, pct in zip(b_b, val_b, pct_b):
        txt = f"{fmt_miles(val)} ({fmt_decimal(pct, 2)} %)"
        ax2.text(val + 6, bar.get_y() + bar.get_height() / 2, txt,
                 va='center', ha='left', fontsize=8.5)
        
    ax2.text(0.98, 0.16, "0 de 550 ingresaron al DW sin control\n(0 de 264 registros afectados)",
             transform=ax2.transAxes, ha='right', va='center', fontsize=8.2, weight='bold',
             bbox=dict(boxstyle='square,pad=0.4', facecolor='#FFFFFF', edgecolor='#222222', lw=1.0))
    
    ax2.text(-0.62, 1.10, "(b) Excepciones de calidad interceptadas en preprocesamiento (n = 550)",
             transform=ax2.transAxes, fontsize=9.2, weight='bold')
    
    guardar_figura(fig, "grafico_4_1_calidad_corpus.png")


# =============================================================================
# 7. Gráfico 4.2: Resoluciones exitosas por etapa de cascada (N = 11.560 entidades)
# =============================================================================
def generar_grafico_4_2():
    p_json = pathlib.Path("docs/mediciones/f3v_lote_1387_r1.json")
    data = json.loads(p_json.read_text(encoding="utf-8"))
    
    # Conteos exactos de SFV Tabla A.1 (N = 11.560 entidades resueltas):
    # CI_EXACTA: 1.850 (16,00 %)
    # ENCABEZADO: 3.079 (26,63 %)
    # REGEX: 3.103 (26,84 %)
    # BETO: 3.382 (29,26 %)
    # FUZZY: 146 (1,26 %)
    etapas = [
        "1. Documento de identidad (CI exacta)",
        "2. Encabezado posicional",
        "3. Expresiones regulares (Regex)",
        "4. Modelo del lenguaje BETO (NLP)",
        "5. Coincidencia difusa (RapidFuzz)"
    ]
    valores = [1850, 3079, 3103, 3382, 146]
    porcentajes = [16.00, 26.63, 26.84, 29.26, 1.26]
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 3.2), dpi=300)
    fig.subplots_adjust(left=0.38, right=0.94, top=0.92, bottom=0.18)
    
    y_pos = np.arange(len(etapas))
    colores = ['#444444', '#777777', '#999999', '#555555', '#CCCCCC']
    tramas = ['///', '...', '\\\\\\', 'xxx', '+++']
    
    barras = ax.barh(y_pos, valores, color=colores, edgecolor='#111111',
                     height=0.55, hatch=tramas, linewidth=1.1)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(etapas)
    ax.set_xlabel("Resoluciones exitosas por etapa (Total N = 11.560)")
    ax.set_xlim(0, 4100)
    ax.xaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='x', linestyle=':', alpha=0.5, color='#888888')
    ax.invert_yaxis()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    for bar, val, pct in zip(barras, valores, porcentajes):
        txt = f"{fmt_miles(val)} ({fmt_decimal(pct, 2)} %)"
        ax.text(val + 50, bar.get_y() + bar.get_height() / 2, txt,
                va='center', ha='left', fontsize=8.5)
        
    guardar_figura(fig, "grafico_4_2_resoluciones_cascada.png")


# =============================================================================
# 8. Gráfico 4.3: Vinculación directa vs HITL por archivo del lote controlado
# =============================================================================
def generar_grafico_4_3():
    p_json = pathlib.Path("docs/mediciones/f3v_lote_1387_r1.json")
    data = json.loads(p_json.read_text(encoding="utf-8"))
    
    # Cifras exactas de SFV Tabla A.2 (docs/fuente_verdad_tesis.md):
    archivos = [
        "Base centralizada Académica ARCA",
        "BD Cobranzas",
        "TBL_INSCRITOS",
        "Evaluación Docente y Unifranz",
        "Experiencia Docente 2.0",
        "BD Egresos",
        "EJECUTADO VS META"
    ]
    directo = [449, 349, 249, 146, 95, 53, 19]
    hitl = [1, 1, 1, 4, 15, 0, 5]
    totales = [d + h for d, h in zip(directo, hitl)]
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.0), dpi=300)
    fig.subplots_adjust(left=0.38, right=0.96, top=0.95, bottom=0.22)
    
    y_pos = np.arange(len(archivos))
    
    b_dir = ax.barh(y_pos, directo, height=0.55, color='#4A4A4A', edgecolor='#111111',
                    hatch='///', linewidth=1.1, label='Consolidación directa (≥ 0,85)')
    b_hitl = ax.barh(y_pos, hitl, left=directo, height=0.55, color='#B0B0B0', edgecolor='#111111',
                     hatch='...', linewidth=1.1, label='Revisión humana HITL (0,60 – 0,85)')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(archivos, fontsize=8.5)
    ax.set_xlabel("Cantidad de registros (Total N = 1.387)")
    ax.set_xlim(0, 580)
    ax.xaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='x', linestyle=':', alpha=0.5, color='#888888')
    ax.invert_yaxis()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    for y_idx, d, h, tot in zip(y_pos, directo, hitl, totales):
        pct_d = d / tot * 100
        txt = f"{fmt_miles(d)} / {h} ({fmt_decimal(pct_d, 1)} % dir)"
        ax.text(tot + 10, y_idx, txt, va='center', ha='left', fontsize=8.2)
        
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=2,
              frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=8.5)
    
    guardar_figura(fig, "grafico_4_3_vinculacion_por_archivo.png")


# =============================================================================
# 9. Gráfico 4.4: Cobertura de KPIs CMI por perspectiva estratégica (23 KPI)
# =============================================================================
def generar_grafico_4_4():
    # Estructurado en las 4 perspectivas oficiales (Total 23 KPI en bi.ref_kpi):
    # - Financiera (9 KPI): 01-05, 12-15
    # - Clientes (5 KPI): 06, 16, 20, 21, 22
    # - Procesos Internos (4 KPI): 10, 11, 18, 23 (DECISIÓN 3 F3V suma KPI-23)
    # - Aprendizaje y Crecimiento (5 KPI): 07, 08, 09, 17, 19
    perspectivas = [
        "Perspectiva\nFinanciera",
        "Perspectiva de\nClientes",
        "Perspectiva de\nProcesos Internos",
        "Aprendizaje y\nCrecimiento"
    ]
    x = np.arange(len(perspectivas))
    width = 0.34
    
    pretest = [0, 0, 0, 0]
    postest = [9, 5, 4, 5]  # Total 23 KPI
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.6), dpi=300)
    fig.subplots_adjust(left=0.09, right=0.96, top=0.94, bottom=0.24)
    
    b_pre = ax.bar(x - width/2, pretest, width, label='Pretest (Línea base manual)',
                   color='#E5E5E5', edgecolor='#222222', hatch='..', linewidth=1.1)
    b_post = ax.bar(x + width/2, postest, width, label='Postest (Cuadro de Mando Integral)',
                    color='#4A4A4A', edgecolor='#111111', hatch='///', linewidth=1.1)
    
    ax.set_ylabel("Cantidad de indicadores KPI disponibles")
    ax.set_xticks(x)
    ax.set_xticklabels(perspectivas, fontsize=8.8)
    ax.set_ylim(0, 11)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.yaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='y', linestyle=':', alpha=0.6, color='#888888')
    
    for r in b_pre:
        ax.text(r.get_x() + r.get_width()/2, 0.20, "0", ha='center', va='bottom', fontsize=8.5, color='#444444')
        
    labels_post = [
        "9 KPI\n(01-05, 12-15)",
        "5 KPI\n(06, 16, 20-22)",
        "4 KPI\n(10, 11, 18, 23)",
        "5 KPI\n(07-09, 17, 19)"
    ]
    for r, val, lbl in zip(b_post, postest, labels_post):
        ax.text(r.get_x() + r.get_width()/2, val + 0.22, lbl,
                ha='center', va='bottom', fontsize=8.2, weight='bold', color='#111111')
        
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2,
              frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=8.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    fig.text(0.09, 0.02, "Fuente: Elaboración propia a partir de docs/mediciones/f3v_invariantes.json y f3v_kpi23.json (23 KPI catalogados)",
             fontsize=8.0, style='italic', color='#333333')
    guardar_figura(fig, "grafico_4_4_kpi_cmi_perspectivas.png")


# =============================================================================
# 10. Gráfico 4.5: Reducción del tiempo de ciclo de consolidación RNF-03 (Semilog)
# =============================================================================
def generar_grafico_4_5():
    # Pretest: 600,0 min (8 a 12 horas, media 10,0 h)
    # Postest medido n=3 (docs/mediciones/f3v_b7_corridas.json):
    # - Tiempo de máquina (caché vacía, n=3): 424,29 s (7,07 min)
    # - Revisión humana estimada (KLM W=2,5 s): 320,60 s (5,34 min)
    # - Total postest: 744,89 s (12,41 min)
    # Reducción: -97,9 % (Δ = -587,59 min)
    escenarios = [
        "Pretest: Consolidación manual\n(Línea base: 8 a 12 horas)",
        "Postest: Pipeline DataOps analítico\n(Máquina + Revisión KLM)"
    ]
    x = np.arange(len(escenarios))
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.2), dpi=300)
    fig.subplots_adjust(left=0.18, right=0.96, top=0.95, bottom=0.25)
    
    # Barra pretest
    ax.bar(x[0], 600.0, width=0.42, color='#666666', edgecolor='#111111',
           hatch='///', linewidth=1.1)
    ax.errorbar([x[0]], [600.0], yerr=[[120.0], [120.0]], fmt='none',
                ecolor='#111111', elinewidth=1.3, capsize=5)
    
    # Barra postest apilada
    t_maquina = 424.29 / 60.0   # 7,07 min
    t_klm = 320.60 / 60.0       # 5,34 min
    t_total = t_maquina + t_klm # 12,41 min
    
    ax.bar(x[1], t_maquina, width=0.42, color='#333333', edgecolor='#111111',
           hatch='\\\\\\', linewidth=1.1, label='Tiempo de máquina (424,29 s / 7,07 min)')
    ax.bar(x[1], t_klm, bottom=t_maquina, width=0.42, color='#D0D0D0', edgecolor='#111111',
           hatch='...', linewidth=1.1, label='Revisión humana estimada (KLM: 320,60 s / 5,34 min)')
    
    ax.set_yscale('log')
    ax.set_ylabel("Tiempo de consolidación (minutos, escala logarítmica)")
    ax.set_xticks(x)
    ax.set_xticklabels(escenarios)
    ax.set_ylim(0.5, 2400)
    
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: fmt_miles(y)))
    ax.grid(axis='y', linestyle=':', alpha=0.5, color='#888888', which='both')
    
    ax.text(x[0], 850, "600,0 min\n(media de 10,0 h)", ha='center', va='bottom', fontsize=8.5, weight='bold')
    ax.text(x[1], 16.0, f"12,41 min total\n(Cumple RNF-03 < 15 min)",
            ha='center', va='bottom', fontsize=8.5, weight='bold')
    
    ax.annotate(
        "Reducción del −97,9 %\n(Δ = −587,59 min)",
        xy=(x[1], 25), xytext=(0.48, 140),
        arrowprops=dict(facecolor='#111111', shrink=0.08, width=1.1, headwidth=5),
        ha='center', va='center', fontsize=8.5,
        bbox=dict(boxstyle="square,pad=0.35", fc="#FFFFFF", ec="#333333", lw=0.9)
    )
    
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=2,
              frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=8.0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    guardar_figura(fig, "grafico_4_5_tiempo_consolidacion_semilog.png")


# =============================================================================
# 11. Gráfico 4.6: Evaluación Likert pretest vs postest (10 usuarios)
# =============================================================================
def generar_grafico_4_6():
    dimensiones = [
        "1. Integración informacional",
        "2. Trazabilidad de origen",
        "3. Confianza en datos",
        "4. Celeridad en consolidación",
        "5. Facilidad de auditoría",
        "6. Soporte a decisiones",
        "7. Autonomía operativa",
        "8. Claridad de indicadores",
        "9. Reducción de retrabajo"
    ]
    pretest = [1.80, 1.40, 2.10, 1.60, 1.50, 2.30, 2.00, 2.40, 1.90]
    postest = [4.70, 4.80, 4.60, 4.80, 4.50, 4.70, 4.60, 4.30, 4.60]
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.6), dpi=300)
    fig.subplots_adjust(left=0.38, right=0.96, top=0.95, bottom=0.18)
    
    y = np.arange(len(dimensiones))
    height = 0.35
    
    b_pre = ax.barh(y - height/2, pretest, height, label='Pretest (Línea base)',
                    color='#D9D9D9', edgecolor='#111111', hatch='..', linewidth=1.1)
    b_post = ax.barh(y + height/2, postest, height, label='Postest (Sistema BI)',
                     color='#444444', edgecolor='#111111', hatch='///', linewidth=1.1)
    
    ax.set_yticks(y)
    ax.set_yticklabels(dimensiones, fontsize=8.5)
    ax.set_xlabel("Puntuación media en escala Likert (1 a 5)")
    ax.set_xlim(0, 5.5)
    ax.xaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='x', linestyle=':', alpha=0.5, color='#888888')
    ax.invert_yaxis()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    for bar, val in zip(b_pre, pretest):
        ax.text(val + 0.08, bar.get_y() + bar.get_height() / 2, f"{fmt_decimal(val, 2)}",
                va='center', ha='left', fontsize=8.0, color='#333333')
    for bar, val in zip(b_post, postest):
        ax.text(val + 0.08, bar.get_y() + bar.get_height() / 2, f"{fmt_decimal(val, 2)}",
                va='center', ha='left', fontsize=8.0, weight='bold', color='#111111')
        
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2,
              frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA', fontsize=8.5)
    
    guardar_figura(fig, "grafico_4_6_evaluacion_likert_pre_post.png")


# =============================================================================
# 12. Figura 3.5: Esquema físico de la constelación del Data Warehouse (10 hechos)
# =============================================================================
def generar_figura_3_5():
    fig, ax = plt.subplots(figsize=(18.0, 13.0), dpi=300)
    ax.set_xlim(0, 180)
    ax.set_ylim(0, 130)
    ax.axis('off')
    
    def dibujar_tabla(x, y, w, h, nombre, columnas, is_fact=False):
        hdr_h = 3.8
        box = patches.Rectangle((x, y), w, h, ec="#111111", fc="#FFFFFF", lw=1.5 if is_fact else 1.2)
        ax.add_patch(box)
        hdr = patches.Rectangle((x, y + h - hdr_h), w, hdr_h, ec="#111111",
                                fc="#E2E2E2" if is_fact else "#F2F2F2", lw=1.1)
        ax.add_patch(hdr)
        ax.text(x + w/2, y + h - hdr_h/2, nombre, fontsize=8.0 if is_fact else 7.6,
                fontweight='bold', ha='center', va='center', color="#111111")
        cur_y = y + h - hdr_h - 2.2
        for col, ctype in columnas:
            is_key = "[PK]" in col or "[FK]" in col
            ax.text(x + 1.2, cur_y, col, fontsize=6.5, fontweight='bold' if is_key else 'normal',
                    color="#111111" if is_key else "#333333")
            ax.text(x + w - 1.2, cur_y, ctype, fontsize=6.2, ha='right', color="#555555")
            cur_y -= 2.2

    # --- 7 Dimensiones Conformadas ---
    dibujar_tabla(4, 98, 32, 26, "dim_docente", [
        ("id_docente [PK]", "INTEGER"),
        ("nombre_completo", "VARCHAR(200)"),
        ("ci_numero", "VARCHAR(30)"),
        ("email", "VARCHAR(150)"),
        ("area_especialidad", "VARCHAR(120)"),
        ("activo", "BOOLEAN")
    ])
    
    dibujar_tabla(40, 98, 38, 28, "dim_estudiante", [
        ("id_estudiante [PK]", "INTEGER"),
        ("nombre_completo", "VARCHAR(250)"),
        ("codigo_estudiante", "VARCHAR(50)"),
        ("ci_numero", "VARCHAR(30)"),
        ("identidad_verificada", "BOOLEAN"),
        ("fk_estado", "VARCHAR(10)"),
        ("deprecado", "BOOLEAN")
    ])
    
    dibujar_tabla(82, 98, 36, 28, "dim_tiempo", [
        ("id_tiempo [PK]", "INTEGER"),
        ("fecha", "DATE"),
        ("anio", "INTEGER"),
        ("mes", "INTEGER"),
        ("nombre_mes", "VARCHAR(20)"),
        ("trimestre", "INTEGER"),
        ("semestre", "INTEGER")
    ])
    
    dibujar_tabla(122, 98, 34, 24, "dim_categoria_financiera", [
        ("id_categoria [PK]", "INTEGER"),
        ("codigo", "VARCHAR(50)"),
        ("nombre_categoria", "VARCHAR(120)"),
        ("tipo_flujo", "VARCHAR(30)"),
        ("activo", "BOOLEAN")
    ])
    
    dibujar_tabla(160, 98, 18, 26, "dim_meta", [
        ("id_meta [PK]", "INTEGER"),
        ("gestion", "INTEGER"),
        ("mes", "INTEGER"),
        ("meta_matricula", "INTEGER"),
        ("meta_recaudacion", "NUMERIC"),
        ("clave_fila [FK]", "VARCHAR(64)")
    ])
    
    dibujar_tabla(4, 8, 42, 26, "dim_modulo", [
        ("id_modulo [PK]", "INTEGER"),
        ("codigo_modulo", "VARCHAR(50)"),
        ("nombre_modulo", "VARCHAR(200)"),
        ("programa", "VARCHAR(150)"),
        ("escuela", "VARCHAR(120)"),
        ("creditos", "INTEGER")
    ])
    
    dibujar_tabla(50, 8, 42, 26, "dim_origen_documental", [
        ("id_documento [PK]", "INTEGER"),
        ("nombre_archivo", "VARCHAR(255)"),
        ("hash_sha256", "VARCHAR(64)"),
        ("tipo_fuente", "VARCHAR(50)"),
        ("total_registros", "INTEGER")
    ])

    dibujar_tabla(96, 8, 34, 20, "bridge_modulo_docente", [
        ("id_modulo [PK,FK]", "INTEGER"),
        ("id_docente [PK,FK]", "INTEGER"),
        ("fecha_asignacion", "DATE"),
        ("es_titular", "BOOLEAN")
    ])

    # --- 10 Tablas de Hechos ---
    # 1. fact_rendimiento_academico
    dibujar_tabla(4, 48, 42, 40, "fact_rendimiento_academico", [
        ("id_rendimiento [PK]", "BIGSERIAL"),
        ("id_estudiante [FK]", "INTEGER"),
        ("id_docente [FK]", "INTEGER"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("id_documento [FK]", "INTEGER"),
        ("nota_final", "NUMERIC(5,2)"),
        ("asistencia_pct", "NUMERIC(5,2)"),
        ("fk_estado [FK]", "VARCHAR(10)"),
        ("confianza_ia", "NUMERIC(4,3)"),
        ("requiere_revision", "BOOLEAN")
    ], is_fact=True)

    # 2. fact_situacion_financiera
    dibujar_tabla(50, 48, 42, 40, "fact_situacion_financiera", [
        ("id_situacion [PK]", "BIGSERIAL"),
        ("id_estudiante [FK]", "INTEGER"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_categoria [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("id_documento [FK]", "INTEGER"),
        ("monto_deuda", "NUMERIC(14,2)"),
        ("monto_pagado", "NUMERIC(14,2)"),
        ("dias_mora", "INTEGER"),
        ("cuotas_impagas", "INTEGER"),
        ("fk_estado [FK]", "VARCHAR(10)")
    ], is_fact=True)

    # 3. fact_evaluacion_docente
    dibujar_tabla(96, 68, 38, 22, "fact_evaluacion_docente", [
        ("id_evaluacion [PK]", "BIGSERIAL"),
        ("id_docente [FK]", "INTEGER"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("puntaje_promedio", "NUMERIC(5,2)")
    ], is_fact=True)

    # 4. fact_marketing
    dibujar_tabla(96, 40, 38, 24, "fact_marketing", [
        ("id_mkt [PK]", "BIGSERIAL"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("leads", "INTEGER"),
        ("inscritos", "INTEGER"),
        ("inversion_bs", "NUMERIC(14,2)")
    ], is_fact=True)

    # 5. fact_rentabilidad
    dibujar_tabla(138, 68, 40, 24, "fact_rentabilidad", [
        ("id_rentabilidad [PK]", "BIGSERIAL"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_categoria [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("monto_ejecutado", "NUMERIC(14,2)"),
        ("monto_meta", "NUMERIC(14,2)")
    ], is_fact=True)

    # 6. fact_costo_programa
    dibujar_tabla(138, 42, 40, 22, "fact_costo_programa", [
        ("id_costo [PK]", "BIGSERIAL"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_documento [FK]", "INTEGER"),
        ("costo_modulo", "NUMERIC(14,2)"),
        ("pago_docente", "NUMERIC(14,2)")
    ], is_fact=True)

    # 7. fact_techo_convenio
    dibujar_tabla(138, 16, 40, 22, "fact_techo_convenio", [
        ("id_techo [PK]", "BIGSERIAL"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("monto_techo_bs", "NUMERIC(14,2)"),
        ("porcentaje_ejec", "NUMERIC(5,2)")
    ], is_fact=True)

    # 8. fact_forecast
    dibujar_tabla(4, 33, 42, 13, "fact_forecast", [
        ("id_forecast [PK]", "SERIAL"),
        ("id_tiempo [FK]", "INTEGER"),
        ("valor_proyectado", "NUMERIC(14,2)")
    ], is_fact=True)

    # 9. fact_cobranzas_proyectadas
    dibujar_tabla(50, 33, 42, 13, "fact_cobranzas_proyectadas", [
        ("id_proyeccion [PK]", "SERIAL"),
        ("id_estudiante [FK]", "INTEGER"),
        ("monto_proyectado", "NUMERIC(14,2)")
    ], is_fact=True)

    # 10. fact_planificacion_programa (DECISIÓN 3 F3V - NUEVA TABLA DE HECHOS)
    dibujar_tabla(96, 14, 38, 24, "fact_planificacion_programa", [
        ("id_planificacion [PK]", "BIGSERIAL"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_tiempo_plan [FK]", "INTEGER"),
        ("id_documento [FK]", "INTEGER"),
        ("clave_fila [FK]", "VARCHAR(64)"),
        ("notificado", "BOOLEAN")
    ], is_fact=True)

    # Cuadro de invariantes
    ax.text(90, 126, "Figura 3.5 Esquema Físico Relacional en Constelación del Data Warehouse GiraGroup BI",
            fontsize=11, weight='bold', ha='center', va='center', color="#111111")
    ax.text(90, 123, "Invariantes F3V: 51 Tablas Base, 10 Vistas Semánticas 'bi', 10 Hechos, 7 Dimensiones Conformadas y 1 Puente",
            fontsize=8.5, style='italic', ha='center', va='center', color="#444444")
    
    guardar_figura(fig, "figura_3_5_esquema_constelacion_fisico.png")


# =============================================================================
# 13. Figura Flujo DataOps Oficial de 3 Pasos
# =============================================================================
def generar_figura_flujo_dataops_3pasos():
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.4), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis('off')
    
    # Título del diagrama
    ax.text(50, 46, "Flujo Oficial del Pipeline DataOps y Resolución Jerárquica de Identidad (3 Pasos)",
            fontsize=10.5, weight='bold', ha='center', va='center', color="#111111")
    ax.text(50, 43, "Arquitectura de ingestión multifuente, inferencia BETO NLP y contención de calidad HITL",
            fontsize=8.5, style='italic', ha='center', va='center', color="#555555")
    
    pasos = [
        {
            "num": "Paso 1",
            "titulo": "Carga de Archivos",
            "subtitulo": "¿Qué estoy cargando y reglas?",
            "items": [
                "• Ingesta (.xlsx, .csv)",
                "• Hash SHA-256 e integridad",
                "• Detección islas y cabeceras",
                "• Descarte excepciones (550)"
            ],
            "x": 6, "w": 26, "h": 32, "color": "#F5F5F5", "edge": "#333333"
        },
        {
            "num": "Paso 2",
            "titulo": "Lectura de BETO",
            "subtitulo": "¿Qué entendió el modelo?",
            "items": [
                "• Inferencia BETO (128 tok)",
                "• Cascada 5 niveles (11.560):",
                "  CI_EXACTA → ENCABEZADO",
                "  → FUZZY → REGEX → BETO",
                "• Separación por bandas"
            ],
            "x": 37, "w": 26, "h": 32, "color": "#EAEAEA", "edge": "#222222"
        },
        {
            "num": "Paso 3",
            "titulo": "Revisión Humana",
            "subtitulo": "¿Qué debo decidir yo?",
            "items": [
                "• Bandeja HITL agrupada",
                "• Criterios: homonimias,",
                "  CI dudosa, baja confianza",
                "• Aprobación por lote/grupo",
                "• Carga DW idempotente"
            ],
            "x": 68, "w": 26, "h": 32, "color": "#DFDFDF", "edge": "#111111"
        }
    ]
    
    for p in pasos:
        box = patches.FancyBboxPatch((p["x"], 7), p["w"], p["h"],
                                     boxstyle="round,pad=0.8,rounding_size=1.5",
                                     ec=p["edge"], fc=p["color"], lw=1.3)
        ax.add_patch(box)
        
        # Cabecera paso
        ax.text(p["x"] + p["w"]/2, 35, f"{p['num']}: {p['titulo']}", fontsize=8.8, weight='bold',
                ha='center', va='center', color="#111111")
        ax.text(p["x"] + p["w"]/2, 31.8, p['subtitulo'], fontsize=7.2, style='italic',
                ha='center', va='center', color="#555555")
        
        # Línea separadora
        ax.plot([p["x"] + 2, p["x"] + p["w"] - 2], [29.5, 29.5], color='#AAAAAA', lw=0.8)
        
        # Ítems
        cur_y = 26.5
        for it in p["items"]:
            ax.text(p["x"] + 2.5, cur_y, it, fontsize=7.2, ha='left', va='center', color="#222222")
            cur_y -= 4.2

    # Flechas de conexión entre pasos
    arrow_kw = dict(arrowstyle="->,head_width=0.4,head_length=0.6", color="#111111", lw=1.8)
    ax.annotate("", xy=(36, 23), xytext=(32.5, 23), arrowprops=arrow_kw)
    ax.annotate("", xy=(67, 23), xytext=(63.5, 23), arrowprops=arrow_kw)
    
    # Anotaciones inferiores
    ax.text(50, 2.5, "Flujo implementado en frontend React (BatchFlowStepper.jsx) y backend FastAPI (/api/v1/dataops)",
            ha='center', va='center', fontsize=7.5, style='italic', color='#555555')
    
    guardar_figura(fig, "figura_flujo_dataops_3pasos.png")


def main():
    print("=================================================================")
    print("Iniciando generación de figuras F3 CONGELADO (18-nov-2026)")
    print("=================================================================")
    generar_grafico_3_1()
    generar_grafico_3_2()
    generar_grafico_3_3()
    generar_grafico_3_4()
    generar_grafico_3_5()
    generar_grafico_4_1()
    generar_grafico_4_2()
    generar_grafico_4_3()
    generar_grafico_4_4()
    generar_grafico_4_5()
    generar_grafico_4_6()
    generar_figura_3_5()
    generar_figura_flujo_dataops_3pasos()
    print("=================================================================")
    print("Todas las figuras analíticas han sido generadas a 300 DPI.")
    print("Nota: Las figuras 3.40, 3.44 y 3.50 (capturas de terminal) se")
    print("generan desde capturas reales en F4-1.")
    print("Destinos:")
    print(" - docs/figuras/f3/")
    print(" - docs/evidencias/graficos_v2/")
    print("=================================================================")

if __name__ == "__main__":
    main()
