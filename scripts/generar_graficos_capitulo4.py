# -*- coding: utf-8 -*-
"""
Script de Generación de Gráficos Académicos para el Capítulo IV: Presentación y Análisis de Resultados
Proyecto de Grado: Sistema de Inteligencia de Negocios para GiraGroup S.R.L.
Estándares: 300 DPI, Escala de Grises Pura con Hatching, Fondo Blanco Puro (#FFFFFF),
            Ancho 16 cm, Sin Título Interno, Coma Decimal con FuncFormatter.
"""

import os
import json
import csv
import pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# Configuración global de Matplotlib
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 9.5
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['axes.labelsize'] = 9.5
plt.rcParams['xtick.labelsize'] = 8.5
plt.rcParams['ytick.labelsize'] = 8.5
plt.rcParams['legend.fontsize'] = 8.5
plt.rcParams['figure.titlesize'] = 11

OUTPUT_DIR = pathlib.Path("docs/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = pathlib.Path(r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0")

def formato_coma(x, pos):
    """Formateador de coma decimal para ejes."""
    if abs(x - int(x)) < 1e-5:
        return f"{int(x):,}".replace(',', '.')
    return f"{x:.1f}".replace('.', ',')

def formato_coma_2dec(x, pos):
    """Formateador con 2 decimales y coma."""
    return f"{x:.2f}".replace('.', ',')

formatter_coma = ticker.FuncFormatter(formato_coma)
formatter_coma_2dec = ticker.FuncFormatter(formato_coma_2dec)


def guardar_grafico(fig, nombre_archivo):
    """Guarda en docs/images y en el directorio de artefactos a 300 DPI."""
    p1 = OUTPUT_DIR / nombre_archivo
    p2 = ARTIFACT_DIR / nombre_archivo
    fig.savefig(p1, dpi=300, bbox_inches='tight', facecolor='#FFFFFF', edgecolor='none')
    fig.savefig(p2, dpi=300, bbox_inches='tight', facecolor='#FFFFFF', edgecolor='none')
    plt.close(fig)
    print(f"[OK] Generado: {nombre_archivo}")


def generar_grafico_4_1():
    """Gráfico 4.1: Distribución de inconsistencias detectadas en la medición retroactiva del corpus pretest (Total = 341)."""
    fig, ax = plt.subplots(figsize=(6.3, 3.2))
    
    categorias = [
        "Calificaciones fuera de escala",
        "Discordancia CI - Nombre",
        "Celdas desplazadas / Asimetría",
        "Homonimia / Duplicidad nominal",
        "CI ausente o sintético"
    ]
    valores = [30, 33, 58, 75, 145]  # Suma exacta: 341
    porcentajes = [v / 341 * 100 for v in valores]
    
    y_pos = np.arange(len(categorias))
    
    # Barra en escala de grises con borde oscuro y trama
    bars = ax.barh(y_pos, valores, color='#E0E0E0', edgecolor='#222222', height=0.6, hatch='///', linewidth=1.1)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categorias)
    ax.set_xlabel("Cantidad de registros observados (n = 341)")
    ax.set_xlim(0, 165)
    ax.xaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='x', linestyle='--', alpha=0.5, color='#888888')
    
    # Etiquetas al extremo de las barras con valor y porcentaje
    for bar, val, pct in zip(bars, valores, porcentajes):
        ax.text(val + 2, bar.get_y() + bar.get_height()/2, 
                f"{val} ({pct:.1f} %)".replace('.', ','), 
                va='center', ha='left', fontsize=8.5, color='#111111', weight='medium')
        
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#333333')
    ax.spines['bottom'].set_color('#333333')
    
    guardar_grafico(fig, "grafico_4_1_inconsistencias_corpus.png")


def generar_grafico_4_2():
    """Gráfico 4.2: Distribución porcentual del lote de ingesta según umbrales de confianza probabilística."""
    # Leer datos reales de confianza.csv
    csv_path = pathlib.Path("confianza.csv")
    datos = []
    if csv_path.exists():
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # encabezado
            for row in reader:
                if row:
                    datos.append((row[0], int(row[1]), float(row[2])))
    else:
        datos = [
            ("Consolidado directo (≥ 0,85)", 1046, 75.4),
            ("Revisión humana HITL (0,60 – 0,84)", 200, 14.4),
            ("Retenido en Staging (< 0,60)", 141, 10.2)
        ]
        
    fig, ax = plt.subplots(figsize=(6.3, 3.0))
    
    labels = [d[0] for d in datos]
    conteos = [d[1] for d in datos]
    porcentajes = [d[2] for d in datos]
    
    y_pos = np.arange(len(labels))
    colores = ['#444444', '#888888', '#CCCCCC']
    tramas = ['///', '\\\\\\', '...']
    
    bars = ax.barh(y_pos, porcentajes, color=colores, edgecolor='#111111', height=0.55, linewidth=1.1)
    for bar, trama in zip(bars, tramas):
        bar.set_hatch(trama)
        
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Porcentaje sobre el total del lote procesable (%)")
    ax.set_xlim(0, 90)
    ax.xaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='x', linestyle='--', alpha=0.5, color='#888888')
    
    for bar, cnt, pct in zip(bars, conteos, porcentajes):
        ax.text(pct + 1.5, bar.get_y() + bar.get_height()/2, 
                f"{pct:.1f} %  (n = {cnt:,})".replace('.', ',').replace(',', '.', 1), 
                va='center', ha='left', fontsize=8.5, color='#111111', weight='medium')
        
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.invert_yaxis()  # El consolidado arriba
    
    guardar_grafico(fig, "grafico_4_2_confianza_probabilistica.png")


