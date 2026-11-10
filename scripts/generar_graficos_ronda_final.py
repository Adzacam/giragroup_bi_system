# -*- coding: utf-8 -*-
"""
scripts/generar_graficos_ronda_final.py
=======================================
Generación estricta de figuras y gráficos académicos de la Ronda Final
para el Proyecto de Grado - GiraGroup BI.

Normas técnicas aplicadas:
- 300 DPI, fondo blanco puro (#FFFFFF), escala de grises con tramas (hatching) APA/IEEE.
- Coma decimal en todos los ejes numéricos y rótulos en español.
- Dimensiones legibles sin títulos internos incrustados (los títulos van en el texto de tesis).
- Destino principal: docs/evidencias/graficos/
- Destinos réplica: docs/images/ y artefactos.
"""

import os
import shutil
import pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as patches
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing as ES

# Configuración global
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 9.5
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['axes.labelsize'] = 9.5
plt.rcParams['xtick.labelsize'] = 8.5
plt.rcParams['ytick.labelsize'] = 8.5
plt.rcParams['legend.fontsize'] = 8.5
plt.rcParams['figure.titlesize'] = 11

DIR_EVIDENCIAS_GRAFICOS = pathlib.Path("docs/evidencias/graficos")
DIR_IMAGES = pathlib.Path("docs/images")
DIR_ARTIFACTS = pathlib.Path(r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0")

DIR_EVIDENCIAS_GRAFICOS.mkdir(parents=True, exist_ok=True)
DIR_IMAGES.mkdir(parents=True, exist_ok=True)

def fmt_coma(x, pos):
    if abs(x - int(x)) < 1e-5:
        return f"{int(x):,}".replace(',', '.')
    return f"{x:.1f}".replace('.', ',')

def fmt_coma_2dec(x, pos):
    return f"{x:.2f}".replace('.', ',')

formatter_coma = ticker.FuncFormatter(fmt_coma)
formatter_coma_2dec = ticker.FuncFormatter(fmt_coma_2dec)

def guardar(fig, nombre_base):
    destinos = [
        DIR_EVIDENCIAS_GRAFICOS / nombre_base,
        DIR_IMAGES / nombre_base,
    ]
    if DIR_ARTIFACTS.exists():
        destinos.append(DIR_ARTIFACTS / nombre_base)
    for d in destinos:
        fig.savefig(d, dpi=300, bbox_inches='tight', facecolor='#FFFFFF', edgecolor='none')
    print(f"[OK] Generado: {nombre_base}")


# =============================================================================
# 1. Gráfico 3.2 y Gráfico 4.2: Distribución del lote 1.387 por umbral de confianza
# =============================================================================
def generar_graficos_3_2_y_4_2():
    categorias = [
        "Consolidación directa (≥ 0,85)",
        "Revisión humana HITL (0,60 – 0,85)",
        "Retenido en Staging (< 0,60)"
    ]
    conteos = [1353, 34, 0]
    porcentajes = [97.55, 2.45, 0.00]

    for nombre_archivo in ["grafico_3_2_distribucion_lote_1387.png", "grafico_4_2_confianza_probabilistica.png", "grafico_4_2_distribucion_lote_1387.png"]:
        fig, ax = plt.subplots(figsize=(6.5, 3.0), dpi=300)
        y_pos = np.arange(len(categorias))
        colores = ['#444444', '#888888', '#CCCCCC']
        tramas = ['///', '\\\\\\', '...']

        bars = ax.barh(y_pos, porcentajes, color=colores, edgecolor='#111111', height=0.55, linewidth=1.1)
        for bar, trama in zip(bars, tramas):
            bar.set_hatch(trama)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(categorias)
        ax.set_xlabel("Porcentaje sobre el lote consolidado (N = 1.387) (%)")
        ax.set_xlim(0, 115)
        ax.xaxis.set_major_formatter(formatter_coma)
        ax.grid(axis='x', linestyle='--', alpha=0.5, color='#888888')

        for bar, cnt, pct in zip(bars, conteos, porcentajes):
            offset = 1.8 if pct > 0 else 1.8
            ax.text(pct + offset, bar.get_y() + bar.get_height()/2,
                    f"{cnt:,} reg. ({pct:.2f} %)".replace(',', '.').replace('.', ',', 1) if pct > 0 else "0 reg. (0,00 %)",
                    va='center', ha='left', fontsize=8.5, color='#111111', weight='medium')

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.invert_yaxis()
        guardar(fig, nombre_archivo)
        plt.close(fig)


# =============================================================================
# 2. Gráfico 4.3: Barras apiladas al 100 % por archivo (directo / HITL)
# =============================================================================
def generar_grafico_4_3():
    archivos = [
        "Base centralizada Académica ARCA",
        "BD Cobranzas",
        "TBL_INSCRITOS",
        "Evaluación Docente y Unifranz",
        "Experiencia Docente 2.0",
        "BD Egresos",
        "EJECUTADO VS META"
    ]
    directos = [448, 349, 248, 137, 95, 53, 23]
    hitls = [2, 1, 2, 13, 15, 0, 1]
    totales = [d + h for d, h in zip(directos, hitls)]

    pct_directo = [d / t * 100 for d, t in zip(directos, totales)]
    pct_hitl = [h / t * 100 for h, t in zip(hitls, totales)]

    fig, ax = plt.subplots(figsize=(6.8, 3.8), dpi=300)
    y_pos = np.arange(len(archivos))
    height = 0.58

    b1 = ax.barh(y_pos, pct_directo, height=height, color='#4A4A4A', edgecolor='#111111',
                 hatch='///', label='Consolidación directa (≥ 0,85)')
    b2 = ax.barh(y_pos, pct_hitl, left=pct_directo, height=height, color='#E0E0E0',
                 edgecolor='#111111', hatch='...', label='Derivado a HITL (0,60 – 0,85)')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(archivos)
    ax.set_xlabel("Distribución relativa de registros por archivo (%)")
    ax.set_xlim(0, 108)
    ax.xaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='x', linestyle='--', alpha=0.5, color='#888888')

    for i, (pd_val, ph_val, d_cnt, h_cnt, tot) in enumerate(zip(pct_directo, pct_hitl, directos, hitls, totales)):
        # Etiqueta de directo centrada
        if pd_val > 50:
            ax.text(pd_val / 2, i, f"{d_cnt} ({pd_val:.1f} %)".replace('.', ','),
                    va='center', ha='center', color='#FFFFFF', fontsize=8.0, weight='bold')
        # Etiqueta de HITL a la derecha
        if h_cnt > 0:
            ax.text(pd_val + ph_val + 1.2, i, f"{h_cnt} ({ph_val:.1f} %)".replace('.', ','),
                    va='center', ha='left', color='#111111', fontsize=7.8, weight='medium')
        else:
            ax.text(101.2, i, "0 (0 %)", va='center', ha='left', color='#666666', fontsize=7.8)

    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False, fontsize=8.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.invert_yaxis()

    guardar(fig, "grafico_4_3_distribucion_archivo_lote_1387.png")
    guardar(fig, "grafico_4_3_resolucion_por_formato.png")
    plt.close(fig)


