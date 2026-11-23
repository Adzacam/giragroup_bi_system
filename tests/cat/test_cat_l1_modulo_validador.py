"""Pruebas de CAT-L1: validación de nombres de módulo, prevención de MOD-GEN y bandeja."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ / "backend") not in sys.path:
    sys.path.insert(0, str(RAIZ / "backend"))

from core.database import Base
from models.dim_modulo import DimModulo
from models.catalogos import CatInstitucion
from models.log_inconsistencia import LogInconsistencia
from services.dw_loader import DWLoaderService
from services.modulo_validador import validar_nombre_modulo, es_nombre_modulo_valido
from services.revision_acciones_descriptor import construir_acciones

REGLAS_PRUEBA = {
    "CENTINELA": {"SI", "SÍ", "NO", "N/A", "NA", "-", "--", "NINGUNO"},
    "PREFIJO_TITULO": {"LIC.", "LIC ", "ING.", "ING ", "INGENIERO ", "ESTUDIANTE DE "},
    "PROFESION_OCUPACION": {"ABOGADO", "ESTUDIANTE", "MARKETING", "MUSICO", "ECONOMISTA"},
}


@pytest.fixture
def dw_mem():
    engine = create_engine("sqlite:///:memory:").execution_options(schema_translate_map={"public": None})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(CatInstitucion(id_institucion=361, nombre_institucion="GiraGroup Posgrado", sigla="GG"))
    db.commit()
    try:
        yield db
    finally:
        db.close()


@pytest.mark.parametrize("valor,esperado_ok", [
    ("0", False),
    ("1", False),
    ("2025-06-24 17:59:00", False),
    ("24/06/2025", False),
    ("SI", False),
    ("NO", False),
    ("N/A", False),
    ("-", False),
    ("AB", False),
    ("123", False),
    ("ABOGADO", False),
    ("LIC. ECONOMIA", False),
    ("ING. SISTEMAS", False),
    ("INGENIERO CIVIL", False),
    ("ESTUDIANTE", False),
    ("MARKETING", False),
    ("MÓDULO 1: MARKETING DIGITAL", True),
    ("2da. JORNADA DE ODONTOLOGÍA PARA BEBÉ - NAL", True),
])
def test_es_nombre_modulo_valido(valor, esperado_ok):
    ok, _ = validar_nombre_modulo(valor, reglas_override=REGLAS_PRUEBA)
    assert ok is esperado_ok
    assert es_nombre_modulo_valido(valor, reglas_override=REGLAS_PRUEBA) is esperado_ok


def test_fixture_inscritos_carrera_ocupacion_no_crea_modulos_y_registra_avisos(dw_mem):
    loader = DWLoaderService(dw_mem)
    inscritos_sinteticos = [
        "ABOGADO",
        "LIC. ECONOMIA",
        "ING. SISTEMAS",
        "ESTUDIANTE",
        "MARKETING",
        "SI",
        "N/A",
        "0",
        "2025-06-24 17:59:00",
        "MÓDULO INEXISTENTE DE POSGRADO",
    ]
    with patch("services.modulo_validador._cargar_reglas_catalogo", return_value={
        "CENTINELA": {"SI", "NO", "N/A", "-"},
        "PREFIJO_TITULO": {"LIC.", "ING.", "INGENIERO "},
        "PROFESION_OCUPACION": {"ABOGADO", "ESTUDIANTE", "MARKETING"},
    }):
        resultados = [
            loader.resolver_o_crear_modulo(nombre, pos_code=None, doc_id=101)
            for nombre in inscritos_sinteticos
        ]
    n_avisos = loader.registrar_avisos_modulo()
    dw_mem.commit()

    assert all(r is None for r in resultados)
    assert dw_mem.query(DimModulo).count() == 0
    assert dw_mem.query(DimModulo).filter(DimModulo.pos_code == "MOD-GEN").count() == 0
    assert n_avisos == len(inscritos_sinteticos)
    avisos = dw_mem.query(LogInconsistencia).filter_by(
        tipo_regla="VALOR_FUERA_DE_CATALOGO", campo_afectado="modulo"
    ).all()
    assert len(avisos) == len(inscritos_sinteticos)
    assert all(a.estado_resolucion == "PENDIENTE" for a in avisos)


def test_solo_crea_modulo_con_pos_valido(dw_mem):
    loader = DWLoaderService(dw_mem)
    id_mod = loader.resolver_o_crear_modulo(
        "Módulo 1: Gestión Hospitalaria", pos_code="POS-9999", doc_id=102, institucion="GiraGroup Posgrado"
    )
    assert id_mod is not None
    mod = dw_mem.query(DimModulo).filter_by(id_modulo=id_mod).first()
    assert mod is not None
    assert mod.pos_code == "POS-9999"

    # Nunca crea MOD-GEN aunque se pase explícitamente pos_code="MOD-GEN"
    id_gen = loader.resolver_o_crear_modulo("Módulo General", pos_code="MOD-GEN", doc_id=102)
    assert id_gen is None
    assert dw_mem.query(DimModulo).filter_by(pos_code="MOD-GEN").count() == 0


def test_bandeja_valor_fuera_de_catalogo_modulo_ofrece_vincular_y_crear():
    datos = {"campo_afectado": "modulo", "valor_recibido": "DIPLOMADO EN SALUD"}
    acc_operador = construir_acciones("VALOR_FUERA_DE_CATALOGO", "academico", datos, rol_usuario="OPERADOR")
    cod_operador = [a["codigo"] for a in acc_operador]
    assert "VINCULAR_MODULO" in cod_operador
    assert "CREAR_MODULO" not in cod_operador

    acc_admin = construir_acciones("VALOR_FUERA_DE_CATALOGO", "academico", datos, rol_usuario="ADMIN")
    cod_admin = [a["codigo"] for a in acc_admin]
    assert "VINCULAR_MODULO" in cod_admin
    assert "CREAR_MODULO" in cod_admin
