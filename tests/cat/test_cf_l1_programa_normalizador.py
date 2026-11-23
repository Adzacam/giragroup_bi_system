"""CF-L1: familia de programa, claves de oferta y coincidencia de módulo."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

from services.programa_normalizador import (
    candidato_modulo,
    codigo_dimension,
    codigo_modulo,
    normalizar_campos_modulo,
    normalizar_programa,
    partes_pos,
)


@pytest.mark.parametrize('raw,nombre,pos,version,edicion,alcance', [
    ('POS-4244 DIPLOMADO EN CONTROL v. I - NAL', 'DIPLOMADO EN CONTROL', 'POS-4244', 1, None, 'NAL'),
    ('1RA JORNADA DE ODONTOLOGÍA PARA BEBÉ - NAL', 'JORNADA DE ODONTOLOGÍA PARA BEBÉ', None, None, 1, 'NAL'),
    ('2da. JORNADA DE ODONTOLOGÍA PARA BEBÉ – NAL', 'JORNADA DE ODONTOLOGÍA PARA BEBÉ', None, None, 2, 'NAL'),
    ('Programa de Ventas v27', 'Programa de Ventas', None, 27, None, None),
    ('Curso de Ventas v. 4–NAL', 'Curso de Ventas', None, 4, None, 'NAL'),
    ('Curso de Ventas V. IX', 'Curso de Ventas', None, 9, None, None),
    ('Curso de Ventas V. XIV', 'Curso de Ventas', None, 14, None, None),
    ('Curso en vídeo – NAL', 'Curso en vídeo', None, None, None, 'NAL'),
    ('DIPLOMADO EN BUSINES INTELLIGENCE v.3 - NAL', 'DIPLOMADO EN BUSINESS INTELLIGENCE', None, 3, None, 'NAL'),
    ('DIPLOMADO EN MARKETING ANALITICS V.1', 'DIPLOMADO EN MARKETING ANALYTICS', None, 1, None, None),
    ('Curso POS 4244 en ventas', 'Curso en ventas', 'POS-4244', None, None, None),
    ('POS--5129 undefined v. undefined', None, None, None, None, None),
    ('CURSO EN LEY 1178 Y GESTIÓN', 'CURSO EN LEY 1178 Y GESTIÓN', None, None, None, None),
    ('ANÁLISIS CLÍNICO – LABORATORIAL', 'ANÁLISIS CLÍNICO – LABORATORIAL', None, None, None, None),
    ('Curso V del siglo XXI', 'Curso V del siglo XXI', None, None, None, None),
    ('TALLER VI', 'TALLER VI', None, None, None, None),
])
def test_parsea_oferta(raw, nombre, pos, version, edicion, alcance):
    programa = normalizar_programa(raw)
    assert (programa.nombre, programa.pos_code, programa.version, programa.edicion, programa.alcance) == (nombre, pos, version, edicion, alcance)
    assert programa.raw == raw


@pytest.mark.parametrize('codigo,base,nro', [
    ('POS-003', 'POS-003', None),
    ('pos 5000', 'POS-5000', None),
    ('POS-4254-M01', 'POS-4254', 1),
    ('POS--5129', None, None),
    ('POS-4567-Mfoo', None, None),
    ('POS-4567 / POS-4568', None, None),
])
def test_separa_codigo_completo(codigo, base, nro):
    assert partes_pos(codigo) == (base, nro)


@pytest.mark.parametrize('codigo,esperado', [('MKT-GEN', 'MKT-GEN'), ('ADM-GEN', 'ADM-GEN'), ('MOD-GEN', None), ('undefined', None)])
def test_conserva_codigos_institucionales(codigo, esperado):
    assert codigo_dimension(codigo) == esperado


def test_conserva_asignatura_con_romano_en_titulo():
    assert normalizar_campos_modulo('Fundamentos V. II', 'Programa UX v.4', 'POS-5000-M02') == (
        'Fundamentos V. II', 'Programa UX', 'POS-5000-M02')


def test_limpia_titulo_de_oferta():
    assert normalizar_campos_modulo('Curso Finanzas v.4', 'Curso Finanzas v.4', 'POS-5000') == (
        'Curso Finanzas', 'Curso Finanzas', 'POS-5000')


def test_clave_modulo_local_es_estable():
    assert codigo_modulo('POS-5000', 1) == 'POS-5000-M01'


@pytest.mark.parametrize('nombre,programa,codigo,resultado', [
    ('Evaluación', 'Finanzas', 'POS-5000-M01', (101, 'VINCULADO')),
    ('Contabilidad', 'Finanzas', 'POS-5000', (101, 'VINCULADO')),
    ('Módulo N.º 2', 'Finanzas', 'POS-5000', (102, 'VINCULADO')),
    ('Módulo 2: Ventas', 'Finanzas', 'POS-5000', (102, 'VINCULADO')),
    ('Crédito', 'Finanzas', 'POS-5000-M01', (None, 'AMBIGUO')),
    ('Módulo 2: Crédito', 'Finanzas', 'POS-5000-M01', (None, 'NUMEROS_CONTRADICTORIOS')),
    ('Finanzas V. 2', 'Finanzas', 'POS-5000', (None, 'OFERTA_COMPLETA')),
    ('Contabilidad', 'Finanzas', None, (None, 'SIN_POS_VALIDO')),
    ('Contabilidad bancaria', 'Finanzas', 'POS-5000', (None, 'SIN_CANDIDATO')),
])
def test_fk_requiere_unicidad_en_oferta(nombre, programa, codigo, resultado):
    modulos = [(1, 'Contabilidad', 101), (2, 'Crédito', 102)]
    assert candidato_modulo(nombre, programa, codigo, modulos) == resultado