def generar_grafico_4_3():
    """Gráfico 4.3: Tasa de resolución y unificación de registros según formato documental de origen."""
    fig, ax = plt.subplots(figsize=(6.3, 3.4))
    
    formatos = [
        "Hojas de cálculo Excel (.xlsx)",
        "Planillas Google Sheets",
        "Formularios Web / CSV (.csv)",
        "Reportes Plataforma / Moodle"
    ]
    
    # Tasas porcentuales: Consolidado directo vs Asistido/Aislado (HITL + Staging)
    pct_consolidado = [77.8, 73.5, 82.1, 68.4]
    pct_revision = [22.2, 26.5, 17.9, 31.6]
    
    y_pos = np.arange(len(formatos))
    height = 0.52
    
    # Barras apiladas al 100%
    b1 = ax.barh(y_pos, pct_consolidado, height=height, color='#555555', edgecolor='#111111', 
                 hatch='///', label='Consolidación automática directa (≥ 0,85)')
    b2 = ax.barh(y_pos, pct_revision, left=pct_consolidado, height=height, color='#E0E0E0', 
                 edgecolor='#111111', hatch='...', label='Derivado a HITL / Staging (< 0,85)')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(formatos)
    ax.set_xlabel("Distribución de registros por formato (%)")
    ax.set_xlim(0, 105)
    ax.xaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='x', linestyle='--', alpha=0.5, color='#888888')
    
    # Anotaciones dentro de las barras
    for i, (p_c, p_r) in enumerate(zip(pct_consolidado, pct_revision)):
        ax.text(p_c / 2, i, f"{p_c:.1f} %".replace('.', ','), 
                va='center', ha='center', color='#FFFFFF', fontsize=8, weight='bold')
        ax.text(p_c + p_r / 2, i, f"{p_r:.1f} %".replace('.', ','), 
                va='center', ha='center', color='#111111', fontsize=8, weight='bold')
        
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=1, frameon=False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.invert_yaxis()
    
    guardar_grafico(fig, "grafico_4_3_resolucion_por_formato.png")


