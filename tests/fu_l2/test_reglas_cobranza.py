"""
FU-L2: reglas puras de cobranza (sin base de datos) y coherencia de esquema, migración y principio rector.
"""

import ast
import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"


# ── DA3: una sola regla de mora ───────────────────────────────────────

def test_da3_mora_es_dos_o_mas_cuotas():
    from services.regla_mora import UMBRAL_CUOTAS_MORA, es_mora, estado_cartera_da3
    assert UMBRAL_CUOTAS_MORA == 2
    assert [es_mora(n) for n in (None, 0, 1, 2, 3, 9)] == [False, False, False, True, True, True]
    assert [estado_cartera_da3(n) for n in (None, 0, 1, 2)] == [None, "Vigente", "Vigente", "Mora"]


def test_umbral_sale_del_catalogo_de_mapeo():
    from pipeline.lector_hojas import cargar_config
    cfg = cargar_config()["tipos_fuente"]["COBRANZA"]
    assert cfg["regla_mora"]["umbral_cuotas"] == 2


def test_alerta_financiera_usa_la_misma_regla():
    from services.dw_loader import calcular_tipo_alerta_financiera
    assert [calcular_tipo_alerta_financiera(n) for n in (0, 1, 2, 7)] == ["NORMAL", "MORA_TEMPRANA", "RIESGO_CARTERA", "RIESGO_CARTERA"]


def test_estado_de_cartera_derivado_ignora_dias_y_rango_de_mora():
    from routers.dataops.consolidacion import derivar_estado_cartera
    # antes, un solo día de mora o un rango 'd) Mayor 361' bastaban para «Mora» (KPI-05 ~ 94 %)
    assert derivar_estado_cartera({"DIAS DE MORA": "400", "RANGO MORA": "d) Mayor 361", "TIPO DE CARTERA": "CARTERA INCOBRABLE"}, 1) == "Vigente"
    assert derivar_estado_cartera({}, 2) == "Mora"


def test_riesgo_cruzado_usa_el_maximo_por_hecho_no_la_suma():
    from services.regla_mora import es_mora
    # dos programas con 1 cuota cada uno no son mora (antes la suma 1+1 = 2 lo era)
    assert not es_mora(max(1, 1))
    assert es_mora(max(2, 0))


# ── Lectura por campos canónicos ──────────────────────────────────────

@pytest.mark.parametrize("crudo,esperado", [
    (None, (None, None)), ("", (None, None)), ("0", (0, None)), ("3", (3, None)), ("2.0", (2, None)),
    ("-5", (0, "CUOTAS_NEGATIVAS")), ("1s", (1, "CUOTAS_CON_TEXTO")), ("abc", (0, "CUOTAS_NO_NUMERICAS")),
])
def test_leer_cuotas(crudo, esperado):
    from services.cobranza_canonica import leer_cuotas
    assert leer_cuotas(crudo) == esperado


@pytest.mark.parametrize("crudo,canon,ok", [
    ("CARTERA CERRADA", "CERRADA", True), ("cartera vigente", "VIGENTE", True), ("Cartera En Mora", "EN MORA", True),
    ("CARTERA PREVISIONABLE", "PREVISIONABLE", True), ("cartera incobrable", "INCOBRABLE", True),
    ("CARTERA RARA", None, False), (None, None, True), ("  ", None, True),
])
def test_vocabulario_de_cartera(crudo, canon, ok):
    from services.cobranza_canonica import normalizar_estado_cartera
    assert normalizar_estado_cartera(crudo) == (canon, ok)


def test_mes_de_columna_y_exclusion_de_preliminar():
    from services.cobranza_canonica import campo_de_cabecera, mes_de_columna
    assert mes_de_columna("MONTO ENERO 2024") == (2024, 1)
    assert mes_de_columna("pago septiembre 2025") == (2025, 9)
    assert mes_de_columna("TIPO DE CARTERA") is None
    assert campo_de_cabecera("MONTO MARZO 2025")[0] == "monto_pago_mes"
    assert campo_de_cabecera("MONTO SEPTIEMBRE 2025 (PRELIMINAR)") is None
    assert campo_de_cabecera("MONTO A COBRAR DESPUES DE DESCUENTO") is None


