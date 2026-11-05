"""
tests/test_coherencia_estado_notas.py
-------------------------------------
Casos tomados del acta ARCA real: cada programa tiene su propio número de módulos y el ESTADO ACADÉMICO
debe coincidir con las notas. 'Aprobado' con un 0 en un módulo (POS 5295) va a revisión; 'Reprobado' con un
módulo en 30 (POS 5381) es coherente.
"""

from services.extraccion_por_encabezado import (
    campos_por_encabezado, coherencia_estado_notas, registros_academicos,
)


def _fila(pos, notas, estado_aca, estado_tut="Aprobado"):
    celdas = [f"POS - ACTAS: {pos}", "CÉDULA DE IDENTIDAD: 4914434", "MES INICIO: 11", "AÑO INICIO: 2024",
              "APELLIDO PATERNO: SOZA", "APELLIDO MATERNO: ALVAREZ", "NOMBRES: CINTHIA MABEL"]
    celdas += [f"MÓDULO {i}: {n}" for i, n in enumerate(notas, start=1)]
    celdas += [f"ESTADO ACADEMICO: {estado_aca}", f"ESTADO TUTORIA: {estado_tut}", "ESTADO ARCA: No titulado"]
    return campos_por_encabezado(celdas)


def test_programa_de_cinco_modulos_genera_cinco_hechos_sin_marcar_faltantes():
    regs = registros_academicos(_fila(5381, [78, 83, 94, 88, 91], "Aprobado"))
    assert len(regs) == 5
    assert not any("MODULO" in (r.get("estado_motivo") or "") for r in regs)


def test_aprobado_con_un_cero_va_a_revision():
    regs = registros_academicos(_fila(5295, [0, 99, 90, 100, 100, 95, 73, 90], "Aprobado"))
    assert all(r["requiere_revision"] for r in regs)
    assert "APROBADO_CON_MODULO_REPROBADO: módulo 1 = 0" in regs[0]["estado_motivo"]


def test_reprobado_con_modulo_bajo_es_coherente():
    assert coherencia_estado_notas("Reprobado", {1: 93, 2: 87, 3: 91, 4: 30, 5: 85}) is None


def test_reprobado_con_notas_altas_no_se_marca_porque_puede_ser_abandono():
    assert coherencia_estado_notas("Reprobado", {1: 90, 2: 85}) is None


def test_aprobado_con_nota_entre_51_y_69_pasa_por_posible_tutoria():
    assert coherencia_estado_notas("Aprobado", {1: 54, 2: 90}) is None


def test_acta_sobre_20_se_lleva_a_base_100():
    regs = registros_academicos(_fila(5100, [17, 18, 20, 19, 20], "Aprobado"))
    assert [r["nota_final"] for r in regs] == [85.0, 90.0, 100.0, 95.0, 100.0]
    assert not regs[0].get("estado_motivo")


def test_estados_que_no_dependen_de_las_notas_no_se_validan():
    assert coherencia_estado_notas("En curso", {1: 0}) is None
    assert coherencia_estado_notas("Deserción", {1: 0}) is None


def test_escala_se_decide_por_programa_en_el_archivo():
    from services.extraccion_por_encabezado import factores_escala_por_programa

    sobre_20 = _fila(5100, [17, 18, 20], "Aprobado")
    sobre_100_bajo = _fila(5381, [15, 12, 18], "Reprobado")   # estudiante con notas bajas en un programa sobre 100
    sobre_100_alto = _fila(5381, [78, 83, 94], "Aprobado")
    factores = factores_escala_por_programa([sobre_20] * 3 + [sobre_100_bajo, sobre_100_alto])
    assert factores == {"POS-5100": 5.0, "POS-5381": 1.0}
    # Por fila, el 15/12/18 se habría multiplicado por 5; con la escala del programa queda tal cual
    assert [r["nota_final"] for r in registros_academicos(sobre_100_bajo, factores)] == [15.0, 12.0, 18.0]
    assert [r["nota_final"] for r in registros_academicos(sobre_20, factores)] == [85.0, 90.0, 100.0]


def test_escala_declarada_en_el_archivo_manda():
    from services.extraccion_por_encabezado import factores_escala_por_programa

    assert factores_escala_por_programa([_fila(5381, [78, 83], "Aprobado")], "VIGESIMAL_20") == {"POS-5381": 5.0}


def test_programa_con_pocas_notas_queda_en_base_100():
    from services.extraccion_por_encabezado import factores_escala_por_programa

    filas = [_fila(5384, [9], "Reprobado"), _fila(5384, [0], "Deserción"), _fila(5384, [0], "Deserción")]
    assert factores_escala_por_programa(filas) == {"POS-5384": 1.0}
