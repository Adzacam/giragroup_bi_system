"""Consultas de revisión sobre resultados guardados, sin inferencia ni escrituras."""
import hashlib
import json
import math
import re
from datetime import datetime

from fastapi import HTTPException
from models.dim_origen import DimOrigenDocumental
from models.staging_entidad import StagingEntidadNoResuelta
from services.bandeja_grupos import clave_grupo, grupos_pendientes, ids_del_grupo
from services.dataops_evaluation_service import enmascarar_ci, texto_sin_ci, strip_accents, cis_en_entidades, NON_PERSON_WORDS
from services.revision_hechos import items_hechos_en_revision
from services.sugerencia_hitl import nombre_extraido, es_sugerencia_un_clic, similitud_nombre_completo

MOTIVOS = {
    'CI_DUDOSA': 'Cédula dudosa', 'CI_ILEGIBLE': 'Cédula ilegible',
    'CI_NOMBRE_DISCORDANTE': 'La cédula coincide pero el nombre es distinto',
    'BAJA_CONFIANZA_IA': 'Lectura con baja confianza', 'BAJA_CONFIANZA': 'Lectura con baja confianza',
    'HOMONIMIA': 'Posible homonimia: nombre parecido a otra persona',
    'FECHA_INSCRIPCION_INVALIDA': 'Fecha de inscripción no válida',
    'POS_NO_EN_DIM_MODULO': 'Programa sin coincidencia en el catálogo',
    'HECHO_EN_REVISION': 'Hecho cargado que necesita revisión',
    'REVISION_GENERAL': 'Revisión general', 'NOTA_FUERA_ESCALA': 'Nota fuera de escala',
    'ENTIDAD_NUEVA': 'Entidad nueva', 'ESCALA_AMBIGUA': 'Escala no declarada',
}


def motivo_publico(motivo):
    return MOTIVOS.get(motivo, (motivo or 'Revisión general').replace('_', ' ').capitalize())


def token_grupo(clave):
    return 'grupo-' + hashlib.sha256(clave.encode('utf-8')).hexdigest()


def documentos(db, id_lote=None, doc_id=None):
    q = db.query(DimOrigenDocumental)
    if id_lote is not None:
        if not str(id_lote).isdigit():
            raise HTTPException(404, 'El lote no existe.')
        q = q.filter(DimOrigenDocumental.id_lote == int(id_lote))
    if doc_id is not None:
        q = q.filter(DimOrigenDocumental.id_documento == doc_id)
    docs = q.all()
    if (id_lote is not None or doc_id is not None) and not docs:
        raise HTTPException(404, 'El lote o archivo no existe en esta selección.')
    return docs


def presupuesto_manual(doc, texto):
    fuente = (doc.tipo_fuente or '').upper() if doc else ''
    rotulo = re.search(r'(?:^|[|;\n])\s*presupuesto[^:|;\n]{0,45}(?=[:|;\n]|$)', strip_accents(texto or '').lower())
    return fuente in ('PRESUPUESTO', 'RENTABILIDAD', 'COSTO_PROGRAMA', 'TECHO_CONVENIO', 'EGRESOS', 'TECHOS') or bool(rotulo)


def datos_payload(ent):
    p = ent.payload_json or {}
    if isinstance(p, str):
        try:
            p = json.loads(p)
        except (TypeError, ValueError):
            p = {}
    return p if isinstance(p, dict) else {}


def proteger_ci(valor, cis=()):
    if isinstance(valor, dict):
        return {k: proteger_ci(v, cis) for k, v in valor.items() if k not in ('ci_real', 'ci_temporal')}
    if isinstance(valor, list):
        return [proteger_ci(v, cis) for v in valor[:50]]
    if isinstance(valor, str):
        valor = texto_sin_ci(valor, cis)
        return re.sub(r'\b(CI|C[ÉE]DULA(?: DE IDENTIDAD)?)\s*[:=#-]\s*(\d[\d .-]*(?:\s+[A-Z]{2})?)',
                      lambda m: m[1] + ': ' + enmascarar_ci(m[2]), valor, flags=re.I)[:4000]
    return valor


