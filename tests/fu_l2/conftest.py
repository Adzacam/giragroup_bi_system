"""
FU-L2: utilidades comunes de las pruebas de cobranza (SQLite en memoria, libros sintéticos con datos ficticios).

`cargar_libro` hace el recorrido real: IngestionService.procesar_archivo (hojas, staging) y la consolidación
(`routers.dataops._consolidar`) con BETO parcheado. Devuelve la «huella» del resultado en la DW: los hechos
financieros por CI ficticio y fecha, sin identificadores internos, para comparar un libro con su variante.
"""

import importlib
from collections import Counter

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.dataops_parches import _MODULOS


def nueva_dw():
    """Otra DW SQLite en memoria (esquema `public` adjunto): sirve para cargar el libro original y su variante por separado."""
    from core.database import Base
    import models  # noqa: F401

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def adjuntar_public(conn, _):
        cur = conn.cursor()
        cur.execute("ATTACH DATABASE ':memory:' AS public")
        cur.close()

    Base.metadata.create_all(bind=engine)
    with engine.begin() as con:   # la tabla de idempotencia no es un modelo: se crea como en la migración
        con.exec_driver_sql("CREATE TABLE IF NOT EXISTS carga_fila_origen (clave VARCHAR(64) PRIMARY KEY, "
                            "id_documento INTEGER, tabla VARCHAR(40), creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    return sessionmaker(bind=engine)()


@pytest.fixture
def dw_a():
    db = nueva_dw()
    yield db
    db.close()


@pytest.fixture
def dw_b():
    db = nueva_dw()
    yield db
    db.close()


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    """Caché de lectura en un directorio temporal, sin aplanador asimétrico y con BETO parcheado (confianza 0,95)."""
    from services import cache_consultas, cache_lectura, ingestion_service
    monkeypatch.setattr(cache_lectura, "DIR", tmp_path / "cache")
    monkeypatch.setattr(ingestion_service, "AsymmetricFlattener", None)
    for modulo in ["services.confianza_service"] + ["routers.dataops" + suf for suf in _MODULOS]:
        mod = importlib.import_module(modulo)
        if hasattr(mod, "obtener_indices"):
            monkeypatch.setattr(mod, "obtener_indices", lambda lineas, **kw: [.95] * len(lineas))
        if hasattr(mod, "indices_en_cache"):
            monkeypatch.setattr(mod, "indices_en_cache", lambda lineas: [.95] * len(lineas))
    monkeypatch.setattr("psycopg2.extras.execute_values", lambda cur, sql, filas, page_size=None: None)
    cache_consultas.invalidar()
    yield tmp_path
    cache_consultas.invalidar()


def cargar_libro(db, ruta, tipo_fuente="COBRANZA"):
    """Ingesta + consolidación de un libro en `db`. Devuelve (id_lote, id_documento)."""
    from routers import dataops
    from models.lote import Lote
    from services import ingestion_service

    lote = Lote(institucion="Prueba", periodo="2026")
    db.add(lote)
    db.commit()
    res = ingestion_service.IngestionService.procesar_archivo(
        db, str(ruta), ruta.name, id_lote=lote.id_lote, institucion="Prueba", tipo_fuente=tipo_fuente)
    dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), db, None)
    db.commit()
    return lote.id_lote, res["id_documento"]


def hechos(db):
    """Hechos financieros como tuplas comparables: (ci, fecha, concepto, deuda, pagado, cuotas, estado, fuente, dias, alerta)."""
    from sqlalchemy import text
    filas = db.execute(text(
        "SELECT e.ci, t.fecha, f.concepto, f.monto_deuda, f.monto_pagado, f.cuotas_impagas, f.estado_cartera, "
        "f.estado_cartera_fuente, f.dias_mora, f.tipo_alerta, f.requiere_revision "
        "FROM fact_situacion_financiera f JOIN dim_estudiante e ON e.id_estudiante = f.id_estudiante "
        "JOIN dim_tiempo t ON t.id_tiempo = f.id_tiempo")).fetchall()
    return sorted(
        ((str(r[0]), str(r[1]), r[2], None if r[3] is None else round(float(r[3]), 2), round(float(r[4] or 0), 2),
          r[5], r[6], r[7], r[8], r[9], bool(r[10])) for r in filas),
        key=lambda x: tuple("" if v is None else str(v) for v in x))


def pagos_por_anio(db):
    from sqlalchemy import text
    filas = db.execute(text(
        "SELECT t.gestion, SUM(f.monto_pagado) FROM fact_situacion_financiera f JOIN dim_tiempo t ON t.id_tiempo = f.id_tiempo "
        "GROUP BY t.gestion")).fetchall()
    return {int(g): round(float(s), 2) for g, s in filas}


def mora_por_anio(db):
    from sqlalchemy import text
    filas = db.execute(text(
        "SELECT t.gestion, COUNT(*) FROM fact_situacion_financiera f JOIN dim_tiempo t ON t.id_tiempo = f.id_tiempo "
        "WHERE f.cuotas_impagas >= 2 GROUP BY t.gestion")).fetchall()
    return {int(g): int(n) for g, n in filas}


def estados_fuente(db):
    from sqlalchemy import text
    filas = db.execute(text(
        "SELECT estado_cartera_fuente, COUNT(*) FROM fact_situacion_financiera WHERE concepto = 'SITUACION_CARTERA' GROUP BY 1")).fetchall()
    return {e: int(n) for e, n in filas}


def avisos(db):
    from models.log_inconsistencia import LogInconsistencia
    return Counter((l.tipo_regla, l.campo_afectado, l.estado_resolucion) for l in db.query(LogInconsistencia).all()
                   if l.tipo_regla in ("CUOTAS_NEGATIVAS", "CUOTAS_CON_TEXTO", "SOBREPAGO", "VALOR_FUERA_DE_CATALOGO",
                                       "CUOTAS_NO_NUMERICAS", "DIAS_MORA_NEGATIVOS"))
