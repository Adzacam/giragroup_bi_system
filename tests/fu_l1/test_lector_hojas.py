"""
FU-L1: lector robusto (pipeline/lector_hojas.py) con libros sintéticos y datos ficticios.

Criterio de aceptación: el libro original y su variante (otro archivo, otras hojas, columnas en
otro orden, hojas basura con otros nombres) dan el mismo resultado: hojas usadas, filas leídas y
hojas ignoradas con motivo.
"""

import json
from collections import Counter
from pathlib import Path

import openpyxl
import pandas as pd
import pytest
import yaml

from pipeline import lector_hojas as lh
from pipeline.ingesta import detectar_bloques, leer_archivo, leer_archivo_con_metadatos
from tests.fixtures.fuentes_sinteticas import constructor as ctor

RAIZ = Path(__file__).resolve().parents[2]


def _resultado(libro):
    """Firma comparable del resultado del lector, sin nombres de hoja ni de archivo."""
    usadas = sorted((h.meta.filas_datos, h.meta.filas_subtotal, h.meta.n_formulas_sin_valor)
                    for h in libro.values() if h.usada)
    ignoradas = Counter((h.clasificacion.regla, h.clasificacion.motivo, h.meta.estado)
                        for h in libro.values() if not h.usada)
    return usadas, ignoradas


@pytest.fixture
def par(tmp_path):
    return ctor.construir_par(tmp_path)


# ── Catálogo ─────────────────────────────────────────────────────────

def test_espejo_json_igual_al_yaml():
    """El contenedor sin PyYAML lee pipeline/mapeo_fuentes.json: debe ser el mismo catálogo que el YAML."""
    yaml_ = yaml.safe_load((RAIZ / "config" / "mapeo_fuentes.yaml").read_text(encoding="utf-8"))
    espejo = json.loads((RAIZ / "pipeline" / "mapeo_fuentes.json").read_text(encoding="utf-8"))
    assert yaml_ == espejo, "Correr scripts/auditoria_fuentes/exportar_mapeo_json.py tras editar el YAML"


def test_reglas_de_hoja_tienen_id_motivo_y_condicion_evaluable():
    reglas = lh.reglas_hoja(lh.cargar_config(recargar=True))
    for grupo in ("ignorar_por_estado", "ignorar_por_forma", "ignorar_por_nombre_senal"):
        for r in reglas[grupo]:
            assert r.get("id") and r.get("motivo")
    claves_forma = {"max_filas_datos", "min_proporcion_casi_vacias", "min_proporcion_montos_texto",
                    "max_proporcion_celdas_con_digito", "min_proporcion_duplicadas",
                    "min_proporcion_cabeceras_vacias", "max_densidad"}
    for r in reglas["ignorar_por_forma"]:
        assert set(r) & claves_forma, f"regla de forma sin condición evaluable: {r['id']}"


# ── API compatible ───────────────────────────────────────────────────

def test_api_paralela_devuelve_los_mismos_dataframes(par):
    original, _ = par
    crudo = leer_archivo(str(original))
    libro = leer_archivo_con_metadatos(str(original))
    assert list(crudo) == list(libro)
    for nombre, df in crudo.items():
        pd.testing.assert_frame_equal(df, libro[nombre].df)


def test_archivo_inexistente_devuelve_vacio():
    assert leer_archivo_con_metadatos("ruta/que/no/existe.xlsx") == {}


# ── Metadatos ────────────────────────────────────────────────────────

def test_metadatos_estado_formulas_y_forma(par):
    original, _ = par
    libro = leer_archivo_con_metadatos(str(original))
    datos = libro[ctor.ORIGINAL.hoja_datos].meta
    assert libro[ctor.ORIGINAL.hoja_oculta].meta.estado == "hidden"
    assert datos.estado == "visible"
    assert datos.filas_datos == 6
    assert datos.filas_subtotal == 1
    assert datos.filas_fantasma == ctor.ORIGINAL.filas_fantasma
    assert datos.n_formulas == 6 and datos.n_formulas_sin_valor == 6  # openpyxl no guarda el valor calculado
    assert datos.corte_final == 1 + 6 + 1  # cabecera + datos + subtotal: la cola fantasma se corta
    assert datos.tipo_sugerido == "COBRANZA"


