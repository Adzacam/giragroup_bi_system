"""V-3: Pruebas de extraccion, carga idempotente y borrado X-1 de PLANIFICACION (Diseno B)."""
import glob
import hashlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from core.database import Base  # noqa: E402
import models  # noqa: F401, E402
from models.dim_meta import DimMeta  # noqa: E402
from models.dim_origen import DimOrigenDocumental  # noqa: E402
from models.fact_planificacion import FactPlanificacionPrograma  # noqa: E402
from services.dw_loader import DWLoaderService  # noqa: E402
from services.extraccion_por_encabezado import campos_por_encabezado, registro_planificacion  # noqa: E402
from services.ingestion_service import IngestionService  # noqa: E402
from services.planificacion_extractor import extraer_libro_planificacion  # noqa: E402


def _make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _attach(dbapi_conn, _rec):
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS public")

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS carga_fila_origen (clave VARCHAR(64) PRIMARY KEY, id_documento INTEGER, tabla VARCHAR(80))"
        )
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _ruta_planificacion():
    matches = glob.glob(os.path.join(ROOT, "uploads", "data", "PLANIFICACION*.xlsx"))
    assert matches, "No se encontro el libro PLANIFICACION en uploads/data/"
    return matches[0]


def test_extraccion_planificacion_real_y_exclusion_borradores_y_derivadas():
    data = extraer_libro_planificacion(_ruta_planificacion())
    assert len(data["filas"]) == 1663
    por_hoja = {h["hoja"]: h for h in data["hojas_resumen"]}
    assert por_hoja["Julio-2025 borrador"]["filas"] == 0
    assert por_hoja["Septiembre-2025boor"]["filas"] == 0
    assert por_hoja["Centralizado_Mensual"]["filas"] == 0
    assert por_hoja["Dashboard Programas"]["filas"] == 0
    assert por_hoja["Dashboard Académico"]["filas"] == 0
    assert por_hoja["Julio"]["filas"] == 0
    assert por_hoja["Programas Notificados"]["filas"] == 1041

    metas = data["metas"]
    assert sum(1 for m in metas if m["categoria"] == "PLAN_INGRESO_TOTAL") == 24
    assert sum(1 for m in metas if m["categoria"] == "PLAN_INGRESO_TECHOS_PROYECTADO") == 10
    assert sum(1 for m in metas if m["categoria"] == "OKR_APERTURAS") == 24
    assert all(m.get("celda_origen") for m in metas)


def test_carga_idempotente_dim_meta_y_borrado_x1():
    db = _make_session()
    doc = DimOrigenDocumental(id_documento=10, nombre_archivo="planificacion.xlsx", tipo_fuente="PLANIFICACION")
    db.add(doc)
    db.commit()

    data = extraer_libro_planificacion(_ruta_planificacion())
    loader = DWLoaderService(db)

    # Cargar metas y filas
    for idx_m, m in enumerate(data["metas"]):
        c_orig = hashlib.sha256(f"doc10|{m['celda_origen']}".encode()).hexdigest()
        c_cont = hashlib.sha256(f"{m['categoria']}|{m['gestion']}|{m['mes']}|{m['monto_meta']}".encode()).hexdigest()
        res = loader.cargar_registro({
            "doc_id": 10,
            "categoria": "planificacion_meta",
            "clave_origen": c_orig,
            "clave_contenido": c_cont,
            "resoluciones": m,
            "calidad": {"requiere_revision": False},
        })
        assert res["status"] == "loaded"

    sin_tiempo = 0
    cont_lineas = {}
    for f in data["filas"]:
        campos = campos_por_encabezado([c.strip() for c in f["texto_linea"].split("|")])
        reg = registro_planificacion(campos, hoja=f["hoja"], anio_hoja=f["anio_hoja"], mes_hoja=f["mes_hoja"])
        reg["fila_excel"] = f["fila_excel"]
        if reg["fecha_plan"] is None:
            sin_tiempo += 1
        occ = cont_lineas.get(f["texto_linea"], 0) + 1
        cont_lineas[f["texto_linea"]] = occ
        c_orig = hashlib.sha256(f"doc10|{f['hoja']}|{f['fila_excel']}|{f['texto_linea']}".encode()).hexdigest()
        c_cont = hashlib.sha256(f"{f['texto_linea']}|{occ}".encode()).hexdigest()
        res = loader.cargar_registro({
            "doc_id": 10,
            "categoria": "planificacion",
            "clave_origen": c_orig,
            "clave_contenido": c_cont,
            "resoluciones": reg,
            "calidad": {"requiere_revision": False},
        })
        assert res["status"] == "loaded"
    db.commit()

    assert db.query(FactPlanificacionPrograma).count() == 1663
    assert db.query(FactPlanificacionPrograma).filter(FactPlanificacionPrograma.id_tiempo_plan.is_(None)).count() == sin_tiempo == 10
    assert db.query(DimMeta).count() == 58

    # Recargar las mismas filas: agrega 0 filas
    for f in data["filas"][:20]:
        campos = campos_por_encabezado([c.strip() for c in f["texto_linea"].split("|")])
        reg = registro_planificacion(campos, hoja=f["hoja"], anio_hoja=f["anio_hoja"], mes_hoja=f["mes_hoja"])
        reg["fila_excel"] = f["fila_excel"]
        c_orig = hashlib.sha256(f"doc10|{f['hoja']}|{f['fila_excel']}|{f['texto_linea']}".encode()).hexdigest()
        c_cont = hashlib.sha256(f["texto_linea"].encode()).hexdigest()
        res = loader.cargar_registro({
            "doc_id": 10,
            "categoria": "planificacion",
            "clave_origen": c_orig,
            "clave_contenido": c_cont,
            "resoluciones": reg,
            "calidad": {"requiere_revision": False},
        })
        assert res["status"] == "skipped"
    assert db.query(FactPlanificacionPrograma).count() == 1663

    # Borrado X-1: deja 0 filas en fact_planificacion_programa y dim_meta
    assert IngestionService.eliminar_fuente(db, 10) is True
    assert db.query(FactPlanificacionPrograma).count() == 0
    assert db.query(DimMeta).count() == 0
