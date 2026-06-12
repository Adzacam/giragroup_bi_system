import os
import pytest
import pandas as pd
from datetime import datetime
from pipeline.ingestion.dispatcher import procesar_documento
from pipeline.ingestion.moodle_reader import leer_moodle_export, normalizar_cabecera
from pipeline.ingestion.sheet_reader import leer_xlsx
from pipeline.ingestion.forms_reader import leer_forms_csv
from pipeline.normalization.text_cleaner import limpiar_texto, normalizar_nombre, preparar_payload_beto


# ── Tests para Dispatcher ───────────────────────────────────────────────────

def test_dispatcher_unsupported_formats(tmp_path):
    # Crear archivos falsos
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_text("dummy")
    docx_file = tmp_path / "test.docx"
    docx_file.write_text("dummy")
    unknown_file = tmp_path / "test.xyz"
    unknown_file.write_text("dummy")

    with pytest.raises(NotImplementedError, match="not soportado"):
        procesar_documento(str(pdf_file))

    with pytest.raises(NotImplementedError, match="not soportado"):
        procesar_documento(str(docx_file))

    with pytest.raises(ValueError, match="no reconocida"):
        procesar_documento(str(unknown_file))


def test_dispatcher_routing(tmp_path, monkeypatch):
    moodle_file = tmp_path / "export_moodle_grades.csv"
    moodle_file.write_text("Número de ID,Nombre,Apellido,Calificación\n123,Juan,Perez,80.5", encoding="utf-8")
    
    forms_file = tmp_path / "respuestas_formulario.csv"
    forms_file.write_text("Marca de tiempo,Email,Sugerencias\n2026-06-11 23:00:00,test@test.com,Buena clase", encoding="utf-8")

    xlsx_file = tmp_path / "reporte_interno.xlsx"
    # Escribir dataframe simple a xlsx usando openpyxl
    df = pd.DataFrame({"cod_alum": [1], "nota": [100]})
    df.to_excel(xlsx_file, index=False)

    # Mockear las llamadas internas de los lectores para comprobar el ruteo
    monkeypatch.setattr("pipeline.ingestion.dispatcher.leer_moodle_export", lambda path: {"fuente_tipo": "MOODLE", "path": path})
    monkeypatch.setattr("pipeline.ingestion.dispatcher.leer_forms_csv", lambda path: {"fuente_tipo": "FORM", "path": path})
    monkeypatch.setattr("pipeline.ingestion.dispatcher.leer_xlsx", lambda path: {"fuente_tipo": "SHEET", "path": path})

    assert procesar_documento(str(moodle_file))["fuente_tipo"] == "MOODLE"
    assert procesar_documento(str(forms_file))["fuente_tipo"] == "FORM"
    assert procesar_documento(str(xlsx_file))["fuente_tipo"] == "SHEET"


# ── Tests para Moodle Reader ────────────────────────────────────────────────

def test_normalizar_cabecera():
    assert normalizar_cabecera("Calificación/100,00") == "calificacion/100,00"
    assert normalizar_cabecera("Dirección de correo") == "direccion de correo"
    assert normalizar_cabecera("  Número de ID  ") == "numero de id"
    assert normalizar_cabecera("Última modificación (entrega)") == "ultima modificacion (entrega)"
    assert normalizar_cabecera("") == ""


def test_moodle_reader_univalle_headers(tmp_path):
    csv_content = (
        "Apellido(s),Nombre(s),Número de ID,Correo institucional,Total del curso,Estado\n"
        "Azaola,Damian,20002131,dazaa@univalle.edu,95.5,Entregado\n"
    )
    moodle_csv = tmp_path / "grades_moodle.csv"
    moodle_csv.write_text(csv_content, encoding="utf-8-sig")

    result = leer_moodle_export(str(moodle_csv))

    assert result["fuente_tipo"] == "MOODLE"
    assert result["nombre_archivo"] == "grades_moodle.csv"
    
    filas = result["filas_raw"]
    assert len(filas) == 1
    assert filas[0]["apellido"] == "Azaola"
    assert filas[0]["nombre"] == "Damian"
    assert filas[0]["codigo_estudiante"] == 20002131
    assert filas[0]["email"] == "dazaa@univalle.edu"
    assert filas[0]["nota_final"] == 95.5
    assert filas[0]["estado_entrega"] == "Entregado"

    # Verificar texto plano recomponiendo nombres e IDs
    assert "Estudiante: Damian Azaola" in result["texto_plano"]
    assert "ID: 20002131" in result["texto_plano"]
    assert "Nota: 95.5" in result["texto_plano"]


