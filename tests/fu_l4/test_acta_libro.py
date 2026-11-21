"""
FU-L4 (DA-FU2, DA2-bis, estados y CI con complemento): el acta de punta a punta (ingesta -> consolidación -> DW SQLite) con
libros sintéticos de datos ficticios, sin nombres de archivo, de hoja ni índices de columna en el código.

- resultado canónico por módulo (número o vocabulario) y nota_final numérica;
- un 0 es INASISTENCIA con estado Deserción o Abandono y un 0 real si no;
- notas mayores de 100 o texto fuera del catálogo: NULL, a revisión y avisos agregados sin el valor;
- estados con otras mayúsculas y acentos dan los mismos estados; un estado desconocido no se descarta;
- un CI con complemento o ciudad resuelve al mismo estudiante que su versión sin complemento (estado A);
- la variante (otro nombre de archivo y de hoja, columnas en otro orden, sinónimos, hoja oculta y borrador) da el mismo resultado.
"""

from collections import Counter

from sqlalchemy import text

from tests.fixtures.fuentes_sinteticas import actas
from tests.fu_l4.conftest import cargar_acta, dw_a, dw_b, entorno  # noqa: F401


def hechos(db):
    """{(ci_numero, módulo): (nota_final, resultado)}"""
    filas = db.execute(text(
        "SELECT e.ci_numero, m.nombre_modulo, f.nota_final, f.resultado FROM fact_rendimiento_academico f "
        "JOIN dim_estudiante e ON e.id_estudiante = f.id_estudiante JOIN dim_modulo m ON m.id_modulo = f.id_modulo")).fetchall()
    return {(ci, mod): (None if n is None else float(n), res) for ci, mod, n, res in filas}


def esperado():
    return {k: (None if n is None else float(n), r) for k, (n, r) in actas.ESPERADO.items()}


def estados(db):
    filas = db.execute(text(
        "SELECT e.ci_numero, f.estado_academico, f.estado_tutoria, f.estado_arca, f.estado_de_fuente, f.requiere_revision "
        "FROM fact_rendimiento_academico f JOIN dim_estudiante e ON e.id_estudiante = f.id_estudiante")).fetchall()
    return sorted({(ci, a, t, r, bool(fu), bool(rev)) for ci, a, t, r, fu, rev in filas}, key=str)


def avisos(db):
    from models.log_inconsistencia import LogInconsistencia
    return {(l.tipo_regla, l.campo_afectado, l.estado_resolucion): l for l in db.query(LogInconsistencia).all()
            if l.tipo_regla in ("NOTA_FUERA_DE_RANGO", "VALOR_FUERA_DE_CATALOGO", "CERO_COMO_INASISTENCIA")}


def test_resultado_por_modulo_segun_el_numero_o_el_vocabulario(dw_a, entorno):
    cargar_acta(dw_a, actas.construir(actas.ORIGINAL, entorno))
    assert hechos(dw_a) == esperado()


def test_cero_es_inasistencia_solo_con_desercion_o_abandono(dw_a, entorno):
    cargar_acta(dw_a, actas.construir(actas.ORIGINAL, entorno))
    h = hechos(dw_a)
    assert h[("9100002", "POS-9001 · Módulo 2")] == (None, "INASISTENCIA")      # 0 de un desertor
    assert h[("9100003", "POS-9001 · Módulo 1")] == (0.0, "REPROBADO")           # 0 real de un reprobado
    assert h[("9100007", "POS-9002 · Módulo 1")] == (0.0, "REPROBADO")           # 0 real de un aprobado: queda como la fuente lo dice


def test_nota_mayor_de_100_y_texto_fuera_de_catalogo_quedan_en_null_y_a_revision(dw_a, entorno):
    cargar_acta(dw_a, actas.construir(actas.ORIGINAL, entorno))
    filas = dw_a.execute(text(
        "SELECT m.nombre_modulo, f.nota_final, f.resultado, f.requiere_revision FROM fact_rendimiento_academico f "
        "JOIN dim_estudiante e ON e.id_estudiante = f.id_estudiante JOIN dim_modulo m ON m.id_modulo = f.id_modulo "
        "WHERE e.ci_numero = '9100005' ORDER BY 1")).fetchall()
    # las dos celdas dudosas no generan hecho (nota NULL); la fila queda en revisión y el módulo válido sigue cargado
    assert [(m, float(n), r, bool(rev)) for m, n, r, rev in filas] == [("POS-9001 · Módulo 3", 90.0, "APROBADO", True)]
    av = avisos(dw_a)
    assert ("NOTA_FUERA_DE_RANGO", "nota_modulo", "PENDIENTE") in av
    assert ("VALOR_FUERA_DE_CATALOGO", "nota_modulo", "PENDIENTE") in av
    assert ("CERO_COMO_INASISTENCIA", "nota_modulo", "REGISTRADO") in av


def test_los_avisos_son_agregados_y_no_publican_el_valor(dw_a, entorno):
    cargar_acta(dw_a, actas.construir(actas.ORIGINAL, entorno))
    for clave in (("NOTA_FUERA_DE_RANGO", "nota_modulo", "PENDIENTE"), ("VALOR_FUERA_DE_CATALOGO", "nota_modulo", "PENDIENTE")):
        aviso = avisos(dw_a)[clave]
        assert aviso.fila_origen is None
        assert "3481044" not in aviso.valor_recibido and "LOZADA" not in aviso.valor_recibido.upper()
        assert "1 celda" in aviso.descripcion


