"""V-2: Pruebas de metas financieras reconocidas por estructura (no por nombre de archivo/hoja)."""
import os
import sys
from datetime import date, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from core.database import Base  # noqa: E402
import models  # noqa: F401, E402
from models.dim_categoria_financiera import DimCategoriaFinanciera  # noqa: E402
from models.dim_origen import DimOrigenDocumental  # noqa: E402
from models.dim_tiempo import DimTiempo  # noqa: E402
from models.fact_rentabilidad import FactRentabilidad  # noqa: E402
from models.log_inconsistencia import LogInconsistencia  # noqa: E402
from services.dw_loader import DWLoaderService  # noqa: E402
from services.extraccion_por_encabezado import campos_por_encabezado, registros_rentabilidad  # noqa: E402
import pandas as pd  # noqa: E402
from services.ingestion_service import detectar_tipo_fuente_por_cabeceras  # noqa: E402


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
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _normalizar_regs(regs):
    return [(r["categoria_financiera"], r["fecha"], r["monto_ejecutado"], r["monto_meta"]) for r in regs]


def test_variante_1_otro_nombre_archivo_y_hoja_clasifica_rentabilidad():
    df = pd.DataFrame([{"CATEGORIA": "PROGRAMAS", "MES": "Enero", "EJECUTADO 2026": 100, "META POR CATEGORIA 2026": 120}])
    tipo = detectar_tipo_fuente_por_cabeceras({"Resumen_2026": df}, "reporte_anual_directorio_v9.xlsx")
    assert tipo == "RENTABILIDAD"


def test_variante_2_columnas_reordenadas_mismos_hechos():
    base = campos_por_encabezado([
        "CATEGORIA: PROGRAMAS",
        "MES: Enero",
        "EJECUTADO 2026: 120000",
        "META POR CATEGORIA 2026: 150000",
    ])
    reordenada = campos_por_encabezado([
        "META POR CATEGORIA 2026: 150000",
        "EJECUTADO 2026: 120000",
        "MES: Enero",
        "CATEGORIA: PROGRAMAS",
    ])
    assert _normalizar_regs(registros_rentabilidad(base)) == _normalizar_regs(registros_rentabilidad(reordenada))


def test_variante_3_anios_distintos_2027():
    campos = campos_por_encabezado([
        "CATEGORIA: PROGRAMAS",
        "MES: Marzo",
        "EJECUTADO 2027: 210500",
        "META POR CATEGORIA 2027: 250000",
    ])
    regs = registros_rentabilidad(campos)
    assert _normalizar_regs(regs) == [("PROGRAMAS", date(2027, 3, 1), 210500.0, 250000.0)]
    assert regs[0]["es_fuente_metas_categoria"] is True


def test_variante_4_tildes_y_mayusculas_distintas():
    base = campos_por_encabezado([
        "CATEGORIA: PROGRAMAS",
        "MES: Febrero",
        "EJECUTADO 2026: 90000",
        "META POR CATEGORIA 2026: 100000",
    ])
    con_tildes = campos_por_encabezado([
        "Categoría: Programas",
        "Mes Numérico: 2",
        "Ejecutado 2026: 90000",
        "Meta por Categoría 2026: 100000",
    ])
    assert _normalizar_regs(registros_rentabilidad(base)) == _normalizar_regs(registros_rentabilidad(con_tildes))


def test_variante_5_meta_por_categoria_con_tilde_prevalece_sobre_meta_generica():
    campos = campos_por_encabezado([
        "Categoría: PROGRAMAS",
        "Mes: Abril",
        "Ejecutado 2026: 80000",
        "Meta por Categoría 2026: 95000",
        "Meta 2026: 123456",
    ])
    regs = registros_rentabilidad(campos)
    assert _normalizar_regs(regs) == [("PROGRAMAS", date(2026, 4, 1), 80000.0, 95000.0)]


def test_variante_6_fila_de_totales_ignorada():
    for label in ("TOTAL", "TOTAL GENERAL", "SUBTOTAL", "GRAN TOTAL", "ACUMULADO ANUAL"):
        campos = campos_por_encabezado([
            f"CATEGORIA: {label}",
            "MES: Mayo",
            "EJECUTADO 2026: 500000",
            "META POR CATEGORIA 2026: 600000",
        ])
        assert registros_rentabilidad(campos) == []


