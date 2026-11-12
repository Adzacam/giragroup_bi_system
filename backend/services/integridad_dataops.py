"""Conteos de solo lectura. No ejecuta BETO ni deduce aprobaciones o hechos sin trazabilidad."""
from collections import Counter
from sqlalchemy import func
from models.staging_registro import StagingRegistroCrudo
from models.staging_entidad import StagingEntidadNoResuelta
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from models.fact_evaluacion import FactEvaluacionDocente
from models.fact_rentabilidad import FactRentabilidad
from models.fact_costo_programa import FactCostoPrograma
from models.fact_techo_convenio import FactTechoConvenio


def consultar(db, documentos, lectura=None):
    ids = [d.id_documento for d in documentos]
    origen = dict(db.query(StagingRegistroCrudo.id_documento,
                          func.sum(StagingRegistroCrudo.n_filas)).filter(
        StagingRegistroCrudo.id_documento.in_(ids),
        StagingRegistroCrudo.registro_origen_id.is_(None),
    ).group_by(StagingRegistroCrudo.id_documento).all())
    texto = Counter()
    for doc, contenido in db.query(StagingRegistroCrudo.id_documento, StagingRegistroCrudo.texto_plano).filter(
        StagingRegistroCrudo.id_documento.in_(ids), StagingRegistroCrudo.registro_origen_id.is_(None),
        StagingRegistroCrudo.es_ruido.is_(False),
    ).yield_per(100):
        texto[doc] += sum(bool(linea.strip()) for linea in (contenido or '').splitlines())
    leidas = Counter()
    directas = Counter()
    if lectura is not None:
        for fila in lectura.get('detalles', []):
            leidas[fila.get('id_documento')] += 1
            if fila.get('estado') == 'AUTOMATICO':
                directas[fila.get('id_documento')] += 1
    casos = {}
    for doc, resuelto, cantidad in db.query(StagingEntidadNoResuelta.id_documento,
            StagingEntidadNoResuelta.resuelto, func.count()).filter(
                StagingEntidadNoResuelta.id_documento.in_(ids)).group_by(
                    StagingEntidadNoResuelta.id_documento, StagingEntidadNoResuelta.resuelto):
        casos[(doc, bool(resuelto))] = cantidad
    hechos = {}
    for nombre, modelo in (
        ('academicos', FactRendimientoAcademico), ('financieros', FactSituacionFinanciera),
        ('respuestas', FactEvaluacionDocente), ('rentabilidad', FactRentabilidad),
        ('costos', FactCostoPrograma), ('convenios', FactTechoConvenio),
    ):
        hechos[nombre] = dict(db.query(modelo.id_documento, func.count()).filter(
            modelo.id_documento.in_(ids)).group_by(modelo.id_documento).all())
    return {'data': [{
        'id_documento': d.id_documento,
        'filas_origen': int(origen[d.id_documento]) if origen.get(d.id_documento) is not None else None,
        'filas_texto': texto[d.id_documento] if d.id_documento in origen else None,
        'filas_lectura': leidas[d.id_documento] if lectura is not None else None,
        'filas_directas': directas[d.id_documento] if lectura is not None else None,
        'casos_pendientes': casos.get((d.id_documento, False), 0),
        'casos_resueltos': casos.get((d.id_documento, True), 0),
        'hechos': {nombre: valores.get(d.id_documento, 0) for nombre, valores in hechos.items()},
    } for d in documentos],
        'nota': 'Una fila puede generar varios hechos: uno por módulo, pregunta o período. '
                'La lectura omite los bloques marcados como ruido. Los casos resueltos no equivalen a filas aprobadas. '
                'Las inscripciones agregadas de marketing no tienen vínculo documental; no se atribuyen a un archivo.'}
