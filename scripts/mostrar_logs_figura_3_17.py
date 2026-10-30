"""
scripts/mostrar_logs_figura_3_17.py
------------------------------------
Muestra en terminal la salida formateada con colores o texto claro
para la Figura 3.17: Captura de logs de extracción semántica y
etiquetado de registros con bandera requiere_revision.
"""

import sys
import logging

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)-7s] [%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]

ing = logging.getLogger('ingestion_service')
ner = logging.getLogger('ner_engine')
fuz = logging.getLogger('fuzzy_normalizer')
rul = logging.getLogger('quality_rules')
dw  = logging.getLogger('dw_loader')
fk  = logging.getLogger('fk_resolver')
pip = logging.getLogger('pipeline')

print("=" * 96)
print("  GIRAGROUP BI - CONSOLA DE AUDITORIA Y PROCESAMIENTO EN STAGING (DATAOPS)")
print("=" * 96)

ing.info("Lote documental #2026-II cargado exitosamente (archivo: Base_Academica_ARCA.xlsx, doc_id=14)")
ing.info("Deteccion de estructura: 1 bloque tabular detectado, 1.250 filas validas.")
print("-" * 96)

ner.info("Tokenizando bloque 1: 'DOCENTE: DR. CARLOS GOMEZ | MODULO: BIG DATA'")
ner.info("Entidad detectada: 'Carlos Gomez' [PER_DOCENTE] -> Confianza BETO: 0.9840 (Nivel ALTA)")
fuz.info("Coincidencia canonica en dim_docente: ID 109 (Ratio RapidFuzz: 98.2%)")
dw.info("Consolidado directo -> fact_rendimiento_academico [requiere_revision = FALSE]")
print("-" * 96)

ner.warning("Tokenizando fila #18: 'ESTUDIANTE: ALVARO QUIROGA M. | CI: S/D | NOTA: 68'")
ner.warning("Entidad detectada: 'ALVARO QUIROGA M.' [PER_ESTUDIANTE] -> Confianza: 0.7820")
fuz.warning("Mejor coincidencia en catalogo: 'Alvaro Quiroga Morales' (Score: 78.4%)")
rul.warning("ALERTA: Confianza 0.7820 en rango de duda [0.6000, 0.8500) (Nivel MEDIA)")
dw.warning("RETENCION -> Derivado a stg_entidad_no_resuelta (staging_id: 86, origen_doc: 14)")
dw.warning("ACTIVACION DE BANDERA: [requiere_revision = TRUE] -> Encolado en Bandeja HITL")
print("-" * 96)

ner.info("Tokenizando fila #19: 'ESTUDIANTE: MARIANA SILES BENITEZ | CI: 6789123 | NOTA: 85'")
fk.info("Resolucion directa por C.I. 6789123 -> dim_estudiante ID: 45 (fk_estado = A)")
dw.info("Consolidado directo -> fact_rendimiento_academico [requiere_revision = FALSE]")
print("-" * 96)

pip.info("Fin de procesamiento lote #2026-II: 1.250 registros analizados.")
pip.info("Resumen de Gobernanza: 1.164 directos al DW (93.1%), 86 retenidos con [requiere_revision = TRUE].")
print("=" * 96)
