"""F3S S-2 (D-A4): una hoja Likert dentro de un libro clasificado como ACTA se consolida como evaluación docente."""
import importlib
import io

import pandas as pd

from models.dim_docente import DimDocente
from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_origen import DimOrigenDocumental
from models.fact_evaluacion import FactEvaluacionDocente
from models.fact_rendimiento import FactRendimientoAcademico
from models.lote import Lote
from models.log_inconsistencia import LogInconsistencia
from models.staging_registro import StagingRegistroCrudo
from routers import dataops
from services import cache_consultas
from tests.dataops_parches import _MODULOS

PREGUNTAS = ["¿El docente explica claramente los temas del módulo?", "¿El docente domina los contenidos del curso?",
             "¿El docente responde las consultas de los estudiantes?"]


def test_hoja_likert_de_libro_acta_llega_a_fact_evaluacion_docente(dw_sqlite, monkeypatch, tmp_path):
    from services import cache_lectura, ingestion_service
    from services.ingestion_service import IngestionService

    db = dw_sqlite
    cache_consultas.invalidar()
    monkeypatch.setattr(cache_lectura, "DIR", tmp_path)
    monkeypatch.setattr(ingestion_service, "AsymmetricFlattener", None)
    # La detección por cabeceras ve actas en el libro (así quedó el archivo real): el tipo del documento es ACTA
    monkeypatch.setattr(ingestion_service, "detectar_tipo_fuente_por_cabeceras", lambda hojas, nombre: "ACTA")
    # Sin servicio BETO: índice fijo para toda línea. Se parchea donde exista el nombre (independiente de cómo se importe)
    for modulo in ["services.confianza_service"] + ["routers.dataops" + suf for suf in _MODULOS]:
        mod = importlib.import_module(modulo)
        if hasattr(mod, "obtener_indices"):
            monkeypatch.setattr(mod, "obtener_indices", lambda lineas, **kw: [.95] * len(lineas))
        if hasattr(mod, "indices_en_cache"):
            monkeypatch.setattr(mod, "indices_en_cache", lambda lineas: [.95] * len(lineas))
    # La carga en bloque de evaluación usa execute_values (solo PostgreSQL): se captura lo que se enviaría a fact_evaluacion_docente
    enviadas = []
    monkeypatch.setattr("psycopg2.extras.execute_values", lambda cur, sql, filas, page_size=None: enviadas.extend(filas))
    lote = Lote(institucion="Prueba", periodo="2025")
    db.add(lote); db.flush()
    alumnos = [("ANA TORREZ SALINAS", "13727801", 90, 80), ("LUIS PEREZ ROJAS", "13727802", 60, 70)]
    for nombre, ci, _, _ in alumnos:
        db.add(DimEstudiante(nombre_completo=nombre, ci=ci, fk_estado="A"))
    for n in (1, 2):
        db.add(DimModulo(nombre_modulo=f"POS-9876 · Módulo {n}", pos_code=f"POS-9876-M0{n}", programa="Programa de prueba"))
    db.commit()

    actas = pd.DataFrame([{"POS - ACTAS": "POS-9876", "CI": ci, "NOMBRE COMPLETO": nombre, "MES INICIO": "Marzo",
                           "AÑO INICIO": 2025, "MÓDULO 1": n1, "MÓDULO 2": n2} for nombre, ci, n1, n2 in alumnos])
    likert = pd.DataFrame([{"NOMBRE COMPLETO": nombre, "FECHA": f"0{i + 1}/03/2025", "PROGRAMA": "POS-9876", "MODULO": "1",
                            **{q: ("5/Totalmente de acuerdo" if (i + j) % 2 else "4/De acuerdo") for j, q in enumerate(PREGUNTAS)}} for i, (nombre, _, _, _) in enumerate(alumnos * 3)])
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as w:
        actas.to_excel(w, sheet_name="ACTAS", index=False)
        likert.to_excel(w, sheet_name="ENCUESTA", index=False)
    archivo = tmp_path / "libro_mixto.xlsx"
    archivo.write_bytes(buffer.getvalue())

    IngestionService.procesar_archivo(db, str(archivo), archivo.name, id_lote=lote.id_lote, tipo_fuente="ACTA",
                                      institucion="Prueba", tipo_escala="CENTESIMAL_100")
    doc = db.query(DimOrigenDocumental).filter_by(id_lote=lote.id_lote).one()
    assert doc.tipo_fuente == "ACTA"  # como en 'Experiencia Docente 2.0.xlsx': libro ACTA con una hoja Likert
    cats = {s.hoja: s.categoria for s in db.query(StagingRegistroCrudo).filter_by(id_documento=doc.id_documento)}
    assert cats["ENCUESTA"] == "evaluacion_docente" and cats["ACTAS"] != "evaluacion_docente"

    dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), db, None)

    # Hoja de actas: sin cambios (2 alumnos x 2 módulos)
    assert db.query(FactRendimientoAcademico).count() == 4
    # Hoja Likert: 6 filas x 3 preguntas = 18 respuestas, ninguna descartada como acta
    assert len(enviadas) == 18
    motivos = [m for (m,) in db.query(LogInconsistencia.tipo_regla).all()]
    assert "FILA_ACADEMICA_SIN_ESTUDIANTE" not in motivos
    cache_consultas.invalidar()
