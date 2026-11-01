"""
tests/test_rentabilidad_ejecutado_meta.py
-----------------------------------------
EJECUTADO VS META por la plataforma: la confirmación contaba 24 inserciones pero fact_rentabilidad
guardaba 1 fila (sin categoría ni fecha, todas caían en la misma clave id_categoria + id_tiempo NULL).
Cada fila mensual debe conservar su categoría y su mes, un hecho por año con dato.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from services.extraccion_por_encabezado import campos_por_encabezado, registros_rentabilidad

ROOT = Path(__file__).resolve().parent.parent
SUBCONJUNTO = ROOT / "output" / "lote1387_archivos" / "EJECUTADO_VS_META_lote1387_24_filas.xlsx"

LINEA_ENERO = ("CATEGORIA: PROGRAMAS | MES: ENERO | MES NUMERICO: 1 | EJECUTADO 2023: 679446.0 | "
               "EJECUTADO 2024: 779434.91 | EJECUTADO 2025: 1045178.9 | META POR CATEGORIA 2025: 828875.0 | "
               "EJECUTADO 2026: 1307697.23 | META POR CATEGORIA 2026: 1085960.0 | META 2025: 828875.0")


@pytest.fixture
def sqlite_dw():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from core.database import Base
    import models  # noqa: F401  registro de todas las tablas

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _public(dbapi_connection, _):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS public")

    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _registros(linea):
    return registros_rentabilidad(campos_por_encabezado(linea.split(" | ")))


def test_fila_mensual_da_un_registro_por_anio_con_su_categoria_y_mes():
    regs = _registros(LINEA_ENERO)
    assert [r["fecha"] for r in regs] == [date(2023, 1, 1), date(2024, 1, 1), date(2025, 1, 1), date(2026, 1, 1)]
    assert {r["categoria_financiera"] for r in regs} == {"PROGRAMAS"}
    r2025 = next(r for r in regs if r["fecha"].year == 2025)
    assert (r2025["monto_ejecutado"], r2025["monto_meta"]) == (1045178.9, 828875.0)


def test_fila_sin_categoria_o_mes_no_se_expande():
    assert _registros("MES: ENERO | EJECUTADO 2025: 10") == []
    assert _registros("CATEGORIA: PROGRAMAS | EJECUTADO 2025: 10") == []


@pytest.mark.skipif(not SUBCONJUNTO.exists(), reason="subconjunto del lote no disponible")
def test_las_24_filas_del_lote_conservan_categoria_y_mes():
    df = pd.read_excel(SUBCONJUNTO, sheet_name="EJECUTADO")
    claves_por_fila = []
    for _, fila in df.iterrows():
        linea = " | ".join(f"{c}: {v}" for c, v in fila.items() if pd.notna(v))
        regs = _registros(linea)
        assert regs, f"fila sin hechos: {linea[:80]}"
        claves_por_fila.append({(r["categoria_financiera"], r["fecha"]) for r in regs})
    assert len(claves_por_fila) == 24
    todas = [k for claves in claves_por_fila for k in claves]
    assert len(todas) == len(set(todas)), "dos filas mensuales comparten clave y colapsarían en fact_rentabilidad"
    assert {(c, f.month) for c, f in todas} == {(c, m) for c in ("PROGRAMAS", "TECHOS_CERRADOS") for m in range(1, 13)}


def test_loader_guarda_un_hecho_por_categoria_y_mes_y_recargar_no_duplica(sqlite_dw):
    from models.fact_rentabilidad import FactRentabilidad
    from services.dw_loader import DWLoaderService

    linea_techos = LINEA_ENERO.replace("PROGRAMAS", "TECHOS/CERRADOS")
    regs = _registros(LINEA_ENERO) + _registros(linea_techos)
    loader = DWLoaderService(sqlite_dw)
    for _ in range(2):  # segunda pasada = recarga del mismo libro
        for r in regs:
            res = loader.cargar_registro({"categoria": "rentabilidad", "tipo_fuente": "RENTABILIDAD", "resoluciones": r,
                                          "calidad": {"requiere_revision": False}})
            assert res["status"] == "loaded"
        sqlite_dw.commit()

    filas = sqlite_dw.query(FactRentabilidad).all()
    assert len(filas) == 8  # 2 categorías x 4 años
    assert len({(f.id_categoria, f.id_tiempo) for f in filas}) == 8
    assert all(f.id_tiempo is not None for f in filas)
    assert sorted(float(f.monto_ejecutado) for f in filas)[-1] == 1307697.23  # no se suma al recargar
