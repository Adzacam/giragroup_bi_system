"""
FU-L5 (DA1): la encuesta de punta a punta (ingesta -> consolidación -> DW SQLite) con libros sintéticos de datos ficticios, sin nombres
de archivo, de hoja ni índices de columna en el código.

- el libro se clasifica por contenido como EVALUACION_DOCENTE aunque se suba como ACTA / CENTESIMAL_100;
- cada respuesta se guarda una sola vez (la doble columna texto + número no la duplica) y con su escala 5 o 10;
- 0, «Sin Información», fuera de escala, etiqueta desconocida y respuesta cruzada quedan NULL y se registran agregados, sin el valor;
- el 0 del NPS (0-10) es un puntaje válido;
- la variante (otro nombre de archivo y de hoja, columnas en otro orden, otros nombres de identificación, hoja oculta y borrador) da lo mismo;
- volver a cargar el mismo libro no duplica hechos ni avisos.
"""

from collections import Counter

from sqlalchemy import text

from services import encuesta_canonica as ec
from services.extraccion_por_encabezado import normalizar_encabezado
from tests.fixtures.fuentes_sinteticas import encuestas
from tests.fu_l5.conftest import cargar_encuesta, dw_a, dw_b, entorno  # noqa: F401


def _pregunta(texto):
    """Clave de pregunta comparable: sin acentos, en mayúsculas y sin el prefijo «A 1.» ni el marcador «N°»."""
    return ec.descomponer_cabecera(normalizar_encabezado(texto))[0]


def hechos(db):
    """Respuestas con puntuación en la DW como lista ordenada (módulo, pregunta, puntuación, escala, tipo)."""
    filas = db.execute(text(
        "SELECT m.nombre_modulo, f.pregunta_bloque, f.puntuacion, f.escala_max, f.tipo_pregunta FROM fact_evaluacion_docente f "
        "JOIN dim_modulo m ON m.id_modulo = f.id_modulo WHERE f.puntuacion IS NOT NULL")).fetchall()
    return sorted(((m, _pregunta(p), float(n), int(e), t) for m, p, n, e, t in filas), key=str)


def esperado(*listas):
    return sorted(((m, _pregunta(p), float(n), int(e), t) for lista in listas for m, p, n, e, t in lista), key=str)


def comentarios(db):
    filas = db.execute(text(
        "SELECT m.nombre_modulo, f.pregunta_bloque, f.comentario FROM fact_evaluacion_docente f "
        "JOIN dim_modulo m ON m.id_modulo = f.id_modulo WHERE f.puntuacion IS NULL AND f.comentario IS NOT NULL")).fetchall()
    return sorted(((m, _pregunta(p), c) for m, p, c in filas), key=str)


def avisos(db, doc=None):
    """{motivo: (n de avisos agregados, n de respuestas)} de FU-L5 en log_inconsistencias (de un documento, o de todos)."""
    from models.log_inconsistencia import LogInconsistencia
    import re
    out = {}
    q = db.query(LogInconsistencia).filter(LogInconsistencia.descripcion.like("FU-L5:%"))
    if doc is not None:
        q = q.filter(LogInconsistencia.id_documento == doc)
    for l in q.all():
        n = int(re.search(r"FU-L5: (\d+) respuesta", l.descripcion).group(1))
        previo = out.get(l.tipo_regla, (0, 0))
        out[l.tipo_regla] = (previo[0] + 1, previo[1] + n)
    return out


def test_el_libro_de_encuestas_se_clasifica_por_contenido_aunque_se_suba_como_acta(dw_a, entorno):
    ruta = encuestas.construir(encuestas.ORIGINAL, entorno)
    _, doc = cargar_encuesta(dw_a, ruta, tipo_fuente="ACTA", tipo_escala="CENTESIMAL_100")
    tipo, escala = dw_a.execute(text("SELECT tipo_fuente, tipo_escala FROM dim_origen_documental WHERE id_documento = :d"), {"d": doc}).one()
    assert (tipo, escala) == ("EVALUACION_DOCENTE", None)


