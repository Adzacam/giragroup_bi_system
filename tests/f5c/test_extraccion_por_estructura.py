"""F5C C-2: cada entidad sale de la columna con su rol por la estructura del encabezado (nunca por el nombre del archivo).
Filas reales de TBL_INSCRITOS (se leen de uploads/data en la prueba; ningún dato personal queda escrito aquí) y variantes de encabezado.
"""
import os
import re
import sys
from types import SimpleNamespace

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from routers.dataops.extraccion import (  # noqa: E402
    EXCLUIR_CELDA_BETO, _es_encabezado_no_docente, _es_encabezado_no_estudiante, extract_entities_from_line,
)
from services.beto_integracion import EntidadBeto, mejor_propuesta  # noqa: E402

LIBRO = os.path.join(ROOT, "uploads", "data", "TBL_INSCRITOS.xlsx")


def _ent(ents, label):
    return next((e for e in ents if e["label"] == label), None)


def _leer(linea, est=(), doc=(), mod=(), tipo_fuente="MARKETING"):
    return extract_entities_from_line(linea, list(est), list(doc), list(mod), tipo_fuente=tipo_fuente)


@pytest.fixture(scope="module")
def filas_inscritos():
    if not os.path.exists(LIBRO):
        pytest.skip("uploads/data/TBL_INSCRITOS.xlsx no está (C-0)")
    import pandas as pd
    df = pd.read_excel(LIBRO, nrows=300).dropna(how="all")
    filas = []
    for _, r in df.iterrows():
        celdas = [f"{str(c).strip()}: {str(v).strip()}" for c, v in r.items() if str(v).strip() not in ("", "nan", "NaT")]
        filas.append((" | ".join(celdas), {str(c).strip(): str(v).strip() for c, v in r.items()}))
    assert len(filas) >= 200
    return filas


# ── (a) programa: código POS primero, luego el nombre; CARRERA / NIVEL / INSTITUCIÓN nunca ─────────────────────
def test_programa_filas_reales_sale_del_codigo_y_del_nombre(filas_inscritos):
    for linea, fila in filas_inscritos:
        prog = _ent(_leer(linea)[0], "PROGRAMA")
        assert prog is not None
        assert prog["posCodigo"] == fila["NUMEROPROYECTO"].upper()
        assert prog["nombrePrograma"] == fila["NOMBRE DEL PROGRAMA"]
        assert prog["token"] != fila.get("CARRERA") or fila.get("CARRERA") == fila["NOMBRE DEL PROGRAMA"]


@pytest.mark.parametrize("encabezado", ["POS", "NUMEROPROYECTO", "NUMERO PROYECTO", "N° POS", "NRO. POS", "Codigo POS", "POS - ACTAS"])
def test_programa_codigo_por_variantes_de_encabezado(encabezado):
    prog = _ent(_leer(f"{encabezado}: POS-4520 | NOMBRES: ANA | PATERNO: ROJAS")[0], "PROGRAMA")
    assert prog and prog["posCodigo"] == "POS-4520"


def test_codigo_que_no_pasa_el_patron_no_es_programa():
    # 'POS-CI INCRITOS' guarda POS + CI concatenados: no es el código del programa
    ents, _, _ = _leer("POS-CI INCRITOS: 4543-7801505 | NOMBRE DEL PROGRAMA: DIPLOMADO EN GESTION DEL TALENTO HUMANO")
    prog = _ent(ents, "PROGRAMA")
    assert prog["posCodigo"] is None and prog["token"] == "DIPLOMADO EN GESTION DEL TALENTO HUMANO"


@pytest.mark.parametrize("encabezado", ["NOMBRE DEL PROGRAMA", "Nombre del Programa", "NOMBRE_PROGRAMA", "PROGRAMA"])
def test_programa_nombre_por_variantes_de_encabezado(encabezado):
    prog = _ent(_leer(f"{encabezado}: DIPLOMADO EN AUDITORIA FORENSE")[0], "PROGRAMA")
    assert prog and prog["token"] == "DIPLOMADO EN AUDITORIA FORENSE"


@pytest.mark.parametrize("atributo", ["CARRERA", "NIVEL ACADEMICO", "UNIVERSIDAD/INSTITUTO", "UNIVERSIDA/INSTITUTO",
                                      "INSTITUCION DONDE TRABAJA", "GRADO ACADEMICO"])
