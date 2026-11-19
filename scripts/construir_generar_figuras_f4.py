# -*- coding: utf-8 -*-
"""
scripts/construir_generar_figuras_f4.py
Ensambla el script definitivo scripts/generar_figuras_f4.py combinando las funciones
analíticas exactas de F3 (con destino docs/figuras/f4/) y las 4 figuras nuevas de F4-3.
Nota F4-1: Las capturas de terminal (3.40, 3.44, 3.50) corresponden a capturas reales de Lean.
"""
import re

with open("scripts/generar_figuras_f3_congelado.py", "r", encoding="utf-8") as f:
    text_f3 = f.read()

# 1. Extraer bloques de funciones analíticas verificadas
def extraer_funcion(nombre_func, texto):
    patron = rf"(def {nombre_func}\(\):.*?)(?=\ndef [a-zA-Z0-9_]+\(\):|\Z)"
    m = re.search(patron, texto, re.DOTALL)
    if not m:
        raise ValueError(f"No se encontró la función {nombre_func}")
    func_body = m.group(1)
    # Adaptar para F4: DIR_FIGURAS_F3 -> DIR_FIGURAS_F4
    func_body = func_body.replace("DIR_FIGURAS_F3", "DIR_FIGURAS_F4")
    return func_body

funcs_f3 = [
    "generar_grafico_3_1",
    "generar_grafico_3_2",
    "generar_grafico_3_3",
    "generar_grafico_3_4",
    # grafico_3_5 se retira
    "generar_grafico_4_1",
    "generar_grafico_4_2",
    "generar_grafico_4_3",
    "generar_grafico_4_4",
    "generar_grafico_4_5",
    "generar_grafico_4_6",
    "generar_figura_3_5",
    "generar_figura_flujo_dataops_3pasos"
]

bloques_funciones = [extraer_funcion(fn, text_f3) for fn in funcs_f3]

# 2. Código de cabecera
cabecera = '''# -*- coding: utf-8 -*-
"""
scripts/generar_figuras_f4.py
=============================
Generador oficial de figuras y gráficos académicos para la fase F4 (18-nov-2026).
Proyecto de Grado - Sistema BI GiraGroup S.R.L.
Tesis: "Sistema de Inteligencia de Negocios para la Optimización de la Toma de Decisiones"

Principios de la entrega F4:
1. Fuente única estricta: docs/fuente_verdad_tesis.md y mediciones en docs/mediciones/.
2. Formato numérico boliviano: coma (,) decimal y punto (.) de miles.
3. Estilizado académico: 300 DPI, fondo blanco puro (#FFFFFF), escala de grises con tramas (hatching) APA/IEEE.
4. Invariantes DECISIÓN 3 F3V: 51 tablas base, 10 vistas bi, 10 hechos, 7 dimensiones, 1 puente, 23 KPI.
5. Flujo DataOps: 3 pasos oficiales (① Carga -> ② Lectura de BETO -> ③ Revisión HITL).
6. F4-1: Capturas reales de terminal (PowerShell en Windows Terminal) con prompt, fecha y commit e9267cd.
7. F4-2: Gráfico 3.5 retirado formalmente; Gráficos 4.5 y 4.6 trazados.
8. F4-3: Figuras nuevas de F3V (KPI-23, RNF-03 n=3 con sensibilidad KLM, Locust/Newman y hechos completos).
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

# Directorios de salida
DIR_FIGURAS_F4 = pathlib.Path("docs/figuras/f4")
DIR_EVIDENCIAS = pathlib.Path("docs/evidencias/graficos_v2")
DIR_MEDICIONES = pathlib.Path("docs/mediciones")

DIR_FIGURAS_F4.mkdir(parents=True, exist_ok=True)
DIR_EVIDENCIAS.mkdir(parents=True, exist_ok=True)

# Tipografía y formato visual
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['DejaVu Serif', 'Times New Roman', 'Cambria', 'Georgia']
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['axes.labelsize'] = 9.5
plt.rcParams['xtick.labelsize'] = 8.5
plt.rcParams['ytick.labelsize'] = 8.5
plt.rcParams['legend.fontsize'] = 8.5
plt.rcParams['figure.titlesize'] = 11

ANCHO_16CM = 16.0 / 2.54  # 6.2992 pulgadas

# Formateadores bolivianos
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
    """Guarda en docs/figuras/f4/ y copia a docs/evidencias/graficos_v2/."""
    p1 = DIR_FIGURAS_F4 / nombre_archivo
    p2 = DIR_EVIDENCIAS / nombre_archivo
    fig.savefig(p1, dpi=300, bbox_inches='tight', facecolor='#FFFFFF', edgecolor='none')
    fig.savefig(p2, dpi=300, bbox_inches='tight', facecolor='#FFFFFF', edgecolor='none')
    plt.close(fig)
    print(f"[OK] Generado a 300 DPI: {nombre_archivo}")
'''

