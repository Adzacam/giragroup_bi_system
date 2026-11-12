"""Selección y paginación de una evaluación existente, sin inferencia ni escritura."""
from services.dataops_evaluation_service import calcular_porcentajes_mayor_residuo, strip_accents


def seleccionar_documento(evaluacion, doc_id=None):
    if doc_id is None:
        return evaluacion
    detalles = [r for r in evaluacion['detalles'] if r.get('id_documento') == doc_id]
    auto = sum(r.get('categoria_particion') == 'AUTOMATICO' for r in detalles)
    revision = sum(r.get('categoria_particion') == 'REVISION' for r in detalles)
    incidencias = sum(r.get('categoria_particion') == 'INCONSISTENCIA' for r in detalles)
    a, b, c = calcular_porcentajes_mayor_residuo(auto, revision, incidencias)
    indices = [r['indice_registro'] for r in detalles if isinstance(r.get('indice_registro'), (int, float))]
    return {**evaluacion, 'detalles': detalles, 'totalTuplas': len(detalles),
            'totalEntidades': sum(len(r.get('lectura', {}).get('entidades', [])) for r in detalles),
            'autoCount': auto, 'auditCount': revision, 'inconsistenciasCount': incidencias,
            'autoPct': a, 'auditPct': b, 'inconsistenciasPct': c,
            'indiceMedio': round(sum(indices) / len(indices), 2) if indices else None}


def coincide_entidad(registro, tipo):
    alias = {'ESTUDIANTE': ('ESTUDIANTE', 'ALUMNO', 'DOCUMENTO / CI'),
             'MODULO': ('MODULO',), 'DOCENTE': ('DOCENTE',),
             'CALIFICACION': ('CALIFICACION', 'NOTA'), 'MONTO': ('MONTO', 'CUOTA', 'CONCEPTO'),
             'ASISTENCIA': ('ASISTENCIA',)}
    tipos = alias.get(tipo.upper(), (tipo.upper(),))
    return any(any(t in strip_accents(str(e.get('label', ''))).upper() for t in tipos)
               for e in registro.get('lectura', {}).get('entidades', []))