def test_atributo_del_estudiante_nunca_es_programa_ni_modulo(atributo):
    ents, _, _ = _leer(f"NOMBRES: ANA MARIA | PATERNO: ROJAS | {atributo}: DIPLOMADO EN GESTION ESPECIALIDAD MAESTRIA")
    assert _ent(ents, "PROGRAMA") is None
    assert _ent(ents, "MÓDULO") is None


# ── (b) docente: solo de columnas con rol de docente ───────────────────────────────────────────────────────────
def test_docente_filas_reales_ninguno(filas_inscritos):
    """TBL_INSCRITOS no tiene columna de docente: antes 752 líneas tomaban CARRERA, CORREO… por la subcadena 'ing.'/'lic.'."""
    for linea, _ in filas_inscritos:
        assert _ent(_leer(linea)[0], "DOCENTE") is None


@pytest.mark.parametrize("columna, valor", [
    ("ASESOR", "Lic. Juan Perez Lopez"), ("COORDINADOR", "Ing. Rosa Vaca"), ("RESPONSABLE", "Dr. Luis Paz"),
    ("RAZON SOCIAL", "Lic. Contadores SRL"), ("CORREO ELECTRONICO", "dr.ana@correo.com"),
    ("COMENTARIOS", "el ing. explico muy bien"), ("CARRERA", "ING. COMERCIAL"),
    ("8. ¿QUE ASPECTOS DEL ESTILO DE ENSENANZA DEL DOCENTE CONSIDERA QUE PODRIAN MEJORARSE?", "Lic. Maria Soto"),
])
def test_columna_no_docente_nunca_da_docente(columna, valor):
    docentes = [SimpleNamespace(id_docente=1, nombre_completo="Juan Perez Lopez", _contextos=[])]
    ents, _, _ = _leer(f"NOMBRES: ANA | PATERNO: ROJAS | {columna}: {valor}", doc=docentes)
    assert _ent(ents, "DOCENTE") is None


@pytest.mark.parametrize("encabezado", ["DOCENTE", "Docente", "PROFESOR", "TUTOR", "FACILITADOR", "NOMBRE DEL DOCENTE", "DOCENTES"])
def test_columna_docente_real_si_da_docente(encabezado):
    ents, _, _ = _leer(f"MODULO: Gestion de Datos | {encabezado}: Ing. Pedro Rojas Vargas", tipo_fuente="ACTA")
    d = _ent(ents, "DOCENTE")
    assert d is not None and d["token"] == "Ing. Pedro Rojas Vargas"


def test_coincidencia_contextual_no_aplica_con_columnas():
    """Antes, 'docente' en un encabezado de pregunta bastaba para buscar en dim_docente nombres contenidos en la línea."""
    docentes = [SimpleNamespace(id_docente=7, nombre_completo="Carlos Alberto Mendoza", _contextos=[])]
    linea = "¿LA/EL DOCENTE EXPLICA CON CLARIDAD?: Si | COMENTARIO: Carlos Alberto Mendoza explico bien"
    assert _ent(_leer(linea, doc=docentes, tipo_fuente="EVALUACION_DOCENTE")[0], "DOCENTE") is None


def test_coincidencia_contextual_en_texto_libre_requiere_el_nombre_entero():
    docentes = [SimpleNamespace(id_docente=7, nombre_completo="Carlos Alberto Mendoza", _contextos=[]),
                SimpleNamespace(id_docente=8, nombre_completo="observaciones del docente sobre la clase", _contextos=[])]
    ents, _, _ = _leer("El docente Carlos Alberto Mendoza dicto la clase", doc=docentes, tipo_fuente="ACTA")
    assert _ent(ents, "DOCENTE")["matchedCanonical"] == "Carlos Alberto Mendoza"


def test_exclusion_beto_por_tipo():
    assert EXCLUIR_CELDA_BETO["DOCENTE"] is _es_encabezado_no_docente
    assert EXCLUIR_CELDA_BETO["ESTUDIANTE"] is _es_encabezado_no_estudiante
    assert not _es_encabezado_no_docente("DOCENTE") and not _es_encabezado_no_docente("NOMBRE DEL DOCENTE")
    for h in ("ASESOR", "COORDINADOR", "RESPONSABLE", "RAZON SOCIAL", "CORREO ELECTRONICO", "COMENTARIOS", "CARRERA"):
        assert _es_encabezado_no_docente(h), h
    # la exclusión del estudiante descartaba la columna DOCENTE también para el docente de BETO
    assert _es_encabezado_no_estudiante("DOCENTE")


