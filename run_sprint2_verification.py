"""
run_sprint2_verification.py — Script de verificación para el Sprint 2.
Ejecuta el pipeline completo de Sprint 2 sobre los 10 ARCHIVOS de uploads/:
1. Lee las bases académicas/estructuradas (Base_Academica_ARCA_TEST, TBL_INSCRITOS, etc.) para poblar catálogos.
2. Ingiere TODAS las encuestas de opinión y hojas de gestión.
3. Verifica que hojas financieras (BD_Cobranzas, BD_Egresos, BD_Techos, IBP) permanezcan financieras/estructuradas.
4. Genera los Documentos Mínimos de encuestas (DIPLOMADOS DOCENTE, CURSOS DOCENTE, DIP. EXP DOC. X MODULO, TBL EVALUACION DOCENTE) con enriquecimiento de DOCENTE por POS+MÓDULO y POS limpio.
"""

import os
import json
import logging
from pprint import pprint
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from pipeline.ingestion.dispatcher import procesar_documento_completo
from pipeline.normalization.entity_enricher import EntityEnricher
from pipeline.normalization.document_builder import construir_documentos_minimos
from pipeline.normalization.fk_checker import ForeignKeyChecker
from pipeline.normalization.audit_logger import AuditLogger
from pipeline.normalization.text_cleaner import deduplicar_respuestas

import sys
import glob

def verificar_sprint2(corpus_dir: str = "uploads/test"):
    print("=" * 70)
    print(f" INICIANDO VERIFICACIÓN MULTITAREA SOBRE CORPUS: {corpus_dir}")
    print("=" * 70)

    if not os.path.exists(corpus_dir):
        print(f"Error: El directorio '{corpus_dir}' no existe.")
        return

    # Inicializar componentes
    enricher = EntityEnricher()
    fk_checker = ForeignKeyChecker()
    audit_logger = AuditLogger("ejecucion_verificacion_multitarea.xlsx")

    # Escanear todos los archivos .xlsx
    all_files = sorted(glob.glob(os.path.join(corpus_dir, "*.xlsx")))
    if not all_files:
        print(f"No se encontraron archivos .xlsx en '{corpus_dir}'.")
        return

    # Identificar maestros académicos (ARCA, TBL_INSCRITOS, Planificacion)
    archivos_maestros = []
    for f in all_files:
        fn = os.path.basename(f).lower()
        if "arca" in fn or "inscrit" in fn or "planific" in fn:
            archivos_maestros.append(f)

    print("\n[1] Cargando catálogos académicos y llaves relacionales...")
    for arca_path in archivos_maestros:
        print(f"  -> Cargando maestro: {os.path.basename(arca_path)}")
        res = procesar_documento_completo(arca_path)
        for hd in res["hojas_descartadas"]:
            audit_logger.registrar_hoja_descartada(hd["nombre_hoja"], hd["razon"])
        enricher.cargar_desde_dataframes(res["hojas_estructuradas"])
        fk_checker.cargar_pos_maestros(res["hojas_estructuradas"])

    print("\n[2] Procesando todos los archivos del corpus...")
    
    resumen_clasificacion = []
    all_docs = []

    for file_path in all_files:
        nombre_file = os.path.basename(file_path)
        res = procesar_documento_completo(file_path)

        resumen_clasificacion.append({
            "archivo": nombre_file,
            "texto_libre": len(res["hojas_texto_libre"]),
            "estructuradas": len(res["hojas_estructuradas"]),
            "financieras": len(res["hojas_financieras"]),
            "descartadas": len(res["hojas_descartadas"]),
        })

        for hd in res["hojas_descartadas"]:
            audit_logger.registrar_hoja_descartada(hd["nombre_hoja"], hd["razon"])

        for col_info in res["auditoria"]["columnas_no_mapeadas_global"]:
            audit_logger.registrar_columnas_no_mapeadas([col_info], col_info.get("hoja", ""))

        # Generar Documentos Mínimos solo para hojas clasificadas como texto_libre
        for hoja in res["hojas_texto_libre"]:
            hoja["nombre_archivo"] = nombre_file
            docs_hoja = construir_documentos_minimos(hoja, enricher=enricher)
            unicos, duplicados = deduplicar_respuestas(docs_hoja)
            audit_logger.registrar_duplicados(duplicados)
            res_fk = fk_checker.verificar_documentos(unicos)
            
            for doc_upd in res_fk["documentos_actualizados"]:
                if doc_upd["estado"] == "sin_llave_valida":
                    audit_logger.registrar_sin_llave_valida(
                        doc_upd["id_documento"],
                        doc_upd["llaves_relacion"].get("POS", ""),
                        hoja["nombre_hoja"]
                    )
            all_docs.extend(res_fk["documentos_actualizados"])

    # 3. Mostrar Resumen de Clasificación por Archivo
    print("\n" + "=" * 70)
    print(f" CLASIFICACIÓN DE HOJAS POR ARCHIVO (CORPUS DE {len(all_files)} ARCHIVOS)")
    print("=" * 70)
    for r in resumen_clasificacion:
        print(f" {r['archivo']:<45} | TL: {r['texto_libre']} | EST: {r['estructuradas']} | FIN: {r['financieras']} | DESC: {r['descartadas']}")

    # 4. Resumen de Documentos Mínimos
    print("\n" + "=" * 70)
    print(" DOCUMENTOS MÍNIMOS RESULTANTES (SPRINT 3 READY)")
    print("=" * 70)
    print(f"Total Documentos Mínimos Generados: {len(all_docs)}")
    print(f"  -> Estado 'ok': {sum(1 for d in all_docs if d['estado'] == 'ok')}")
    print(f"  -> Estado 'pos_valido_dado_de_baja': {sum(1 for d in all_docs if d['estado'] == 'pos_valido_dado_de_baja')}")
    print(f"  -> Estado 'sin_llave_valida': {sum(1 for d in all_docs if d['estado'] == 'sin_llave_valida')}")
    print(f"  -> Estado 'vacio_descartado': {sum(1 for d in all_docs if d['estado'] == 'vacio_descartado')}")

    # Mostrar Muestras de Documentos
    ok_docs_with_docente = [d for d in all_docs if d["estado"] == "ok" and d["llaves_relacion"]["DOCENTE"]]
    if ok_docs_with_docente:
        print("\n[MUESTRA 1] Documento Mínimo 'ok' Enriquecido con DOCENTE:")
        pprint(ok_docs_with_docente[0])

    inscritos_docs = [d for d in all_docs if "inscritos" in d["fuente"]["hoja"].lower()]
    if inscritos_docs:
        print("\n[MUESTRA 2] Documento Mínimo con POS Compuesto Recortado:")
        pprint(inscritos_docs[0])

    reporte = audit_logger.exportar_reporte()
    print(f"\n[REPORT] Log de auditoría exportado a: pipeline/logs/ingestion_audit.json")

if __name__ == "__main__":
    target_dir = "uploads/test"
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    verificar_sprint2(target_dir)
