"""Bitácora pública de un documento: hechos registrados y campos permitidos, sin muestras personales."""
import math
from fastapi import HTTPException
from sqlalchemy import func
from models.dim_origen import DimOrigenDocumental
from models.log_pipeline import LogPipelineIngesta
from models.staging_registro import StagingRegistroCrudo

ETAPAS = {
    'INGESTA': 'Carga del archivo', 'DISPATCH': 'Clasificación de la fuente',
    'VALIDATE': 'Validación de datos', 'STAGE': 'Guardado de la carga', 'SUMMARY': 'Resumen del procesamiento',
    'UPLOAD': 'Recepción del archivo', 'DETECT': 'Identificación del formato',
    'EXTRACT': 'Lectura del archivo', 'NORMALIZE': 'Normalización de columnas',
    'CLEAN': 'Preparación de filas', 'SERIALIZE': 'Preparación del texto',
    'PERSIST': 'Guardado de la carga', 'DW_CONSOLIDACION': 'Consolidación del lote',
    'HITL_RESOLUCION_INDIVIDUAL': 'Revisión de un caso',
    'HITL_APROBACION_EN_BLOQUE': 'Revisión en bloque',
    'HITL_RESOLUCION_LOTE': 'Revisión de casos del lote',
}
NIVELES = {'INFO': 'Información', 'SUCCESS': 'Completado', 'WARN': 'Observación',
           'WARNING': 'Observación', 'ERROR': 'Error'}


def documento(db, doc_id):
    doc = db.get(DimOrigenDocumental, doc_id)
    if doc is None:
        raise HTTPException(404, 'El documento no existe.')
    return doc


def evento_publico(evento):
    # Los mensajes históricos pueden contener nombres, documentos y parámetros SQL.
    # Se publica la etapa y el nivel reales; no se exponen mensajes ni muestras sin estructura.
    etapa = ETAPAS.get(evento.etapa, 'Evento de procesamiento')
    return {'id': evento.id, 'etapa': etapa, 'nivel': NIVELES.get(evento.nivel, 'Sin dato'),
            'fecha': evento.created_at.isoformat() if evento.created_at else None,
            'tiempo_ms': evento.tiempo_ms}


def matriz_registrada(db, doc_id):
    log = db.query(LogPipelineIngesta).filter_by(id_documento=doc_id, etapa='NORMALIZE').order_by(LogPipelineIngesta.id.desc()).first()
    matriz = (log.metadata_json or {}).get('matriz') if log and isinstance(log.metadata_json, dict) else None
    if not isinstance(matriz, list):
        return []
    campos = {'original': ('cabecera_original', 'original_col', 'columna_original'),
              'normalizado': ('cabecera_normalizada', 'mapped_col', 'campo_canonico'),
              'regla': ('regla', 'rule'), 'tipo': ('tipo_dato', 'type')}
    from services.dataops_privacy import texto_publico
    return [{k: texto_publico(next((m[c] for c in aliases if m.get(c) is not None), ''))[:300] or None
             for k, aliases in campos.items()} for m in matriz if isinstance(m, dict)]


def paginacion(page, total):
    return {'page': page, 'page_size': 5, 'total_items': total, 'total_pages': max(1, math.ceil(total / 5))}


def consultar(db, doc_id, page=1, map_page=1):
    doc = documento(db, doc_id)
    q = db.query(LogPipelineIngesta).filter_by(id_documento=doc_id)
    total = q.count()
    eventos = q.order_by(LogPipelineIngesta.id).offset((page - 1) * 5).limit(5).all()
    matriz = matriz_registrada(db, doc_id)
    filas, bloques, con_conteo = db.query(func.sum(StagingRegistroCrudo.n_filas), func.count(StagingRegistroCrudo.id),
                                         func.count(StagingRegistroCrudo.n_filas)).filter_by(id_documento=doc_id).one()
    return {'status': 'success', 'document_meta': {
        'id_documento': doc.id_documento, 'id_lote': doc.id_lote, 'nombre_archivo': doc.nombre_archivo,
        'tipo_fuente': doc.tipo_fuente, 'tipo_escala': doc.tipo_escala, 'institucion': doc.institucion,
        'periodo': doc.periodo, 'hash_sha256': doc.hash_sha256,
        'fecha_procesamiento': doc.fecha_procesamiento.isoformat() if doc.fecha_procesamiento else None},
        'summary_metrics': {'total_registros': int(filas) if bloques and bloques == con_conteo else None,
                            'bloques_guardados': bloques, 'eventos_registrados': total, 'columnas_mapeadas': len(matriz)},
        'data': [evento_publico(e) for e in eventos], 'pagination': paginacion(page, total),
        'normalization_matrix': matriz[(map_page - 1) * 5:map_page * 5],
        'matrix_pagination': paginacion(map_page, len(matriz))}


def reporte(db, doc):
    def celda(valor):
        return str(valor if valor is not None else 'Sin dato').replace('|', '\\|').replace('\n', ' ')
    yield '# Bitácora del documento\n\n'
    for label, valor in (('Documento', doc.id_documento), ('Lote', doc.id_lote), ('Archivo', doc.nombre_archivo),
                         ('Institución', doc.institucion), ('Periodo', doc.periodo), ('SHA-256', doc.hash_sha256)):
        yield f'- {label}: {celda(valor)}\n'
    yield '\nLos eventos indican etapas y niveles registrados. No incluyen mensajes internos ni muestras personales.\n\n'
    yield '| Fecha registrada | Etapa | Nivel | Duración registrada (ms) |\n|---|---|---|---|\n'
    q = db.query(LogPipelineIngesta).filter_by(id_documento=doc.id_documento).order_by(LogPipelineIngesta.id)
    for e in q.yield_per(100):
        fila = evento_publico(e)
        yield '| ' + ' | '.join(celda(fila[k]) for k in ('fecha', 'etapa', 'nivel', 'tiempo_ms')) + ' |\n'
    yield '\n## Columnas registradas\n\n| Columna original | Campo identificado | Regla | Tipo |\n|---|---|---|---|\n'
    for m in matriz_registrada(db, doc.id_documento):
        yield '| ' + ' | '.join(celda(m[k]) for k in ('original', 'normalizado', 'regla', 'tipo')) + ' |\n'