def caso_guardado(ent, doc):
    p = datos_payload(ent)
    raw = p.get('raw_line') or ent.texto_original or ''
    nombre = p.get('estudiante') or nombre_extraido(ent.texto_original, p.get('raw_line'))
    palabras = set(re.findall(r'[a-z]+', strip_accents(nombre or '').lower()))
    if '@' in (nombre or '') or '|' in (nombre or '') or palabras.intersection(NON_PERSON_WORDS):
        nombre = None
    ci = ent.ci_temporal or p.get('ci_real') or p.get('ci')
    score = float(ent.score_fuzzy) if ent.score_fuzzy is not None else None
    manual = presupuesto_manual(doc, raw) or presupuesto_manual(doc, ent.texto_original)
    area = p.get('area') or ('financiera' if doc and doc.tipo_fuente == 'COBRANZA' else 'comercial' if doc and doc.tipo_fuente == 'ADMISION' else 'academica')
    motivo = ent.motivo or 'REVISION_GENERAL'
    publico = {
        'id': ent.id_staging, 'db_id': ent.id_staging, 'id_documento': ent.id_documento,
        'tipo_entidad': ent.tipo_entidad, 'tipo_fuente': doc.tipo_fuente if doc else None,
        'archivo_origen': doc.nombre_archivo if doc else None, 'motivo': motivo, 'motivo_label': motivo_publico(motivo),
        'estudiante': nombre, 'nombre_extraido': nombre, 'sugerencia': ent.mejor_candidato,
        'ci': enmascarar_ci(ci) if ci else None, 'ci_enmascarado': enmascarar_ci(ci) if ci else None,
        'que_vio': raw, 'contexto_raw': raw, 'por_que_detuvo': 'Fila de presupuesto: verifica su clasificación antes de aprobar.' if manual else p.get('motivo_llano') or 'Comprueba los datos identificados antes de aprobar.',
        'indice_registro': score, 'similitud': score,
        'ner_confidence': float(ent.nivel_confianza) if ent.nivel_confianza is not None else None,
        'modulo_detectado': p.get('modulo'), 'nota_final': p.get('nota_normalizada'),
        'monto_deuda': p.get('monto_deuda'), 'cuotas_impagas': p.get('cuotas_impagas'),
        'mes': p.get('mes'), 'gestion': p.get('gestion'), 'area': area,
        'en_calidad': bool(p.get('en_calidad')), 'manual_presupuesto': manual,
        'estado_resolucion': ent.estado_resolucion or 'PENDIENTE',
        'locked': bool(ent.lock_usuario_id and ent.lock_expira and ent.lock_expira > datetime.utcnow()),
        'un_clic': not manual and es_sugerencia_un_clic(nombre, ent.mejor_candidato),
        'similitud_nombre_completo': similitud_nombre_completo(nombre, ent.mejor_candidato),
        'cuando': ent.resuelto_en.isoformat() if ent.resuelto_en else None,
        'entidades': p.get('entities') or p.get('entidades') or [],
    }
    return proteger_ci(publico, cis_en_entidades(publico['entidades'], str(ci) if ci else None))


def iterar_casos(db, docs, resueltos=False):
    ids = [d.id_documento for d in docs]
    mapa = {d.id_documento: d for d in docs}
    q = db.query(StagingEntidadNoResuelta).filter(
        StagingEntidadNoResuelta.resuelto == resueltos,
        StagingEntidadNoResuelta.id_documento.in_(ids)).order_by(StagingEntidadNoResuelta.id_staging)
    # La respuesta solo materializa cinco casos. El recorrido usa bloques acotados, sin modelos NLP.
    for ent in q.yield_per(200):
        yield caso_guardado(ent, mapa.get(ent.id_documento)), clave_grupo(ent.motivo, ent.texto_original)
    if not resueltos:
        offset = 0
        while True:
            bloque = items_hechos_en_revision(db, ids, offset=offset, limit=200)
            for caso in bloque:
                caso['motivo_label'] = motivo_publico(caso.get('motivo'))
                yield proteger_ci(caso), None
            if len(bloque) < 200:
                break
            offset += len(bloque)


