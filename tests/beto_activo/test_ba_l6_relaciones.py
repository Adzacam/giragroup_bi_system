"""Tests unitarios de BA-L6: validación configurable de relaciones antes de insertar al DW."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from pipeline import config as cfg
from services.validacion_relaciones import (
    ContextoRelaciones,
    MOTIVO_RELACION_INCOHERENTE,
    ReglaRelacion,
    validar_registro,
)


def _ctx_demo() -> ContextoRelaciones:
    reglas = {
        "ESTUDIANTE_PROGRAMA_PERIODO": ReglaRelacion(
            codigo_regla="ESTUDIANTE_PROGRAMA_PERIODO",
            nombre_regla="Estudiante <-> Programa y período",
            descripcion="POS existente y fecha dentro del período",
            activa=True,
            severidad="ALTA",
            parametros={"validar_pos": True, "validar_periodo": True},
            acciones_sugeridas=["VINCULAR_RELACION", "CORREGIR_FECHA"],
        ),
        "MODULO_EN_PROGRAMA": ReglaRelacion(
            codigo_regla="MODULO_EN_PROGRAMA",
            nombre_regla="Módulo <-> Programa",
            descripcion="Número de módulo existe en POS",
            activa=True,
            severidad="ALTA",
            parametros={},
            acciones_sugeridas=["VINCULAR_RELACION"],
        ),
        "DOCENTE_MODULO_BRIDGE": ReglaRelacion(
            codigo_regla="DOCENTE_MODULO_BRIDGE",
            nombre_regla="Docente <-> Módulo",
            descripcion="Docente en bridge_modulo_docente",
            activa=True,
            severidad="MEDIA",
            parametros={},
            acciones_sugeridas=["VINCULAR_RELACION", "MARCAR_SIN_DATO"],
        ),
        "PAGO_INSCRIPCION_PROGRAMA": ReglaRelacion(
            codigo_regla="PAGO_INSCRIPCION_PROGRAMA",
            nombre_regla="Pago <-> Inscripción",
            descripcion="Estudiante inscrito en el programa",
            activa=True,
            severidad="ALTA",
            parametros={"categorias": ["financiero"]},
            acciones_sugeridas=["VINCULAR_RELACION"],
        ),
        "RESPUESTA_ESCALA_PREGUNTA": ReglaRelacion(
            codigo_regla="RESPUESTA_ESCALA_PREGUNTA",
            nombre_regla="Respuesta <-> Escala",
            descripcion="Puntuación dentro de la escala",
            activa=True,
            severidad="ALTA",
            parametros={"escala_min": 1},
            acciones_sugeridas=["MARCAR_SIN_DATO"],
        ),
        "FECHA_GESTION_VALIDA": ReglaRelacion(
            codigo_regla="FECHA_GESTION_VALIDA",
            nombre_regla="Fecha <-> Gestión válida",
            descripcion="Año válido",
            activa=True,
            severidad="ALTA",
            parametros={"anio_min": 2015, "anio_max": 2030, "anios_invalidos": [205, 2580, 3035]},
            acciones_sugeridas=["CORREGIR_FECHA", "MARCAR_SIN_DATO"],
        ),
    }
    return ContextoRelaciones(
        reglas=reglas,
        pos_validos={"POS-101", "POS-202"},
        modulos_por_pos={"POS-101": {1, 2, 3}, "POS-202": {1, 2}},
        periodos_por_pos={"POS-101": (2023, 2025)},
        bridge_docente_pos={("DRA. ANA PEREZ", "POS-101")},
        inscripciones_est_pos={("MARIA LOPEZ", "POS-101")},
    )


def test_regla_a_estudiante_programa_correcto_e_incorrecto():
    ctx = _ctx_demo()
    ok = validar_registro({"categoria": "academico", "resoluciones": {"estudiante": {"valor_extraido": "Maria Lopez"}, "programa": {"metadata": {"pos_canonico": "POS-101"}}, "fecha": "2024-05-10"}}, ctx)
    assert ok == []

    bad_pos = validar_registro({"categoria": "academico", "resoluciones": {"estudiante": {"valor_extraido": "Maria Lopez"}, "programa": {"metadata": {"pos_canonico": "POS-999"}}, "fecha": "2024-05-10"}}, ctx)
    assert len(bad_pos) == 1
    assert bad_pos[0].regla == "ESTUDIANTE_PROGRAMA_PERIODO"

    bad_periodo = validar_registro({"categoria": "academico", "resoluciones": {"estudiante": {"valor_extraido": "Maria Lopez"}, "programa": {"metadata": {"pos_canonico": "POS-101"}}, "fecha": "2021-01-15"}}, ctx)
    assert len(bad_periodo) == 1
    assert bad_periodo[0].regla == "ESTUDIANTE_PROGRAMA_PERIODO"


def test_regla_b_modulo_programa_correcto_e_incorrecto():
    ctx = _ctx_demo()
    ok = validar_registro({"categoria": "academico", "resoluciones": {"programa": {"metadata": {"pos_canonico": "POS-101"}}, "numero_modulo": 2}}, ctx)
    assert ok == []

    bad = validar_registro({"categoria": "academico", "resoluciones": {"programa": {"metadata": {"pos_canonico": "POS-101"}}, "numero_modulo": 9}}, ctx)
    assert len(bad) == 1
    assert bad[0].regla == "MODULO_EN_PROGRAMA"


def test_regla_c_docente_modulo_correcto_e_incorrecto():
    ctx = _ctx_demo()
    ok = validar_registro({"categoria": "academico", "resoluciones": {"programa": {"metadata": {"pos_canonico": "POS-101"}}, "docente": {"valor_extraido": "Dra. Ana Perez"}}}, ctx)
    assert ok == []

    bad = validar_registro({"categoria": "academico", "resoluciones": {"programa": {"metadata": {"pos_canonico": "POS-101"}}, "docente": {"valor_extraido": "Lic. Otro Docente"}}}, ctx)
    assert len(bad) == 1
    assert bad[0].regla == "DOCENTE_MODULO_BRIDGE"


def test_regla_d_pago_inscripcion_correcto_e_incorrecto():
    ctx = _ctx_demo()
    ok = validar_registro({"categoria": "financiero", "resoluciones": {"estudiante": {"valor_extraido": "Maria Lopez"}, "programa": {"metadata": {"pos_canonico": "POS-101"}}}}, ctx)
    assert ok == []

    bad = validar_registro({"categoria": "financiero", "resoluciones": {"estudiante": {"valor_extraido": "Juan Perez"}, "programa": {"metadata": {"pos_canonico": "POS-101"}}}}, ctx)
    assert len(bad) == 1
    assert bad[0].regla == "PAGO_INSCRIPCION_PROGRAMA"


def test_regla_e_respuesta_escala_correcto_e_incorrecto():
    ctx = _ctx_demo()
    ok = validar_registro({"categoria": "evaluacion_docente", "resoluciones": {"puntuacion": 5, "escala_max": 5}}, ctx)
    assert ok == []

    bad = validar_registro({"categoria": "evaluacion_docente", "resoluciones": {"puntuacion": 8, "escala_max": 5}}, ctx)
    assert len(bad) == 1
    assert bad[0].regla == "RESPUESTA_ESCALA_PREGUNTA"


def test_regla_f_fecha_gestion_correcto_e_incorrecto():
    ctx = _ctx_demo()
    ok = validar_registro({"categoria": "academico", "resoluciones": {"fecha": "2024-08-01"}}, ctx)
    assert ok == []

    for anio_bad in ("0205-01-01", "2580-03-10", "3035-12-01"):
        bad = validar_registro({"categoria": "academico", "resoluciones": {"fecha": anio_bad}}, ctx)
        assert len(bad) == 1
        assert bad[0].regla == "FECHA_GESTION_VALIDA"


def test_invariantes_cascada_y_umbrales_intactos():
    assert MOTIVO_RELACION_INCOHERENTE == "RELACION_INCOHERENTE"
    assert cfg.UMBRAL_CONFIANZA_ALTO == 0.85
    assert cfg.UMBRAL_CONFIANZA_MEDIO == 0.60
    assert cfg.BETO_MAX_LENGTH_TOKENS == 128
