"""Catálogo de referencia de DataOps: módulos e instituciones, sin consultas de personas."""
import math
import re
from typing import Any, Dict, List, Optional
from sqlalchemy import exists, func, or_, select
from models.dim_modulo import DimModulo
from models.catalogos import CatInstitucion, CatInstitucionConvenio
from models.dim_estudiante import DimEstudiante
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from models.fact_marketing import FactMarketing
from models.fact_rentabilidad import FactRentabilidad
from models.fact_planificacion import FactPlanificacionPrograma
from models.fact_costo_programa import FactCostoPrograma
from models.fact_techo_convenio import FactTechoConvenio
from models.bridge_modulo_docente import BridgeModuloDocente
from models.staging_entidad import StagingEntidadNoResuelta
from services.dataops_privacy import texto_publico, _numero_publico

PAGE_SIZE = 20

try:
    from models.fact_evaluacion import FactEvaluacionDocente
except Exception:
    FactEvaluacionDocente = None

_TABLAS_USO_MODULO = [
    m for m in (
        FactRendimientoAcademico,
        FactEvaluacionDocente,
        FactSituacionFinanciera,
        FactMarketing,
        FactRentabilidad,
        FactPlanificacionPrograma,
        FactCostoPrograma,
        FactTechoConvenio,
        BridgeModuloDocente,
    )
    if m is not None
]


def texto_de_referencia(valor):
    if not isinstance(valor, str):
        return valor
    if re.fullmatch(r'[\d\s()+.\-]+', valor) and len(re.sub(r'\D', '', valor)) >= 5:
        return _numero_publico(valor)
    return texto_publico(valor)


def _filtro_en_uso():
    return or_(*(exists(select(1).where(m.id_modulo == DimModulo.id_modulo)) for m in _TABLAS_USO_MODULO))


def _filtro_sin_referencias():
    conds = [~exists(select(1).where(m.id_modulo == DimModulo.id_modulo)) for m in _TABLAS_USO_MODULO]
    conds.append(
        ~exists(
            select(1).where(
                StagingEntidadNoResuelta.tipo_entidad == "MODULO",
                StagingEntidadNoResuelta.id_dimension_resuelta == DimModulo.id_modulo,
            )
        )
    )
    return conds


def _contar_uso_por_modulos(db, ids: List[int]) -> Dict[int, int]:
    conteos = {i: 0 for i in ids}
    if not ids:
        return conteos
    for m in _TABLAS_USO_MODULO:
        try:
            filas = db.query(m.id_modulo, func.count()).filter(m.id_modulo.in_(ids)).group_by(m.id_modulo).all()
            for id_mod, n in filas:
                if id_mod in conteos:
                    conteos[id_mod] += int(n or 0)
        except Exception:
            pass
    return conteos


def _sigla_convenio(nombre: str) -> str:
    palabras = [p for p in re.findall(r"[A-Za-z0-9]+", nombre or "") if p.upper() not in ("S", "R", "L", "SRL", "SA", "LTDA")]
    if len(palabras) == 1 and len(palabras[0]) <= 8:
        return palabras[0].upper()
    return ""


def _consultar_modulos(
    db,
    page: int,
    search: str,
    solo_genericos: bool = False,
    sin_programa: bool = False,
    uso: str = "todos",
) -> Dict[str, Any]:
    q = db.query(
        DimModulo.id_modulo,
        DimModulo.nombre_modulo,
        DimModulo.pos_code,
        DimModulo.programa,
        DimModulo.nombre_institucion,
    )
    if search:
        termino = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_").lower() + "%"
        q = q.filter(
            or_(
                func.lower(DimModulo.nombre_modulo).like(termino, escape="\\"),
                func.lower(DimModulo.pos_code).like(termino, escape="\\"),
                func.lower(DimModulo.programa).like(termino, escape="\\"),
                func.lower(DimModulo.nombre_institucion).like(termino, escape="\\"),
            )
        )
    if solo_genericos:
        q = q.filter(or_(DimModulo.pos_code == "MOD-GEN", DimModulo.pos_code.like("%-GEN")))
    if sin_programa:
        q = q.filter(
            or_(
                DimModulo.programa.is_(None),
                func.trim(DimModulo.programa) == "",
                func.lower(func.trim(DimModulo.programa)) == "sin dato",
            )
        )
    if uso == "en_uso":
        q = q.filter(_filtro_en_uso())
    elif uso == "sin_uso":
        q = q.filter(~_filtro_en_uso())

    total = q.count()
    filas = q.order_by(DimModulo.nombre_modulo, DimModulo.id_modulo).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    ids = [f[0] for f in filas]
    usos = _contar_uso_por_modulos(db, ids)
    total_sin_uso = db.query(func.count(DimModulo.id_modulo)).filter(*_filtro_sin_referencias()).scalar() or 0

    data = []
    for id_mod, nom, cod, prog, inst in filas:
        data.append({
            "id": id_mod,
            "nombre": texto_de_referencia(nom),
            "codigo": texto_de_referencia(cod),
            "programa": texto_de_referencia(prog),
            "institucion": texto_de_referencia(inst),
            "en_uso": usos.get(id_mod, 0),
        })

    return {
        "status": "success",
        "tipo": "modulos",
        "data": data,
        "resumen": {"total_sin_uso": int(total_sin_uso)},
        "pagination": {
            "page": page,
            "page_size": PAGE_SIZE,
            "total_items": total,
            "total_pages": max(1, math.ceil(total / PAGE_SIZE)),
        },
    }


