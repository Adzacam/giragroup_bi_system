"""Lectura paginada del texto de ingesta. No ejecuta BETO ni modifica el lote."""
import io
import json
from sqlalchemy import func

from models.staging_registro import StagingRegistroCrudo
from services.dataops_privacy import (
    texto_publico, _columnas, _fila_publica, _valores_privados,
    _reemplazar_privados, _proteger_metadatos,
)


def _payload(valor):
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except (TypeError, ValueError):
            return {}
    return valor if isinstance(valor, dict) else {}


def obtener_texto_preparado(db, docs, page=1, page_size=5):
    """Recorre bloques por lotes; solo materializa las filas y metadatos de la página solicitada."""
    doc_map = {d.id_documento: d for d in docs}
    consulta = db.query(StagingRegistroCrudo).filter(
        StagingRegistroCrudo.id_documento.in_(doc_map), StagingRegistroCrudo.es_ruido == False,
    )
    filas, omitidas, alertas, columnas = 0, 0, 0, 0
    seleccionadas = []
    privados_pagina = {}
    desde, hasta = (page - 1) * page_size, page * page_size
    # Se excluye el JSON de diagnóstico de este recorrido; puede contener muestras de todo el libro.
    for bloque in consulta.with_entities(StagingRegistroCrudo.id, StagingRegistroCrudo.id_documento, StagingRegistroCrudo.texto_plano).order_by(StagingRegistroCrudo.id).yield_per(100):
        tiene_lineas = False
        for linea in io.StringIO(bloque.texto_plano or ''):
            linea = linea.strip()
            if not linea:
                continue
            tiene_lineas = True
            celdas = _columnas(linea)
            columnas = max(columnas, len(celdas))
            # Las preguntas de una encuesta llevan '?' en el encabezado, no son datos dudosos.
            valores = [c.partition(':')[2] if ':' in c else c for c in celdas]
            alerta = 'La fila contiene ? en un valor; comprueba si es correcto.' if any('?' in v for v in valores) else ('La fila contiene un solo campo.' if len(celdas) < 2 else None)
            alertas += bool(alerta)
            if desde <= filas < hasta:
                doc = doc_map[bloque.id_documento]
                cols, texto = _fila_publica(linea, doc.tipo_fuente)
                privados = _valores_privados(linea, doc.tipo_fuente)
                privados_pagina[filas + 1] = privados
                cols = [_reemplazar_privados(c, privados) for c in cols]
                texto = _reemplazar_privados(texto, privados)
                seleccionadas.append({
                    'line_number': filas + 1, 'stg_id': bloque.id, 'id_documento': doc.id_documento,
                    'nombre_archivo': texto_publico(doc.nombre_archivo or 'Sin dato'),
                    'tipo_fuente': doc.tipo_fuente, 'tipo_escala': doc.tipo_escala,
                    'fila_original': [c[:512] for c in cols[:50]], 'fila_original_raw': texto[:4000],
                    'oracion_beto': texto[:4000], 'texto_crudo': texto[:4000], 'alerta': alerta,
                    'vista_abreviada': len(texto) > 4000 or len(cols) > 50 or any(len(c) > 512 for c in cols),
                    'rango_fechas': doc.periodo, 'chips': {},
                })
            filas += 1
        omitidas += not tiene_lineas
    # Una muestra de diagnóstico por documento y los bloques de la página, nunca todos los JSON.
    ids_pagina = {r['stg_id'] for r in seleccionadas}
    muestras = consulta.with_entities(StagingRegistroCrudo.id_documento, func.min(StagingRegistroCrudo.id)).group_by(StagingRegistroCrudo.id_documento).all()
    ids_metadata = ids_pagina | {r[1] for r in muestras}
    payloads = {r.id: _payload(r.payload_json) for r in consulta.filter(StagingRegistroCrudo.id.in_(ids_metadata)).all()}
    for fila in seleccionadas:
        chips = payloads.get(fila['stg_id'], {}).get('chips_catalogo') or {}
        fila['chips'] = _proteger_metadatos({k: chips.get(k) for k in ('programa_cat', 'modulo_cat', 'precio_base_cat', 'fecha_detectada')}, privados_pagina[fila['line_number']]) if isinstance(chips, dict) else {}
    diagnosticos = []
    for doc_id, bloque_id in muestras:
        diag = payloads.get(bloque_id, {}).get('diagnostico_estructural') or {}
        if not isinstance(diag, dict):
            continue
        diagnosticos.append({
            'id_documento': doc_id,
            'fila_cabecera': diag.get('fila_cabecera_desplazada') or diag.get('fila_cabecera'),
            'filas_subtotales_descartadas': diag.get('filas_subtotales_descartadas'),
            'encabezados_multinivel_aplanados': diag.get('encabezados_multinivel_aplanados'),
        })
    return {
        'status': 'success', 'registros': seleccionadas, 'total': filas, 'page': page, 'page_size': page_size,
        'total_pages': max(1, (filas + page_size - 1) // page_size),
        'kpis': {'filas_leidas': filas, 'filas_omitidas': omitidas, 'columnas_detectadas': columnas or None, 'total_alertas': alertas},
        'diagnosticos': diagnosticos,
        'alertas': [{'line': r['line_number'], 'motivo': r['alerta']} for r in seleccionadas if r['alerta']],
        'datos_protegidos': True,
    }
