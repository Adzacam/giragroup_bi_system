"""
FU-L6 (DA-FU3): prioridad por TIPO de fuente y campo; el conflicto queda resuelto por regla (informativo, no pendiente).

- `monto_meta` y `monto_ejecutado`: RENTABILIDAD manda sobre EGRESOS, llegue primero o después (el resultado no depende del orden);
- el valor descartado y el elegido, su diferencia y la señal de múltiplo de 100.000 quedan en el aviso, sin nombres de archivo;
- dos fuentes del MISMO tipo con valores distintos no tienen regla: el conflicto queda PENDIENTE para una persona;
- un 0 de otra fuente no es una cifra ni un conflicto; una cifra igual (o dentro de tolerancia) tampoco;
- la prioridad es del catálogo: cambiar el orden en `prioridad_fuentes` cambia quién gana, sin tocar código.
"""

import pytest

from services import metas_canonica
from tests.fixtures.fuentes_sinteticas import metas
from tests.fu_l6.conftest import cargar_libro, conflictos, conflictos_resueltos, dw_a, dw_b, entorno, filas_rentabilidad  # noqa: F401


def _cargar_ambos(db, carpeta, primero):
    ruta_r = metas.construir_rentabilidad(carpeta, metas.ORIGINAL)
    ruta_e = metas.construir_egresos(carpeta, metas.ORIGINAL)
    orden = [(ruta_r, "RENTABILIDAD"), (ruta_e, "EGRESOS")]
    if primero == "EGRESOS":
        orden.reverse()
    for ruta, tipo in orden:
        cargar_libro(db, ruta, tipo_fuente=tipo)


# ── Regla pura ───────────────────────────────────────────────────────

def test_decidir_por_tipo_y_campo():
    assert metas_canonica.decidir("monto_meta", "RENTABILIDAD", "EGRESOS") is True      # la nueva gana
    assert metas_canonica.decidir("monto_meta", "EGRESOS", "RENTABILIDAD") is False     # gana la previa
    assert metas_canonica.decidir("monto_ejecutado", "EGRESOS", "RENTABILIDAD") is False
    assert metas_canonica.decidir("monto_meta", "RENTABILIDAD", "RENTABILIDAD") is None  # mismo tipo: no hay regla
    assert metas_canonica.decidir("monto_meta", "TECHOS", "RENTABILIDAD") is None        # tipo fuera de la lista
    assert metas_canonica.decidir("monto_meta", None, "EGRESOS") is None
    # egresos y costos: manda EGRESOS (prioridad invertida)
    assert metas_canonica.decidir("monto_egreso", "EGRESOS", "RENTABILIDAD") is True
    assert metas_canonica.decidir("costos", "RENTABILIDAD", "EGRESOS") is False


def test_la_prioridad_viene_del_catalogo(monkeypatch):
    base = metas_canonica._config()
    cambiada = {**base, "prioridad_fuentes": {**base["prioridad_fuentes"], "monto_meta": ["EGRESOS", "RENTABILIDAD"]}}
    monkeypatch.setattr(metas_canonica, "_config", lambda: cambiada)
    assert metas_canonica.decidir("monto_meta", "RENTABILIDAD", "EGRESOS") is False
    assert metas_canonica.decidir("monto_ejecutado", "RENTABILIDAD", "EGRESOS") is True   # otro campo, otra lista


@pytest.mark.parametrize("dif,esperado", [(100000, True), (200000.0, True), (100000.004, True), (99999.999, True), (100000.5, False), (39724.0, False), (12345, False),
                                           (0, False), (150000, False), (-300000, True)])
def test_multiplo_de_aviso(dif, esperado):
    assert metas_canonica.es_multiplo_de_aviso(dif) is esperado


def test_texto_del_conflicto_ida_y_vuelta():
    txt = metas_canonica.describir_conflicto("PROGRAMAS", 20320401, "monto_meta", "RENTABILIDAD", "EGRESOS", 1000.0, 1100000.5)
    d = metas_canonica.leer_conflicto(txt)
    assert d["categoria"] == "PROGRAMAS" and d["elegida"] == "RENTABILIDAD" and d["descartada"] == "EGRESOS"
    assert float(d["diferencia"]) == 1099000.5 and d["multiplo_100000"] == "no"
    assert metas_canonica.leer_conflicto("otra cosa") is None


# ── Carga de dos libros (ambos órdenes de llegada) ────────────────────