def test_celdas_combinadas_contadas(tmp_path):
    ruta = ctor.construir_encuesta_por_modulo(tmp_path)
    meta = next(iter(leer_archivo_con_metadatos(str(ruta)).values())).meta
    assert meta.n_combinadas == 1
    assert meta.fila_cabecera == 1  # cabecera en la fila 2, bajo la fila de grupo
    assert meta.filas_datos == 6 and meta.filas_fantasma == 40


def test_fila_con_solo_numero_de_orden_es_fantasma_y_no_dato():
    df = pd.DataFrame([["N°", "Programa", "Nota"], ["1", "P-1", "80"], ["2", None, None], ["3", None, None]], dtype=object)
    meta = lh.medir_forma(df, lh.MetadatosHoja(nombre="x", posicion=0))
    assert meta.filas_datos == 1 and meta.filas_fantasma == 2 and meta.corte_final == 2


def test_fantasma_intermedio_se_descarta_sin_cortar_la_isla():
    filas = [["POS", "Programa", "Activo"], ["P-1", "A", "TRUE"], [None, None, "FALSE"], ["P-2", "B", "TRUE"]]
    df = pd.DataFrame(filas, dtype=object)
    meta = lh.medir_forma(df, lh.MetadatosHoja(nombre="x", posicion=0))
    assert meta.filas_descartadas == [2]
    bloques = detectar_bloques(df, filas_transparentes=set(meta.filas_descartadas))
    assert len(bloques) == 1 and len(bloques[0]) == 3  # cabecera + 2 datos; la fantasma no es fila leída
    assert bloques[0].attrs["fila_inicio"] == 0 and bloques[0].attrs["fila_fin"] == 3


def test_detectar_bloques_sin_transparentes_no_cambia():
    df = pd.DataFrame([["a", "b"], ["1", "2"], [None, None], [None, None], ["c", "d"], ["3", "4"]], dtype=object)
    assert [len(b) for b in detectar_bloques(df)] == [len(b) for b in detectar_bloques(df, filas_transparentes=None)] == [2, 2]


# ── Clasificación ────────────────────────────────────────────────────

def test_clasificacion_por_estado_forma_y_nombre(par):
    original, _ = par
    libro = leer_archivo_con_metadatos(str(original))
    r = {n: h.clasificacion.regla for n, h in libro.items()}
    o = ctor.ORIGINAL
    assert libro[o.hoja_datos].usada and r[o.hoja_datos] == "tabla_de_datos"
    assert r[o.hoja_oculta] == "oculta"
    assert r[o.hoja_borrador] == "borrador"
    assert r[o.hoja_copia] == "copia"
    assert r[o.hoja_dinamica] == "sin_filas_de_datos"
    assert r[o.hoja_numerada] == "hoja_numerada"
    assert r[o.hoja_resumen] == "resumen_montos_texto"
    # Ninguna hoja sin decisión ni motivo
    assert all(h.clasificacion.decision in ("usar", "ignorar") and h.clasificacion.motivo for h in libro.values())


def test_criterio_aceptacion_original_y_variante_identicos(par):
    original, variante = par
    a = leer_archivo_con_metadatos(str(original))
    b = leer_archivo_con_metadatos(str(variante))
    assert list(a) != list(b)  # otros nombres y otro orden de hojas
    assert _resultado(a) == _resultado(b)
    datos_a = a[ctor.ORIGINAL.hoja_datos].meta
    datos_b = b[ctor.VARIANTE.hoja_datos].meta
    assert datos_a.campos_por_tipo == datos_b.campos_por_tipo  # mismas columnas canónicas en otro orden
    assert datos_a.tipo_sugerido == datos_b.tipo_sugerido == "COBRANZA"


