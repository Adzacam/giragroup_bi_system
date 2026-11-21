"""
backend/routers/cmi.py
----------------------
Cuadro de Mando Integral sobre la capa semántica bi (migración 006).

La SPA y los endpoints del CMI leen las mismas vistas (bi.vw_cmi_scorecard, bi.vw_cmi_perspectiva,
bi.vw_cmi_global), así que valores, metas y semáforos coinciden en toda la plataforma. La configuración
de perspectivas e indicadores se edita aquí y el tablero la refleja al refrescar.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import require_roles
from models.user import User
from services import cache_consultas, captacion_cobertura
from services.cmi_personalizacion_service import (
    ejecutar_consulta_medida,
    evaluar_kpi_personalizado,
)

router = APIRouter(prefix="/api/v1/cmi", tags=["Cuadro de Mando Integral"])
logger = logging.getLogger("cmi_router")

TTL_SEG = 60
TODAS = ("FINANCIERA", "CLIENTES", "PROCESOS_INTERNOS", "APRENDIZAJE")

FALTANTES = {
    'KPI-06': 'No hay cifras comprobables de interesados e inscritos en una misma fuente de captación para esta gestión.',
    'KPI-07': 'No hay calificaciones con fecha de esta gestión para calcular el promedio.',
    'KPI-08': 'No hay calificaciones con fecha de esta gestión para calcular la aprobación.',
    'KPI-10': 'No hay registros académicos con índice de confianza y fecha de esta gestión.',
    'KPI-11': 'No hay registros académicos con índice de confianza y fecha de esta gestión.',
    'KPI-16': 'No hay registros académicos con fecha de esta gestión para calcular este indicador.',
    'KPI-21': 'No hay estudiantes vinculados a registros académicos con fecha de esta gestión.',
    'KPI-22': 'No hay cifras de inscritos en convenios vinculados a esta gestión.',
    'KPI-23': 'No hay registros de planificación con estado conocido en esta gestión.',
}

# PoLP (HU-12): perspectivas visibles por rol
VISIBILIDAD: Dict[str, set] = {
    "ADMIN": set(TODAS),
    "DIRECTOR_ACADEMICO": {"CLIENTES", "PROCESOS_INTERNOS", "APRENDIZAJE"},
    "ANALISTA_FINANCIERO": {"FINANCIERA"},
    "ANALISTA_MARKETING": {"CLIENTES"},
    "AUDITOR_CALIDAD": {"PROCESOS_INTERNOS"},
}

ROLES_CONFIG = ["ADMIN", "ANALISTA_FINANCIERO", "ANALISTA_MARKETING"]


def _plantillas_captacion() -> dict:
    """Textos del motivo «sin dato» del KPI-06 (editables en config/mapeo_fuentes.yaml, sección captacion)."""
    try:
        from pipeline.lector_hojas import cargar_config
        return (cargar_config().get("captacion") or {}).get("motivos_sin_dato") or {}
    except Exception:  # sin catálogo se usan los textos por defecto
        return {}


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
    captacion = None   # FU-L3: se lee una sola vez y solo si el KPI-06 se muestra
    for p in perspectivas:
        p["kpis"] = [k for k in kpis if k["perspectiva"] == p["codigo"]]
        for k in p['kpis']:
            k['motivo_sin_dato'] = FALTANTES.get(k['codigo']) if k['valor'] is None else None
            if k['codigo'] == 'KPI-06':
                if captacion is None:
                    captacion = captacion_cobertura.por_mes(db)
                cob = captacion_cobertura.cobertura(captacion).get(gestion)
                # Cobertura mensual de la gestión (meses con dato de los 12) y, sin dato, desde qué mes hay datos
                k['cobertura'] = ({"meses_con_dato": cob["meses_con_dato"], "meses_gestion": cob["meses_gestion"],
                                   "desde": cob["desde"], "hasta": cob["hasta"]} if cob else
                                  {"meses_con_dato": 0, "meses_gestion": captacion_cobertura.MESES_GESTION,
                                   "desde": None, "hasta": None})
                if k['valor'] is None:
                    k['motivo_sin_dato'] = captacion_cobertura.motivo_sin_dato(
                        captacion, gestion, _plantillas_captacion())

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


def _resumen(db: Session, permitidas: List[str]) -> dict:
    gestiones = [r["gestion"] for r in _filas(db, "SELECT gestion FROM bi.vw_cmi_gestiones ORDER BY gestion")]
    if not gestiones:
        return {"gestiones": [], "global_por_gestion": [], "perspectivas_por_gestion": []}

    persp = _filas(db, """
        SELECT gestion, perspectiva AS codigo, nombre, peso, orden, indicadores,
               verdes, ambar, rojos, sin_evaluar, indice
        FROM bi.vw_cmi_perspectiva
        WHERE perspectiva = ANY(:p)
        ORDER BY gestion, orden""", {"p": permitidas})

    # Si ve todas las perspectivas, leer directamente bi.vw_cmi_global; si no, ponderar sobre permitidas
    if len(permitidas) == len(TODAS):
        glob = _filas(db, """
            SELECT gestion, indice, verdes, ambar, rojos, sin_evaluar
            FROM bi.vw_cmi_global
            WHERE gestion = ANY(:gs)
            ORDER BY gestion""", {"gs": gestiones})
    else:
        glob = []
        for g in gestiones:
            pg = [x for x in persp if x["gestion"] == g]
            con_ind = [x for x in pg if x["indice"] is not None]
            pt = sum(x["peso"] for x in con_ind)
            glob.append({
                "gestion": g,
                "indice": round(sum(x["indice"] * x["peso"] for x in con_ind) / pt, 1) if pt else None,
                **{c: sum(x[c] for x in pg) for c in ("verdes", "ambar", "rojos", "sin_evaluar")},
            })

    return {
        "gestiones": gestiones,
        "global_por_gestion": glob,
        "perspectivas_por_gestion": persp,
    }


@router.get("/resumen", summary="Serie histórica del índice global y por perspectiva (todas las gestiones)")
def get_resumen(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(list(VISIBILIDAD))),
):
    permitidas = sorted(VISIBILIDAD[user.role])
    return cache_consultas.obtener(
        ("cmi_resumen", tuple(permitidas)), TTL_SEG,
        lambda: _resumen(db, permitidas),
    )


def _detalle_perspectiva(db: Session, codigo: str, gestion: Optional[int]) -> dict:
    gestiones = [r["gestion"] for r in _filas(db, "SELECT gestion FROM bi.vw_cmi_gestiones ORDER BY gestion")]
    if gestion is None or (gestiones and gestion not in gestiones):
        gestion = gestiones[-1] if gestiones else None

    series: Dict[str, Any] = {}
    avisos: List[str] = []

    def serie(clave: str, sql: str, params: Optional[dict] = None) -> None:
        """Una serie que falla no tumba el desglose: se registra y se avisa al usuario."""
        try:
            series[clave] = _filas(db, sql, params)
        except SQLAlchemyError:
            logger.exception("CMI detalle %s: falló la serie «%s»", codigo, clave)
            db.rollback()
            series[clave] = []
            avisos.append(f"La serie «{clave}» no está disponible por un error interno; ya quedó registrado.")

    if codigo == "FINANCIERA" and gestion is not None:
        serie("metas_mensual", """
            SELECT mes, nombre_mes, categoria, ejecutado, meta, avance_pct, ejecutado_anio_ant
            FROM bi.vw_metas_mensual
            WHERE gestion = :g
            ORDER BY mes, categoria""", {"g": gestion})
        serie("cartera_estado", """
            SELECT estado_cartera, n_estudiantes, deuda_bs, pagado_bs, cuotas_impagas
            FROM bi.vw_cartera_estado
            WHERE gestion = :g
            ORDER BY deuda_bs DESC""", {"g": gestion})
    elif codigo == "CLIENTES" and gestion is not None:
        serie("inscritos_programa", """
            SELECT COALESCE(m.nombre_modulo, 'Sin nombre') AS programa, SUM(f.inscritos) AS inscritos
            FROM public.fact_marketing f
            JOIN public.dim_modulo m ON m.id_modulo = f.id_modulo
            JOIN public.dim_tiempo t ON t.id_tiempo = f.id_tiempo
            WHERE t.gestion = :g
            GROUP BY 1
            HAVING SUM(f.inscritos) > 0
            ORDER BY inscritos DESC
            LIMIT 12""", {"g": gestion})
        # FU-L3 (DA6): captación por mes y cobertura de la gestión (leads e inscritos de un mismo programa y mes)
        todos_los_meses = captacion_cobertura.por_mes(db)
        series["captacion_mensual"] = [m for m in todos_los_meses if m["gestion"] == gestion]
        cob = captacion_cobertura.cobertura(todos_los_meses).get(gestion)
        series["captacion_cobertura"] = [cob] if cob else []
        if not cob:
            avisos.append(captacion_cobertura.motivo_sin_dato(todos_los_meses, gestion, _plantillas_captacion()))
        elif cob["meses_con_dato"] < cob["meses_gestion"]:
            avisos.append(f"Conversión de captación con dato en {cob['meses_con_dato']} de {cob['meses_gestion']} meses "
                          f"de la gestión ({cob['desde']} a {cob['hasta']}).")
    elif codigo == "PROCESOS_INTERNOS":
        serie("dataops_documento", """
            SELECT tipo_fuente, COUNT(*) AS documentos, COALESCE(SUM(registros), 0) AS registros,
                   ROUND(AVG(confianza_media_pct)::numeric, 1) AS confianza_media_pct,
                   COALESCE(SUM(consolidado_directo), 0) AS consolidado_directo,
                   COALESCE(SUM(revision_hitl), 0) AS revision_hitl,
                   COALESCE(SUM(pendientes_revision), 0) AS pendientes_revision
            FROM bi.vw_dataops_documento
            GROUP BY tipo_fuente
            ORDER BY registros DESC""")
    elif codigo == "APRENDIZAJE" and gestion is not None:
        serie("riesgo_estudiante", """
            SELECT nivel_prioridad, COUNT(*) AS estudiantes,
                   ROUND(AVG(prom_notas)::numeric, 1) AS promedio_notas,
                   COALESCE(SUM(total_cuotas_impagas), 0) AS cuotas_impagas
            FROM bi.vw_riesgo_estudiante
            WHERE gestion = :g
            GROUP BY nivel_prioridad
            ORDER BY estudiantes DESC""", {"g": gestion})

    kpis_pers: List[dict] = []
    graficos_pers: List[dict] = []
    try:
        medidas = {m["codigo"]: m for m in _filas(db, "SELECT * FROM app.medida_catalogo WHERE activo = TRUE")}
        for k in _filas(db, """
            SELECT codigo, perspectiva, nombre, descripcion, medida_codigo, agregacion,
                   unidad, sentido, meta, umbral_verde, umbral_ambar, estado
            FROM app.kpi_personalizado
            WHERE perspectiva = :p AND estado = 'ACTIVO'
            ORDER BY codigo""", {"p": codigo}):
            med = medidas.get(k["medida_codigo"])
            if med:
                kpis_pers.append(evaluar_kpi_personalizado(db, k, med))
        for g in _filas(db, """
            SELECT id, perspectiva, titulo, medida_codigo, dimension_codigo, agregacion, tipo_grafico, orden
            FROM app.grafico_personalizado
            WHERE perspectiva = :p AND visible = TRUE
            ORDER BY orden, id""", {"p": codigo}):
            med = medidas.get(g["medida_codigo"])
            if med:
                datos = ejecutar_consulta_medida(db, med, g["dimension_codigo"], g["agregacion"])
                graficos_pers.append({**g, "datos": datos})
    except Exception:  # KPP y gráficas son opcionales: se registra y se avisa, no se tumba el desglose
        logger.exception("CMI detalle %s: fallaron los KPP o las gráficas personalizadas", codigo)
        db.rollback()
        avisos.append("Los indicadores o gráficas personalizados no están disponibles por un error interno; ya quedó registrado.")

    return {
        "codigo": codigo,
        "gestion": gestion,
        "series": series,
        "kpis_personalizados": kpis_pers,
        "graficos_personalizados": graficos_pers,
        "avisos": avisos,
    }


@router.get("/perspectivas/{codigo}/detalle", summary="Series analíticas sin PII para el desglose de una perspectiva")
def get_detalle_perspectiva(
    codigo: str,
    gestion: Optional[int] = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(list(VISIBILIDAD))),
):
    if codigo not in TODAS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Perspectiva no encontrada.")
    if codigo not in VISIBILIDAD[user.role]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a esta perspectiva.")
    return cache_consultas.obtener(
        ("cmi_persp_detalle", codigo, gestion), TTL_SEG,
        lambda: _detalle_perspectiva(db, codigo, gestion),
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


# ── Configuración (ADMIN + ANALISTA_FINANCIERO / ANALISTA_MARKETING por perspectiva) ──

def _exigir_perspectiva_visible(user: User, perspectiva: str) -> None:
    if perspectiva not in VISIBILIDAD.get(user.role, set()):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para modificar indicadores de esta perspectiva.")


@router.get("/config", summary="Perspectivas, indicadores, KPP y gráficas configurables del CMI")
def get_config(db: Session = Depends(get_db), user: User = Depends(require_roles(ROLES_CONFIG))):
    permitidas = sorted(VISIBILIDAD[user.role])
    perspectivas = _filas(db, """
        SELECT codigo, nombre, objetivo, pregunta, peso, orden, activa, actualizado_en, actualizado_por
        FROM bi.ref_perspectiva
        WHERE codigo = ANY(:p)
        ORDER BY orden""", {"p": permitidas})
    kpis = _filas(db, """
        SELECT codigo, perspectiva, nombre, descripcion, unidad, sentido, meta, umbral_verde,
               umbral_ambar, peso, orden, activo, actualizado_en, actualizado_por
        FROM bi.ref_kpi
        WHERE perspectiva = ANY(:p)
        ORDER BY orden""", {"p": permitidas})
    for p in perspectivas:
        p["kpis"] = [k for k in kpis if k["perspectiva"] == p["codigo"]]

    catalogo_medidas, kpis_pers, graficos_pers = [], [], []
    try:
        catalogo_medidas = _filas(db, """
            SELECT codigo, nombre, perspectiva, origen_schema, origen_tabla, columna_medida,
                   agregaciones_permitidas, dimensiones_permitidas, unidad, descripcion
            FROM app.medida_catalogo
            WHERE activo = TRUE AND perspectiva = ANY(:p)
            ORDER BY perspectiva, codigo""", {"p": permitidas})
        kpis_pers = _filas(db, """
            SELECT codigo, perspectiva, nombre, descripcion, medida_codigo, agregacion,
                   unidad, sentido, meta, umbral_verde, umbral_ambar, estado,
                   creado_por, creado_en, actualizado_por, actualizado_en
            FROM app.kpi_personalizado
            WHERE perspectiva = ANY(:p)
            ORDER BY codigo""", {"p": permitidas})
        graficos_pers = _filas(db, """
            SELECT id, perspectiva, titulo, medida_codigo, dimension_codigo, agregacion,
                   tipo_grafico, orden, visible, creado_por, creado_en, actualizado_por, actualizado_en
            FROM app.grafico_personalizado
            WHERE perspectiva = ANY(:p)
            ORDER BY orden, id""", {"p": permitidas})
    except Exception:
        logger.exception("CMI config: fallaron las medidas, KPP o gráficas personalizadas")
        db.rollback()

    return {
        "puede_editar_perspectivas": user.role == "ADMIN",
        "perspectivas": perspectivas,
        "catalogo_medidas": catalogo_medidas,
        "kpis_personalizados": kpis_pers,
        "graficos_personalizados": graficos_pers,
    }


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


class KpiPersonalizadoIn(BaseModel):
    perspectiva: str = Field(..., min_length=3, max_length=30)
    nombre: str = Field(..., min_length=3, max_length=120)
    descripcion: Optional[str] = Field(None, max_length=300)
    medida_codigo: str = Field(..., min_length=3, max_length=40)
    agregacion: str = Field("SUM", pattern="^(SUM|AVG|COUNT|COUNT_DISTINCT|MIN|MAX)$")
    sentido: str = Field("MAX", pattern="^(MAX|MIN)$")
    meta: Optional[float] = None
    umbral_verde: Optional[float] = None
    umbral_ambar: Optional[float] = None
    estado: str = Field("ACTIVO", pattern="^(ACTIVO|ARCHIVADO)$")

    @model_validator(mode="after")
    def _validar_umbrales(self):
        if self.umbral_ambar is not None and self.umbral_verde is None:
            raise ValueError("El umbral ámbar requiere un umbral verde.")
        v, a = self.umbral_verde, self.umbral_ambar
        if v is not None and a is not None and ((self.sentido == "MAX" and a > v) or (self.sentido == "MIN" and a < v)):
            regla = "menor o igual" if self.sentido == "MAX" else "mayor o igual"
            raise ValueError(f"En un indicador donde {'más' if self.sentido == 'MAX' else 'menos'} es mejor, el umbral ámbar debe ser {regla} que el verde.")
        return self


class GraficoPersonalizadoIn(BaseModel):
    perspectiva: str = Field(..., min_length=3, max_length=30)
    titulo: str = Field(..., min_length=3, max_length=120)
    medida_codigo: str = Field(..., min_length=3, max_length=40)
    dimension_codigo: str = Field(..., min_length=2, max_length=60)
    agregacion: str = Field("SUM", pattern="^(SUM|AVG|COUNT|COUNT_DISTINCT|MIN|MAX)$")
    tipo_grafico: str = Field("bar", pattern="^(bar|line|area|doughnut|table)$")
    orden: int = Field(10, ge=0, le=999)
    visible: bool = True


class GraficoPreviewIn(BaseModel):
    medida_codigo: str
    dimension_codigo: str
    agregacion: str = Field("SUM", pattern="^(SUM|AVG|COUNT|COUNT_DISTINCT|MIN|MAX)$")


def _actualizar(db: Session, sql: str, params: dict, entidad: str) -> None:
    if db.execute(text(sql), params).rowcount == 0:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{entidad} no encontrada.")
    db.commit()
    cache_consultas.invalidar()


@router.put("/config/perspectivas/{codigo}", summary="Editar una perspectiva del CMI (solo ADMIN)")
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
            user: User = Depends(require_roles(ROLES_CONFIG))):
    fila = db.execute(text("SELECT sentido, perspectiva FROM bi.ref_kpi WHERE codigo = :c"), {"c": codigo}).first()
    if fila is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Indicador no encontrado.")
    sentido, perspectiva = fila[0], fila[1]
    _exigir_perspectiva_visible(user, perspectiva)
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


def _obtener_medida_autorizada(db: Session, user: User, medida_codigo: str) -> dict:
    filas = _filas(db, "SELECT * FROM app.medida_catalogo WHERE codigo = :c AND activo = TRUE", {"c": medida_codigo})
    if not filas:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medida del catálogo no encontrada.")
    med = filas[0]
    _exigir_perspectiva_visible(user, med["perspectiva"])
    return med


@router.post("/config/kpis-personalizados", summary="Crear un KPI personalizado (KPP-nn)")
def post_kpi_personalizado(body: KpiPersonalizadoIn, db: Session = Depends(get_db),
                           user: User = Depends(require_roles(ROLES_CONFIG))):
    _exigir_perspectiva_visible(user, body.perspectiva)
    med = _obtener_medida_autorizada(db, user, body.medida_codigo)
    if body.agregacion not in (med.get("agregaciones_permitidas") or []):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Agregación no permitida para esta medida.")
    existentes = db.execute(text("SELECT codigo FROM app.kpi_personalizado")).scalars().all()
    nums = [int(c.split("-")[1]) for c in existentes if c.startswith("KPP-") and c.split("-")[1].isdigit()]
    siguiente = (max(nums) + 1) if nums else 1
    codigo = f"KPP-{siguiente:02d}"
    db.execute(text("""
        INSERT INTO app.kpi_personalizado
            (codigo, perspectiva, nombre, descripcion, medida_codigo, agregacion, unidad,
             sentido, meta, umbral_verde, umbral_ambar, estado, creado_por, actualizado_por, actualizado_en)
        VALUES
            (:codigo, :perspectiva, :nombre, :descripcion, :medida_codigo, :agregacion, :unidad,
             :sentido, :meta, :umbral_verde, :umbral_ambar, :estado, :usuario, :usuario, now())"""),
        {**body.model_dump(), "codigo": codigo, "unidad": med["unidad"], "usuario": user.username})
    db.commit()
    cache_consultas.invalidar()
    return get_config(db, user)


@router.put("/config/kpis-personalizados/{codigo}", summary="Editar o archivar un KPI personalizado")
def put_kpi_personalizado(codigo: str, body: KpiPersonalizadoIn, db: Session = Depends(get_db),
                          user: User = Depends(require_roles(ROLES_CONFIG))):
    persp = db.execute(text("SELECT perspectiva FROM app.kpi_personalizado WHERE codigo = :c"), {"c": codigo}).scalar()
    if persp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "KPI personalizado no encontrado.")
    _exigir_perspectiva_visible(user, persp)
    _exigir_perspectiva_visible(user, body.perspectiva)
    med = _obtener_medida_autorizada(db, user, body.medida_codigo)
    if body.agregacion not in (med.get("agregaciones_permitidas") or []):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Agregación no permitida para esta medida.")
    _actualizar(db, """
        UPDATE app.kpi_personalizado
        SET perspectiva = :perspectiva, nombre = :nombre, descripcion = :descripcion,
            medida_codigo = :medida_codigo, agregacion = :agregacion, unidad = :unidad, sentido = :sentido,
            meta = :meta, umbral_verde = :umbral_verde, umbral_ambar = :umbral_ambar,
            estado = :estado, actualizado_por = :usuario, actualizado_en = now()
        WHERE codigo = :codigo""",
        {**body.model_dump(), "codigo": codigo, "unidad": med["unidad"], "usuario": user.username}, "KPI personalizado")
    return get_config(db, user)


@router.post("/config/graficos/preview", summary="Vista previa segura de una gráfica personalizada")
def preview_grafico(body: GraficoPreviewIn, db: Session = Depends(get_db),
                    user: User = Depends(require_roles(ROLES_CONFIG))):
    med = _obtener_medida_autorizada(db, user, body.medida_codigo)
    return cache_consultas.obtener(
        ("cmi_grafico_preview", body.medida_codigo, body.dimension_codigo, body.agregacion),
        TTL_SEG,
        lambda: ejecutar_consulta_medida(db, med, body.dimension_codigo, body.agregacion),
    )


@router.post("/config/graficos", summary="Crear una gráfica personalizada")
def post_grafico(body: GraficoPersonalizadoIn, db: Session = Depends(get_db),
                 user: User = Depends(require_roles(ROLES_CONFIG))):
    _exigir_perspectiva_visible(user, body.perspectiva)
    med = _obtener_medida_autorizada(db, user, body.medida_codigo)
    ejecutar_consulta_medida(db, med, body.dimension_codigo, body.agregacion)
    db.commit()  # Cierra la transacción READ ONLY antes del INSERT en app
    db.execute(text("""
        INSERT INTO app.grafico_personalizado
            (perspectiva, titulo, medida_codigo, dimension_codigo, agregacion, tipo_grafico,
             orden, visible, creado_por, actualizado_por, actualizado_en)
        VALUES
            (:perspectiva, :titulo, :medida_codigo, :dimension_codigo, :agregacion, :tipo_grafico,
             :orden, :visible, :usuario, :usuario, now())"""),
        {**body.model_dump(), "usuario": user.username})
    db.commit()
    cache_consultas.invalidar()
    return get_config(db, user)


@router.put("/config/graficos/{grafico_id}", summary="Actualizar o ocultar una gráfica personalizada")
def put_grafico(grafico_id: int, body: GraficoPersonalizadoIn, db: Session = Depends(get_db),
                user: User = Depends(require_roles(ROLES_CONFIG))):
    persp = db.execute(text("SELECT perspectiva FROM app.grafico_personalizado WHERE id = :id"), {"id": grafico_id}).scalar()
    if persp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gráfica personalizada no encontrada.")
    _exigir_perspectiva_visible(user, persp)
    _exigir_perspectiva_visible(user, body.perspectiva)
    med = _obtener_medida_autorizada(db, user, body.medida_codigo)
    ejecutar_consulta_medida(db, med, body.dimension_codigo, body.agregacion)
    db.commit()  # Cierra la transacción READ ONLY antes del UPDATE en app
    _actualizar(db, """
        UPDATE app.grafico_personalizado
        SET perspectiva = :perspectiva, titulo = :titulo, medida_codigo = :medida_codigo,
            dimension_codigo = :dimension_codigo, agregacion = :agregacion,
            tipo_grafico = :tipo_grafico, orden = :orden, visible = :visible,
            actualizado_por = :usuario, actualizado_en = now()
        WHERE id = :id""",
        {**body.model_dump(), "id": grafico_id, "usuario": user.username}, "Gráfica personalizada")
    return get_config(db, user)
