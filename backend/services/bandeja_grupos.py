"""
backend/services/bandeja_grupos.py
----------------------------------
Agrupa los casos pendientes de la bandeja HITL por (motivo, valor normalizado) para aprobarlos de una vez.
- CI_NOMBRE_DISCORDANTE: el CI del caso.  - HOMONIMIA: el nombre sin títulos ni acentos.
- BAJA_CONFIANZA_IA y otros: la forma de la línea (encabezados sin valores, dígitos como '#'); sin encabezados, el texto normalizado.
"""
import re
import unicodedata
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models.fact_financiero import FactSituacionFinanciera
from models.fact_rendimiento import FactRendimientoAcademico
from models.staging_entidad import StagingEntidadNoResuelta


def _sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")


def valor_normalizado(motivo: Optional[str], texto: Optional[str]) -> str:
    t = (texto or "").strip()
    m = (motivo or "").upper()
    if m == "CI_NOMBRE_DISCORDANTE":
        ci = re.search(r"CI:\s*([0-9A-Za-z\-]+)", t)
        return ci.group(1).upper() if ci else _sin_acentos(t).lower()[:80]
    if m == "HOMONIMIA":
        from pipeline.normalization.person_resolver import quitar_titulos
        return quitar_titulos(t)[:80]
    celdas = [c.strip() for c in t.split("|") if c.strip()]
    hdrs = [c.partition(": ")[0] for c in celdas if ": " in c]
    base = " | ".join(hdrs) if hdrs else " | ".join(celdas)
    return re.sub(r"\d+", "#", _sin_acentos(base).lower())[:120]


def clave_grupo(motivo: Optional[str], texto: Optional[str]) -> str:
    return f"{(motivo or '').upper()}::{valor_normalizado(motivo, texto)}"


def grupos_pendientes(db: Session, doc_ids: Optional[List[int]] = None, limite: int = 500) -> Dict[str, Any]:
    """Grupos de casos de staging pendientes: [{clave, motivo, valor, n, ejemplo, ids}] por tamaño; total de casos y de grupos."""
    q = db.query(StagingEntidadNoResuelta.id_staging, StagingEntidadNoResuelta.motivo, StagingEntidadNoResuelta.texto_original).filter(
        StagingEntidadNoResuelta.resuelto == False)  # noqa: E712
    if doc_ids is not None:
        q = q.filter(StagingEntidadNoResuelta.id_documento.in_(list(doc_ids)))
    grupos: Dict[str, Dict[str, Any]] = {}
    n_casos = 0
    for id_stg, motivo, texto in q.order_by(StagingEntidadNoResuelta.id_staging).all():
        n_casos += 1
        k = clave_grupo(motivo, texto)
        g = grupos.setdefault(k, {"clave": k, "motivo": motivo, "valor": valor_normalizado(motivo, texto), "n": 0, "ejemplo": (texto or "")[:160], "ids": []})
        g["n"] += 1
        if len(g["ids"]) < 50:
            g["ids"].append(id_stg)
    for k, g in _grupos_hechos(db, doc_ids).items():
        n_casos += g["n"]
        grupos[k] = g
    ordenados = sorted(grupos.values(), key=lambda g: -g["n"])
    return {"total_casos": n_casos, "total_grupos": len(ordenados), "grupos": ordenados[:limite]}


def motivo_estado(aca, tut, arca) -> str:
    """OK, ESTADO_FUERA_DE_CATALOGO o COMBINACION_INVALIDA según el catálogo vigente de estados de acta."""
    from services.catalogo_estados import reglas_estado
    from pipeline.normalization.quality_rules import canonizar_estado, validar_combinacion_estados
    r = reglas_estado()
    ca, oka = canonizar_estado(aca, r.academicos)
    ct, okt = canonizar_estado(tut, r.tutoria)
    car, okar = canonizar_estado(arca, r.arca)
    if not (oka and okt and okar):
        return "ESTADO_FUERA_DE_CATALOGO"
    return "OK" if validar_combinacion_estados(ca, ct, car, r.combinaciones)[0] else "COMBINACION_INVALIDA"


def _faltan_aca(h) -> str:
    return ",".join(f for f, falta in (("estudiante", not h[2]), ("modulo", not h[3]), ("nota", h[4] is None), ("fecha", not h[5])) if falta) or "ninguno"