def coincide(caso, search='', area=None, motivo=None, estado=None):
    if area and area not in ('TODAS', 'ALL') and caso.get('area') != area and not (area == 'calidad' and caso.get('en_calidad')):
        return False
    if motivo and motivo not in ('ALL', 'TODOS') and caso.get('motivo') != motivo:
        return False
    if estado and estado not in ('ALL', 'TODOS') and caso.get('estado_resolucion') != estado:
        return False
    texto = ' '.join(str(caso.get(k) or '') for k in ('estudiante', 'sugerencia', 'modulo_detectado', 'archivo_origen', 'que_vio', 'motivo', 'motivo_label'))
    return not search or strip_accents(search).lower() in strip_accents(texto).lower()


def consultar(db, docs, page=1, page_size=5, search='', area=None, motivo=None, estado=None, vista='PENDIENTES', grupo=None):
    seleccion, total, un_clic = [], 0, 0
    ids_grupo = set(str(i) for i in ids_del_grupo(db, clave_interna(db, grupo, [d.id_documento for d in docs]), [d.id_documento for d in docs])) if grupo else None
    for caso, clave in iterar_casos(db, docs, vista == 'RESUELTOS'):
        if ids_grupo is not None and str(caso['id']) not in ids_grupo:
            continue
        if not coincide(caso, search, area, motivo, estado):
            continue
        if (page - 1) * page_size <= total < page * page_size:
            seleccion.append(caso)
        total += 1
        un_clic += bool(caso.get('un_clic'))
    pag = {'page': page, 'page_size': page_size, 'total_items': total, 'total_pages': max(1, math.ceil(total / page_size))}
    return {'status': 'success', 'total': total, 'pendientes': total if vista != 'RESUELTOS' else None,
            'un_clic_total': un_clic, 'pagination': pag, 'data': seleccion, 'items': seleccion,
            'resolved_history': seleccion if vista == 'RESUELTOS' else []}


def grupos_publicos(db, docs, page=1, search=''):
    ids = [d.id_documento for d in docs]
    # La clave de agrupación interna puede contener una cédula. Solo sale su hash, nunca la clave original.
    base = grupos_pendientes(db, ids, limite=10**9)
    grupos = []
    for g in base['grupos']:
        titulo = motivo_publico(g.get('motivo'))
        ejemplo = proteger_ci(g.get('ejemplo') or '')
        if search and strip_accents(search).lower() not in strip_accents(titulo + ' ' + ejemplo).lower():
            continue
        accion = g.get('accion_grupo') or 'MANUAL'
        if accion == 'MAPEAR_ESTADO' and '|falta:ninguno|' not in g['clave']:
            accion = 'MANUAL'
        grupos.append({'clave': token_grupo(g['clave']), 'motivo': g['motivo'], 'titulo': titulo,
                       'ejemplo': ejemplo, 'n': g['n'], 'accion_grupo': accion})
    return {'total_casos': sum(g['n'] for g in grupos), 'total_grupos': len(grupos), 'doc_ids': ids,
            'grupos': grupos[(page - 1) * 5:page * 5],
            'pagination': {'page': page, 'page_size': 5, 'total_items': len(grupos), 'total_pages': max(1, math.ceil(len(grupos) / 5))}}


def clave_interna(db, clave, ids):
    if not clave.startswith('grupo-'):
        return clave
    for g in grupos_pendientes(db, ids, limite=10**9)['grupos']:
        if token_grupo(g['clave']) == clave:
            return g['clave']
    raise HTTPException(409, 'El grupo cambió o ya fue resuelto. Actualiza la bandeja.')