@pytest.mark.parametrize("primero", ["RENTABILIDAD", "EGRESOS"])
def test_gana_rentabilidad_llegue_primero_o_despues(entorno, dw_a, primero):
    _cargar_ambos(dw_a, entorno, primero)
    filas = filas_rentabilidad(dw_a)
    # la DW queda con las cifras de RENTABILIDAD en todo 2032 (ninguna de las tres celdas de EGRESOS)
    for (cat, anio, mes), (ejec, meta, _gran) in filas.items():
        if anio != 2032:
            continue
        assert ejec == metas.ejecutado({"TECHOS_CERRADOS": "TECHOS/CERRADOS"}.get(cat, cat), 2032, mes), (cat, mes)
        assert meta == metas.meta_mensual({"TECHOS_CERRADOS": "TECHOS/CERRADOS"}.get(cat, cat), 2032, mes), (cat, mes)

    resueltos = conflictos_resueltos(dw_a)
    esperados = metas.conflictos_esperados()
    assert set(resueltos) == set(esperados)
    for clave, (elegido, descartado) in esperados.items():
        elegida, descartada, v_elegido, v_descartado, multiplo = resueltos[clave]
        assert (elegida, descartada) == ("RENTABILIDAD", "EGRESOS")
        assert (v_elegido, v_descartado) == (elegido, descartado)
        assert multiplo == ("si" if clave == ("monto_meta", "PROGRAMAS", 4) else "no")
    # ninguno queda pendiente: se cierran por regla (informativo, no bandeja)
    assert conflictos(dw_a, "PENDIENTE") == []
    assert {c.estado_resolucion for c in conflictos(dw_a)} == {"RESUELTO_REGLA"}
    assert all(c.resuelto_en is not None and c.severidad == "BAJA" for c in conflictos(dw_a))


def test_el_resultado_no_depende_del_orden_de_llegada(entorno, dw_a, dw_b):
    _cargar_ambos(dw_a, entorno, "RENTABILIDAD")
    _cargar_ambos(dw_b, entorno, "EGRESOS")
    assert filas_rentabilidad(dw_a) == filas_rentabilidad(dw_b)
    assert conflictos_resueltos(dw_a) == conflictos_resueltos(dw_b)


def test_el_cero_de_otra_fuente_no_es_conflicto_ni_pisa_la_cifra(entorno, dw_a):
    _cargar_ambos(dw_a, entorno, "RENTABILIDAD")
    filas = filas_rentabilidad(dw_a)
    # EGRESOS trae 0 en el ejecutado de TECHOS/CERRADOS de julio 2032: se conserva la cifra de RENTABILIDAD y no hay aviso
    assert filas[("TECHOS_CERRADOS", 2032, 7)][0] == metas.ejecutado("TECHOS/CERRADOS", 2032, 7)
    assert ("monto_ejecutado", "TECHOS_CERRADOS", 7) not in conflictos_resueltos(dw_a)


def test_recargar_no_duplica_los_avisos(entorno, dw_a):
    _cargar_ambos(dw_a, entorno, "RENTABILIDAD")
    n = len(conflictos(dw_a))
    filas = filas_rentabilidad(dw_a)
    _cargar_ambos(dw_a, entorno, "RENTABILIDAD")
    assert len(conflictos(dw_a)) == n
    assert filas_rentabilidad(dw_a) == filas


def test_variante_de_los_libros_da_los_mismos_conflictos(entorno, dw_a, dw_b):
    _cargar_ambos(dw_a, entorno, "RENTABILIDAD")
    cargar_libro(dw_b, metas.construir_rentabilidad(entorno, metas.VARIANTE), tipo_fuente="RENTABILIDAD")
    cargar_libro(dw_b, metas.construir_egresos(entorno, metas.VARIANTE), tipo_fuente="EGRESOS")
    assert filas_rentabilidad(dw_a) == filas_rentabilidad(dw_b)
    assert conflictos_resueltos(dw_a) == conflictos_resueltos(dw_b)


# ── Mismo tipo: sin regla, queda pendiente ────────────────────────────

