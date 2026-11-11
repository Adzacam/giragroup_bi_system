"""
backend/routers/cmi.py
----------------------
Cuadro de Mando Integral sobre la capa semántica bi (migración 006).

La SPA y Power BI leen las mismas vistas (bi.vw_cmi_scorecard, bi.vw_cmi_perspectiva,
bi.vw_cmi_global), así que valores, metas y semáforos coinciden en ambos. La configuración
de perspectivas e indicadores se edita aquí y ambos front-ends la reflejan al refrescar.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import require_roles
from models.user import User
from services import cache_consultas

router = APIRouter(prefix="/api/v1/cmi", tags=["Cuadro de Mando Integral"])

TTL_SEG = 60
TODAS = ("FINANCIERA", "CLIENTES", "PROCESOS_INTERNOS", "APRENDIZAJE")

# PoLP (HU-12): perspectivas visibles por rol
VISIBILIDAD: Dict[str, set] = {
    "ADMIN": set(TODAS),
    "DIRECTOR_ACADEMICO": {"CLIENTES", "PROCESOS_INTERNOS", "APRENDIZAJE"},
    "ANALISTA_FINANCIERO": {"FINANCIERA"},
    "ANALISTA_MARKETING": {"CLIENTES"},
    "AUDITOR_CALIDAD": {"PROCESOS_INTERNOS"},
}


def _num(v: Any) -> Any:
    return float(v) if isinstance(v, Decimal) else v


def _filas(db: Session, sql: str, params: Optional[dict] = None) -> List[dict]:
    return [{k: _num(v) for k, v in r.items()} for r in db.execute(text(sql), params or {}).mappings()]


def _scorecard(db: Session, gestion: Optional[int], permitidas: List[str]) -> dict:
    gestiones = [r["gestion"] for r in _filas(db, "SELECT gestion FROM bi.vw_cmi_gestiones ORDER BY gestion")]
    if not gestiones:
        return {"gestion": None, "gestiones": [], "global": None, "perspectivas": []}
    if gestion is None or gestion not in gestiones:
        gestion = gestiones[-1]

    params = {"g": gestion, "p": permitidas}
    perspectivas = _filas(db, """
        SELECT perspectiva AS codigo, nombre, objetivo, pregunta, peso, orden, indicadores,
               verdes, ambar, rojos, sin_evaluar, indice
        FROM bi.vw_cmi_perspectiva
        WHERE gestion = :g AND perspectiva = ANY(:p)
        ORDER BY orden""", params)
    kpis = _filas(db, """
        SELECT perspectiva, codigo, nombre, descripcion, unidad, sentido, valor, valor_anterior,
               delta, meta, umbral_verde, umbral_ambar, peso, semaforo, puntaje, tendencia
        FROM bi.vw_cmi_scorecard
        WHERE gestion = :g AND perspectiva = ANY(:p)
        ORDER BY orden""", params)
    for p in perspectivas:
        p["kpis"] = [k for k in kpis if k["perspectiva"] == p["codigo"]]

    # Índice global sólo sobre las perspectivas visibles para el rol
    con_indice = [p for p in perspectivas if p["indice"] is not None]
    peso_total = sum(p["peso"] for p in con_indice)
    global_ = {
        "indice": round(sum(p["indice"] * p["peso"] for p in con_indice) / peso_total, 1) if peso_total else None,
        **{c: sum(p[c] for p in perspectivas) for c in ("verdes", "ambar", "rojos", "sin_evaluar", "indicadores")},
    }
    return {"gestion": gestion, "gestiones": gestiones, "global": global_, "perspectivas": perspectivas}


@router.get("/scorecard", summary="Scorecard del CMI por perspectiva, con semáforo e índice")
def get_scorecard(
    gestion: Optional[int] = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(list(VISIBILIDAD))),
):
    permitidas = sorted(VISIBILIDAD[user.role])
    return cache_consultas.obtener(
        ("cmi_scorecard", gestion, tuple(permitidas)), TTL_SEG,
        lambda: _scorecard(db, gestion, permitidas),
    )


@router.get("/kpis/{codigo}/historial", summary="Evolución de un indicador por gestión (detalle del scorecard)")
def get_historial_kpi(
    codigo: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(list(VISIBILIDAD))),
):
    permitidas = sorted(VISIBILIDAD[user.role])
    filas = _filas(db, """
        SELECT gestion, perspectiva, nombre, descripcion, unidad, sentido, valor, meta,
               umbral_verde, umbral_ambar, semaforo
        FROM bi.vw_cmi_scorecard
        WHERE codigo = :c AND perspectiva = ANY(:p)
        ORDER BY gestion""", {"c": codigo, "p": permitidas})
    if not filas:
        raise HTTPException(status_code=404, detail="Indicador no encontrado o sin acceso para tu rol.")
    ultima = filas[-1]
    return {
        "codigo": codigo, "nombre": ultima["nombre"], "descripcion": ultima["descripcion"],
        "unidad": ultima["unidad"], "sentido": ultima["sentido"],
        "serie": [{k: f[k] for k in ("gestion", "valor", "meta", "semaforo")} for f in filas],
    }


# ── Configuración (solo ADMIN) ────────────────────────────────────────────────

@router.get("/config", summary="Perspectivas e indicadores configurables del CMI")
def get_config(db: Session = Depends(get_db), _: User = Depends(require_roles(["ADMIN"]))):
    perspectivas = _filas(db, """
        SELECT codigo, nombre, objetivo, pregunta, peso, orden, activa, actualizado_en, actualizado_por
        FROM bi.ref_perspectiva ORDER BY orden""")
    kpis = _filas(db, """
        SELECT codigo, perspectiva, nombre, descripcion, unidad, sentido, meta, umbral_verde,
               umbral_ambar, peso, orden, activo, actualizado_en, actualizado_por
        FROM bi.ref_kpi ORDER BY orden""")
    for p in perspectivas:
        p["kpis"] = [k for k in kpis if k["perspectiva"] == p["codigo"]]
    return {"perspectivas": perspectivas}


class PerspectivaIn(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=80)
    objetivo: str = Field(..., min_length=10, max_length=300)
    pregunta: str = Field(..., min_length=5, max_length=200)
    peso: float = Field(..., ge=0, le=100)
    activa: bool = True


class KpiIn(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=120)
    descripcion: Optional[str] = Field(None, max_length=300)
    meta: Optional[float] = None
    umbral_verde: Optional[float] = None
    umbral_ambar: Optional[float] = None
    peso: float = Field(1, ge=0, le=100)
    activo: bool = True

    @model_validator(mode="after")
    def _ambar_requiere_verde(self):
        if self.umbral_ambar is not None and self.umbral_verde is None:
            raise ValueError("El umbral ámbar requiere un umbral verde.")
        return self


def _actualizar(db: Session, sql: str, params: dict, entidad: str) -> None:
    if db.execute(text(sql), params).rowcount == 0:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{entidad} no encontrada.")
    db.commit()
    cache_consultas.invalidar()


@router.put("/config/perspectivas/{codigo}", summary="Editar una perspectiva del CMI")
def put_perspectiva(codigo: str, body: PerspectivaIn, db: Session = Depends(get_db),
                    user: User = Depends(require_roles(["ADMIN"]))):
    _actualizar(db, """
        UPDATE bi.ref_perspectiva
        SET nombre = :nombre, objetivo = :objetivo, pregunta = :pregunta, peso = :peso,
            activa = :activa, actualizado_en = now(), actualizado_por = :usuario
        WHERE codigo = :codigo""",
        {**body.model_dump(), "codigo": codigo, "usuario": user.username}, "Perspectiva")
    return get_config(db, user)


@router.put("/config/kpis/{codigo}", summary="Editar meta, umbrales y peso de un indicador")
def put_kpi(codigo: str, body: KpiIn, db: Session = Depends(get_db),
            user: User = Depends(require_roles(["ADMIN"]))):
    sentido = db.execute(text("SELECT sentido FROM bi.ref_kpi WHERE codigo = :c"), {"c": codigo}).scalar()
    if sentido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Indicador no encontrado.")
    v, a = body.umbral_verde, body.umbral_ambar
    if v is not None and a is not None and ((sentido == "MAX" and a > v) or (sentido == "MIN" and a < v)):
        regla = "menor o igual" if sentido == "MAX" else "mayor o igual"
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"En un indicador donde {'más' if sentido == 'MAX' else 'menos'} es mejor, "
                            f"el umbral ámbar debe ser {regla} que el verde.")
    _actualizar(db, """
        UPDATE bi.ref_kpi
        SET nombre = :nombre, descripcion = :descripcion, meta = :meta, umbral_verde = :umbral_verde,
            umbral_ambar = :umbral_ambar, peso = :peso, activo = :activo,
            actualizado_en = now(), actualizado_por = :usuario
        WHERE codigo = :codigo""",
        {**body.model_dump(), "codigo": codigo, "usuario": user.username}, "Indicador")
    return get_config(db, user)