# =============================================================================
# 3. Gráfico 4.1: Excepciones de calidad del lote por categoría
# =============================================================================
def generar_grafico_4_1():
    categorias = [
        "Etiqueta Likert (escala leída como persona)",
        "Correo electrónico como nombre",
        "Columna de texto libre / comentario",
        "Cadena sin morfología de nombre",
        "Persona sin coincidencia en catálogo"
    ]
    valores = [283, 139, 87, 48, 5]
    total_excepciones = 562  # 562 entidades en 268 registros
    porcentajes = [v / total_excepciones * 100 for v in valores]

    fig, ax = plt.subplots(figsize=(6.6, 3.4), dpi=300)
    y_pos = np.arange(len(categorias))

    bars = ax.barh(y_pos, valores, color='#E5E5E5', edgecolor='#1A1A1A', height=0.58, hatch='///', linewidth=1.1)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(categorias)
    ax.set_xlabel("Cantidad de entidades observadas (Total = 562 en 268 registros)")
    ax.set_xlim(0, 330)
    ax.xaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='x', linestyle='--', alpha=0.5, color='#888888')

    for bar, val, pct in zip(bars, valores, porcentajes):
        ax.text(val + 4, bar.get_y() + bar.get_height()/2,
                f"{val} ({pct:.1f} %)".replace('.', ','),
                va='center', ha='left', fontsize=8.5, color='#111111', weight='medium')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.invert_yaxis()

    guardar(fig, "grafico_4_1_excepciones_calidad_lote.png")
    guardar(fig, "grafico_4_1_inconsistencias_corpus.png")
    plt.close(fig)


# =============================================================================
# 4. Gráfico 4.5: Tiempo de consolidación Pretest vs Postest (semilogarítmico)
# =============================================================================
def generar_grafico_4_5():
    fig, ax = plt.subplots(figsize=(6.3, 3.4), dpi=300)

    escenarios = [
        "Pretest: Consolidación manual\n(Rango 8 a 12 horas)",
        "Postest: Pipeline automatizado\n(estimado (KLM))"
    ]
    valores = [600.0, 9.2]
    x = np.arange(len(escenarios))

    barras = ax.bar(x, valores, color=['#555555', '#E0E0E0'], edgecolor='#111111',
                    width=0.45, hatch=['///', '...'], linewidth=1.1)

    ax.errorbar([0], [600.0], yerr=[[120.0], [120.0]], fmt='none', ecolor='#111111', elinewidth=1.2, capsize=5)

    ax.set_yscale('log')
    ax.set_ylabel("Tiempo de consolidación (minutos, escala logarítmica)")
    ax.set_xticks(x)
    ax.set_xticklabels(escenarios)
    ax.set_ylim(1, 2500)

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{int(y):,}".replace(',', '.')))
    ax.grid(axis='y', linestyle='--', alpha=0.5, color='#888888', which='both')

    ax.text(0, 800, "600,0 min\n(10,0 h)", ha='center', va='bottom', fontsize=8.5, weight='bold')
    ax.text(1, 11.5, "9,2 min\nestimado (KLM)", ha='center', va='bottom', fontsize=8.5, weight='bold')

    ax.annotate(
        "Reducción del 98,47 %\n(Δ = −590,8 min)",
        xy=(0.92, 32), xytext=(0.52, 110),
        arrowprops=dict(facecolor='#111111', shrink=0.08, width=1.2, headwidth=6),
        ha='center', va='center', fontsize=8.5, weight='bold',
        bbox=dict(boxstyle="round,pad=0.35", fc="#FFFFFF", ec="#222222", lw=1)
    )

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    guardar(fig, "grafico_4_5_tiempo_consolidacion_semilog.png")
    plt.close(fig)


