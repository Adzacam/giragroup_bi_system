"""
backend/services/cmi_personalizacion_service.py
---------------------------------------------
Motor de consulta seguro en lista blanca para KPI y gráficas personalizadas (esquema `app`, D3/D6).
- Nunca ejecuta SQL libre del usuario: solo identificadores registrados en `app.medida_catalogo`.
- Ejecuta bajo `SET LOCAL TRANSACTION READ ONLY` y `statement_timeout = '5000'`.
- Agrupa siempre (máx 500 grupos) y oculta grupos con n < 5 («< 5») para proteger privacidad.
"""

from decimal import Decimal
from typing import Any, Dict, List

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

AGREGACIONES_SQL = {
    "SUM": lambda col: f"COALESCE(SUM({col}), 0)",
    "AVG": lambda col: f"ROUND(AVG({col})::numeric, 2)",
    "COUNT": lambda col: f"COUNT({col})",
    "COUNT_DISTINCT": lambda col: f"COUNT(DISTINCT {col})",
    "MIN": lambda col: f"MIN({col})",
    "MAX": lambda col: f"MAX({col})",
}

MIN_GRUPO_PRIVACIDAD = 5
MAX_GRUPOS = 500


def _num(v: Any) -> Any:
    return float(v) if isinstance(v, Decimal) else v


def ejecutar_consulta_medida(
    db: Session,
    medida: Dict[str, Any],
    dimension_codigo: str,
    agregacion: str,
) -> Dict[str, Any]:
    if agregacion not in AGREGACIONES_SQL or agregacion not in (medida.get("agregaciones_permitidas") or []):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Agregación '{agregacion}' no permitida para esta medida.")

    dims = {d["codigo"]: d for d in (medida.get("dimensiones_permitidas") or [])}
    if dimension_codigo not in dims:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Dimensión '{dimension_codigo}' no permitida para esta medida.")

    dim = dims[dimension_codigo]
    schema = medida["origen_schema"]
    tabla = medida["origen_tabla"]
    col = medida["columna_medida"]

    # Doble defensa: nunca permitir dim_estudiante ni esquemas fuera de bi/public
    if schema not in ("bi", "public") or "estudiante" in tabla.lower() and schema == "public":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Origen de datos no permitido.")

    agg_expr = AGREGACIONES_SQL[agregacion](f"base.{col}")
    join_sql = dim.get("join") or ""
    dim_expr = dim["expr"]

    sql = f"""
        SELECT ({dim_expr})::text AS etiqueta,
               {agg_expr} AS valor,
               COUNT(*) AS n_registros
        FROM {schema}.{tabla} AS base
        {join_sql}
        GROUP BY 1
        ORDER BY valor DESC NULLS LAST
        LIMIT {MAX_GRUPOS}
    """

    try:
        db.execute(text("SET LOCAL TRANSACTION READ ONLY"))
        db.execute(text("SET LOCAL statement_timeout = '5000'"))
        filas = db.execute(text(sql)).mappings().all()
    except OperationalError as exc:
        db.rollback()
        msg = str(exc).lower()
        if "timeout" in msg or "canceling statement" in msg:
            raise HTTPException(
                status.HTTP_504_GATEWAY_TIMEOUT,
                "La consulta personalizada superó el tiempo máximo permitido (5 s).",
            ) from exc
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error al consultar la medida.") from exc

    resultado: List[Dict[str, Any]] = []
    for f in filas:
        n = int(f["n_registros"] or 0)
        oculto = n < MIN_GRUPO_PRIVACIDAD
        resultado.append({
            "etiqueta": f["etiqueta"] or "Sin dato",
            "valor": None if oculto else _num(f["valor"]),
            "n_registros": "< 5" if oculto else n,
            "oculto": oculto,
        })
    return {
        "medida": medida["codigo"],
        "dimension": dimension_codigo,
        "agregacion": agregacion,
        "unidad": medida.get("unidad", "CANT"),
        "filas": resultado,
    }


def evaluar_kpi_personalizado(db: Session, kpi: Dict[str, Any], medida: Dict[str, Any]) -> Dict[str, Any]:
    agregacion = kpi.get("agregacion", "SUM")
    if agregacion not in AGREGACIONES_SQL or agregacion not in (medida.get("agregaciones_permitidas") or []):
        return {**kpi, "valor": None, "semaforo": "SIN_UMBRAL"}

    schema = medida["origen_schema"]
    tabla = medida["origen_tabla"]
    col = medida["columna_medida"]
    agg_expr = AGREGACIONES_SQL[agregacion](f"base.{col}")

    try:
        db.execute(text("SET LOCAL TRANSACTION READ ONLY"))
        db.execute(text("SET LOCAL statement_timeout = '5000'"))
        val = _num(db.execute(text(f"SELECT {agg_expr} FROM {schema}.{tabla} AS base")).scalar())
    except OperationalError:
        db.rollback()
        val = None

    semaforo = "SIN_UMBRAL"
    uv, ua, sentido = kpi.get("umbral_verde"), kpi.get("umbral_ambar"), kpi.get("sentido", "MAX")
    if val is not None and uv is not None:
        if sentido == "MAX":
            semaforo = "VERDE" if val >= uv else ("AMBAR" if ua is not None and val >= ua else "ROJO")
        else:
            semaforo = "VERDE" if val <= uv else ("AMBAR" if ua is not None and val <= ua else "ROJO")
    return {**kpi, "valor": val, "semaforo": semaforo}
