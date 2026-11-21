"""ADW L8: revisión humana (DA7 y D2).

- Filas sin estudiante: catálogo y docentes se descartan con motivo; sin identidad o con dinero van a la bandeja.
- Aprobación en bloque y revelación de datos no cuentan como corrección humana.
- Las discordancias de nombre se agrupan por patrón de similitud.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from services.extraccion_por_encabezado import (  # noqa: E402
    MOTIVOS_A_BANDEJA, campos_por_encabezado, motivo_fila_sin_entidad,
)

IBP = "N°: 1 | POS - IBP: POS-5000 | NOMBRE DEL PROGRAMA: DIPLOMADO X | VERSIÓN: 1 | MES IBP: 3 | AÑO IBP: 2025 | PUNTO EQUILIBRIO: 20"
DOCENTE = "N°: 3 | POS - MODULO: POS-5381 | N° POS: 5381 | DOCENTE: Fulano | HRS MODULO: 20 | PAGO DOCENTE: 100"
CATALOGO_FIN = "POS: POS-5008 | NOMBRE DEL PROGRAMA: DIPLOMADO X | INSCRITOS: 5 | COSTO PROGRAMA: 100 | TIPO DE PROGRAMA: DIPLOMADO"
FACTURA = "Fecha de Facturación: 2025-01-01 | N° de Factura: 123 | NIT: 99 | Razón Social: ACME | Monto en Bs.: 100 | Carrera: X"
ESTADO = "Estado académico: Aprobado | Estado ARCA: Titulado"
CON_ALUMNO = "CI: 1234567 | Nombre: Ana Pérez | Nota: 80"


def _motivo(linea, categoria):
    return motivo_fila_sin_entidad(campos_por_encabezado([c.strip() for c in linea.split("|")]), categoria)


@pytest.mark.parametrize("linea,categoria,esperado", [
    (IBP, "academico", "CATALOGO_PROGRAMA_NO_ALUMNO"),
    (DOCENTE, "academico", "DOCENTE_NO_ESTUDIANTE"),
    (CATALOGO_FIN, "financiero", "CATALOGO_PROGRAMA_NO_PAGO"),
    (FACTURA, "financiero", "FILA_SIN_IDENTIDAD"),
    (ESTADO, "academico", "FILA_SIN_IDENTIDAD"),
    (CON_ALUMNO, "academico", None),
    ("", "academico", "FILA_SIN_CABECERAS"),  # una fila vacía ya se descarta sola
])
def test_motivo_de_las_filas_sin_estudiante(linea, categoria, esperado):
    assert _motivo(linea, categoria) == esperado


def test_solo_la_fila_sin_identidad_va_a_la_bandeja():
    assert MOTIVOS_A_BANDEJA == {"FILA_SIN_IDENTIDAD"}


def test_fila_sin_identidad_queda_pendiente_y_el_catalogo_descartado(dw_sqlite):
    from routers.dataops.consolidacion import _registrar_descarte_ruido

    stg = SimpleNamespace(id_documento=1, id=1, hoja="Hoja", fila_inicio=0)
    pend, desc, logs = [], [], []
    _registrar_descarte_ruido(dw_sqlite, stg, FACTURA, 0.5, "FILA_SIN_IDENTIDAD", "COBRANZA", logs_out=logs, stg_out=pend, pendiente=True)
    _registrar_descarte_ruido(dw_sqlite, stg, CATALOGO_FIN, 0.9, "CATALOGO_PROGRAMA_NO_PAGO", "COBRANZA", logs_out=logs, stg_out=desc)

    p, d = pend[0], desc[0]
    assert (p.tipo_entidad, p.resuelto, p.estado_resolucion, p.motivo) == ("ESTUDIANTE", False, "PENDIENTE", "FILA_SIN_IDENTIDAD")
    assert "descarte" not in p.payload_json
    assert (d.tipo_entidad, d.resuelto, d.estado_resolucion, d.motivo) == ("RUIDO", True, "DESCARTADO", "CATALOGO_PROGRAMA_NO_PAGO")
    assert [l.estado_resolucion for l in logs] == ["PENDIENTE", "DESCARTADO"]


def test_los_motivos_nuevos_tienen_texto_para_la_bandeja():
    from services.revision_consulta import motivo_publico

    for m in ("FILA_SIN_IDENTIDAD", "CATALOGO_PROGRAMA_NO_ALUMNO", "CATALOGO_PROGRAMA_NO_PAGO", "DOCENTE_NO_ESTUDIANTE"):
        assert "_" not in motivo_publico(m)


# ── D2 ───────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("valor,es_correccion,accion", [
    ("APROBACION_BLOQUE", False, "Aprobación en bloque (sin cambios)"),
    ("Aprobación en bloque sin cambios", False, "Aprobación en bloque (sin cambios)"),   # filas históricas
    ("REVELAR_CI_AUTORIZADO (admin)", False, "Revelación autorizada de dato personal"),
    ("Aprobación en bloque con corrección (fecha)", True, "Resolución HITL: Validación de Entidad"),
    ("Aprobado sin cambios", True, "Resolución HITL: Validación de Entidad"),
    ("Descartado", True, "Resolución HITL: Validación de Entidad"),
])
def test_que_cuenta_como_correccion_humana(valor, es_correccion, accion):
    from services.auditoria_hitl import accion_de_auditoria, es_correccion_humana

    assert es_correccion_humana(valor) is es_correccion
    assert accion_de_auditoria(valor) == accion


# ── agrupación por patrón ─────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("score,patron", [(None, "Sin similitud"), (0, "muy distinto"), (29.9, "muy distinto"),
                                           (30, "parcialmente"), (59, "parcialmente"), (60, "casi igual"), (100, "casi igual")])
def test_patron_de_discordancia(score, patron):
    from services.bandeja_grupos import patron_discordancia

    assert patron in patron_discordancia(score)


def test_discordancias_con_ci_distintas_se_agrupan_por_patron(dw_sqlite):
    from models.staging_entidad import StagingEntidadNoResuelta as S
    from services.bandeja_grupos import grupos_pendientes

    casos = [(1001, 12), (1002, 25), (1003, 45), (1004, 80)]
    for ci, score in casos:
        dw_sqlite.add(S(id_documento=43, tipo_entidad="ESTUDIANTE", texto_original=f"CI: {ci} | NOMBRE: X", fk_estado="C",
                        resuelto=False, motivo="CI_NOMBRE_DISCORDANTE", score_fuzzy=score, estado_resolucion="PENDIENTE"))
    dw_sqlite.commit()
    res = grupos_pendientes(dw_sqlite, [43])
    discordantes = [g for g in res["grupos"] if g["motivo"] == "CI_NOMBRE_DISCORDANTE"]
    assert len(discordantes) == 4, "la aprobación sigue siendo por CI: personas distintas no se juntan"
    por_patron = {p["patron"].split(" (")[0]: (p["n"], p["grupos"]) for p in res["patrones"]}
    assert por_patron["Nombre muy distinto"] == (2, 2)
    assert sum(n for n, _ in por_patron.values()) == 4