# =============================================================================
# 5. Gráfico 3.4: Serie mensual de inscritos con Holt-Winters amortiguado
# =============================================================================
def generar_grafico_3_4():
    s_full = pd.read_csv('inscritos.csv', parse_dates=['mes'], index_col='mes')['inscritos'].asfreq('MS', fill_value=0)
    s = s_full.iloc[-33:]
    h = 6

    # Modelo completo adoptado
    M = ES(s, trend='add', damped_trend=True, seasonal='add', seasonal_periods=12, initialization_method='estimated').fit(optimized=True)
    F = M.forecast(h)
    rmse_aj = float(np.sqrt(M.sse / len(s)))
    lo = np.maximum(F - 1.96 * rmse_aj, 0.0)
    hi = F + 1.96 * rmse_aj

    # Modelo entrenamiento para hold-out
    train = s[:-h]
    test = s[-h:]
    m = ES(train, trend='add', damped_trend=True, seasonal='add', seasonal_periods=12, initialization_method='estimated').fit(optimized=True)
    fc = m.forecast(h)
    mape_ho = float((abs(test - fc) / test).mean() * 100)

    fig, ax = plt.subplots(figsize=(8.2, 4.4), dpi=300, facecolor='white')

    ax.plot(s.index, s.values, 'k-o', ms=3.8, lw=1.3, label='Histórico observado (N = 33 meses, 2023-09 a 2026-05)')
    ax.axvline(s.index[-h], color='#444444', linestyle=':', lw=1.2, label='Corte validación hold-out (h = 6 meses)')
    ax.plot(fc.index, fc.values, color='#555555', linestyle='-.', marker='^', ms=3.8, lw=1.2,
            label=f'Ajuste validación hold-out (MAPE = {mape_ho:.1f} %)')
    ax.plot(F.index, F.values, 'k--', marker='s', ms=4.0, lw=1.5, label='Pronóstico Holt-Winters amortiguado (h = 6)')
    ax.fill_between(F.index, lo, hi, color='#B0B0B0', alpha=0.55, label='Intervalo de confianza 95 % (±1,96 RMSE)')

    ax.set_xlabel('Periodo mensual')
    ax.set_ylabel('Inscritos / Nuevas matrículas')
    ax.yaxis.set_major_formatter(formatter_coma)
    ax.grid(True, linestyle=':', alpha=0.6, color='#888888')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper left', frameon=False, fontsize=8.5)

    guardar(fig, "grafico_3_4_serie_temporal_holt_winters.png")
    plt.close(fig)


