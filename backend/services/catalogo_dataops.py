"""Catálogo de referencia de DataOps: módulos e instituciones, sin consultas de personas."""
import math
import re
from sqlalchemy import func, or_
from models.dim_modulo import DimModulo
from models.catalogos import CatInstitucion
from services.dataops_privacy import texto_publico, _numero_publico


def texto_de_referencia(valor):
    if not isinstance(valor, str):
        return valor
    if re.fullmatch(r'[\d\s()+.\-]+', valor) and len(re.sub(r'\D', '', valor)) >= 5:
        return _numero_publico(valor)
    return texto_publico(valor)


def consultar(db, tipo, page=1, search=''):
    if tipo == 'modulos':
        modelo, sesion = DimModulo, db
        campos = ('id_modulo', 'nombre_modulo', 'pos_code', 'programa', 'nombre_institucion')
        buscar = (DimModulo.nombre_modulo, DimModulo.pos_code, DimModulo.programa, DimModulo.nombre_institucion)
        nombres = ('id', 'nombre', 'codigo', 'programa', 'institucion')
    else:
        modelo, sesion = CatInstitucion, db
        campos = ('id_institucion', 'nombre_institucion', 'sigla', 'tipo_escala_default')
        buscar = (CatInstitucion.nombre_institucion, CatInstitucion.sigla)
        nombres = ('id', 'nombre', 'codigo', 'escala')
    columnas = [getattr(modelo, c) for c in campos]
    q = sesion.query(*columnas)
    if search:
        termino = '%' + search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_').lower() + '%'
        q = q.filter(or_(*(func.lower(c).like(termino, escape='\\') for c in buscar)))
    total = q.count()
    filas = q.order_by(columnas[1], columnas[0]).offset((page - 1) * 5).limit(5).all()
    return {'status': 'success', 'tipo': tipo, 'data': [{k: texto_de_referencia(v) for k, v in zip(nombres, f)} for f in filas],
            'pagination': {'page': page, 'page_size': 5, 'total_items': total,
                           'total_pages': max(1, math.ceil(total / 5))}}
