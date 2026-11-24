"""Pruebas unitarias F6-2a, F6-2b y F6-2c: Limpieza de falsos positivos HITL."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

RAIZ = Path(__file__).resolve().parents[2]
for p in (str(RAIZ), str(RAIZ / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from services import encuesta_canonica
from services.extraccion_por_encabezado import fila_resuelta_por_regla
from services.dw_loader import DWLoaderService
from models.log_inconsistencia import LogInconsistencia
from models.staging_entidad import StagingEntidadNoResuelta


def test_f6_2a_encuesta_likert_sin_programa_resuelta_por_regla():
    filas = [
        {
            "EL DOCENTE DOMINA EL TEMA Y RESPONDE CON CLARIDAD?": "5/Totalmente de acuerdo",
            "EL MATERIAL DEL CURSO FUE ADECUADO PARA EL APRENDIZAJE?": "4/De acuerdo",
            "RECOMENDARIA EL PROGRAMA A UN COLEGA? (ESCALA 1 A 10)": "9",
        },
        {
            "EL DOCENTE DOMINA EL TEMA Y RESPONDE CON CLARIDAD?": "4/De acuerdo",
            "EL MATERIAL DEL CURSO FUE ADECUADO PARA EL APRENDIZAJE?": "5/Totalmente de acuerdo",
            "RECOMENDARIA EL PROGRAMA A UN COLEGA? (ESCALA 1 A 10)": "10",
        },
        {
            "EL DOCENTE DOMINA EL TEMA Y RESPONDE CON CLARIDAD?": "5/Totalmente de acuerdo",
            "EL MATERIAL DEL CURSO FUE ADECUADO PARA EL APRENDIZAJE?": "5/Totalmente de acuerdo",
            "RECOMENDARIA EL PROGRAMA A UN COLEGA? (ESCALA 1 A 10)": "8",
        },
    ]
    perfil = encuesta_canonica.perfilar(filas)
    assert fila_resuelta_por_regla(filas[0], "evaluacion_docente", perfil_encuesta=perfil) is True


def test_f6_2b_auto_hidratacion_placeholder_sin_hitl_y_colision_real_en_hitl():
    db = MagicMock()
    est_ph = SimpleNamespace(
        id_estudiante=101,
        ci="6543269",
        ci_numero="6543269",
        ci_complemento=None,
        nombre_completo="Estudiante 6543269",
        programa_origen=None,
        deprecado=False,
    )
    q = db.query.return_value
    q.filter.return_value.order_by.return_value.first.return_value = est_ph

    dw = DWLoaderService(db)
    dw._registrar_staging_si_nuevo = MagicMock(return_value=True)
    id_est, estado = dw.resolver_o_crear_estudiante(ci="6543269", nombre="Lucia Salas Nina", doc_id=1)

    assert id_est == 101
    assert estado == "A"
    assert est_ph.nombre_completo == "Lucia Salas Nina"
    dw._registrar_staging_si_nuevo.assert_not_called()
    assert any(
        isinstance(call.args[0], LogInconsistencia) and call.args[0].tipo_regla == "PLACEHOLDER_HIDRATADO"
        for call in db.add.call_args_list
    )

    # Colisión real de dos personas distintas con el mismo CI -> sigue en HITL
    db2 = MagicMock()
    est_real = SimpleNamespace(
        id_estudiante=102,
        ci="7771148",
        ci_numero="7771148",
        ci_complemento=None,
        nombre_completo="Lopez Maria Ana",
        programa_origen=None,
        deprecado=False,
    )
    db2.query.return_value.filter.return_value.order_by.return_value.first.return_value = est_real
    dw2 = DWLoaderService(db2)
    dw2._registrar_staging_si_nuevo = MagicMock(return_value=True)
    id_est2, estado2 = dw2.resolver_o_crear_estudiante(ci="7771148", nombre="Mary Helen Flores Lino", doc_id=1)

    assert id_est2 is None
    assert estado2 == "C"
    dw2._registrar_staging_si_nuevo.assert_called_once()
    stg_arg = dw2._registrar_staging_si_nuevo.call_args.args[0]
    assert isinstance(stg_arg, StagingEntidadNoResuelta)
    assert stg_arg.motivo == "CI_NOMBRE_DISCORDANTE"


def test_f6_2c_homonimia_candidato_unico_100_resuelve_directo_y_dos_distintos_hitl():
    db = MagicMock()
    est1 = SimpleNamespace(id_estudiante=201, nombre_completo="Juan Carlos Perez Gomez", deprecado=False)
    est2 = SimpleNamespace(id_estudiante=202, nombre_completo="Juan Carlos Perez Gomez", deprecado=False)

    dw = DWLoaderService(db)
    dw._registrar_staging_si_nuevo = MagicMock(return_value=True)
    dw._candidatos_estudiante_fuzzy = MagicMock(return_value=[(est1, 100.0)])

    # 1 único candidato con score 100% (>= 92%) en otro programa -> resuelve directo sin HOMONIMIA
    id_est, estado = dw.resolver_o_crear_estudiante(ci=None, nombre="Juan Carlos Perez Gomez", doc_id=1, programa="POS-5000")
    assert id_est == 201
    assert estado == "B"
    dw._registrar_staging_si_nuevo.assert_not_called()

    # 2 id_estudiante distintos >= 90% sin desempate -> HOMONIMIA real en HITL
    dw._candidatos_estudiante_fuzzy = MagicMock(return_value=[(est1, 100.0), (est2, 98.0)])
    dw._desempatar_homonimos = MagicMock(return_value=None)
    id_est_c, estado_c = dw.resolver_o_crear_estudiante(ci=None, nombre="Juan Carlos Perez Gomez", doc_id=1, programa="POS-5000")
    assert id_est_c is None
    assert estado_c == "C"
    dw._registrar_staging_si_nuevo.assert_called_once()
    assert dw._registrar_staging_si_nuevo.call_args.args[0].motivo == "HOMONIMIA"