def test_cada_respuesta_se_guarda_una_vez_con_su_escala(dw_a, entorno):
    cargar_encuesta(dw_a, encuestas.construir(encuestas.ORIGINAL, entorno))
    assert hechos(dw_a) == esperado(encuestas.ESPERADO_A, encuestas.ESPERADO_B)


def test_la_doble_columna_no_duplica_ni_carga_el_cero(dw_a, entorno):
    cargar_encuesta(dw_a, encuestas.construir(encuestas.ORIGINAL, entorno))
    por_pregunta = Counter(h[1] for h in hechos(dw_a) if h[0] == encuestas.M_B)
    assert por_pregunta[_pregunta(encuestas.PREG_B["a1"])] == 5          # 6 filas: una con 0/Sin Información
    assert por_pregunta[_pregunta(encuestas.PREG_B["a2"])] == 3          # 6 filas: tres con 0/Sin Información
    assert dw_a.execute(text("SELECT COUNT(*) FROM fact_evaluacion_docente WHERE puntuacion = 0 AND tipo_pregunta <> 'NPS'")).scalar() == 0
    # la columna calculada de promedio no es una respuesta
    assert dw_a.execute(text("SELECT COUNT(*) FROM fact_evaluacion_docente WHERE UPPER(pregunta_bloque) LIKE '%PROMEDIO%'")).scalar() == 0


def test_el_cero_del_nps_es_un_puntaje_valido_y_no_hay_puntuaciones_fuera_de_escala(dw_a, entorno):
    cargar_encuesta(dw_a, encuestas.construir(encuestas.ORIGINAL, entorno))
    assert (encuestas.M1, _pregunta(encuestas.PREG["p4"]), 0.0, 10, "NPS") in hechos(dw_a)
    fuera = dw_a.execute(text(
        "SELECT COUNT(*) FROM fact_evaluacion_docente WHERE puntuacion IS NOT NULL AND "
        "(escala_max IS NULL OR puntuacion > escala_max OR puntuacion < CASE WHEN tipo_pregunta = 'NPS' THEN 0 ELSE 1 END)")).scalar()
    assert fuera == 0


def test_los_comentarios_se_conservan_y_los_vacios_no(dw_a, entorno):
    cargar_encuesta(dw_a, encuestas.construir(encuestas.ORIGINAL, entorno))
    esp = sorted((m, _pregunta(p), c) for m, p, c in encuestas.COMENTARIOS_A + encuestas.COMENTARIOS_B)
    assert comentarios(dw_a) == esp


def test_los_avisos_son_agregados_y_no_publican_el_valor(dw_a, entorno):
    from models.log_inconsistencia import LogInconsistencia
    cargar_encuesta(dw_a, encuestas.construir(encuestas.ORIGINAL, entorno))
    por_motivo = avisos(dw_a)
    assert {m: n for m, (_, n) in por_motivo.items()} == encuestas.AVISOS_ESPERADOS
    filas = dw_a.query(LogInconsistencia).filter(LogInconsistencia.descripcion.like("FU-L5:%")).all()
    assert all(l.fila_origen is None for l in filas)                                  # agrupados, no fila por fila
    texto = " ".join(f"{l.valor_recibido} {l.descripcion}" for l in filas)
    for secreto in ("Estupendo", "respuesta larga", "FICTICIA", "Más casos"):
        assert secreto not in texto
    estados = {l.tipo_regla: l.estado_resolucion for l in filas}
    assert estados["SIN_INFORMACION"] == "REGISTRADO"                               # informativo
    assert estados["RESPUESTA_EN_COLUMNA_EQUIVOCADA"] == "PENDIENTE"                 # lo ve una persona (FU-L7)
    # la respuesta cruzada se agrupa por hoja y pregunta: la hoja va en el campo
    assert all("::" in l.campo_afectado for l in filas)


