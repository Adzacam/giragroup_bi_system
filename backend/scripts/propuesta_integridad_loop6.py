"""Genera una propuesta reproducible, sin datos personales ni escrituras.

Uso en el contenedor: python -m scripts.propuesta_integridad_loop6
Los identificadores corresponden exclusivamente a la auditoría del loop 6.
"""
import hashlib
import json
from sqlalchemy import text
from core.database import SessionLocal
from services.extraccion_por_encabezado import campos_por_encabezado, _parsear_fecha_cruda


def generar(db):
    documento = db.execute(text('SELECT id_documento, hash_sha256 FROM dim_origen_documental WHERE id_documento=19')).mappings().one()
    edades = []
    for bloque in db.execute(text('SELECT id, texto_plano FROM staging_registros_crudos WHERE id_documento=19 AND registro_origen_id IS NULL ORDER BY id')).mappings():
        for numero, linea in enumerate((bloque['texto_plano'] or '').splitlines(), 1):
            campos = campos_por_encabezado([c.strip() for c in linea.split('|')])
            try:
                edad = float(campos.get('EDAD L', ''))
            except ValueError:
                continue
            if edad <= 100:
                continue
            edades.append({'staging_id': bloque['id'], 'linea_en_bloque': numero,
                'huella_fila': hashlib.sha256(linea.encode('utf-8')).hexdigest(),
                'edad_original': edad, 'edad_propuesta_en_copia': None,
                'nacimiento_interpretable': _parsear_fecha_cruda(campos.get('FECHA NACIMIENTO')) is not None})
    modulos = [dict(r) for r in db.execute(text("SELECT id_modulo,nombre_modulo,pos_code FROM dim_modulo WHERE id_modulo IN (4937,4957) ORDER BY id_modulo")).mappings()]
    for m in modulos:
        m['propuesto'] = {'nombre_modulo': f"Programa por identificar ({m['id_modulo']})", 'pos_code': None}
        m['inscripciones_conservadas'] = [dict(r) for r in db.execute(text('SELECT id_hecho_mkt, inscritos FROM fact_marketing WHERE id_modulo=:id ORDER BY id_hecho_mkt'), {'id': m['id_modulo']}).mappings()]
    convenio = dict(db.execute(text('SELECT id_hecho_techo,id_documento,id_tiempo,gestion,fecha_inicio,fecha_fin,requiere_revision,motivo_revision FROM fact_techo_convenio WHERE id_hecho_techo=25')).mappings().one())
    convenio['propuesto'] = {'fecha_inicio': None, 'id_tiempo': None,
        'requiere_revision': True, 'motivo_revision': 'FECHA_INICIO_PENDIENTE: confirmar contra el convenio original; fecha recibida 2034-01-12'}
    return {'estado': 'PROPUESTA_SIN_APLICAR', 'documento_admision': dict(documento),
        'documentos_mismo_archivo': list(db.execute(text('SELECT id_documento FROM dim_origen_documental WHERE hash_sha256=:h ORDER BY id_documento'), {'h': documento['hash_sha256']}).scalars()),
        'edades': {'accion': 'Crear una copia de corrección, conservar el original y dejar vacía la edad sin nacimiento comprobable. No actualizar dim_estudiante.', 'filas': edades},
        'modulos': modulos, 'convenio': convenio,
        'resguardo': 'Antes de aplicar: respaldo de filas afectadas, comparación de valores y huellas, transacción, auditoría y verificación de conteos. Sin fusiones ni borrados.',
        'reconstruccion_inscripciones': 'Preparar en base aislada una reconstrucción por huella, hoja y fila de la fuente única. Comparar antes de proponer reemplazo; no dividir ni deduplicar agregados por suposición.'}


def main():
    with SessionLocal() as db:
        db.execute(text('SET TRANSACTION READ ONLY'))
        try:
            print(json.dumps(generar(db), ensure_ascii=False, indent=2, default=str))
        finally:
            db.rollback()


if __name__ == '__main__':
    main()