def test_tres_columnas_mora_tienen_tres_destinos():
    from services.cobranza_canonica import campo_de_cabecera
    assert campo_de_cabecera("DIAS DE MORA")[0] == "dias_mora"
    assert campo_de_cabecera("TOTAL CUOTAS EN MORA")[0] == "cuotas_en_mora"
    assert campo_de_cabecera("RANGO MORA") is None            # descriptiva: no_mapear
    campo, _, ambiguo = campo_de_cabecera("MORA")
    assert campo == "cuotas_en_mora" and ambiguo is True


def test_cabecera_ambigua_solo_vale_si_no_hay_especifica():
    from services.cobranza_canonica import leer_fila
    con_ambas = leer_fila({"MORA": "99", "TOTAL CUOTAS EN MORA": "1"})
    assert con_ambas.cuotas_impagas == 1
    sola = leer_fila({"MORA": "4", "DEUDA TOTAL": "10"})
    assert sola.cuotas_impagas == 4


def test_fila_sin_campos_de_cobranza_va_al_camino_generico():
    from services.cobranza_canonica import leer_fila
    assert leer_fila({"POS": "POS-1", "CI": "123"}) is None


def test_fila_lee_pagos_por_mes_deuda_y_estado():
    from services.cobranza_canonica import registros_cobranza
    campos = {"TIPO DE CARTERA": "CARTERA EN MORA", "TOTAL CUOTAS EN MORA": "-3", "DIAS DE MORA": "30",
              "DEUDA TOTAL": "-50", "MONTO ENERO 2024": "10", "MONTO FEBRERO 2025": "5,5",
              "MONTO ENERO 2026 (PRELIMINAR)": "999", "FECHA INICIO DIPLOMADO": "2024-02-10"}
    regs, fila = registros_cobranza(campos)
    sit, *pagos = regs
    assert sit["cuotas_impagas"] == 0 and sit["monto_deuda"] == 0.0 and sit["estado_cartera_fuente"] == "EN MORA"
    assert sit["dias_mora"] == 30 and sit["fecha"].isoformat() == "2024-02-10"
    assert [(p["fecha"].isoformat(), p["monto_pagado"]) for p in pagos] == [("2024-01-01", 10.0), ("2025-02-01", 5.5)]
    assert {a.motivo for a in fila.avisos} == {"CUOTAS_NEGATIVAS", "SOBREPAGO"}
    # todos los pagos resuelven la identidad con la fecha de la fila, no la del mes del pago
    assert {p["fecha_identidad"] for p in regs} == {sit["fecha"]}


def test_valor_fuera_de_catalogo_no_se_descarta_va_a_revision():
    from services.cobranza_canonica import registros_cobranza
    regs, fila = registros_cobranza({"TIPO DE CARTERA": "CARTERA XYZ", "TOTAL CUOTAS EN MORA": "0"})
    assert regs[0]["estado_cartera_fuente"] is None and regs[0]["_revision_fila"] is True
    assert [a.motivo for a in fila.avisos] == ["VALOR_FUERA_DE_CATALOGO"]


# ── Fusión de hechos con la misma clave única ─────────────────────────

def test_fusion_suma_pagos_y_conserva_cuotas_y_deuda():
    from services.dw_loader import fusionar_hechos_financieros
    situacion = {"concepto": "SITUACION_CARTERA", "monto_deuda": 100.0, "monto_pagado": 0.0, "cuotas_impagas": 2,
                 "estado_cartera_fuente": "CERRADA", "dias_mora": 10, "requiere_revision": False}
    pago = {"concepto": "PAGO_MES", "monto_deuda": None, "monto_pagado": 30.0, "cuotas_impagas": None,
            "estado_cartera_fuente": None, "dias_mora": None, "requiere_revision": True}
    f = fusionar_hechos_financieros(situacion, pago)
    assert f["monto_pagado"] == 30.0 and f["monto_deuda"] == 100.0 and f["cuotas_impagas"] == 2
    assert f["concepto"] == "SITUACION_CARTERA" and f["estado_cartera"] == "Mora" and f["estado_cartera_fuente"] == "CERRADA"
    assert f["requiere_revision"] is True
    dos_pagos = fusionar_hechos_financieros(pago, {**pago, "monto_pagado": 20.0})
    assert dos_pagos["monto_pagado"] == 50.0 and dos_pagos["cuotas_impagas"] is None and dos_pagos["estado_cartera"] is None


