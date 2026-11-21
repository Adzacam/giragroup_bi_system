"""Tests FU-L7: motivos nuevos, bug patrones/patron, explicación sin PII, descarte de filas vacías 0.0000 y agrupación VALOR_FUERA_DE_CATALOGO."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from core.database import Base  # noqa: E402
from models.dim_modulo import DimModulo  # noqa: E402
from models.dim_origen import DimOrigenDocumental  # noqa: E402
from models.fact_evaluacion import FactEvaluacionDocente  # noqa: E402
from models.fact_financiero import FactSituacionFinanciera  # noqa: E402
from models.fact_rendimiento import FactRendimientoAcademico  # noqa: E402
from models.staging_entidad import StagingEntidadNoResuelta  # noqa: E402
from services.bandeja_grupos import (  # noqa: E402
    MOTIVOS_INFORMATIVOS,
    es_fila_vacia_sin_confianza,
    explicacion_motivo,
    grupos_pendientes,
)
from services.revision_consulta import MOTIVOS, caso_guardado, consultar, grupos_publicos  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", execution_options={"schema_translate_map": {"public": None}})
    tablas = [
        DimOrigenDocumental.__table__,
        DimModulo.__table__,
        StagingEntidadNoResuelta.__table__,
        FactRendimientoAcademico.__table__,
        FactSituacionFinanciera.__table__,
        FactEvaluacionDocente.__table__,
    ]
    Base.metadata.create_all(engine, tables=tablas)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _doc(db, id_doc=44, nombre="TBL_INSCRITOS.xlsx", tipo="MARKETING"):
    d = DimOrigenDocumental(id_documento=id_doc, nombre_archivo=nombre, tipo_fuente=tipo, id_lote=1)
    db.add(d)
    db.commit()
    return d


def test_motivos_nuevos_en_catalogo_y_reglas():
    esperados = {
        "HOJA_IGNORADA",
        "NOTA_FUERA_DE_RANGO",
        "RESPUESTA_EN_COLUMNA_EQUIVOCADA",
        "CUOTAS_NEGATIVAS",
        "CONFLICTO_META",
        "VALOR_FUERA_DE_CATALOGO",
        "PUNTUACION_FUERA_DE_ESCALA",
        "ESCALA_NO_INFERIBLE",
    }
    assert esperados.issubset(set(MOTIVOS))
    assert "HOJA_IGNORADA" in MOTIVOS_INFORMATIVOS
    for m in esperados:
        exp = explicacion_motivo(m, "CI: 12345678 | Estudiante: Juan Perez | valor=999")
        assert exp["regla"]
        assert exp["umbral"]
        assert "12345678" not in exp["valor_enmascarado"]
        assert "Juan Perez" not in exp["valor_enmascarado"]


def test_grupos_publicos_propaga_patrones_patron_explicacion_y_filtra_hoja_ignorada(db):
    doc = _doc(db, id_doc=43, nombre="ARCA.xlsx", tipo="ACTA")
    # 2 casos CI_NOMBRE_DISCORDANTE con distinta similitud
    db.add(StagingEntidadNoResuelta(
        id_documento=43, tipo_entidad="ESTUDIANTE",
        texto_original="CI: 12345678 | Estudiante: Ana Lopez",
        motivo="CI_NOMBRE_DISCORDANTE", score_fuzzy=22.0, nivel_confianza=0.7, resuelto=False,
    ))
    db.add(StagingEntidadNoResuelta(
        id_documento=43, tipo_entidad="ESTUDIANTE",
        texto_original="CI: 87654321 | Estudiante: Carlos Diaz",
        motivo="CI_NOMBRE_DISCORDANTE", score_fuzzy=45.0, nivel_confianza=0.7, resuelto=False,
    ))
    # 1 caso HOJA_IGNORADA que NO debe aparecer en la bandeja pendiente
    db.add(StagingEntidadNoResuelta(
        id_documento=43, tipo_entidad="HOJA",
        texto_original="Hoja oculta Copia",
        motivo="HOJA_IGNORADA", nivel_confianza=1.0, resuelto=False,
    ))
    db.commit()

    res = grupos_publicos(db, [doc], page=1)
    assert res["total_casos"] == 2
    assert all(g["motivo"] != "HOJA_IGNORADA" for g in res["grupos"])
    assert len(res["patrones"]) == 2
    for g in res["grupos"]:
        assert g["patron"]
        assert g["explicacion"]["regla"]
        assert g["explicacion"]["umbral"]
        assert "12345678" not in g["explicacion"]["valor_enmascarado"]
        assert "Ana Lopez" not in g["explicacion"]["valor_enmascarado"]

    tray = consultar(db, [doc], page=1, page_size=5, vista="PENDIENTES")
    assert tray["total"] == 2
    assert all(item["motivo"] != "HOJA_IGNORADA" for item in tray["items"])
    assert all(item["explicacion"]["regla"] for item in tray["items"])


def test_descarta_5_filas_vacias_confianza_cero_doc44(db):
    doc = _doc(db, id_doc=44, nombre="TBL_INSCRITOS.xlsx", tipo="MARKETING")
    for idx in range(5):
        db.add(StagingEntidadNoResuelta(
            id_documento=44, tipo_entidad="ESTUDIANTE",
            texto_original=f"Nombre_{idx}: | CI: ",
            motivo="FILA_SIN_IDENTIDAD", nivel_confianza=0.0, resuelto=False,
        ))
    db.add(StagingEntidadNoResuelta(
        id_documento=44, tipo_entidad="ESTUDIANTE",
        texto_original="CI: 55667788 | Estudiante: Maria Rojas",
        motivo="CI_DUDOSA", nivel_confianza=0.5, resuelto=False,
    ))
    db.commit()

    assert es_fila_vacia_sin_confianza("", 0.0) is True
    assert es_fila_vacia_sin_confianza("Nombre: | CI: ", 0.0) is True
    assert es_fila_vacia_sin_confianza("CI: 55667788", 0.0) is False

    base = grupos_pendientes(db, [44])
    assert base["descartadas_vacias"] == 5
    assert base["total_casos"] == 1
    tray = consultar(db, [doc], page=1, page_size=5, vista="PENDIENTES")
    assert tray["total"] == 1


def test_agrupa_1255_valor_fuera_de_catalogo(db):
    doc = _doc(db, id_doc=42, nombre="Experiencia.xlsx", tipo="EVALUACION_DOCENTE")
    db.bulk_save_objects([
        StagingEntidadNoResuelta(
            id_documento=42, tipo_entidad="EVALUACION",
            texto_original="Pregunta: P8 | Valor: excelente" if i < 1000 else "Pregunta: P9 | Valor: todo bien",
            motivo="VALOR_FUERA_DE_CATALOGO", nivel_confianza=0.9, resuelto=False,
        )
        for i in range(1255)
    ])
    db.commit()

    res = grupos_publicos(db, [doc], page=1)
    assert res["total_casos"] == 1255
    assert res["total_grupos"] == 2
    assert sum(g["n"] for g in res["grupos"]) == 1255
    assert res["grupos"][0]["explicacion"]["regla"]


def test_regresion_cero_pii_lote35_discordante_y_lote36_asesor(db):
    from services.revision_formularios import construir_motivo_detalle

    # Caso 1 (Lote #35): CI_NOMBRE_DISCORDANTE individual no debe filtrar el nombre real en motivo_detalle
    doc_35 = _doc(db, id_doc=35, nombre="ARCA_35.xlsx", tipo="ACTA")
    ent_35 = StagingEntidadNoResuelta(
        id_documento=35,
        tipo_entidad="ESTUDIANTE",
        texto_original="CI: 8349269 | Estudiante: JUAN CARLOS PEREZ",
        ci_temporal="8349269",
        mejor_candidato="JUANITA PEREZ",
        motivo="CI_NOMBRE_DISCORDANTE",
        score_fuzzy=40.0,
        nivel_confianza=0.75,
        resuelto=False,
    )
    db.add(ent_35)
    db.commit()

    caso = caso_guardado(ent_35, doc_35)
    assert "JUAN CARLOS PEREZ" not in (caso.get("motivo_detalle") or "")
    assert "JUANITA PEREZ" not in (caso.get("motivo_detalle") or "")
    assert "JUAN CARLOS PEREZ" not in (caso.get("por_que_detuvo") or "")
    assert "8349269" not in (caso.get("motivo_detalle") or "")
    assert "••••" in (caso.get("motivo_detalle") or "")

    detalle_directo = construir_motivo_detalle(
        "academico",
        "CI_NOMBRE_DISCORDANTE",
        {"ci": "8349269", "nombre": "JUAN CARLOS PEREZ", "sugerencia": "JUANITA PEREZ (••••269)"},
    )
    assert "JUAN CARLOS PEREZ" not in detalle_directo
    assert "JUANITA PEREZ" not in detalle_directo

    ent_35.mejor_candidato = "JUANITA PEREZ ••••269"
    caso_parcial = caso_guardado(ent_35, doc_35)
    assert "JUANITA PEREZ" not in (caso_parcial.get("motivo_detalle") or "")

    # Caso 2 (Lote #36): Por grupos -> CI_DUDOSA no debe filtrar ASESOR: <NOMBRE REAL> en ejemplo ni explicacion
    doc_36 = _doc(db, id_doc=36, nombre="TBL_INSCRITOS_36.xlsx", tipo="ADMISION")
    db.add(
        StagingEntidadNoResuelta(
            id_documento=36,
            tipo_entidad="ESTUDIANTE",
            texto_original="ASESOR: CARLOS MENDOZA ROJAS | CI: 1234X | Estudiante: MARIA LOPEZ",
            motivo="CI_DUDOSA",
            nivel_confianza=0.65,
            resuelto=False,
        )
    )
    db.commit()

    res_grupos = grupos_publicos(db, [doc_36], page=1)
    assert res_grupos["total_casos"] == 1
    g = res_grupos["grupos"][0]
    assert "CARLOS MENDOZA ROJAS" not in g["ejemplo"]
    assert "MARIA LOPEZ" not in g["ejemplo"]
    assert "ASESOR: ••••" in g["ejemplo"]
    assert "CARLOS MENDOZA ROJAS" not in g["explicacion"]["valor_enmascarado"]
    assert "MARIA LOPEZ" not in g["explicacion"]["valor_enmascarado"]
