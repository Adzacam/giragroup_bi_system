"""
scripts/imprimir_f3_17.py
-------------------------
Imprime en consola el log de auditoría de extracción del lote de 1.387 registros
con los totales (1.387 / 1.353 / 34 / 0) y la cascada híbrida de resolución
(CI / Encabezado / Regex / BETO / Fuzzy) para la captura de la Figura F3.17.
"""

import json
from pathlib import Path

def main():
    json_path = Path("docs/evidencias/lote_1387_uploads_data_arquitectura_b.json")
    if not json_path.exists():
        print(f"Error: No se encontró {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        d = json.load(f)

    tot = d["lote_evaluado"]["total_registros"]
    bandas = d["distribucion_bandas_con_regla_personas"]
    directo_cnt = bandas["directo"]["conteo"]
    directo_pct = bandas["directo"]["porcentaje"]
    hitl_cnt = bandas["hitl"]["conteo"]
    hitl_pct = bandas["hitl"]["porcentaje"]
    stg_cnt = bandas["staging"]["conteo"]
    stg_pct = bandas["staging"]["porcentaje"]

    cascada = d["conteos_fuente_resolucion"]
    ci_cnt = cascada["CI_EXACTA"]
    enc_cnt = cascada["ENCABEZADO"]
    reg_cnt = cascada["REGEX"]
    beto_cnt = cascada["BETO"]
    fuz_cnt = cascada["FUZZY"]
    total_cascada = sum([ci_cnt, enc_cnt, reg_cnt, beto_cnt, fuz_cnt])

    # Formateo boliviano
    def fmt_num(n):
        return f"{n:,.0f}".replace(",", ".")

    def fmt_pct(p):
        return f"{p:.2f}".replace(".", ",")

    print("=" * 78)
    print("  GIRAGROUP BI - AUDITORÍA DE EXTRACCIÓN Y GOBERNANZA DATAOPS (LOTE 1.387)")
    print("=" * 78)
    print(f"Total registros evaluados: {fmt_num(tot)} registros (100,00 %)")
    print(f"  • Consolidación directa   (Banda >= 0,85):   {fmt_num(directo_cnt):>5} ({fmt_pct(directo_pct)} %)")
    print(f"  • Revisión humana HITL    (Banda 0,60-0,85): {fmt_num(hitl_cnt):>5} ({fmt_pct(hitl_pct)} %)")
    print(f"  • Retenido en Staging     (Banda < 0,60):    {fmt_num(stg_cnt):>5} ({fmt_pct(stg_pct)} %)")
    print("-" * 78)
    print(f"RESOLUCIONES EXITOSAS POR CASCADA HÍBRIDA MULTI-ETAPA (N = {fmt_num(total_cascada)}):")
    print(f"  1. Documento de Identidad (CI_EXACTA):   {fmt_num(ci_cnt):>5} ({fmt_pct(ci_cnt / total_cascada * 100)} %)")
    print(f"  2. Encabezado Posicional  (ENCABEZADO):  {fmt_num(enc_cnt):>5} ({fmt_pct(enc_cnt / total_cascada * 100)} %)")
    print(f"  3. Expresiones Regulares   (REGEX):       {fmt_num(reg_cnt):>5} ({fmt_pct(reg_cnt / total_cascada * 100)} %)")
    print(f"  4. Inferencia Semántica    (BETO):        {fmt_num(beto_cnt):>5} ({fmt_pct(beto_cnt / total_cascada * 100)} %)")
    print(f"  5. Coincidencia Difusa     (FUZZY):       {fmt_num(fuz_cnt):>5} ({fmt_pct(fuz_cnt / total_cascada * 100)} %)")
    print("=" * 78)

if __name__ == "__main__":
    main()