def _grupos_hechos(db: Session, doc_ids: Optional[List[int]] = None) -> Dict[str, Dict[str, Any]]:
    """Hechos en revisión agrupados por (área, documento, campos faltantes, estados de acta): un grupo = una misma situación."""
    out: Dict[str, Dict[str, Any]] = {}
    q = db.query(FactRendimientoAcademico.id_hecho_aca, FactRendimientoAcademico.id_documento, FactRendimientoAcademico.id_estudiante,
                 FactRendimientoAcademico.id_modulo, FactRendimientoAcademico.nota_final, FactRendimientoAcademico.id_tiempo,
                 FactRendimientoAcademico.estado_academico, FactRendimientoAcademico.estado_arca,
                 FactRendimientoAcademico.estado_tutoria).filter(
        FactRendimientoAcademico.requiere_revision == True)  # noqa: E712
    if doc_ids is not None:
        q = q.filter(FactRendimientoAcademico.id_documento.in_(list(doc_ids)))
    for h in q.all():
        me = motivo_estado(h[6], h[8], h[7])
        v = f"academico|doc{h[1]}|falta:{_faltan_aca(h)}|{h[6]}|{h[8]}|{h[7]}|estado:{me}"
        accion = ("MAPEAR_ESTADO" if me != "OK" else "APROBAR" if _faltan_aca(h) == "ninguno"
                  else "CORREGIR_FECHA" if _faltan_aca(h) == "fecha" else "MANUAL")
        g = out.setdefault(f"HECHO_EN_REVISION::{v}", {"clave": f"HECHO_EN_REVISION::{v}", "motivo": "HECHO_EN_REVISION", "valor": v, "n": 0,
                                                      "ejemplo": f"HECHO-ACA-{h[0]}", "ids": [], "un_clic": accion == "APROBAR", "accion_grupo": accion})
        g["n"] += 1
        if len(g["ids"]) < 50:
            g["ids"].append(f"HECHO-ACA-{h[0]}")
    q = db.query(FactSituacionFinanciera.id_hecho_fin, FactSituacionFinanciera.id_documento, FactSituacionFinanciera.id_estudiante,
                 FactSituacionFinanciera.id_tiempo, FactSituacionFinanciera.monto_deuda).filter(FactSituacionFinanciera.requiere_revision == True)  # noqa: E712
    if doc_ids is not None:
        q = q.filter(FactSituacionFinanciera.id_documento.in_(list(doc_ids)))
    for h in q.all():
        faltan = ",".join(f for f, falta in (("estudiante", not h[2]), ("fecha", not h[3]), ("monto", h[4] is None)) if falta) or "ninguno"
        v = f"financiero|doc{h[1]}|falta:{faltan}"
        g = out.setdefault(f"HECHO_EN_REVISION::{v}", {"clave": f"HECHO_EN_REVISION::{v}", "motivo": "HECHO_EN_REVISION", "valor": v, "n": 0,
                                                      "ejemplo": f"HECHO-FIN-{h[0]}", "ids": [], "un_clic": faltan == "ninguno",
                                                      "accion_grupo": "APROBAR" if faltan == "ninguno" else "CORREGIR_FECHA" if faltan == "fecha" else "MANUAL"})
        g["n"] += 1
        if len(g["ids"]) < 50:
            g["ids"].append(f"HECHO-FIN-{h[0]}")
    return out


def ids_del_grupo(db: Session, clave: str, doc_ids: Optional[List[int]] = None) -> List[Any]:
    motivo = clave.split("::", 1)[0]
    if motivo == "HECHO_EN_REVISION":
        g = _grupos_hechos(db, doc_ids).get(clave)
        if not g:
            return []
        # los ids del grupo (todos, no solo los 50 de muestra) se recuperan con la misma regla
        return _ids_hechos(db, clave, doc_ids)
    q = db.query(StagingEntidadNoResuelta.id_staging, StagingEntidadNoResuelta.motivo, StagingEntidadNoResuelta.texto_original).filter(
        StagingEntidadNoResuelta.resuelto == False, StagingEntidadNoResuelta.motivo == motivo)  # noqa: E712
    if doc_ids is not None:
        q = q.filter(StagingEntidadNoResuelta.id_documento.in_(list(doc_ids)))
    return [i for i, m, t in q.order_by(StagingEntidadNoResuelta.id_staging).all() if clave_grupo(m, t) == clave]


def _ids_hechos(db: Session, clave: str, doc_ids: Optional[List[int]]) -> List[str]:
    v = clave.split("::", 1)[1]
    ids = []
    if v.startswith("academico"):
        q = db.query(FactRendimientoAcademico.id_hecho_aca, FactRendimientoAcademico.id_documento, FactRendimientoAcademico.id_estudiante,
                     FactRendimientoAcademico.id_modulo, FactRendimientoAcademico.nota_final, FactRendimientoAcademico.id_tiempo,
                     FactRendimientoAcademico.estado_academico, FactRendimientoAcademico.estado_arca,
                     FactRendimientoAcademico.estado_tutoria).filter(FactRendimientoAcademico.requiere_revision == True)  # noqa: E712
        if doc_ids is not None:
            q = q.filter(FactRendimientoAcademico.id_documento.in_(list(doc_ids)))
        ids = [f"HECHO-ACA-{h[0]}" for h in q.all()
               if f"academico|doc{h[1]}|falta:{_faltan_aca(h)}|{h[6]}|{h[8]}|{h[7]}|estado:{motivo_estado(h[6], h[8], h[7])}" == v]
    else:
        q = db.query(FactSituacionFinanciera.id_hecho_fin, FactSituacionFinanciera.id_documento, FactSituacionFinanciera.id_estudiante,
                     FactSituacionFinanciera.id_tiempo, FactSituacionFinanciera.monto_deuda).filter(FactSituacionFinanciera.requiere_revision == True)  # noqa: E712
        if doc_ids is not None:
            q = q.filter(FactSituacionFinanciera.id_documento.in_(list(doc_ids)))
        for h in q.all():
            faltan = ",".join(f for f, falta in (("estudiante", not h[2]), ("fecha", not h[3]), ("monto", h[4] is None)) if falta) or "ninguno"
            if f"financiero|doc{h[1]}|falta:{faltan}" == v:
                ids.append(f"HECHO-FIN-{h[0]}")
    return ids


