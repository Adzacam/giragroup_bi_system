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

def verificar_sprint2():
    print("=" * 70)
    print(" INICIANDO VERIFICACIÓN MULTITAREA SOBRE LOS 10 ARCHIVOS DE UPLOADS")
    print("=" * 70)

    # Inicializar componentes
    enricher = EntityEnricher()
    fk_checker = ForeignKeyChecker()
    audit_logger = AuditLogger("ejecucion_verificacion_multitarea.xlsx")

    # Archivos maestros académicos a cargar primero
    archivos_maestros = [
        "uploads/Base_Academica_ARCA_TEST.xlsx",
        "uploads/TBL_INSCRITOS_TEST.xlsx",
        "uploads/Planificacion_Ejecucion_TEST.xlsx"
    ]

    print("\n[1] Cargando catálogos académicos y llaves relacionales...")
    for arca_path in archivos_maestros:
        if os.path.exists(arca_path):
            res = procesar_documento_completo(arca_path)
            for hd in res["hojas_descartadas"]:
                audit_logger.registrar_hoja_descartada(hd["nombre_hoja"], hd["razon"])
            enricher.cargar_desde_dataframes(res["hojas_estructuradas"])
            fk_checker.cargar_pos_maestros(res["hojas_estructuradas"])

    # Archivos de la carpeta uploads a verificar
    todos_archivos = [
        "uploads/Base_Academica_ARCA_TEST.xlsx",
        "uploads/BD_Cobranzas_giraGroup.xlsx",
        "uploads/BD_Egresos_TEST.xlsx",
        "uploads/BD_Techos_TEST.xlsx",
        "uploads/EJECUTADO_VS_META_TEST.xlsx",
        "uploads/Evaluacion_Docente_GiraGroup_TEST.xlsx",
        "uploads/Experiencia_Docente_TEST.xlsx",
        "uploads/Planificacion_Ejecucion_TEST.xlsx",
        "uploads/TBL_INSCRITOS_TEST.xlsx",
        "uploads/BBDD_Evaluacion_Docente_GiraGroup_TEST.xlsx"
    ]

    print("\n[2] Procesando los 10 archivos de uploads/...")
    
    resumen_clasificacion = []
    all_docs = []

    for file_path in todos_archivos:
        if not os.path.exists(file_path):
            continue
        
        res = procesar_documento_completo(file_path)
        nombre_file = res["nombre_archivo"]

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
    print(" CLASIFICACIÓN DE HOJAS POR ARCHIVO (CORPUS DE 10 ARCHIVOS)")
    print("=" * 70)
    for r in resumen_clasificacion:
        print(f" {r['archivo']:<45} | TL: {r['texto_libre']} | EST: {r['estructuradas']} | FIN: {r['financieras']} | DESC: {r['descartadas']}")

    # 4. Resumen de Documentos Mínimos
    print("\n" + "=" * 70)
    print(" DOCUMENTOS MÍNIMOS RESULTANTES (SPRINT 3 READY)")
    print("=" * 70)
    print(f"Total Documentos Mínimos Generados: {len(all_docs)}")
    print(f"  -> Estado 'ok': {sum(1 for d in all_docs if d['estado'] == 'ok')}")
    print(f"  -> Estado 'sin_llave_valida': {sum(1 for d in all_docs if d['estado'] == 'sin_llave_valida')}")
    print(f"  -> Estado 'vacio_descartado': {sum(1 for d in all_docs if d['estado'] == 'vacio_descartado')}")

    # Mostrar Muestras de Documentos
    ok_docs_with_docente = [d for d in all_docs if d["estado"] == "ok" and d["llaves_relacion"]["DOCENTE"]]
    if ok_docs_with_docente:
        print("\n[MUESTRA 1] Documento Mínimo 'ok' Enriquecido con DOCENTE (DIP. EXP DOC. X MODULO):")
        pprint(ok_docs_with_docente[0])

    inscritos_docs = [d for d in all_docs if d["fuente"]["hoja"] == "TBL_INSCRITOS"]
    if inscritos_docs:
        print("\n[MUESTRA 2] Documento Mínimo con POS Compuesto Recortado (TBL_INSCRITOS):")
        pprint(inscritos_docs[0])

    reporte = audit_logger.exportar_reporte()
    print(f"\n[REPORT] Log de auditoría exportado a: pipeline/logs/ingestion_audit.json")

if __name__ == "__main__":
    verificar_sprint2()
