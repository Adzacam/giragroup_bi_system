"""
FU-L9: el riesgo de deserción de Alertas Tempranas también se enciende con el estado académico o de tutoría
Deserción / Abandono (misma definición que KPI-16, DA2-bis), aunque las cargas no traigan el % de incumplimiento.
"""
from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.fact_rendimiento import FactRendimientoAcademico
from services.risk_service import evaluar_alertas_tempranas_deterministicas
from tests.sprint4.test_alertas_tempranas_vista3 import _crear_mock_db_constelacion


def _agregar(db, id_est, estado_academico=None, estado_tutoria=None, nota=85.0):
    db.add(DimEstudiante(id_estudiante=id_est, nombre_completo=f"Estudiante Prueba {id_est}", ci=f"88{id_est:05d}",
                         ci_numero=f"88{id_est:05d}", codigo_estudiante=f"88{id_est:05d}",
                         programa_origen="Programa Prueba", deprecado=False))
    db.flush()
    db.add(FactRendimientoAcademico(id_hecho_aca=7000 + id_est, id_estudiante=id_est, id_modulo=1, id_tiempo=202602,
                                    nota_final=nota, estado_academico=estado_academico, estado_tutoria=estado_tutoria))
    db.commit()


def _desercion_ids(res):
    return {e["id_estudiante"] for e in res["estudiantes"] if e["regla_desercion"]}


def test_estado_desercion_o_abandono_enciende_la_regla_sin_incumplimiento():
    db = _crear_mock_db_constelacion()
    base = evaluar_alertas_tempranas_deterministicas(db=db)["tarjetas"]["riesgo_desercion"]["total_alumnos"]
    _agregar(db, 301, estado_academico="Deserción")      # con tilde
    _agregar(db, 302, estado_tutoria="Abandono")         # estado de tutoría
    _agregar(db, 303, estado_academico="DESERCION")      # sin tilde y en mayúsculas
    _agregar(db, 304, estado_academico="Aprobado")       # no desertor
    res = evaluar_alertas_tempranas_deterministicas(db=db)
    assert res["tarjetas"]["riesgo_desercion"]["total_alumnos"] == base + 3
    ids = _desercion_ids(res)
    assert {301, 302, 303} <= ids
    assert 304 not in ids
    assert "Deserción/Abandono" in res["tarjetas"]["riesgo_desercion"]["regla_texto"]


def test_desertor_con_nota_baja_suma_a_la_matriz_academico_desercion():
    db = _crear_mock_db_constelacion()
    antes = {m["codigo"]: m["total_alumnos"] for m in evaluar_alertas_tempranas_deterministicas(db=db)["matriz_interseccion"]}
    _agregar(db, 310, estado_academico="Deserción", nota=50.0)
    res = evaluar_alertas_tempranas_deterministicas(db=db)
    despues = {m["codigo"]: m["total_alumnos"] for m in res["matriz_interseccion"]}
    assert despues["A+D"] == antes["A+D"] + 1
    item = next(e for e in res["estudiantes"] if e["id_estudiante"] == 310)
    assert item["regla_academico"] and item["regla_desercion"]
    assert item["prioridad"] == "CRITICA"


def test_filtro_por_regla_desercion_incluye_a_los_desertores_por_estado():
    db = _crear_mock_db_constelacion()
    _agregar(db, 320, estado_tutoria="Abandono")
    res = evaluar_alertas_tempranas_deterministicas(db=db, regla_filtro="DESERCION")
    assert 320 in {e["id_estudiante"] for e in res["estudiantes"]}