def mapear_estado_grupo(db: Session, clave: str, doc_ids: Optional[List[int]], canonico: Optional[str] = None) -> Dict[str, Any]:
    """Acción de grupo 'mapear a estado canónico' (grupos de hechos con estado fuera de catálogo o combinación no admitida).
    - COMBINACION_INVALIDA: se agrega la combinación (academico, tutoria, arca) a cat_combinacion_estado.
    - ESTADO_FUERA_DE_CATALOGO: con `canonico` (nombre del estado del catálogo) se reescribe el estado del grupo; sin él, el valor
      se agrega al catálogo cat_estado_* correspondiente.
    Después se invalida la caché del catálogo y se aprueban los hechos del grupo (requiere_revision = False)."""
    from core.database import CatalogSessionLocal
    from models.catalogos import CatCombinacionEstado, CatEstadoAcademico, CatEstadoArca, CatEstadoReprobado
    from services.catalogo_estados import invalidar_cache
    partes = clave.split("::", 1)[1].split("|")
    aca, tut, arca, motivo = partes[3], partes[4], partes[5], partes[6].split(":", 1)[1]
    ids = [int(i.replace("HECHO-ACA-", "")) for i in _ids_hechos(db, clave, doc_ids)]
    if motivo == "OK" or not ids:
        return {"mapeados": 0, "motivo": motivo}
    cdb = CatalogSessionLocal()
    try:
        def _id(modelo, col_id, col_nom, valor, crear):
            fila = cdb.query(modelo).filter(getattr(modelo, col_nom) == valor).first()
            if fila is None and crear:
                fila = modelo(**{col_nom: valor})
                cdb.add(fila)
                cdb.flush()
            return getattr(fila, col_id) if fila is not None else None
        if motivo == "COMBINACION_INVALIDA":
            ia = _id(CatEstadoAcademico, "id_estado_academico", "nombre_estado", aca, False)
            it = _id(CatEstadoReprobado, "id_estado_reprobado", "nombre_detalle", tut, False)
            ir = _id(CatEstadoArca, "id_estado_arca", "nombre_arca", arca, False)
            existe = cdb.query(CatCombinacionEstado).filter_by(id_estado_academico=ia, id_estado_reprobado=it, id_estado_arca=ir).first()
            if existe is None:
                cdb.add(CatCombinacionEstado(id_estado_academico=ia, id_estado_reprobado=it, id_estado_arca=ir, activo=True))
            elif not existe.activo:
                existe.activo = True
            accion = f"combinación ({aca}, {tut}, {arca}) agregada a cat_combinacion_estado"
        else:
            campos = (("estado_academico", aca, CatEstadoAcademico, "id_estado_academico", "nombre_estado"),
                      ("estado_tutoria", tut, CatEstadoReprobado, "id_estado_reprobado", "nombre_detalle"),
                      ("estado_arca", arca, CatEstadoArca, "id_estado_arca", "nombre_arca"))
            accion = []
            for campo, valor, modelo, cid, cnom in campos:
                if valor and cdb.query(modelo).filter(getattr(modelo, cnom) == valor).first() is None:
                    if canonico:
                        db.query(FactRendimientoAcademico).filter(FactRendimientoAcademico.id_hecho_aca.in_(ids)).update(
                            {campo: canonico}, synchronize_session=False)
                        accion.append(f"{campo}: '{valor}' -> '{canonico}'")
                    else:
                        cdb.add(modelo(**{cnom: valor}))
                        accion.append(f"'{valor}' agregado a catálogo de {campo}")
            accion = "; ".join(accion)
        cdb.commit()
    finally:
        cdb.close()
    invalidar_cache()
    db.query(FactRendimientoAcademico).filter(FactRendimientoAcademico.id_hecho_aca.in_(ids)).update(
        {"requiere_revision": False}, synchronize_session=False)
    db.commit()
    return {"mapeados": len(ids), "motivo": motivo, "accion": accion}
