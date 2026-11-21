"""
FU-L3: migración 023 (fact_marketing.id_documento y grano programa x día x documento) contra la PostgreSQL tmpfs aislada.

Aplica la migración dentro de una transacción que SIEMPRE se revierte (nunca la DW viva ni el snapshot) y comprueba que:
- se puede aplicar dos veces (idempotente);
- dos documentos pueden traer inscripciones del mismo programa y día, y la captación (documento NULL) convive con ellas;
- el mismo programa y día sin documento (o del mismo documento) sigue siendo único;
- borrar el documento borra sus filas de fact_marketing (la causa del ×2).
Se omite si la copia tmpfs no está disponible. URL por defecto: la de `fu_l3_pg_tmpfs` (127.0.0.1:55438), con FU_L3_PG_URL.
"""

import os
import re
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

RAIZ = Path(__file__).resolve().parents[2]
URL = os.environ.get("FU_L3_PG_URL", "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55438/giragroup_db")
MIGRACION = RAIZ / "backend" / "scripts" / "migrations" / "023_fu_l3_fact_marketing_documento.sql"


def _aislada(url: str) -> bool:
    return bool(re.search(r"@(127\.0\.0\.1|localhost):554\d\d/", url))


@pytest.fixture
def cur():
    if not _aislada(URL):
        pytest.skip("FU_L3_PG_URL no apunta a una copia tmpfs aislada (127.0.0.1:554xx)")
    try:
        con = psycopg2.connect(URL, connect_timeout=3)
    except Exception:
        pytest.skip("copia tmpfs de PostgreSQL no disponible")
    con.autocommit = False
    c = con.cursor()
    try:
        yield c
    finally:
        con.rollback()   # nada de lo que escribe esta prueba se conserva
        con.close()


def _aplicar(c):
    sql = MIGRACION.read_text(encoding="utf-8")
    c.execute(sql.replace("\nBEGIN;", "\n").replace("\nCOMMIT;", "\n"))


def _sembrar(c):
    c.execute("INSERT INTO dim_tiempo (id_tiempo, gestion, semestre, mes, nombre_mes, periodo_mes, fecha, trimestre, "
              "semana_iso, dia_mes, dia_semana, nombre_dia, es_fin_semana) "
              "VALUES (20970101, 2097, 1, 1, 'Enero', '2097-01', '2097-01-01', 1, 1, 1, 4, 'Jueves', FALSE) ON CONFLICT (id_tiempo) DO NOTHING")
    c.execute("INSERT INTO dim_modulo (nombre_modulo, programa) VALUES ('MODULO FICTICIO', 'P') RETURNING id_modulo")
    mod = c.fetchone()[0]
    docs = []
    for n in ("a", "b"):
        c.execute("INSERT INTO dim_origen_documental (nombre_archivo, tipo_fuente) VALUES (%s, 'MARKETING') RETURNING id_documento",
                  (f"ficticio_{n}.xlsx",))
        docs.append(c.fetchone()[0])
    return mod, docs


def _fila(c, mod, doc, inscritos=1):
    c.execute("INSERT INTO fact_marketing (id_modulo, id_tiempo, leads, reservas, inscritos, costo_programa, id_documento) "
              "VALUES (%s, 20970101, 0, 0, %s, 0, %s)", (mod, inscritos, doc))


def test_la_migracion_es_idempotente(cur):
    _aplicar(cur)
    _aplicar(cur)
    cur.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'fact_marketing' AND column_name = 'id_documento'")
    assert cur.fetchone()[0] == 1


def test_dos_documentos_y_la_captacion_conviven_en_el_mismo_programa_y_dia(cur):
    _aplicar(cur)
    mod, (doc_a, doc_b) = _sembrar(cur)
    _fila(cur, mod, doc_a)
    _fila(cur, mod, doc_b)
    _fila(cur, mod, None)          # captación de planificación o fila sin documento
    cur.execute("SELECT COUNT(*) FROM fact_marketing WHERE id_modulo = %s", (mod,))
    assert cur.fetchone()[0] == 3


def test_el_mismo_programa_dia_y_documento_sigue_siendo_unico(cur):
    _aplicar(cur)
    mod, (doc_a, _) = _sembrar(cur)
    _fila(cur, mod, doc_a)
    cur.execute("SAVEPOINT s")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        _fila(cur, mod, doc_a)
    cur.execute("ROLLBACK TO SAVEPOINT s")
    _fila(cur, mod, None)
    cur.execute("SAVEPOINT s2")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        _fila(cur, mod, None)       # sin documento: una sola fila por programa y día, como antes de la 023
    cur.execute("ROLLBACK TO SAVEPOINT s2")


def test_borrar_el_documento_borra_sus_inscripciones(cur):
    _aplicar(cur)
    mod, (doc_a, doc_b) = _sembrar(cur)
    _fila(cur, mod, doc_a, inscritos=5)
    _fila(cur, mod, doc_b, inscritos=7)
    cur.execute("DELETE FROM dim_origen_documental WHERE id_documento = %s", (doc_a,))
    cur.execute("SELECT COALESCE(SUM(inscritos), 0) FROM fact_marketing WHERE id_modulo = %s", (mod,))
    assert cur.fetchone()[0] == 7
