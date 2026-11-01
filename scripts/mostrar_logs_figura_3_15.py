import sys
import logging

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]

log = logging.getLogger('ner_engine')
dw = logging.getLogger('dw_loader')
fz = logging.getLogger('fuzzy_matcher')

print("=" * 86)
print("  Terminal Log Output - Motor de Inferencia PLN y Etiquetado requiere_revision")
print("=" * 86)

log.info("Ingestion batch #2026-II cargado (doc_id=14)")
log.info("Tokenizando bloque: \"Docente: Dr. Carlos Gomez | Modulo: Big Data\"")
log.info("Entidad detectada: 'Carlos Gomez' [PER] -> Confianza BETO: 0.9840")
log.info("Coincidencia canonica en dim_docente: ID 109 (Ratio: 98.2%)")
dw.info("OK -> Insertado en fact_rendimiento_academico (requiere_revision=False)")

print("-" * 86)

log.warning("Tokenizando fila #18: \"Estudiante: ALVARO QUIROGA M. | CI: S/D\"")
log.info("Entidad detectada: 'ALVARO QUIROGA M.' [PER] -> Confianza: 0.7820")
fz.warning("Similitud maxima en dim_estudiante: 'Alvaro Quiroga Morales' (Score: 78.4%)")
dw.warning("ALERTA: Confianza 0.7820 < Umbral 0.8500")
dw.warning("RETENCION -> Derivado a staging_entidad_no_resuelta (ID: 86)")
dw.warning("Marcado con bandera: [requiere_revision = TRUE] para Consola HITL")

print("-" * 86)

log.info("Tokenizando fila #19: \"Estudiante: MARIANA SILES BENITEZ | CI: 6789123\"")
log.info("Resolucion directa por CI: 6789123 -> dim_estudiante ID: 45")
dw.info("OK -> Insertado en fact_rendimiento_academico (requiere_revision=False)")
log.info("Lote #2026-II finalizado: 1250 procesados, 86 derivados a HITL")
print("=" * 86)