# ── Tests para Sheet Reader ──────────────────────────────────────────────────

def test_sheet_reader_validation_error(tmp_path):
    df_invalido = pd.DataFrame({"nota_parcial": [80], "observaciones": ["Falto"]})
    xlsx_file = tmp_path / "invalido.xlsx"
    df_invalido.to_excel(xlsx_file, index=False)

    with pytest.raises(ValueError, match="Fallo de validacion estructural"):
        leer_xlsx(str(xlsx_file))


def test_sheet_reader_validation_success(tmp_path):
    df_valido = pd.DataFrame({"cod_alumno": [101], "nota": [80]})
    xlsx_file = tmp_path / "valido.xlsx"
    df_valido.to_excel(xlsx_file, index=False)

    result = leer_xlsx(str(xlsx_file))
    assert result["fuente_tipo"] == "SHEET"
    assert len(result["filas_raw"]) == 1


# ── Tests para Forms Reader ──────────────────────────────────────────────────

def test_forms_reader_bom_and_newlines(tmp_path):
    # Saltos de línea huérfanos dentro de las comillas dobles
    csv_content = (
        "Marca de tiempo,Correo,Comentario\n"
        '2026-06-11 23:00:00,correo1@test.com,"Primer comentario\ncon salto de linea"\n'
        '2026-06-11 23:05:00 UTC,correo2@test.com,"Segundo comentario"\n'
    )
    forms_csv = tmp_path / "respuestas_forms.csv"
    forms_csv.write_text(csv_content, encoding="utf-8-sig")

    result = leer_forms_csv(str(forms_csv))

    assert result["fuente_tipo"] == "FORM"
    filas = result["filas_raw"]
    assert len(filas) == 2
    
    # Comprobar que los saltos de línea se hayan limpiado/reemplazado por un espacio
    assert filas[0]["comentario"] == "Primer comentario con salto de linea"
    
    # Comprobar normalización de fechas
    assert filas[0]["fecha_respuesta"].startswith("2026-06-11T23:00:00")
    assert filas[1]["fecha_respuesta"].startswith("2026-06-11T23:05:00")


# ── Tests para Text Cleaner y Payload BETO ────────────────────────────────────

def test_limpiar_texto():
    texto = "  Hola   Mundo!   \n\n\nEste es un   comentario con acentos (canción, ñandú)\n---"
    limpio = limpiar_texto(texto)
    assert limpio == "Hola Mundo!\n\nEste es un comentario con acentos (canción, ñandú)"


def test_normalizar_nombre():
    assert normalizar_nombre("  Ing. JUAN   pérez   ") == "Juan Perez"
    assert normalizar_nombre("Lic. Maria Gómez") == "Maria Gomez" or normalizar_nombre("Lic. Maria Gómez") == "Maria Gómez"  # depende de la normalización exacta


def test_preparar_payload_beto_explicit_cols():
    df = pd.DataFrame({
        "id": [1, 2],
        "comentario": ["Excelente curso, aprendí mucho.", "No me gustó el contenido."],
        "edad": [25, 30]
    })
    
    payload = preparar_payload_beto(df, "FORM", "evaluacion.csv", ["comentario"])
    
    assert len(payload) == 2
    assert payload[0]["texto_limpio"] == "Excelente curso, aprendí mucho."
    assert payload[0]["columna_origen"] == "comentario"
    assert payload[0]["id_fila"] == 0
    assert payload[0]["fuente_tipo"] == "FORM"
    assert payload[0]["nombre_archivo"] == "evaluacion.csv"


def test_preparar_payload_beto_heuristic():
    # Creamos un DF con una columna de comentarios (largos) y columnas cortas
    df = pd.DataFrame({
        "id": [101, 102, 103],
        "estado": ["aprobado", "reprobado", "aprobado"],  # Corto, promedio < 15
        "comentario_docente": [
            "El docente demuestra alto dominio de la materia y buena didáctica.",
            "Las clases fueron dinámicas, aunque faltó material complementario.",
            "Explicaciones claras y excelente predisposición a consultas de los estudiantes."
        ]  # Largo, promedio > 15 y 100% de celdas > 15
    })
    
    payload = preparar_payload_beto(df, "FORM", "docentes.xlsx")
    
    # Debe auto-detectar solo "comentario_docente" y no "estado"
    assert len(payload) == 3
    assert all(p["columna_origen"] == "comentario_docente" for p in payload)
    assert payload[0]["texto_limpio"].startswith("El docente demuestra")