def test_la_variante_con_otros_nombres_columnas_y_hoja_oculta_da_lo_mismo(dw_a, dw_b, entorno):
    ruta_a = encuestas.construir(encuestas.ORIGINAL, entorno)
    ruta_b = encuestas.construir(encuestas.VARIANTE, entorno)
    assert ruta_a.name != ruta_b.name
    cargar_encuesta(dw_a, ruta_a)
    cargar_encuesta(dw_b, ruta_b)
    assert hechos(dw_a) == hechos(dw_b) == esperado(encuestas.ESPERADO_A, encuestas.ESPERADO_B)
    assert comentarios(dw_a) == comentarios(dw_b)
    assert avisos(dw_a) == avisos(dw_b)


def test_recargar_el_mismo_libro_no_duplica_hechos(dw_a, entorno):
    """Subir otra vez el mismo contenido crea otro documento, pero sus respuestas ya están: ningún hecho se suma, y el documento nuevo
    deja sus propios avisos (los mismos que el primero)."""
    ruta = encuestas.construir(encuestas.ORIGINAL, entorno)
    _, doc1 = cargar_encuesta(dw_a, ruta)
    antes = (hechos(dw_a), comentarios(dw_a), dw_a.execute(text("SELECT COUNT(*) FROM fact_evaluacion_docente")).scalar())
    _, doc2 = cargar_encuesta(dw_a, ruta)
    assert (hechos(dw_a), comentarios(dw_a), dw_a.execute(text("SELECT COUNT(*) FROM fact_evaluacion_docente")).scalar()) == antes
    assert avisos(dw_a, doc1) == avisos(dw_a, doc2) != {}


def test_registrar_dos_veces_el_mismo_aviso_lo_reemplaza_y_no_lo_duplica(dw_a):
    """Una consolidación repetida del mismo documento deja un solo aviso por hoja, pregunta y motivo, con la cuenta al día."""
    from models.log_inconsistencia import LogInconsistencia
    from services.dw_loader import DWLoaderService
    cargador = DWLoaderService(dw_a)
    for _ in range(3):
        cargador._registrar_aviso_encuesta(7, "Hoja uno", "SIN_INFORMACION", "¿Pregunta?", "0")
    assert cargador.registrar_avisos_encuesta() == 1
    for _ in range(5):
        cargador._registrar_aviso_encuesta(7, "Hoja uno", "SIN_INFORMACION", "¿Pregunta?", "0")
    assert cargador.registrar_avisos_encuesta() == 1
    filas = dw_a.query(LogInconsistencia).filter(LogInconsistencia.id_documento == 7).all()
    assert len(filas) == 1 and "5 respuesta(s)" in filas[0].descripcion and filas[0].estado_resolucion == "REGISTRADO"


def test_los_hechos_de_la_hoja_oculta_y_el_borrador_no_se_cargan(dw_a, entorno):
    cargar_encuesta(dw_a, encuestas.construir(encuestas.ORIGINAL, entorno))
    # las dos hojas repetidas traen 12 respuestas de las 4 primeras filas de la hoja A; si se cargaran, habría más hechos de los esperados
    assert len(hechos(dw_a)) == len(encuestas.ESPERADO_A) + len(encuestas.ESPERADO_B)


def test_kpi_de_satisfaccion_local_solo_cuenta_puntuaciones_validas(dw_a, entorno):
    """Sin vistas bi (SQLite) los promedios por docente salen del servicio de catálogo: el 0 y lo fuera de escala no promedian."""
    cargar_encuesta(dw_a, encuestas.construir(encuestas.ORIGINAL, entorno))
    validos = dw_a.execute(text(
        "SELECT COUNT(*) FROM fact_evaluacion_docente WHERE puntuacion >= 1 AND puntuacion <= escala_max")).scalar()
    con_valor = dw_a.execute(text("SELECT COUNT(*) FROM fact_evaluacion_docente WHERE puntuacion IS NOT NULL")).scalar()
    nps_cero = dw_a.execute(text("SELECT COUNT(*) FROM fact_evaluacion_docente WHERE puntuacion = 0")).scalar()
    assert con_valor - validos == nps_cero == 1                                         # el único 0 es el del NPS, que va aparte