def generar_grafico_4_4():
    """Gráfico 4.4: Disponibilidad de KPI por perspectiva estratégica de Kaplan y Norton (Pretest vs Postest)."""
    fig, ax = plt.subplots(figsize=(6.3, 3.2))
    
    perspectivas = [
        "Perspectiva Financiera",
        "Perspectiva de Clientes",
        "Procesos Internos",
        "Aprendizaje y Crecimiento"
    ]
    
    pretest = [0, 0, 0, 0]
    postest = [2, 2, 3, 2]  # Total = 9 KPI
    
    x = np.arange(len(perspectivas))
    width = 0.35
    
    rects1 = ax.bar(x - width/2, pretest, width, label='Pretest (Sistemas dispersos)', 
                    color='#E8E8E8', edgecolor='#222222', hatch='..')
    rects2 = ax.bar(x + width/2, postest, width, label='Postest (CMI Centralizado)', 
                    color='#444444', edgecolor='#111111', hatch='///')
    
    ax.set_ylabel("Cantidad de KPI operativos disponibles")
    ax.set_xticks(x)
    ax.set_xticklabels(perspectivas)
    ax.set_ylim(0, 4)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.yaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='y', linestyle='--', alpha=0.5, color='#888888')
    
    # Anotar valores sobre las barras
    for r in rects1:
        ax.text(r.get_x() + r.get_width()/2, 0.1, "0", ha='center', va='bottom', fontsize=8.5, color='#333333')
    for r, v in zip(rects2, postest):
        ax.text(r.get_x() + r.get_width()/2, v + 0.1, f"{v}", ha='center', va='bottom', fontsize=8.5, weight='bold')
        
    ax.legend(loc='upper right', frameon=False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    guardar_grafico(fig, "grafico_4_4_disponibilidad_kpi_cmi.png")


def generar_grafico_4_5():
    """Gráfico 4.5: Impacto en el tiempo de consolidación de reportes de gestión (Pretest vs Postest) en escala semilogarítmica."""
    fig, ax = plt.subplots(figsize=(6.3, 3.2))
    
    escenarios = [
        "Pretest: Consolidación manual\n(Rango 8 a 12 horas)", 
        "Postest: Pipeline automatizado\n(Ejecución batch ETL + NER)"
    ]
    
    # Pretest punto medio: 600 min con rango [480, 720]
    # Postest media: 4.5 min con DE: 0.1 min
    valores = [600.0, 4.5]
    yerr = [[120.0, 0.1], [120.0, 0.1]]  # Pretest -120/+120 min, Postest ±0.1 min
    
    x = np.arange(len(escenarios))
    
    bars = ax.bar(x, valores, width=0.45, color=['#CCCCCC', '#444444'], edgecolor='#111111', 
                  hatch=['...', '///'], linewidth=1.1,
                  yerr=yerr, capsize=6, error_kw={'ecolor': '#111111', 'elinewidth': 1.2})
    
    ax.set_yscale('log')
    ax.set_ylabel("Tiempo de consolidación (minutos, escala logarítmica)")
    ax.set_xticks(x)
    ax.set_xticklabels(escenarios)
    ax.set_ylim(1, 1500)
    
    # Formato de eje logarítmico legible
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{int(y):,}".replace(',', '.')))
    ax.grid(axis='y', linestyle='--', alpha=0.5, color='#888888', which='both')
    
    # Textos explicativos en las barras
    ax.text(0, 680, "600,0 min\n(10,0 h)", ha='center', va='bottom', fontsize=8.5, weight='bold')
    ax.text(1, 5.2, "4,5 min\n(± 0,1 min)", ha='center', va='bottom', fontsize=8.5, weight='bold')
    
    # Flecha y etiqueta de reducción del -99,25 %
    ax.annotate(
        "Reducción del 99,25 %\n(Δ = −595,5 min)",
        xy=(1, 12), xytext=(0.55, 60),
        arrowprops=dict(facecolor='#111111', shrink=0.08, width=1.2, headwidth=6),
        ha='center', va='center', fontsize=8.5, weight='bold',
        bbox=dict(boxstyle="round,pad=0.3", fc="#FFFFFF", ec="#222222", lw=1)
    )
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    guardar_grafico(fig, "grafico_4_5_tiempo_consolidacion_semilog.png")


def generar_grafico_4_6():
    """Gráfico 4.6: Evaluación comparativa de usabilidad por dimensión Likert (Pretest vs Postest, N = 10)."""
    fig, ax = plt.subplots(figsize=(6.3, 4.4))
    
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
    
    medias_pre = [1.80, 1.90, 1.70, 2.10, 1.60, 1.40, 2.30, 2.40, 2.00]
    desv_pre =   [0.63, 0.57, 0.48, 0.74, 0.52, 0.52, 0.67, 0.70, 0.67]
    
    medias_post = [4.60, 4.50, 4.70, 4.80, 4.40, 4.50, 4.60, 4.30, 4.70]
    desv_post =   [0.52, 0.53, 0.48, 0.42, 0.52, 0.53, 0.52, 0.67, 0.48]
    
    y = np.arange(len(items))
    height = 0.36
    
    b1 = ax.barh(y - height/2, medias_pre, height, label='Pretest (Línea base)', 
                 color='#CCCCCC', edgecolor='#222222', hatch='..', xerr=desv_pre, capsize=3,
                 error_kw={'ecolor': '#333333', 'elinewidth': 1})
    b2 = ax.barh(y + height/2, medias_post, height, label='Postest (Sistema BI)', 
                 color='#444444', edgecolor='#111111', hatch='///', xerr=desv_post, capsize=3,
                 error_kw={'ecolor': '#111111', 'elinewidth': 1})
    
    ax.set_yticks(y)
    ax.set_yticklabels(items)
    ax.set_xlabel("Puntuación media en escala Likert (1: Muy deficiente a 5: Excelente)")
    ax.set_xlim(0, 5.6)
    ax.xaxis.set_major_formatter(formatter_coma)
    ax.grid(axis='x', linestyle='--', alpha=0.5, color='#888888')
    
    # Línea de referencia en 3.0 (Neutro)
    ax.axvline(3.0, color='#888888', linestyle=':', linewidth=1)
    
    ax.legend(loc='lower right', frameon=True, facecolor='#FFFFFF', edgecolor='#AAAAAA')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.invert_yaxis()
    
    guardar_grafico(fig, "grafico_4_6_evaluacion_likert_pre_post.png")


if __name__ == "__main__":
    print("Iniciando generación de los 6 gráficos del Capítulo IV...")
    generar_grafico_4_1()
    generar_grafico_4_2()
    generar_grafico_4_3()
    generar_grafico_4_4()
    generar_grafico_4_5()
    generar_grafico_4_6()
    print("¡Todos los gráficos fueron generados exitosamente a 300 DPI en escala de grises!")