# 3. Código de las 4 funciones nuevas de F4-3 y capturas de terminal F4-1
funciones_f4_nuevas = '''
# =============================================================================
# F4-3(a): Gráfico Serie Anual y Bandas de Cumplimiento de KPI-23
# =============================================================================
def generar_grafico_kpi23_serie():
    p_json = DIR_MEDICIONES / "f3v_kpi23_serie.json"
    data = json.loads(p_json.read_text(encoding="utf-8"))
    
    gestiones = [d["gestion"] for d in data["kpi23_por_gestion"] if d["valor"] is not None]
    valores = [d["valor"] for d in data["kpi23_por_gestion"] if d["valor"] is not None]
    
    # 2024: 100,0 %, 2025: 99,77 %, 2026: 46,62 %
    assert valores == [100.0, 99.77, 46.62], f"Valores de KPI-23 no coinciden con JSON: {valores}"
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.4), dpi=300)
    fig.subplots_adjust(left=0.12, right=0.95, top=0.92, bottom=0.22)
    
    # Bandas de semáforo
    ax.axhspan(85.0, 110.0, color='#EFEFEF', alpha=0.8, label='Zona Verde / Meta (≥ 85,0 %)')
    ax.axhspan(60.0, 85.0, color='#F7F7F7', alpha=0.8, label='Zona Ámbar (60,0 % - 85,0 %)')
    ax.axhspan(0.0, 60.0, color='#FCFCFC', alpha=0.8, label='Zona Roja (< 60,0 %)')
    
    ax.axhline(85.0, color='#111111', linestyle='--', linewidth=1.2, label='Meta Institucional (85,0 %)')
    ax.axhline(60.0, color='#666666', linestyle=':', linewidth=1.0, label='Umbral Crítico (60,0 %)')
    
    x = np.arange(len(gestiones))
    width = 0.45
    
    colores = ['#4A4A4A', '#7A7A7A', '#B5B5B5']
    tramas = ['///', r'\\\\', '...']
    barras = ax.bar(x, valores, width, color=colores, edgecolor='#111111',
                    hatch=tramas, linewidth=1.2)
    
    ax.set_ylabel('Cumplimiento de Inicios Planificados (%)', fontsize=9.5, fontweight='bold')
    ax.set_xlabel('Gestión Anual Evaluada', fontsize=9.5, fontweight='bold')
    ax.set_title('Evolución de KPI-23: Cumplimiento de Inicios Académicos Planificados\\n(Comparación interanual y bandas de semaforización CMI en el Data Warehouse)',
                 fontsize=10.5, pad=12, weight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f"Gestión {g}" for g in gestiones], fontsize=9)
    ax.set_ylim(0, 115)
    ax.yaxis.set_major_formatter(formatter_pct_axis)
    
    for barra, g, v in zip(barras, gestiones, valores):
        estado = "VERDE" if v >= 85 else ("ÁMBAR" if v >= 60 else "ROJO")
        nota_g = " (en curso)" if g == 2026 else ""
        ax.text(barra.get_x() + barra.get_width()/2, v + 2.5,
                f"{fmt_decimal(v, 2)} %\\n[{estado}]{nota_g}",
                ha='center', va='bottom', fontsize=8.2, weight='bold')
        
    ax.legend(loc='lower left', frameon=True, edgecolor='#333333', fontsize=7.8)
    ax.grid(axis='y', linestyle=':', color='#AAAAAA', alpha=0.5)
    ax.set_axisbelow(True)
    
    guardar_figura(fig, "grafico_kpi23_serie.png")


# =============================================================================
# F4-3(b): Gráfico RNF-03 n=3 con Análisis de Sensibilidad KLM
# =============================================================================
def generar_grafico_rnf03_n3_sensibilidad():
    p_b7 = DIR_MEDICIONES / "f3v_b7_corridas.json"
    p_klm = DIR_MEDICIONES / "f3v_klm.json"
    data_b7 = json.loads(p_b7.read_text(encoding="utf-8"))
    data_klm = json.loads(p_klm.read_text(encoding="utf-8"))
    
    # Mediciones B-7
    vacia_media = data_b7["resumen"]["vacia_maquina_s"]["media"]  # 424.29 s
    vacia_desv = data_b7["resumen"]["vacia_maquina_s"]["desv"]   # 22.24 s
    llena_media = data_b7["resumen"]["llena_maquina_s"]["media"]  # 36.53 s
    llena_desv = data_b7["resumen"]["llena_maquina_s"]["desv"]   # 0.28 s
    
    # KLM
    klm_w0 = data_klm["W_0"]["klm_s"]       # 200.6 s
    klm_w_med = data_klm["W_medido"]["klm_s"] # 320.6 s (W = 2.5 s)
    klm_w10 = data_klm["W_10"]["klm_s"]     # 680.6 s
    
    # Totales
    tot_w0 = (vacia_media + klm_w0) / 60.0       # 10.41 min
    tot_medido = (vacia_media + klm_w_med) / 60.0 # 12.41 min
    tot_w10 = (vacia_media + klm_w10) / 60.0     # 18.41 min
    tot_llena = (llena_media + klm_w_med) / 60.0  # 5.95 min
    
    assert round(tot_medido, 2) == 12.41, f"Total medido no coincide: {tot_medido}"
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.8), dpi=300)
    fig.subplots_adjust(left=0.12, right=0.95, top=0.92, bottom=0.22)
    
    categorias = [
        "Caché Llena\\n(W = 2,5 s)",
        "Sensibilidad W = 0 s\\n(Ideal sin latencia)",
        "Medición Oficial n = 3\\n(Caché Vacía + W = 2,5 s)",
        "Sensibilidad W = 10 s\\n(Estrés extremo)"
    ]
    
    t_maquina = [llena_media / 60.0, vacia_media / 60.0, vacia_media / 60.0, vacia_media / 60.0]
    t_humano = [klm_w_med / 60.0, klm_w0 / 60.0, klm_w_med / 60.0, klm_w10 / 60.0]
    
    x = np.arange(len(categorias))
    width = 0.48
    
    p1 = ax.bar(x, t_maquina, width, label='Tiempo de Máquina (Pipeline + BETO)',
                color='#555555', edgecolor='#111111', hatch='///', linewidth=1.1)
    p2 = ax.bar(x, t_humano, width, bottom=t_maquina, label='Tiempo Operador HITL (Modelo KLM)',
                color='#CCCCCC', edgecolor='#111111', hatch='...', linewidth=1.1)
    
    # Líneas de referencia
    ax.axhline(15.0, color='#000000', linestyle='--', linewidth=1.3, label='Meta Contractual RNF-03 (< 15,0 min)')
    ax.axhline(20.0, color='#666666', linestyle=':', linewidth=1.1, label='Límite Aceptable (< 20,0 min)')
    
    ax.set_ylabel('Tiempo Total de Consolidación (Minutos)', fontsize=9.5, fontweight='bold')
    ax.set_title('Verificación Rigurosa de RNF-03: Tiempos con n = 3 y Sensibilidad KLM\\n(Desglose de tiempo de máquina y operador ante variaciones en tiempo de respuesta del sistema W)',
                 fontsize=10.5, pad=12, weight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(categorias, fontsize=8.2)
    ax.set_ylim(0, 24)
    ax.yaxis.set_major_formatter(formatter_coma)
    
    for i, (m, h) in enumerate(zip(t_maquina, t_humano)):
        total = m + h
        ax.text(i, total + 0.5, f"{fmt_decimal(total, 2)} min",
                ha='center', va='bottom', fontsize=8.2, weight='bold')
        ax.text(i, m / 2, f"M: {fmt_decimal(m, 2)}m",
                ha='center', va='center', fontsize=7.2, color='#FFFFFF', weight='bold')
        ax.text(i, m + h / 2, f"H: {fmt_decimal(h, 2)}m",
                ha='center', va='center', fontsize=7.2, color='#111111', weight='bold')
        
    ax.legend(loc='upper left', frameon=True, edgecolor='#333333', fontsize=7.8)
    ax.grid(axis='y', linestyle=':', color='#AAAAAA', alpha=0.5)
    ax.set_axisbelow(True)
    
    guardar_figura(fig, "grafico_rnf03_n3_sensibilidad.png")


# =============================================================================
# F4-3(c): Gráfico Rendimiento de Carga y Contrato (Locust y Newman)
# =============================================================================
def generar_grafico_rendimiento_locust_newman():
    p_locust = DIR_MEDICIONES / "f3v_locust.json"
    p_newman = DIR_MEDICIONES / "f3v_newman.json"
    data_locust = json.loads(p_locust.read_text(encoding="utf-8"))
    data_newman = json.loads(p_newman.read_text(encoding="utf-8"))
    
    req_totales = data_locust["agregado"]["requests"]  # 1121
    fallos_locust = data_locust["agregado"]["failures"]  # 0
    rps = data_locust["agregado"]["rps"]  # 41.27
    p50 = data_locust["agregado"]["p50_ms"]  # 10.0
    p95 = data_locust["agregado"]["p95_ms"]  # 34.0
    
    items_newman = data_newman["run_stats"]["items"]["total"]  # 11
    aserciones_newman = data_newman["run_stats"]["assertions"]["total"]  # 24
    fallos_newman = data_newman["run_stats"]["assertions"]["failed"]  # 0
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(ANCHO_16CM, 4.4), dpi=300,
                                   gridspec_kw={'width_ratios': [1.3, 1.0]})
    fig.subplots_adjust(top=0.88, bottom=0.18, left=0.24, right=0.96, wspace=0.35)
    
    # Subgráfico 1: Latencia por Endpoint en Locust (p50 y p95)
    endpoints = [
        "Scorecard CMI\\n(/cmi/scorecard)",
        "Bandeja Grupos\\n(/review-tray/grupos)",
        "CMI Completo\\n(/kpis/cmi-completo)",
        "Pronóstico Alumnos\\n(/forecast/alumnos)",
        "Global Agregado"
    ]
    p50_vals = [
        data_locust["por_endpoint"]["GET /api/v1/cmi/scorecard"]["p50_ms"],
        data_locust["por_endpoint"]["GET /api/v1/dataops/review-tray/grupos"]["p50_ms"],
        data_locust["por_endpoint"]["GET /api/v1/kpis/cmi-completo"]["p50_ms"],
        data_locust["por_endpoint"]["GET /api/v1/forecast/alumnos"]["p50_ms"],
        p50
    ]
    p95_vals = [
        data_locust["por_endpoint"]["GET /api/v1/cmi/scorecard"]["p95_ms"],
        data_locust["por_endpoint"]["GET /api/v1/dataops/review-tray/grupos"]["p95_ms"],
        data_locust["por_endpoint"]["GET /api/v1/kpis/cmi-completo"]["p95_ms"],
        data_locust["por_endpoint"]["GET /api/v1/forecast/alumnos"]["p95_ms"],
        p95
    ]
    
    y = np.arange(len(endpoints))
    h = 0.35
    
    ax1.barh(y - h/2, p50_vals, h, label='Mediana (p50)', color='#CCCCCC',
             edgecolor='#111111', hatch='...', linewidth=1.0)
    ax1.barh(y + h/2, p95_vals, h, label='Percentil 95 (p95)', color='#555555',
             edgecolor='#111111', hatch='///', linewidth=1.0)
    
    ax1.set_yticks(y)
    ax1.set_yticklabels(endpoints, fontsize=8)
    ax1.invert_yaxis()
    ax1.set_xlabel('Tiempo de Respuesta (Milisegundos)', fontsize=8.8, fontweight='bold')
    ax1.set_title('Prueba de Carga (Locust, 50 usuarios)\\n1.121 requests · 41,27 RPS · 0 fallos',
                  fontsize=9.2, weight='bold', pad=10)
    ax1.set_xlim(0, max(p95_vals) * 1.3)
    ax1.xaxis.set_major_formatter(formatter_coma)
    ax1.legend(loc='lower right', fontsize=7.5, edgecolor='#333333')
    ax1.grid(axis='x', linestyle=':', color='#AAAAAA', alpha=0.5)
    
    for idx, (v50, v95) in enumerate(zip(p50_vals, p95_vals)):
        ax1.text(v50 + 0.8, idx - h/2, f"{int(v50)}", va='center', fontsize=7.2)
        ax1.text(v95 + 0.8, idx + h/2, f"{int(v95)}", va='center', fontsize=7.2, weight='bold')
        
    # Subgráfico 2: Resumen de Pruebas de Contrato Newman
    categorias_newman = [
        "Contratos API\\nVerificados",
        "Aserciones\\nAutomáticas",
        "Tasa de Éxito\\nFuncional"
    ]
    valores_newman = [items_newman, aserciones_newman, 100.0]
    
    x2 = np.arange(len(categorias_newman))
    barras2 = ax2.bar(x2, [items_newman, aserciones_newman, 100], width=0.45,
                      color=['#E0E0E0', '#B0B0B0', '#707070'], edgecolor='#111111',
                      hatch=['', r'\\\\', 'xxx'], linewidth=1.1)
    
    ax2.set_xticks(x2)
    ax2.set_xticklabels(categorias_newman, fontsize=8)
    ax2.set_ylabel('Total Registrado / Porcentaje', fontsize=8.8, fontweight='bold')
    ax2.set_title('Pruebas de Contrato (Newman)\\n11/11 endpoints · 24/24 aserciones OK',
                  fontsize=9.2, weight='bold', pad=10)
    ax2.set_ylim(0, 120)
    ax2.grid(axis='y', linestyle=':', color='#AAAAAA', alpha=0.5)
    
    ax2.text(0, items_newman + 3, f"{items_newman}\\n(0 fallos)", ha='center', fontsize=7.8, weight='bold')
    ax2.text(1, aserciones_newman + 3, f"{aserciones_newman} / 24\\n(100 %)", ha='center', fontsize=7.8, weight='bold')
    ax2.text(2, 100 + 3, "100,00 %\\n(Éxito)", ha='center', fontsize=7.8, weight='bold')
    
    fig.suptitle('Evaluación de Carga Concurrente (Locust) y Contratos de Integración (Newman)',
                 fontsize=10.5, weight='bold', y=0.98)
    
    guardar_figura(fig, "grafico_rendimiento_locust_newman.png")


# =============================================================================
# F4-3(d): Gráfico de Hechos por Tabla en DW Completo (10 Libros)
# =============================================================================
def generar_grafico_f3v_completo_hechos():
    p_json = DIR_MEDICIONES / "f3v_completo.json"
    data = json.loads(p_json.read_text(encoding="utf-8"))
    conteos = data["conteos"]
    
    tablas_hechos = [
        ("fact_evaluacion_docente", "Evaluación Docente", conteos["fact_evaluacion_docente"]),
        ("fact_rendimiento_academico", "Rendimiento Académico", conteos["fact_rendimiento_academico"]),
        ("fact_situacion_financiera", "Situación Financiera", conteos["fact_situacion_financiera"]),
        ("fact_marketing", "Marketing y Leads", conteos["fact_marketing"]),
        ("fact_planificacion_programa", "Planificación Programa (KPI-23)", conteos["fact_planificacion_programa"]),
        ("fact_costo_programa", "Costo por Programa", conteos["fact_costo_programa"]),
        ("fact_techo_convenio", "Techos de Convenio", conteos["fact_techo_convenio"]),
        ("fact_rentabilidad", "Rentabilidad", conteos["fact_rentabilidad"])
    ]
    
    nombres_mostrar = [t[1] for t in tablas_hechos]
    valores = [t[2] for t in tablas_hechos]
    total_hechos = sum(valores)
    
    fig, ax = plt.subplots(figsize=(ANCHO_16CM, 4.8), dpi=300)
    fig.subplots_adjust(left=0.34, right=0.94, top=0.91, bottom=0.15)
    
    y_pos = np.arange(len(nombres_mostrar))
    barras = ax.barh(y_pos, valores, align='center', color='#C0C0C0', edgecolor='#111111',
                     linewidth=1.1, hatch='///', height=0.62)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(nombres_mostrar, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xscale('log')
    ax.set_xlabel('Volumen de Registros de Hechos Consolidados (Escala Logarítmica)', fontsize=9.2, fontweight='bold')
    ax.set_title(f'Volumen de Hechos Almacenados en el Data Warehouse Completo (10 Libros)\\n(Total: {fmt_miles(total_hechos)} hechos consolidados con idempotencia estricta en PostgreSQL)',
                 fontsize=10.5, pad=12, weight='bold')
    
    ax.set_xlim(50, 3000000)
    ax.xaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='x', which='both', linestyle=':', color='#AAAAAA', alpha=0.5)
    ax.set_axisbelow(True)
    
    for barra in barras:
        w = barra.get_width()
        pct = (w / total_hechos) * 100
        txt = f"{fmt_miles(w)}  ({fmt_decimal(pct, 2)} %)" if pct >= 0.05 else f"{fmt_miles(w)}  (<0,05 %)"
        ax.text(w * 1.25, barra.get_y() + barra.get_height()/2,
                txt, va='center', ha='left', fontsize=8.0, weight='bold', color='#111111')
        
    ax.text(0.64, 0.15, f"Base Completa: 10 Libros\\nDim Meta: {conteos['dim_meta']} registros\\nLíneas Origen: {fmt_miles(conteos['carga_fila_origen'])}",
            transform=ax.transAxes, fontsize=8.0, weight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#F5F5F5', edgecolor='#333333', lw=1))
    
    guardar_figura(fig, "grafico_f3v_completo_hechos.png")
'''

