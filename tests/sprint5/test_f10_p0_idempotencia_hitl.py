"""Pruebas F10-1 (P0): idempotencia estricta de stg_entidad_no_resuelta y casos borde #4233/#4149/#5888."""
import sys
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parents[2]
for p in (str(RAIZ), str(RAIZ / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from models.staging_entidad import StagingEntidadNoResuelta
from services.dw_loader import DWLoaderService
from services.extraccion_por_encabezado import campos_por_encabezado, fila_resuelta_por_regla


def test_f10_1_dw_loader_idempotente_en_fase_a_y_b(dw_sqlite):
    db = dw_sqlite
    loader = DWLoaderService(db)
    stg1 = StagingEntidadNoResuelta(
        id_documento=1, tipo_entidad="ESTUDIANTE", texto_original="CI: 123456 | Nombre: Juan  Perez",
        motivo="CI_NOMBRE_DISCORDANTE", fk_estado="C", resuelto=False,
    )
    stg2 = StagingEntidadNoResuelta(
        id_documento=1, tipo_entidad="ESTUDIANTE", texto_original="CI: 123456 | Nombre: Juan Perez",
        motivo="CI_NOMBRE_DISCORDANTE", fk_estado="C", resuelto=False,
    )
    assert loader._registrar_staging_si_nuevo(stg1) is True
    assert loader._registrar_staging_si_nuevo(stg2) is False
    db.commit()
    assert db.query(StagingEntidadNoResuelta).count() == 1


def test_f10_1_casos_estructurados_4233_4149_5888():
    # #4149 (BD Cobranzas: deuda negativa -30)
    cob_4149 = campos_por_encabezado([
        "TIPO DE PROGRAMA: DIPLOMADO",
        "POS: POS-4980",
        "CI: 5310118",
        "NOMBRES: FABIOLA KAREN",
        "PATERNO: HUAITA",
        "MATERNO: CABRERA",
        "DEUDA TOTAL: -30",
        "TOTAL CUOTAS EN MORA: 0",
    ])
    assert fila_resuelta_por_regla(cob_4149, "financiero") is True

    # #4233 (TBL_INSCRITOS: marketing/admision)
    mkt_4233 = campos_por_encabezado([
        "NUMEROPROYECTO: POS-4519",
        "NOMBRE DEL PROGRAMA: PROGRAMA EXPERTO EN MICROSOFT POWER BI",
        "CI: 5409096",
        "NOMBRES: JUAN JOSE",
        "PATERNO: PARADA",
        "MATERNO: MENDEZ",
    ])
    assert fila_resuelta_por_regla(mkt_4233, "admision") is True

    # #5888 (ARCA MODULOS: asignacion docente sin CI)
    asig_5888 = campos_por_encabezado([
        "POS - MODULO: POS-5358",
        "DOCENTE: Yosuany Alzola Amaya",
        "MODULO: 1",
        "NOMBRE DEL PROGRAMA: Curso de Interpretacion de Electrocardiograma",
    ])
    assert fila_resuelta_por_regla(asig_5888, "academico") is True