# ── Catálogo: YAML y espejo JSON ──────────────────────────────────────

def test_espejo_json_igual_al_yaml():
    yaml = pytest.importorskip("yaml")
    datos = yaml.safe_load((RAIZ / "config" / "mapeo_fuentes.yaml").read_text(encoding="utf-8"))
    espejo = json.loads((RAIZ / "pipeline" / "mapeo_fuentes.json").read_text(encoding="utf-8"))
    assert datos == espejo


# ── Esquema y migración: coherentes y no destructivos ─────────────────

def test_modelo_esquema_y_migracion_declaran_las_mismas_columnas_nuevas():
    schema = (RAIZ / "db" / "schema.sql").read_text(encoding="utf-8")
    mig = (BACKEND / "scripts" / "migrations" / "022_fu_l2_cobranza_mora_da3.sql").read_text(encoding="utf-8")
    modelo = (BACKEND / "models" / "fact_financiero.py").read_text(encoding="utf-8")
    for col in ("estado_cartera_fuente", "dias_mora"):
        assert col in schema and col in mig and col in modelo
        assert re.search(rf"ADD COLUMN IF NOT EXISTS {col}\b", mig)


def test_migracion_022_no_es_destructiva_ni_crea_tablas():
    mig = (BACKEND / "scripts" / "migrations" / "022_fu_l2_cobranza_mora_da3.sql").read_text(encoding="utf-8")
    sin_comentarios = "\n".join(l.split("--")[0] for l in mig.splitlines())
    assert not re.search(r"\b(DROP|TRUNCATE|DELETE\s+FROM|CREATE\s+TABLE)\b", sin_comentarios, re.I)
    assert "BEGIN;" in sin_comentarios and "COMMIT;" in sin_comentarios
    assert "ON CONFLICT (version) DO NOTHING" in sin_comentarios            # reaplicable
    # DA3 en las tres vistas bi: el mismo umbral
    for vista in ("bi.vw_cmi_valores", "bi.vw_cartera_estado", "bi.vw_riesgo_estudiante"):
        assert f"CREATE OR REPLACE VIEW {vista}" in sin_comentarios
    assert len(re.findall(r">= 2\b", sin_comentarios)) >= 4
    assert "Previsionable" not in sin_comentarios.split("CREATE OR REPLACE VIEW bi.vw_cmi_valores")[1]


# ── Principio rector: nada de nombres de columna, archivo ni «contiene MORA» en el código ──

ARCHIVOS_FLUJO = ["services/cobranza_canonica.py", "services/regla_mora.py", "services/dw_loader.py"]
CABECERAS_DE_LA_FUENTE = ["TIPO DE CARTERA", "TOTAL CUOTAS EN MORA", "DIAS DE MORA", "RANGO MORA", "DEUDA TOTAL",
                          "COBRANZAS 2024 2025", "BD Cobranzas", "TOTAL PAGADO HASTA LA FECHA", "FECHA INICIO DIPLOMADO"]


def _literales(ruta: Path):
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    docs = {id(n.value) for n in ast.walk(arbol) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
    return [(n.lineno, n.value) for n in ast.walk(arbol)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


@pytest.mark.parametrize("rel", ARCHIVOS_FLUJO)
def test_el_codigo_de_cobranza_no_quema_cabeceras_ni_nombres_de_libro(rel):
    prohibidos = [c.lower() for c in CABECERAS_DE_LA_FUENTE]
    quemados = [(rel, n, v) for n, v in _literales(BACKEND / rel) if any(p in v.lower() for p in prohibidos)]
    assert not quemados


@pytest.mark.parametrize("rel", ARCHIVOS_FLUJO + ["services/ingestion_service.py", "routers/dataops/consolidacion.py"])
def test_ninguna_regla_decide_la_mora_por_contiene_mora(rel):
    texto = (BACKEND / rel).read_text(encoding="utf-8")
    assert not re.search(r"""["']MORA["']\s+in\s""", texto), f"{rel}: «'MORA' in …» decide la mora por texto"