def test_estados_normalizados_y_el_desconocido_no_se_descarta(dw_a, entorno):
    cargar_acta(dw_a, actas.construir(actas.ORIGINAL, entorno))
    por_ci = {e[0]: e for e in estados(dw_a)}
    assert por_ci["9100002"][1:4] == ("Deserción", "Deserción", "No Titulado")
    assert por_ci["9100004"][1:4] == ("Participó", "Abandono", "No Titulado")
    assert por_ci["9100008"][1] == "Egresado"                       # fuera de catálogo: se guarda como vino
    assert por_ci["9100008"][5] is True                              # y queda en revisión
    assert ("VALOR_FUERA_DE_CATALOGO", "estado_academico", "PENDIENTE") in avisos(dw_a)
    assert all(e[4] for e in estados(dw_a))                           # el estado viene de la fuente


def test_ci_con_complemento_resuelve_al_mismo_estudiante_en_estado_a(dw_a, entorno):
    cargar_acta(dw_a, actas.construir(actas.ORIGINAL, entorno))
    est = dw_a.execute(text("SELECT id_estudiante, ci_numero, ci_complemento FROM dim_estudiante WHERE ci_numero = '9100006'")).fetchall()
    assert len(est) == 1                                             # '9100006-1C' y '9100006' son la misma persona
    assert est[0][2] == "1C"
    n_hechos = dw_a.execute(text("SELECT COUNT(*) FROM fact_rendimiento_academico WHERE id_estudiante = :i"), {"i": est[0][0]}).scalar()
    assert n_hechos == 2                                             # un hecho en cada programa
    assert dw_a.execute(text("SELECT DISTINCT fk_estado FROM fact_rendimiento_academico WHERE id_estudiante = :i"),
                        {"i": est[0][0]}).fetchall() == [("A",)]
    assert dw_a.execute(text("SELECT COUNT(*) FROM dim_estudiante WHERE ci_numero LIKE '91000061%'")).scalar() == 0   # ya no se pega el complemento


def test_la_variante_con_otros_nombres_columnas_y_sinonimos_da_lo_mismo(dw_a, dw_b, entorno):
    ruta_a = actas.construir(actas.ORIGINAL, entorno)
    ruta_b = actas.construir(actas.VARIANTE, entorno)
    assert ruta_a.name != ruta_b.name
    cargar_acta(dw_a, ruta_a)
    cargar_acta(dw_b, ruta_b)
    assert hechos(dw_a) == hechos(dw_b) == esperado()
    assert estados(dw_a) == estados(dw_b)                            # otras mayúsculas, acentos y espacios: mismos estados
    assert {k: v for k, v in Counter((a[0], a[1]) for a in avisos(dw_a)).items()} == \
           {k: v for k, v in Counter((a[0], a[1]) for a in avisos(dw_b)).items()}


def test_recargar_el_mismo_libro_no_duplica(dw_a, entorno):
    ruta = actas.construir(actas.ORIGINAL, entorno)
    cargar_acta(dw_a, ruta)
    antes = (hechos(dw_a), dw_a.execute(text("SELECT COUNT(*) FROM fact_rendimiento_academico")).scalar())
    cargar_acta(dw_a, ruta)
    assert (hechos(dw_a), dw_a.execute(text("SELECT COUNT(*) FROM fact_rendimiento_academico")).scalar()) == antes


def test_sin_columnas_de_estado_el_estado_se_deduce_y_no_es_de_la_fuente(dw_a, entorno):
    cargar_acta(dw_a, actas.construir(actas.ORIGINAL, entorno, con_estados=False))
    assert hechos(dw_a)[("9100001", "POS-9001 · Módulo 1")] == (85.0, "APROBADO")
    assert dw_a.execute(text("SELECT COUNT(*) FROM fact_rendimiento_academico WHERE estado_de_fuente")).scalar() == 0
    assert dw_a.execute(text("SELECT COUNT(*) FROM fact_rendimiento_academico")).scalar() > 0


def test_kpi07_y_kpi08_locales_siguen_la_regla_de_da_fu2(dw_a, entorno):
    """Sin vistas bi (SQLite) KPIService calcula local: promedio solo de notas numéricas (el 0 real entra, la inasistencia no) y
    aprobación = APROBADO / (APROBADO + REPROBADO + INASISTENCIA); EXIMIDO y SIN_NOTA fuera del denominador."""
    from services.kpi_service import KPIService
    cargar_acta(dw_a, actas.construir(actas.ORIGINAL, entorno))
    notas = [n for n, _ in actas.ESPERADO.values() if n is not None]
    res = KPIService(dw_a).obtener_kpis_academicos()
    assert res["promedio_general_notas"] == round(sum(notas) / len(notas), 2)
    resultados = Counter(r for _, r in actas.ESPERADO.values())
    esperada = round(100.0 * resultados["APROBADO"] / (resultados["APROBADO"] + resultados["REPROBADO"] + resultados["INASISTENCIA"]), 2)
    assert res["tasa_aprobacion_pct"] == esperada