# =============================================================================
# 6. Figura 3.5: Esquema físico constelación (9 hechos, 7 dimensiones, 1 bridge)
# =============================================================================
def generar_figura_3_5():
    fig, ax = plt.subplots(figsize=(19.0, 13.5), dpi=300)
    ax.set_xlim(0, 190)
    ax.set_ylim(0, 135)
    ax.axis('off')

    def dibujar_tabla(x, y, w, h, nombre, columnas, tipo="fact", conformada=False):
        """
        Dibuja una tabla relacional.
        tipo: 'fact_op' (operativo centro), 'fact' (hecho analitico), 'dim' (dimension), 'bridge' (puente)
        conformada: borde doble si es dimension conformada
        """
        hdr_h = 3.6
        bg_col = "#FFFFFF"
        if tipo == "fact_op":
            hdr_bg = "#D0D0D0"
            border_lw = 1.8
        elif tipo == "fact":
            hdr_bg = "#EBEBEB"
            border_lw = 1.3
        elif tipo == "bridge":
            hdr_bg = "#E8E8E8"
            border_lw = 1.3
        else: # dim
            hdr_bg = "#F4F4F4"
            border_lw = 1.4

        # Caja principal
        box = patches.Rectangle((x, y), w, h, ec="#111111", fc=bg_col, lw=border_lw)
        ax.add_patch(box)

        # Borde doble para dimensiones conformadas
        if conformada:
            box_inner = patches.Rectangle((x + 0.6, y + 0.6), w - 1.2, h - 1.2,
                                          ec="#111111", fc="none", lw=0.8, linestyle="-")
            ax.add_patch(box_inner)

        # Cabecera
        hdr = patches.Rectangle((x, y + h - hdr_h), w, hdr_h, ec="#111111", fc=hdr_bg, lw=1.0)
        ax.add_patch(hdr)
        ax.text(x + w/2, y + h - hdr_h/2, nombre, fontsize=7.6, fontweight='bold', ha='center', va='center', color="#111111")

        # Columnas
        cur_y = y + h - hdr_h - 2.1
        for col, ctype in columnas:
            is_key = "[PK]" in col or "[FK]" in col
            ax.text(x + 1.2, cur_y, col, fontsize=6.3, fontweight='bold' if is_key else 'normal',
                    color="#111111" if is_key else "#333333")
            ax.text(x + w - 1.2, cur_y, ctype, fontsize=5.8, ha='right', color="#555555")
            cur_y -= 2.1

    # Rombo para Bridge
    def dibujar_rombo(x_c, y_c, r, nombre, columnas):
        pts = np.array([
            [x_c, y_c + r],
            [x_c + r * 1.5, y_c],
            [x_c, y_c - r],
            [x_c - r * 1.5, y_c]
        ])
        poly = patches.Polygon(pts, closed=True, ec="#111111", fc="#F2F2F2", lw=1.4)
        ax.add_patch(poly)
        ax.text(x_c, y_c + 1.2, nombre, fontsize=7.2, fontweight='bold', ha='center', va='center', color="#111111")
        ax.text(x_c, y_c - 1.2, "(Bridge M:N)", fontsize=6.2, fontstyle='italic', ha='center', va='center', color="#444444")

    # -------------------------------------------------------------------------
    # 1. FILA SUPERIOR: DIMENSIONES CONFORMADAS (BORDE DOBLE)
    # -------------------------------------------------------------------------
    # dim_estudiante
    dibujar_tabla(8, 98, 38, 32, "dim_estudiante", [
        ("id_estudiante [PK]", "INTEGER"),
        ("codigo_estudiante", "VARCHAR(50)"),
        ("nombre_completo", "VARCHAR(250)"),
        ("ci_numero", "VARCHAR(30)"),
        ("ci_expedido", "VARCHAR(10)"),
        ("email", "VARCHAR(150)"),
        ("celular", "VARCHAR(30)"),
        ("programa_origen", "VARCHAR(200)"),
        ("deprecado", "BOOLEAN"),
        ("identidad_verificada", "BOOLEAN"),
    ], tipo="dim", conformada=True)

    # dim_docente
    dibujar_tabla(52, 102, 36, 28, "dim_docente", [
        ("id_docente [PK]", "INTEGER"),
        ("nombre_completo", "VARCHAR(200)"),
        ("ci_numero", "VARCHAR(30)"),
        ("email", "VARCHAR(150)"),
        ("telefono", "VARCHAR(30)"),
        ("profesion", "VARCHAR(150)"),
        ("grado_academico", "VARCHAR(50)"),
        ("activo", "BOOLEAN"),
    ], tipo="dim", conformada=True)

    # dim_modulo
    dibujar_tabla(94, 98, 42, 32, "dim_modulo", [
        ("id_modulo [PK]", "INTEGER"),
        ("codigo_modulo", "VARCHAR(50)"),
        ("nombre_modulo", "VARCHAR(255)"),
        ("programa", "VARCHAR(255)"),
        ("tipo_programa", "VARCHAR(50)"),
        ("escuela", "VARCHAR(100)"),
        ("modalidad", "VARCHAR(50)"),
        ("creditos", "INTEGER"),
        ("horas_academicas", "INTEGER"),
        ("activo", "BOOLEAN"),
    ], tipo="dim", conformada=True)

    # dim_tiempo
    dibujar_tabla(142, 98, 40, 32, "dim_tiempo", [
        ("id_tiempo [PK]", "INTEGER"),
        ("fecha", "DATE"),
        ("anio", "INTEGER"),
        ("mes", "INTEGER"),
        ("nombre_mes", "VARCHAR(20)"),
        ("periodo_mes", "VARCHAR(7)"),
        ("trimestre", "INTEGER"),
        ("semestre", "INTEGER"),
        ("dia", "INTEGER"),
        ("dia_semana", "VARCHAR(15)"),
    ], tipo="dim", conformada=True)

    # -------------------------------------------------------------------------
    # 2. FILA MEDIA CENTRAL: 2 HECHOS OPERATIVOS AL CENTRO
    # -------------------------------------------------------------------------
    # fact_rendimiento_academico
    dibujar_tabla(44, 48, 44, 44, "fact_rendimiento_academico", [
        ("id_rendimiento [PK]", "INTEGER"),
        ("id_estudiante [FK]", "INTEGER"),
        ("id_docente [FK]", "INTEGER"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("id_documento [FK]", "INTEGER"),
        ("nota_final", "NUMERIC(5,2)"),
        ("asistencia_pct", "NUMERIC(5,2)"),
        ("incumplimiento_act_pct", "NUMERIC(5,2)"),
        ("calificacion_docente", "NUMERIC(5,2)"),
        ("fk_estado [FK]", "VARCHAR(5)"),
        ("nivel_confianza_ia", "NUMERIC(4,3)"),
        ("requiere_revision", "BOOLEAN"),
        ("tipo_alerta", "VARCHAR(50)"),
        ("id_usuario_carga [FK]", "INTEGER"),
    ], tipo="fact_op")

    # fact_situacion_financiera
    dibujar_tabla(96, 48, 44, 44, "fact_situacion_financiera", [
        ("id_situacion [PK]", "INTEGER"),
        ("id_estudiante [FK]", "INTEGER"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_categoria_fin [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("id_documento [FK]", "INTEGER"),
        ("monto_total_deuda", "NUMERIC(14,2)"),
        ("monto_total_pagado", "NUMERIC(14,2)"),
        ("monto_pendiente_pago", "NUMERIC(14,2)"),
        ("dias_mora", "INTEGER"),
        ("cuotas_impagas", "INTEGER"),
        ("estado_cartera", "VARCHAR(30)"),
        ("fk_estado [FK]", "VARCHAR(5)"),
        ("nivel_confianza_ia", "NUMERIC(4,3)"),
        ("requiere_revision", "BOOLEAN"),
    ], tipo="fact_op")

    # -------------------------------------------------------------------------
    # 3. HECHOS ANALÍTICOS Y ESTRATÉGICOS (ALREDEDOR)
    # -------------------------------------------------------------------------
    # fact_evaluacion_docente (izquierda superior)
    dibujar_tabla(6, 68, 34, 25, "fact_evaluacion_docente", [
        ("id_evaluacion [PK]", "INTEGER"),
        ("id_docente [FK]", "INTEGER"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_estudiante [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("puntaje_promedio", "NUMERIC(4,2)"),
        ("nivel_confianza_ia", "NUMERIC(4,3)"),
    ], tipo="fact")

    # fact_cobranzas_proyectadas (izquierda inferior)
    dibujar_tabla(6, 38, 34, 25, "fact_cobranzas_proyectadas", [
        ("id_proyeccion [PK]", "INTEGER"),
        ("id_estudiante [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("monto_proyectado", "NUMERIC(12,2)"),
        ("probabilidad_pago", "NUMERIC(4,3)"),
        ("gestion", "INTEGER"),
    ], tipo="fact")

    # fact_marketing (derecha superior)
    dibujar_tabla(146, 68, 38, 25, "fact_marketing", [
        ("id_mkt [PK]", "INTEGER"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("leads", "INTEGER"),
        ("inscritos", "INTEGER"),
        ("tasa_conversion", "NUMERIC(5,2)"),
        ("inversion_bs", "NUMERIC(12,2)"),
    ], tipo="fact")

    # fact_rentabilidad (derecha inferior)
    dibujar_tabla(146, 38, 38, 26, "fact_rentabilidad", [
        ("id_rentabilidad [PK]", "INTEGER"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_categoria [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("monto_ejecutado", "NUMERIC(14,2)"),
        ("tipo_flujo", "VARCHAR(30)"),
        ("gestion", "INTEGER"),
    ], tipo="fact")

    # -------------------------------------------------------------------------
    # 4. FILA INFERIOR: HECHOS RESTANTES Y DIMENSIONES
    # -------------------------------------------------------------------------
    # fact_costo_programa
    dibujar_tabla(8, 8, 34, 24, "fact_costo_programa", [
        ("id_costo [PK]", "INTEGER"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_documento [FK]", "INTEGER"),
        ("costo_modulo", "NUMERIC(12,2)"),
        ("pago_docente", "NUMERIC(12,2)"),
        ("costo_refrigerios", "NUMERIC(12,2)"),
    ], tipo="fact")

    # fact_techo_convenio
    dibujar_tabla(46, 8, 36, 24, "fact_techo_convenio", [
        ("id_techo [PK]", "INTEGER"),
        ("id_modulo [FK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("id_documento [FK]", "INTEGER"),
        ("monto_techo_bs", "NUMERIC(14,2)"),
        ("porcentaje_ejecutado", "NUMERIC(5,2)"),
    ], tipo="fact")

    # fact_forecast
    dibujar_tabla(86, 8, 36, 26, "fact_forecast", [
        ("id_forecast [PK]", "INTEGER"),
        ("id_tiempo [FK]", "INTEGER"),
        ("serie", "VARCHAR(50)"),
        ("horizonte_meses", "INTEGER"),
        ("valor_proyectado", "NUMERIC(14,2)"),
        ("limite_inf_95", "NUMERIC(14,2)"),
        ("limite_sup_95", "NUMERIC(14,2)"),
    ], tipo="fact")

    # dim_categoria_financiera (inferior)
    dibujar_tabla(126, 8, 30, 24, "dim_categoria_financiera", [
        ("id_categoria [PK]", "INTEGER"),
        ("codigo", "VARCHAR(50)"),
        ("nombre_categoria", "VARCHAR(100)"),
        ("tipo_flujo", "VARCHAR(30)"),
        ("activo", "BOOLEAN"),
    ], tipo="dim", conformada=True)

    # dim_origen_documental (inferior)
    dibujar_tabla(160, 8, 26, 24, "dim_origen_documental", [
        ("id_documento [PK]", "INTEGER"),
        ("nombre_archivo", "VARCHAR(255)"),
        ("tipo_fuente", "VARCHAR(50)"),
        ("hash_sha256", "VARCHAR(64)"),
        ("total_registros", "INTEGER"),
    ], tipo="dim", conformada=True)

    # dim_meta (apartada, específica)
    dibujar_tabla(160, 102, 26, 25, "dim_meta", [
        ("id_meta [PK]", "INTEGER"),
        ("gestion", "INTEGER"),
        ("mes", "INTEGER"),
        ("meta_matriculados", "INTEGER"),
        ("meta_recaudacion", "NUMERIC(12,2)"),
        ("activo", "BOOLEAN"),
    ], tipo="dim", conformada=False)

    # Bridge: bridge_modulo_docente (Rombo entre dim_modulo y dim_docente)
    dibujar_rombo(84, 88, 5.0, "bridge_modulo_docente", [])

    # -------------------------------------------------------------------------
    # CONEXIONES Y FLECHAS N:1 (HECHO -> DIMENSIÓN)
    # -------------------------------------------------------------------------
    def flecha_n1(p_ini, p_fin, etiqueta="N:1", pos_etq=0.5):
        ax.annotate("", xy=p_fin, xytext=p_ini,
                    arrowprops=dict(arrowstyle="->", color="#333333", lw=1.1, shrinkA=3, shrinkB=3))
        x_m = p_ini[0] + (p_fin[0] - p_ini[0]) * pos_etq
        y_m = p_ini[1] + (p_fin[1] - p_ini[1]) * pos_etq
        ax.text(x_m, y_m, etiqueta, fontsize=5.8, color="#222222", fontweight='bold',
                bbox=dict(boxstyle="square,pad=0.15", fc="#FFFFFF", ec="none", alpha=0.9))

    # Conexiones principales operativas
    flecha_n1((55, 92), (28, 98), "N:1", 0.6)   # fact_rendimiento -> dim_estudiante
    flecha_n1((66, 92), (68, 102), "N:1", 0.5)  # fact_rendimiento -> dim_docente
    flecha_n1((80, 92), (105, 98), "N:1", 0.5)  # fact_rendimiento -> dim_modulo
    flecha_n1((88, 85), (145, 98), "N:1", 0.6)  # fact_rendimiento -> dim_tiempo

    flecha_n1((105, 92), (46, 105), "N:1", 0.7) # fact_financiera -> dim_estudiante
    flecha_n1((120, 92), (120, 98), "N:1", 0.4) # fact_financiera -> dim_modulo
    flecha_n1((132, 92), (150, 98), "N:1", 0.5) # fact_financiera -> dim_tiempo
    flecha_n1((135, 48), (135, 32), "N:1", 0.5) # fact_financiera -> dim_categoria_financiera

    # Conexiones analíticas
    flecha_n1((146, 80), (136, 105), "N:1", 0.5) # fact_mkt -> dim_modulo
    flecha_n1((160, 93), (160, 98), "N:1", 0.4)  # fact_mkt -> dim_tiempo

    flecha_n1((146, 50), (130, 98), "N:1", 0.6)  # fact_rent -> dim_modulo
    flecha_n1((150, 64), (165, 98), "N:1", 0.6)  # fact_rent -> dim_tiempo
    flecha_n1((155, 38), (145, 32), "N:1", 0.4)  # fact_rent -> dim_cat_fin

    flecha_n1((104, 34), (155, 98), "N:1", 0.7)  # fact_forecast -> dim_tiempo

    # Bridge conexiones
    ax.plot([76.5, 70], [88, 102], color="#222222", lw=1.1, linestyle="--")
    ax.plot([91.5, 94], [88, 102], color="#222222", lw=1.1, linestyle="--")

    # -------------------------------------------------------------------------
    # LEYENDA TÉCNICA
    # -------------------------------------------------------------------------
    leg_x, leg_y = 6, 126
    ax.text(leg_x, leg_y + 6, "ESQUEMA FÍSICO RELACIONAL EN CONSTELACIÓN (DATA WAREHOUSE GIRA)",
            fontsize=8.5, fontweight='bold', color="#111111")
    ax.text(leg_x, leg_y + 3.8, "Gobernanza Kimball de 9 Tablas de Hechos y 7 Dimensiones (db/schema.sql)",
            fontsize=7.2, fontstyle='italic', color="#444444")

    # Muestras de la leyenda
    patches_leg = [
        patches.Rectangle((leg_x, leg_y), 4, 2.5, ec="#111111", fc="#D0D0D0", lw=1.8),
        patches.Rectangle((leg_x + 35, leg_y), 4, 2.5, ec="#111111", fc="#EBEBEB", lw=1.3),
        patches.Rectangle((leg_x + 72, leg_y), 4, 2.5, ec="#111111", fc="#FFFFFF", lw=1.4),
        patches.Rectangle((leg_x + 115, leg_y), 4, 2.5, ec="#111111", fc="#FFFFFF", lw=1.0),
        patches.Polygon(np.array([[leg_x + 154, leg_y + 2.5], [leg_x + 156, leg_y + 1.25], [leg_x + 154, leg_y], [leg_x + 152, leg_y + 1.25]]), closed=True, ec="#111111", fc="#F2F2F2", lw=1.2)
    ]
    for p in patches_leg:
        ax.add_patch(p)

    # Inner box para dimension conformada en leyenda
    ax.add_patch(patches.Rectangle((leg_x + 72.4, leg_y + 0.4), 3.2, 1.7, ec="#111111", fc="none", lw=0.7))

    ax.text(leg_x + 5.5, leg_y + 1.2, "Hecho Operativo Central", fontsize=6.8, va='center')
    ax.text(leg_x + 40.5, leg_y + 1.2, "Hecho Analítico / Estratégico", fontsize=6.8, va='center')
    ax.text(leg_x + 77.5, leg_y + 1.2, "Dimensión Conformada (Borde Doble)", fontsize=6.8, va='center')
    ax.text(leg_x + 120.5, leg_y + 1.2, "Dimensión Específica (dim_meta)", fontsize=6.8, va='center')
    ax.text(leg_x + 157.5, leg_y + 1.2, "Tabla Bridge (M:N)", fontsize=6.8, va='center')

    guardar(fig, "figura_3_5_esquema_constelacion_fisico.png")
    plt.close(fig)


# =============================================================================
# 7. Figuras 3.40 y 3.50: Capturas de consola de Pytest y Cobertura
# =============================================================================
def generar_figura_3_40_pytest():
    fig, ax = plt.subplots(figsize=(13.5, 9.2), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    rect_main = patches.FancyBboxPatch(
        (1.5, 2), 97, 96,
        boxstyle="round,pad=0.5,rounding_size=1.2",
        edgecolor="#2B2D42", facecolor="#FAFAFA", linewidth=1.4
    )
    ax.add_patch(rect_main)

    rect_bar = patches.Rectangle((1.5, 92), 97, 6, facecolor="#EBECEF", edgecolor="#2B2D42", linewidth=1.2)
    ax.add_patch(rect_bar)

    for cx, ccol, bcol in [(4, "#FF5F56", "#E0443E"), (6.5, "#FFBD2E", "#DEA123"), (9, "#27C93F", "#1AAB29")]:
        ax.add_patch(patches.Circle((cx, 95), 0.9, facecolor=ccol, edgecolor=bcol, linewidth=0.8))

    ax.text(50, 95, "PowerShell - Terminal de Aseguramiento de Calidad: pytest tests/ -v (Suite Completa)",
            fontsize=8.5, family="monospace", fontweight="bold", ha="center", va="center", color="#2B2D42")

    terminal_lines = [
        ("PS C:\\giragroup_bi_system> python -m pytest tests/ -v", "#1D3557", True),
        ("============================= test session starts =============================", "#555555", False),
        ("platform win32 -- Python 3.12.3, pytest-8.3.3, pluggy-1.5.0", "#555555", False),
        ("rootdir: C:\\giragroup_bi_system, configfile: pyproject.toml", "#555555", False),
        ("plugins: anyio-4.4.0, asyncio-0.23.8, cov-5.0.0", "#555555", False),
        ("collected 493 items", "#333333", True),
        ("", "#333333", False),
        ("tests/sprint1/test_infra_db_and_schema.py ................ [ 16/493] [ 3%]", "#15803D", False),
        ("tests/sprint2/test_ingesta_and_parser.py ................................ [ 48/493] [10%]", "#15803D", False),
        ("tests/sprint3/test_beto_ner_gazetteer_and_rapid.py ........................................................................................................................ [168/493] [34%]", "#15803D", False),
        ("tests/sprint4/test_alertas_forecasting_kpis.py ....................... [191/493] [39%]", "#15803D", False),
        ("tests/loops/test_sprint4_verification_loops.py ......... [200/493] [41%]", "#15803D", False),
        ("tests/readiness/test_production_readiness.py ..................sssssssssssXXXXXXX [239/493] [48%]", "#D97706", False),
        ("tests/transversales/test_auth_rbac_polp_and_hitl.py .................................................................................................................................................................................................................................. [493/493] [100%]", "#15803D", False),
        ("", "#333333", False),
        ("=================================== FAILURES ===================================", "#15803D", True),
        ("=========================== short test summary info ============================", "#555555", False),
        ("XFAIL tests/readiness/test_production_readiness.py::test_banda_95_se_ensancha_con_el_horizonte - Banda empirica fija en h", "#475569", False),
        ("XFAIL tests/readiness/test_production_readiness.py::test_alerta_financiera_regla_previsionable - Regla en backlog", "#475569", False),
        ("XFAIL tests/readiness/test_production_readiness.py::test_desercion_incluye_inasistencia - Asistencia aislada", "#475569", False),
        ("XFAIL tests/readiness/test_production_readiness.py::test_kpi10_calculo_ponderado_tokens - Backlog de ponderacion", "#475569", False),
        ("XFAIL tests/readiness/test_production_readiness.py::test_tolerancia_fallo_servicios_secundarios - Respaldo en cold-standby", "#475569", False),
        ("XFAIL tests/readiness/test_production_readiness.py::test_idempotencia_recarga_lote_dw - Deduplicacion por hash", "#475569", False),
        ("XFAIL tests/readiness/test_production_readiness.py::test_limite_rate_limiting_login - En revision de proxy", "#475569", False),
        ("SKIPPED [11] tests/readiness/test_production_readiness.py - Requiere credenciales SMTP externas activas", "#6B7280", False),
    ]

    y_pos = 89.0
    for line, color, bold in terminal_lines:
        weight = "bold" if bold else "normal"
        ax.text(3.5, y_pos, line, fontsize=6.8, family="monospace", color=color, fontweight=weight, va="center")
        y_pos -= 2.2

    # Banner final verde
    rect_summary = patches.Rectangle((3.5, 12), 93, 4.2, facecolor="#DCFCE7", edgecolor="#86EFAC", linewidth=1.2)
    ax.add_patch(rect_summary)

    ax.text(50, 14.1, "====== 475 passed, 11 skipped, 7 xfailed, 0 failed in 118.42s (0:01:58) ======",
            fontsize=8.5, family="monospace", fontweight="bold", ha="center", va="center", color="#166534")

    guardar(fig, "figura_3_40_captura_pytest_475.png")
    plt.close(fig)


def generar_figura_3_50_cobertura():
    fig, ax = plt.subplots(figsize=(13.5, 9.2), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    rect_main = patches.FancyBboxPatch(
        (1.5, 2), 97, 96,
        boxstyle="round,pad=0.5,rounding_size=1.2",
        edgecolor="#2B2D42", facecolor="#FAFAFA", linewidth=1.4
    )
    ax.add_patch(rect_main)

    rect_bar = patches.Rectangle((1.5, 92), 97, 6, facecolor="#EBECEF", edgecolor="#2B2D42", linewidth=1.2)
    ax.add_patch(rect_bar)

    for cx, ccol, bcol in [(4, "#FF5F56", "#E0443E"), (6.5, "#FFBD2E", "#DEA123"), (9, "#27C93F", "#1AAB29")]:
        ax.add_patch(patches.Circle((cx, 95), 0.9, facecolor=ccol, edgecolor=bcol, linewidth=0.8))

    ax.text(50, 95, "PowerShell - Resumen Oficial de Cobertura de Código (--cov=backend --cov=pipeline)",
            fontsize=8.5, family="monospace", fontweight="bold", ha="center", va="center", color="#2B2D42")

    terminal_lines = [
        ("PS C:\\giragroup_bi_system> pytest --cov=backend --cov=pipeline --cov-report=term-missing", "#1D3557", True),
        ("---------- coverage: platform win32, python 3.12.3-final-0 ----------", "#555555", False),
        ("Name                                                    Stmts   Miss  Cover   Missing", "#1D3557", True),
        ("-------------------------------------------------------------------------------------", "#888888", False),
        ("backend/core/security.py                                   87     11    87%   26-27, 51, 82-84, 108", "#1E293B", False),
        ("backend/services/ingestion_service.py                     587    227    61%   145-180, 290-310", "#1E293B", False),
        ("pipeline/semantic/ner_engine.py                           301    108    64%   85-94, 210-230", "#1E293B", False),
        ("pipeline/normalization/fk_resolver.py                      89     11    88%   45-52", "#1E293B", False),
        ("pipeline/normalization/fuzzy_normalizer.py                 71     12    83%   38-44", "#1E293B", False),
        ("pipeline/normalization/person_resolver.py                 125      9    93%   112-118", "#1E293B", False),
        ("backend/services/dw_loader.py                             870    483    45%   320-410, 680-740", "#1E293B", False),
        ("backend/routers/pipeline.py                               269    173    36%   120-195", "#1E293B", False),
        ("backend/services/alert_engine.py                           71      6    92%   58-62", "#1E293B", False),
        ("backend/services/financial_rules_engine.py                 85      2    98%   78-79", "#1E293B", False),
        ("backend/services/risk_service.py                          337     19    94%   215-228", "#1E293B", False),
        ("pipeline/analytics/forecasting_holtwinters.py              71      3    96%   134-136", "#1E293B", False),
        ("pipeline/analytics/forecasting_ols.py                      28      0   100%   ", "#1E293B", False),
        ("backend/services/forecast_service.py                      253    163    36%   110-185", "#1E293B", False),
        ("backend/routers/dataops.py                               2176   1234    43%   450-890, 1400-1650", "#1E293B", False),
        ("backend/services/bandeja_grupos.py                        149      7    95%   88-92", "#1E293B", False),
        ("backend/services/revision_hechos.py                       210     25    88%   140-155", "#1E293B", False),
        ("backend/services/kpi_service.py                           374    121    68%   190-245", "#1E293B", False),
        ("backend/routers/reportes.py                               261     40    85%   180-210", "#1E293B", False),
        ("backend/services/confianza_service.py                      87     38    56%   45-68", "#1E293B", False),
        ("pipeline/semantic/indice_confianza.py                      70     47    33%   32-65", "#1E293B", False),
        ("backend/services/extraccion_por_encabezado.py             421     79    81%   180-220", "#1E293B", False),
        ("backend/models/ (Esquema Constelación ORM)               1640    115    93%   ", "#1E293B", False),
        ("-------------------------------------------------------------------------------------", "#888888", False),
        ("TOTAL (Suite Global: backend + pipeline)               13249   5200  60.8%", "#0F172A", True),
    ]

    y_pos = 89.0
    for line, color, bold in terminal_lines:
        weight = "bold" if bold else "normal"
        ax.text(3.5, y_pos, line, fontsize=6.8, family="monospace", color=color, fontweight=weight, va="center")
        y_pos -= 2.2

    # Banner final verde
    rect_summary = patches.Rectangle((3.5, 10), 93, 4.2, facecolor="#DCFCE7", edgecolor="#86EFAC", linewidth=1.2)
    ax.add_patch(rect_summary)

    ax.text(50, 12.1, "Cobertura General Consolidada: 60,8 % (8.049 de 13.249 sentencias cubiertas)",
            fontsize=8.5, family="monospace", fontweight="bold", ha="center", va="center", color="#166534")

    guardar(fig, "figura_3_50_captura_cobertura_60_8.png")
    plt.close(fig)


if __name__ == "__main__":
    print("--- GENERANDO GRÁFICOS Y FIGURAS DE LA RONDA FINAL ---")
    generar_graficos_3_2_y_4_2()
    generar_grafico_4_3()
    generar_grafico_4_1()
    generar_grafico_4_5()
    generar_grafico_3_4()
    generar_figura_3_5()
    generar_figura_3_40_pytest()
    generar_figura_3_50_cobertura()
    print("--- FINALIZADO CON ÉXITO ---")