def test_mejor_propuesta_docente_conserva_la_columna_docente_y_excluye_el_asesor():
    linea = "ASESOR: Juan Perez Lopez | DOCENTE: Pedro Rojas Vargas"
    asesor = EntidadBeto("DOCENTE", "Juan Perez Lopez", linea.index("Juan"), linea.index("Juan") + 16, 0.99)
    real = EntidadBeto("DOCENTE", "Pedro Rojas Vargas", linea.index("Pedro"), linea.index("Pedro") + 18, 0.80)
    assert mejor_propuesta([asesor, real], "DOCENTE", linea, EXCLUIR_CELDA_BETO) is real
    # con la exclusión del estudiante (la de antes) también se perdía la columna DOCENTE real
    assert mejor_propuesta([asesor, real], "DOCENTE", linea, _es_encabezado_no_estudiante) is None


# ── (c) módulo: solo columnas de módulo o curso (o la del programa si la hoja no tiene) ─────────────────────────
def test_modulo_filas_reales_sale_del_nombre_del_programa(filas_inscritos):
    for linea, fila in filas_inscritos:
        mod = _ent(_leer(linea)[0], "MÓDULO")
        assert mod is not None and mod["token"] == fila["NOMBRE DEL PROGRAMA"]
        assert mod["token"] not in (fila.get("NIVEL ACADEMICO"), fila.get("CARRERA")) or mod["token"] == fila["NOMBRE DEL PROGRAMA"]


@pytest.mark.parametrize("encabezado", ["MODULO", "Módulo", "NOMBRE DEL MODULO", "CURSO", "ASIGNATURA", "MATERIA", "COD_MODULO"])
def test_modulo_por_variantes_de_encabezado(encabezado):
    ents, _, _ = _leer(f"{encabezado}: Gestion de Datos | NOMBRE DEL PROGRAMA: DIPLOMADO EN DATOS", tipo_fuente="ACTA")
    assert _ent(ents, "MÓDULO")["token"] == "Gestion de Datos"


def test_modulo_no_sale_de_nivel_academico():
    ents, _, _ = _leer("NOMBRES: ANA | PATERNO: ROJAS | NIVEL ACADEMICO: ESPECIALIDAD | DIRECCION: Av. Gestion de proyectos 12")
    assert _ent(ents, "MÓDULO") is None


# ── (d) estudiante: RAZON SOCIAL y NIT nunca son el nombre ─────────────────────────────────────────────────────
def test_razon_social_y_nit_no_son_estudiante():
    ents, _, _ = _leer("RAZON SOCIAL: Maria Lopez Quispe | NIT: Juan Carlos Mamani | TIPO DE INSCRIPCION: INSCRIPCION NUEVO")
    est = _ent(ents, "ESTUDIANTE")
    assert est is None or est["token"] not in ("Maria Lopez Quispe", "Juan Carlos Mamani")
    assert _es_encabezado_no_estudiante("RAZON SOCIAL") and _es_encabezado_no_estudiante("NIT")
    assert not _es_encabezado_no_estudiante("COMUNITARIO")   # 'NIT' se compara como palabra completa


def test_estudiante_filas_reales_de_nombres_paterno_materno(filas_inscritos):
    for linea, fila in filas_inscritos[:50]:
        est = _ent(_leer(linea)[0], "ESTUDIANTE")
        partes = [fila.get(k) for k in ("NOMBRES", "PATERNO", "MATERNO") if fila.get(k) and fila.get(k) != "nan"]
        assert est is not None and est["token"] == " ".join(partes)


def test_ninguna_regla_menciona_el_nombre_de_un_archivo():
    src = open(os.path.join(ROOT, "backend", "routers", "dataops", "extraccion.py"), encoding="utf-8").read()
    assert not re.search(r"TBL_INSCRITOS|INSCRITOS\.xlsx|Cobranzas\.xlsx|ARCA", src)
