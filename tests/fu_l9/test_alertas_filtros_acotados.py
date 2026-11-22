"""
FU-L9: los filtros de Alertas Tempranas se acotan (la pestaña se congelaba con ~2.900 opciones).
Solo cuentan valores de estudiantes con alguna alerta, sin duplicados por mayúsculas/espacios,
ordenados por casos y con un tope; el valor elegido por el usuario siempre se conserva.
"""
from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_tiempo import DimTiempo
from models.fact_rendimiento import FactRendimientoAcademico
from services import risk_service
from services.risk_service import evaluar_alertas_tempranas_deterministicas
from tests.sprint4.test_alertas_tempranas_vista3 import _crear_mock_db_constelacion


def _agregar_modulos_sin_alerta(db, n: int):
    """n módulos y estudiantes con buena nota: no deben aparecer como opciones de filtro."""
    db.add(DimTiempo(id_tiempo=202603, gestion=2026, semestre=2, mes=9, periodo_mes="2026-09")) if not db.get(DimTiempo, 202603) else None
    for i in range(n):
        db.add(DimEstudiante(id_estudiante=500 + i, nombre_completo=f"Sin Alerta {i}", ci=f"90{i:05d}", ci_numero=f"90{i:05d}",
                             codigo_estudiante=f"90{i:05d}", programa_origen="Programa Sin Alerta", deprecado=False))
        db.add(DimModulo(id_modulo=500 + i, nombre_modulo=f"MODULO SIN ALERTA {i}", programa="Programa Sin Alerta"))
    db.flush()
    for i in range(n):
        db.add(FactRendimientoAcademico(id_hecho_aca=900 + i, id_estudiante=500 + i, id_modulo=500 + i, id_tiempo=202602,
                                        nota_final=95.0, asistencia_pct=100.0, incumplimiento_actividades_pct=0.0))
    db.commit()


def test_opciones_solo_de_estudiantes_con_alerta():
    db = _crear_mock_db_constelacion()
    _agregar_modulos_sin_alerta(db, 30)
    res = evaluar_alertas_tempranas_deterministicas(db=db, limit=5)
    f = res["filtros_disponibles"]
    assert "Programa Sin Alerta" not in f["programas"]
    assert not any(m.startswith("MODULO SIN ALERTA") for m in f["modulos"])
    assert "Maestría en BI" in f["programas"]
    assert res["filtros_totales"]["programas"] == len(f["programas"])


def test_opciones_acotadas_y_valor_elegido_se_conserva(monkeypatch):
    db = _crear_mock_db_constelacion()
    monkeypatch.setattr(risk_service, "MAX_OPCIONES_FILTRO", 1)
    res = evaluar_alertas_tempranas_deterministicas(db=db, limit=5)
    assert len(res["filtros_disponibles"]["programas"]) == 1
    assert res["filtros_totales"]["programas"] >= 1
    # lo que el usuario eligió siempre vuelve en la lista aunque quede fuera del tope
    res2 = evaluar_alertas_tempranas_deterministicas(db=db, programa="Diplomado Finanzas", limit=5)
    assert "Diplomado Finanzas" in res2["filtros_disponibles"]["programas"]


def test_sin_duplicados_por_mayusculas_ni_espacios():
    db = _crear_mock_db_constelacion()
    db.add(DimModulo(id_modulo=77, nombre_modulo="mod-02:  minería de datos", programa="MAESTRÍA  EN BI"))
    db.flush()
    db.add(FactRendimientoAcademico(id_hecho_aca=800, id_estudiante=101, id_modulo=77, id_tiempo=202602,
                                    nota_final=60.0, asistencia_pct=50.0, incumplimiento_actividades_pct=50.0))
    db.commit()
    res = evaluar_alertas_tempranas_deterministicas(db=db, limit=5)
    claves = [" ".join(p.split()).casefold() for p in res["filtros_disponibles"]["programas"]]
    assert len(claves) == len(set(claves))