def _consultar_instituciones(
    db,
    page: int,
    search: str,
    grupo: str = "todos",
    db_catalog=None,
) -> Dict[str, Any]:
    termino = search.strip().lower()
    items_propia: List[Dict[str, Any]] = []
    items_convenio: List[Dict[str, Any]] = []

    # 1. Grupo "Propia" (cat_institucion en giragroup_db)
    for c in db.query(CatInstitucion).order_by(CatInstitucion.id_institucion).all():
        if termino and termino not in (c.nombre_institucion or "").lower() and termino not in (c.sigla or "").lower():
            continue
        n_mods = db.query(func.count(DimModulo.id_modulo)).filter(DimModulo.id_institucion == c.id_institucion).scalar() or 0
        n_ests = db.query(func.count(DimEstudiante.id_estudiante)).filter(DimEstudiante.id_institucion == c.id_institucion).scalar() or 0
        items_propia.append({
            "id": c.id_institucion,
            "grupo": "propia",
            "nombre": texto_de_referencia(c.nombre_institucion),
            "codigo": texto_de_referencia(c.sigla),
            "escala": c.tipo_escala_default,
            "n_programas": int(n_mods),
            "n_inscritos": int(n_ests),
            "anios": [],
        })

    # 2. Grupo "Convenio" (cat_institucion_convenio en giragroup_catalog_db + estadísticas de fact_techo_convenio)
    stats_por_conv: Dict[int, Dict[str, Any]] = {}
    stats_por_nombre: Dict[str, Dict[str, Any]] = {}
    try:
        hechos = db.query(
            FactTechoConvenio.id_convenio_catalogo,
            FactTechoConvenio.institucion,
            FactTechoConvenio.id_modulo,
            FactTechoConvenio.n_inscritos,
            FactTechoConvenio.gestion,
        ).all()
        for id_conv, inst_nom, id_mod, n_ins, gestion in hechos:
            for mapa, clave in ((stats_por_conv, id_conv), (stats_por_nombre, (inst_nom or "").strip().upper())):
                if clave is None or clave == "":
                    continue
                st = mapa.setdefault(clave, {"mods": set(), "inscritos": 0, "anios": set()})
                if id_mod:
                    st["mods"].add(id_mod)
                if n_ins:
                    st["inscritos"] += int(n_ins)
                if gestion:
                    st["anios"].add(int(gestion))
    except Exception:
        pass

    session_cat = db_catalog
    cerrar_cat = False
    if session_cat is None:
        try:
            from core.database import CatalogSessionLocal
            session_cat = CatalogSessionLocal()
            cerrar_cat = True
        except Exception:
            session_cat = None

    if session_cat is not None:
        try:
            for conv in session_cat.query(CatInstitucionConvenio).order_by(CatInstitucionConvenio.nombre_institucion).all():
                sigla = _sigla_convenio(conv.nombre_institucion)
                if termino and (
                    termino not in (conv.nombre_institucion or "").lower()
                    and termino not in sigla.lower()
                    and termino not in (conv.variantes_origen or "").lower()
                ):
                    continue
                st = stats_por_conv.get(conv.id_convenio) or stats_por_nombre.get((conv.nombre_institucion or "").strip().upper()) or {}
                items_convenio.append({
                    "id": f"conv-{conv.id_convenio}",
                    "id_convenio": conv.id_convenio,
                    "grupo": "convenio",
                    "nombre": texto_de_referencia(conv.nombre_institucion),
                    "codigo": sigla or None,
                    "escala": None,
                    "n_programas": len(st.get("mods", ())),
                    "n_inscritos": int(st.get("inscritos", 0)),
                    "anios": sorted(st.get("anios", ())),
                    "variantes": conv.variantes_origen,
                })
        except Exception:
            pass
        finally:
            if cerrar_cat:
                session_cat.close()

    if grupo == "propia":
        combinado = items_propia
    elif grupo == "convenio":
        combinado = items_convenio
    else:
        combinado = items_propia + items_convenio

    total = len(combinado)
    inicio = (page - 1) * PAGE_SIZE
    pagina_items = combinado[inicio:inicio + PAGE_SIZE]

    return {
        "status": "success",
        "tipo": "instituciones",
        "data": pagina_items,
        "grupos": {
            "propia": len(items_propia),
            "convenio": len(items_convenio),
        },
        "pagination": {
            "page": page,
            "page_size": PAGE_SIZE,
            "total_items": total,
            "total_pages": max(1, math.ceil(total / PAGE_SIZE)),
        },
    }


def consultar(
    db,
    tipo: str,
    page: int = 1,
    search: str = "",
    solo_genericos: bool = False,
    sin_programa: bool = False,
    uso: str = "todos",
    grupo: str = "todos",
    db_catalog=None,
) -> Dict[str, Any]:
    if tipo == "modulos":
        return _consultar_modulos(
            db,
            page=page,
            search=search,
            solo_genericos=solo_genericos,
            sin_programa=sin_programa,
            uso=uso,
        )
    return _consultar_instituciones(db, page=page, search=search, grupo=grupo, db_catalog=db_catalog)


def preview_modulos_sin_uso(db, limite: int = 25) -> Dict[str, Any]:
    q = db.query(DimModulo).filter(*_filtro_sin_referencias())
    total = q.count()
    filas = q.order_by(DimModulo.id_modulo).limit(limite).all()
    return {
        "status": "success",
        "total_sin_uso": total,
        "muestra": [
            {
                "id": m.id_modulo,
                "nombre": texto_de_referencia(m.nombre_modulo),
                "codigo": texto_de_referencia(m.pos_code),
                "programa": texto_de_referencia(m.programa),
            }
            for m in filas
        ],
    }


def limpiar_modulos_sin_uso(db) -> int:
    q = db.query(DimModulo).filter(*_filtro_sin_referencias())
    eliminados = q.delete(synchronize_session=False)
    db.commit()
    return int(eliminados or 0)