def test_nombre_es_solo_senal_la_unica_hoja_se_usa(tmp_path):
    """Un libro de una sola hoja «Hoja 1» (nombre por defecto) no se queda sin datos."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hoja 1"
    for r, fila in enumerate([["POS", "PROGRAMA", "LEADS"], ["P-1", "A", 10], ["P-2", "B", 20]], start=1):
        for c, v in enumerate(fila, start=1):
            ws.cell(row=r, column=c, value=v)
    ruta = tmp_path / "unica.xlsx"
    wb.save(ruta)
    h = leer_archivo_con_metadatos(str(ruta))["Hoja 1"]
    assert h.usada and h.clasificacion.regla == "unica_tabla"
    assert "nombre" in (h.clasificacion.aviso or "")


def test_oculta_se_ignora_aunque_sea_la_unica_hoja_con_datos(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Visible vacía"
    wo = wb.create_sheet("Datos")
    for r, fila in enumerate([["POS", "PROGRAMA"], ["P-1", "A"], ["P-2", "B"]], start=1):
        for c, v in enumerate(fila, start=1):
            wo.cell(row=r, column=c, value=v)
    wo.sheet_state = "veryHidden"
    ruta = tmp_path / "oculta.xlsx"
    wb.save(ruta)
    libro = leer_archivo_con_metadatos(str(ruta))
    assert libro["Datos"].clasificacion.regla == "oculta"
    assert libro["Datos"].meta.estado == "veryHidden"


def test_excepcion_del_catalogo_rescata_hoja_por_nombre():
    reglas = lh.reglas_hoja()
    meta = lh.MetadatosHoja(nombre="IBP", posicion=0, filas_datos=1, celdas_datos=4, celdas_con_digito=2)
    decision, regla, _, _ = lh._clasificar_sola(meta, reglas)  # caería en «una sola fila»
    assert decision == "usar" and regla == "excepcion"


def test_csv_se_clasifica_por_forma(tmp_path):
    ruta = tmp_path / "datos.csv"
    ruta.write_text("POS,PROGRAMA,LEADS\nP-1,A,10\nP-2,B,20\n", encoding="utf-8")
    libro = leer_archivo_con_metadatos(str(ruta))
    h = next(iter(libro.values()))
    assert h.usada and h.meta.filas_datos == 2 and h.meta.estado == "visible"


# ── Tipo por hoja (contenido, no nombre) ─────────────────────────────

def test_hoja_de_planificacion_en_libro_de_actas_toma_su_tipo(tmp_path):
    ruta = ctor.construir_libro_mixto(tmp_path)
    libro = leer_archivo_con_metadatos(str(ruta))
    plan = libro["Planificación por POS"].meta
    assert plan.tipo_sugerido == "PLANIFICACION"
    assert lh.tipo_de_hoja_distinto(plan, "ACTA") == "PLANIFICACION"
    actas = libro["Notas"].meta
    assert lh.tipo_de_hoja_distinto(actas, "ACTA") is None


def test_tipo_de_hoja_no_cambia_con_tipo_desconocido_o_misma_categoria():
    meta = lh.MetadatosHoja(nombre="x", posicion=0, cabeceras=["EJECUTADO 2024", "META 2025", "NRO POS"])
    meta.campos_por_tipo = lh.campos_por_tipo(meta.cabeceras)
    meta.tipo_sugerido = lh.tipo_sugerido(meta.campos_por_tipo)
    assert lh.tipo_de_hoja_distinto(meta, "ADMISION") is None      # tipo del libro fuera del catálogo
    assert lh.tipo_de_hoja_distinto(meta, "RENTABILIDAD") is None  # misma categoría de staging


# ── PII ──────────────────────────────────────────────────────────────

def test_cabecera_con_correo_se_enmascara(tmp_path):
    receta = ctor.Receta(**{**ctor.ORIGINAL.__dict__, "archivo": "con_correo.xlsx", "con_correo_en_cabecera": True})
    ruta = ctor.construir(receta, tmp_path)
    libro = leer_archivo_con_metadatos(str(ruta))
    texto = json.dumps([h.meta.como_dict() for h in libro.values()] + lh.resumen_publico(libro), ensure_ascii=False)
    assert ctor.CORREO_FICTICIO not in texto
    assert "col_13" in libro[receta.hoja_datos].meta.cabeceras
    for ci in ctor.CIS_FICTICIOS:
        assert ci not in texto


def test_enmascarar_utilidades():
    assert lh.cabecera_segura("a.b@ejemplo.test", 3) == "col_3"
    assert lh.cabecera_segura("PE\nA", 2) == "PE\nA"  # no toca cabeceras sin PII (las líneas no cambian)
    assert lh.enmascarar_cabecera("  TOTAL   PAGADO ", 1) == "TOTAL PAGADO"
    assert lh.enmascarar_texto("Hoja de 1234567 y x@y.test") == "Hoja de <numero> y <correo>"