def test_dos_fuentes_del_mismo_tipo_con_otro_valor_quedan_pendientes(entorno, dw_a):
    from services.dw_loader import DWLoaderService
    from models.dim_origen import DimOrigenDocumental
    from datetime import datetime
    dw_a.add(DimOrigenDocumental(id_documento=1, nombre_archivo="a.xlsx", tipo_fuente="RENTABILIDAD", fecha_procesamiento=datetime(2032, 1, 1)))
    dw_a.add(DimOrigenDocumental(id_documento=2, nombre_archivo="b.xlsx", tipo_fuente="RENTABILIDAD", fecha_procesamiento=datetime(2032, 2, 1)))
    dw_a.commit()
    loader = DWLoaderService(dw_a)
    for doc, meta in ((1, 1000.0), (2, 2000.0)):
        loader.cargar_registro({
            "doc_id": doc, "categoria": "rentabilidad", "clave_origen": f"c{doc}", "clave_contenido": f"c{doc}",
            "resoluciones": {"categoria_financiera": "PROGRAMAS", "fecha": "2032-02-01", "monto_meta": meta, "es_fuente_metas_categoria": True,
                             "granularidad_meta": "MENSUAL"},
            "calidad": {"requiere_revision": False}})
    dw_a.commit()
    pendientes = conflictos(dw_a, "PENDIENTE")
    assert len(pendientes) == 1 and conflictos(dw_a, "RESUELTO_REGLA") == []
    assert filas_rentabilidad(dw_a)[("PROGRAMAS", 2032, 2)][1] == 2000.0       # entre iguales gana la fuente más reciente


# ── Granularidad al decidir ───────────────────────────────────────────

def test_la_bandera_sigue_a_la_meta_vigente(entorno, dw_a):
    """Si la fuente prioritaria reemplaza una meta ANUAL de la de menor prioridad por una mensual, la bandera cambia con el valor."""
    from services.dw_loader import DWLoaderService
    from models.dim_origen import DimOrigenDocumental
    from datetime import datetime
    dw_a.add(DimOrigenDocumental(id_documento=1, nombre_archivo="a.xlsx", tipo_fuente="EGRESOS", fecha_procesamiento=datetime(2032, 1, 1)))
    dw_a.add(DimOrigenDocumental(id_documento=2, nombre_archivo="b.xlsx", tipo_fuente="RENTABILIDAD", fecha_procesamiento=datetime(2032, 2, 1)))
    dw_a.commit()
    loader = DWLoaderService(dw_a)
    for doc, meta, gran in ((1, 6_000_000.0, "ANUAL"), (2, 500_000.0, "MENSUAL")):
        loader.cargar_registro({
            "doc_id": doc, "categoria": "rentabilidad", "clave_origen": f"c{doc}", "clave_contenido": f"c{doc}",
            "resoluciones": {"categoria_financiera": "PROGRAMAS", "fecha": "2032-12-01", "monto_meta": meta, "granularidad_meta": gran},
            "calidad": {"requiere_revision": False}})
    dw_a.commit()
    assert filas_rentabilidad(dw_a)[("PROGRAMAS", 2032, 12)][1:] == (500_000.0, "MENSUAL")
    assert [c.estado_resolucion for c in conflictos(dw_a)] == ["RESUELTO_REGLA"]


# ── Huecos: la otra fuente los llena, llegue antes o después ──────────

@pytest.mark.parametrize("orden", [("RENTABILIDAD", "EGRESOS"), ("EGRESOS", "RENTABILIDAD")])
@pytest.mark.parametrize("hueco", [None, 0.0])
def test_un_hueco_de_la_fuente_prioritaria_lo_llena_la_otra_sin_conflicto(entorno, dw_a, orden, hueco):
    """La fuente prioritaria no trae la meta (vacía o 0) y la otra sí: se carga la que existe, en cualquier orden, y no hay aviso."""
    from services.dw_loader import DWLoaderService
    from models.dim_origen import DimOrigenDocumental
    from datetime import datetime
    docs = {"RENTABILIDAD": 1, "EGRESOS": 2}
    for tipo, i in docs.items():
        dw_a.add(DimOrigenDocumental(id_documento=i, nombre_archivo=f"{i}.xlsx", tipo_fuente=tipo, fecha_procesamiento=datetime(2032, 1, i)))
    dw_a.commit()
    loader = DWLoaderService(dw_a)
    valor = {"RENTABILIDAD": hueco, "EGRESOS": 750.0}
    for tipo in orden:
        res = {"categoria_financiera": "PROGRAMAS", "fecha": "2032-03-01", "monto_ejecutado": 10.0, "granularidad_meta": "MENSUAL"}
        if valor[tipo] is not None:
            res["monto_meta"] = valor[tipo]
        loader.cargar_registro({"doc_id": docs[tipo], "categoria": "rentabilidad", "clave_origen": f"c{docs[tipo]}",
                                "clave_contenido": f"c{docs[tipo]}", "resoluciones": res, "calidad": {"requiere_revision": False}})
    dw_a.commit()
    assert filas_rentabilidad(dw_a)[("PROGRAMAS", 2032, 3)][1] == 750.0
    assert conflictos(dw_a) == []
