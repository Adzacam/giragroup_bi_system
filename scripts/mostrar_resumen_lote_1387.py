# -*- coding: utf-8 -*-
"""
scripts/mostrar_resumen_lote_1387.py
------------------------------------
Imprime en consola el log y auditoría oficial del lote de 1.387 registros
con los totales reales y la cascada híbrida para la captura de la Figura 3.17.
"""
import json

with open('docs/evidencias/lote_1387_uploads_data_arquitectura_b.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

def fmt_miles(n):
    return f"{n:,}".replace(",", ".")

def fmt_pct(p):
    return f"{p:.2f}".replace(".", ",")

print('=' * 78)
print('  GIRAGROUP BI - AUDITORÍA DE EXTRACCIÓN Y GOBERNANZA DATAOPS (LOTE 1.387)')
print('=' * 78)
print(f'Total registros evaluados: {fmt_miles(d["lote_evaluado"]["total_registros"])}')
print(f'  • Consolidación directa  (Banda >= 0,85): {fmt_miles(d["distribucion_bandas_con_regla_personas"]["directo"]["conteo"]):>5} ({fmt_pct(d["distribucion_bandas_con_regla_personas"]["directo"]["porcentaje"])} %)')
print(f'  • Revisión humana HITL   (Banda 0,60-0,85): {fmt_miles(d["distribucion_bandas_con_regla_personas"]["hitl"]["conteo"]):>5} ({fmt_pct(d["distribucion_bandas_con_regla_personas"]["hitl"]["porcentaje"])} %)')
print(f'  • Retenido en Staging    (Banda < 0,60):    {fmt_miles(d["distribucion_bandas_con_regla_personas"]["staging"]["conteo"]):>5} ({fmt_pct(d["distribucion_bandas_con_regla_personas"]["staging"]["porcentaje"])} %)')
print('-' * 78)
print('RESOLUCIONES EXITOSAS POR COMPONENTE DE CASCADA HÍBRIDA (N = 11.426):')
print(f'  1. Documento de Identidad (CI_EXACTA): {fmt_miles(d["conteos_fuente_resolucion"]["CI_EXACTA"]):>5} (16,19 %)')
print(f'  2. Encabezado Posicional (ENCABEZADO):  {fmt_miles(d["conteos_fuente_resolucion"]["ENCABEZADO"]):>5} (26,95 %)')
print(f'  3. Expresiones Regulares  (REGEX):      {fmt_miles(d["conteos_fuente_resolucion"]["REGEX"]):>5} (27,16 %)')
print(f'  4. Modelo del Lenguaje    (BETO):       {fmt_miles(d["conteos_fuente_resolucion"]["BETO"]):>5} (28,43 %)')
print(f'  5. Coincidencia Difusa    (FUZZY):      {fmt_miles(d["conteos_fuente_resolucion"]["FUZZY"]):>5} ( 1,28 %)')
print('=' * 78)
