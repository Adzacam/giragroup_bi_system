"""BA-L6: Pruebas unitarias por regla de validación de relaciones (a)-(f) e invariantes de cascada."""
import pytest
from pipeline import config as cfg
from services.validacion_relaciones import (
    ContextoRelaciones,
    ReglaRelacion,
    validar_registro,
)


def _ctx_completo() -> ContextoRelaciones:
    return ContextoRelaciones(
        reglas={
            "ESTUDIANTE_PROGRAMA_PERIODO": ReglaRelacion(
                "ESTUDIANTE_PROGRAMA_PERIODO", "Estudiante ↔ Programa", "", True, "ALTA",
                {"validar_pos": True, "validar_periodo": True}, ["VINCULAR_PROGRAMA", "CORREGIR_FECHA", "MARCAR_SIN_DATO"],
            ),
            "MODULO_EN_PROGRAMA": ReglaRelacion(
                "MODULO_EN_PROGRAMA", "Módulo ↔ Programa", "", True, "ALTA",
                {"validar_numero_modulo": True}, ["VINCULAR_MODULO", "MARCAR_SIN_DATO"],
            ),
            "DOCENTE_MODULO_BRIDGE": ReglaRelacion(
                "DOCENTE_MODULO_BRIDGE", "Docente ↔ Módulo", "", True, "MEDIA",
                {"motivo_sin_vincular": "DOCENTE_SIN_VINCULAR"}, ["VINCULAR_DOCENTE", "MARCAR_SIN_DATO"],
            ),
            "PAGO_INSCRIPCION_PROGRAMA": ReglaRelacion(
                "PAGO_INSCRIPCION_PROGRAMA", "Pago ↔ Inscripción", "", True, "ALTA",
                {"categorias": ["financiero"]}, ["VINCULAR_INSCRIPCION", "MARCAR_SIN_DATO"],
            ),
            "RESPUESTA_ESCALA_PREGUNTA": ReglaRelacion(
                "RESPUESTA_ESCALA_PREGUNTA", "Respuesta ↔ Escala", "", True, "ALTA",
                {"escala_min": 1}, ["CORREGIR_PUNTUACION", "MARCAR_SIN_DATO"],
            ),
            "FECHA_GESTION_VALIDA": ReglaRelacion(
                "FECHA_GESTION_VALIDA", "Fecha ↔ Gestión", "", True, "ALTA",
                {"anio_min": 2015, "anio_max": 2030, "anios_invalidos": [205, 2580, 3035]},
                ["CORREGIR_FECHA", "MARCAR_SIN_DATO"],
            ),
        },
        pos_validos={"POS-5252"},
        modulos_por_pos={"POS-5252": {1, 2, 3}},
        periodos_por_pos={"POS-5252": (2023, 2025)},
        bridge_docente_pos={("CARLOS MENDOZA", "POS-5252")},
        inscripciones_est_pos={("ANA PEREZ", "POS-5252")},
    )


def test_regla_a_estudiante_programa_y_periodo():
    ctx = _ctx_completo()
    ok = {"categoria": "academico", "resoluciones": {"programa": {"valor_extraido": "POS-5252"}, "fecha": "2024-06-01"}}
    assert validar_registro(ok, ctx) == []

    bad_pos = {"categoria": "academico", "resoluciones": {"programa": {"valor_extraido": "POS-9999"}, "fecha": "2024-06-01"}}
    f1 = validar_registro(bad_pos, ctx)
    assert any(f.regla == "ESTUDIANTE_PROGRAMA_PERIODO" for f in f1)

    bad_per = {"categoria": "academico", "resoluciones": {"programa": {"valor_extraido": "POS-5252"}, "fecha": "2020-01-01"}}
    f2 = validar_registro(bad_per, ctx)
    assert any(f.regla == "ESTUDIANTE_PROGRAMA_PERIODO" for f in f2)


def test_regla_b_modulo_en_programa():
    ctx = _ctx_completo()
    ok = {"categoria": "academico", "resoluciones": {"programa": {"valor_extraido": "POS-5252"}, "numero_modulo": 2}}
    assert validar_registro(ok, ctx) == []

    bad = {"categoria": "academico", "resoluciones": {"programa": {"valor_extraido": "POS-5252"}, "numero_modulo": 9}}
    f = validar_registro(bad, ctx)
    assert len(f) == 1 and f[0].regla == "MODULO_EN_PROGRAMA"


def test_regla_c_docente_modulo_bridge():
    ctx = _ctx_completo()
    ok = {"categoria": "evaluacion_docente", "resoluciones": {"programa": {"valor_extraido": "POS-5252"}, "docente": {"valor_extraido": "Carlos Mendoza"}}}
    assert validar_registro(ok, ctx) == []

    bad = {"categoria": "evaluacion_docente", "resoluciones": {"programa": {"valor_extraido": "POS-5252"}, "docente": {"valor_extraido": "Docente Desconocido"}}}
    f = validar_registro(bad, ctx)
    assert len(f) == 1 and f[0].regla == "DOCENTE_MODULO_BRIDGE"


def test_regla_d_pago_inscripcion_programa():
    ctx = _ctx_completo()
    ok = {"categoria": "financiero", "resoluciones": {"programa": {"valor_extraido": "POS-5252"}, "estudiante": {"valor_extraido": "Ana Pérez"}}}
    assert validar_registro(ok, ctx) == []

    bad = {"categoria": "financiero", "resoluciones": {"programa": {"valor_extraido": "POS-5252"}, "estudiante": {"valor_extraido": "Juan Nadie"}}}
    f = validar_registro(bad, ctx)
    assert len(f) == 1 and f[0].regla == "PAGO_INSCRIPCION_PROGRAMA"


def test_regla_e_respuesta_escala():
    ctx = _ctx_completo()
    ok = {"categoria": "evaluacion_docente", "resoluciones": {"puntuacion": 5, "escala_max": 5}}
    assert validar_registro(ok, ctx) == []

    bad = {"categoria": "evaluacion_docente", "resoluciones": {"puntuacion": 7, "escala_max": 5}}
    f = validar_registro(bad, ctx)
    assert len(f) == 1 and f[0].regla == "RESPUESTA_ESCALA_PREGUNTA"


@pytest.mark.parametrize("fecha_bad", ["0205-03-10", "2580-01-01", "3035-12-31"])
def test_regla_f_fecha_gestion_invalida(fecha_bad):
    ctx = _ctx_completo()
    ok = {"categoria": "academico", "resoluciones": {"fecha": "2024-11-15"}}
    assert validar_registro(ok, ctx) == []

    bad = {"categoria": "academico", "resoluciones": {"fecha": fecha_bad}}
    f = validar_registro(bad, ctx)
    assert len(f) == 1 and f[0].regla == "FECHA_GESTION_VALIDA"


def test_invariantes_cascada_y_umbrales_no_cambian():
    assert cfg.UMBRAL_CONFIANZA_ALTO == 0.85
    assert cfg.UMBRAL_CONFIANZA_MEDIO == 0.60
    assert cfg.BETO_MAX_LENGTH_TOKENS == 128