def test_variante_7_categoria_techos_y_cerrados():
    base = campos_por_encabezado([
        "CATEGORIA: TECHOS/CERRADOS",
        "MES: Junio",
        "EJECUTADO 2026: 75000",
        "META POR CATEGORIA 2026: 99024",
    ])
    variante = campos_por_encabezado([
        "CATEGORIA: Techos y cerrados",
        "MES: Junio",
        "EJECUTADO 2026: 75000",
        "META POR CATEGORIA 2026: 99024",
    ])
    assert _normalizar_regs(registros_rentabilidad(base)) == _normalizar_regs(registros_rentabilidad(variante))
    assert registros_rentabilidad(variante)[0]["categoria_financiera"] == "TECHOS_CERRADOS"


def test_precedencia_entre_dos_fuentes_y_libro_mas_reciente():
    db = _make_session()
    db.add(DimTiempo(id_tiempo=202602, gestion=2026, mes=2))
    db.add(DimCategoriaFinanciera(id_categoria=1, nombre_categoria="TECHOS_CERRADOS", tipo="INGRESO"))
    # Doc 1: fuente metas por categoria (otro nombre cualquiera)
    db.add(DimOrigenDocumental(id_documento=1, nombre_archivo="metas_presupuesto_2026.xlsx", tipo_fuente="RENTABILIDAD", fecha_procesamiento=datetime(2026, 3, 1, 10, 0)))
    # Doc 2: fuente secundaria (egresos/gestiones), cargada despues
    db.add(DimOrigenDocumental(id_documento=2, nombre_archivo="corte_egresos.xlsx", tipo_fuente="RENTABILIDAD", fecha_procesamiento=datetime(2026, 3, 2, 10, 0)))
    # Doc 3: segundo libro del mismo tipo metas por categoria, mas reciente
    db.add(DimOrigenDocumental(id_documento=3, nombre_archivo="metas_presupuesto_2026_rev2.xlsx", tipo_fuente="RENTABILIDAD", fecha_procesamiento=datetime(2026, 3, 5, 10, 0)))
    db.commit()

    loader = DWLoaderService(db)
    # 1) Carga doc 1 (metas por categoria): meta=99024
    loader.cargar_registro({
        "doc_id": 1,
        "categoria": "rentabilidad",
        "clave_origen": "c1",
        "clave_contenido": "c1",
        "resoluciones": {
            "categoria_financiera": "TECHOS_CERRADOS",
            "fecha": "2026-02-01",
            "monto_ejecutado": 80000.0,
            "monto_meta": 99024.0,
            "es_fuente_metas_categoria": True,
        },
        "calidad": {"requiere_revision": False},
    })

    # 2) Carga doc 2 (fuente secundaria, sin es_fuente_metas_categoria) -> debe ceder ante doc 1
    loader.cargar_registro({
        "doc_id": 2,
        "categoria": "rentabilidad",
        "clave_origen": "c2",
        "clave_contenido": "c2",
        "resoluciones": {
            "categoria_financiera": "TECHOS_CERRADOS",
            "fecha": "2026-02-01",
            "monto_ejecutado": 50000.0,
            "monto_meta": 89000.0,
            "es_fuente_metas_categoria": False,
        },
        "calidad": {"requiere_revision": False},
    })
    db.commit()

    hecho = db.query(FactRentabilidad).first()
    assert float(hecho.monto_meta) == 99024.0
    assert float(hecho.monto_ejecutado) == 80000.0
    assert hecho.id_documento == 1

    # 3) Carga doc 3 (mismo tipo metas por categoria, mas reciente) -> reemplaza y registra en log_inconsistencias
    loader.cargar_registro({
        "doc_id": 3,
        "categoria": "rentabilidad",
        "clave_origen": "c3",
        "clave_contenido": "c3",
        "resoluciones": {
            "categoria_financiera": "TECHOS_CERRADOS",
            "fecha": "2026-02-01",
            "monto_ejecutado": 82000.0,
            "monto_meta": 105000.0,
            "es_fuente_metas_categoria": True,
        },
        "calidad": {"requiere_revision": False},
    })
    db.commit()

    hecho = db.query(FactRentabilidad).first()
    assert float(hecho.monto_meta) == 105000.0
    assert float(hecho.monto_ejecutado) == 82000.0
    assert hecho.id_documento == 3
    logs = db.query(LogInconsistencia).filter(LogInconsistencia.tipo_regla == "CONFLICTO_FUENTES").all()
    assert len(logs) >= 2