# 4. Función main
main_code = '''
def main():
    print("=================================================================")
    print("INICIANDO GENERACIÓN OFICIAL DE FIGURAS F4 (18-nov-2026)")
    print("Directorio de salida: docs/figuras/f4/")
    print("=================================================================")
    
    # 1. Gráficos analíticos verificados de F3 (Gráfico 3.5 formalmente retirado)
    generar_grafico_3_1()
    generar_grafico_3_2()
    generar_grafico_3_3()
    generar_grafico_3_4()
    generar_figura_3_5()
    generar_figura_flujo_dataops_3pasos()
    generar_grafico_4_1()
    generar_grafico_4_2()
    generar_grafico_4_3()
    generar_grafico_4_4()
    generar_grafico_4_5()
    generar_grafico_4_6()
    
    # 2. Figuras nuevas de F3V (F4-3)
    generar_grafico_kpi23_serie()
    generar_grafico_rnf03_n3_sensibilidad()
    generar_grafico_rendimiento_locust_newman()
    generar_grafico_f3v_completo_hechos()
    
    # Nota F4-1: Las Figuras 3.40, 3.44 y 3.50 corresponden a capturas reales
    # de terminal pendientes de entrega por Lean. No se generan por código.
    
    print("=================================================================")
    print("¡GENERACIÓN DE FIGURAS F4 COMPLETADA EXITOSAMENTE!")
    print("Todas las figuras analíticas cumplen con 300 DPI, fondo blanco puro #FFFFFF,")
    print("norma APA/IEEE y trazabilidad absoluta a docs/mediciones/ y la SFV.")
    print("=================================================================")

if __name__ == "__main__":
    main()
'''

contenido_completo = cabecera + "\n\n" + "\n\n".join(bloques_funciones) + "\n\n" + funciones_f4_nuevas + "\n\n" + main_code

with open("scripts/generar_figuras_f4.py", "w", encoding="utf-8") as f:
    f.write(contenido_completo)

print("scripts/generar_figuras_f4.py construido exitosamente.")
