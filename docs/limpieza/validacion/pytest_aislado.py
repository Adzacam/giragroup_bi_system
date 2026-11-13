"""Ejecuta pytest permitiendo exclusivamente las dos PostgreSQL efímeras de limpieza."""
import argparse
import json
import os
from pathlib import Path
import socket
import sys
import threading

parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[3])
parser.add_argument('--dest', type=Path, required=True)
parser.add_argument('--collect', action='store_true')
parser.add_argument('--quick', action='store_true')
parser.add_argument('--paths', nargs='*')
args = parser.parse_args()
root, dest = args.repo.resolve(), args.dest.resolve()
dest.mkdir(parents=True, exist_ok=True)
os.chdir(root)
sys.path[:0] = [str(root), str(root/'backend')]
os.environ.update(
    DATABASE_URL='postgresql+psycopg2://giragroup_user:limpieza_solo_validacion@127.0.0.1:55434/giragroup_db',
    DW_TEST_URL='postgresql+psycopg2://giragroup_user:limpieza_solo_validacion@127.0.0.1:55434/giragroup_db',
    CATALOG_DATABASE_URL='postgresql+psycopg2://giragroup_user:limpieza_solo_validacion@127.0.0.1:55433/giragroup_catalog_db',
    PGOPTIONS='-c default_transaction_read_only=on',
    COVERAGE_FILE=str(dest/'.coverage'),
)
for key in ('READINESS_TOKEN','READINESS_TOKEN_2','READINESS_DB_URL','READINESS_BETO_URL'):
    os.environ[key] = ''

local = threading.local()
original_pair, original_connect, original_connect_ex = socket.socketpair, socket.socket.connect, socket.socket.connect_ex
def pair(*a, **kw):
    local.pair = True
    try:
        return original_pair(*a, **kw)
    finally:
        local.pair = False
def allowed(address):
    return (isinstance(address, tuple) and address[0] in ('localhost','127.0.0.1','::1')
            and (getattr(local,'pair',False) or address[1] in (55433,55434)))
def connect(self,address):
    if not allowed(address):
        raise OSError('LIMPIEZA: sólo se permiten las PostgreSQL de validación aislada')
    return original_connect(self,address)
def connect_ex(self,address):
    if not allowed(address):
        raise OSError('LIMPIEZA: destino de red no permitido')
    return original_connect_ex(self,address)
socket.socketpair, socket.socket.connect, socket.socket.connect_ex = pair, connect, connect_ex

import psycopg2
from psycopg2.extensions import parse_dsn
raw_connect = psycopg2._connect
def guarded_pg(dsn,*a,**kw):
    settings = parse_dsn(dsn)
    allowed_db = {('55434','giragroup_db'),('55433','giragroup_catalog_db')}
    if settings.get('host') not in ('127.0.0.1','localhost') or (settings.get('port'),settings.get('dbname')) not in allowed_db:
        raise psycopg2.OperationalError('LIMPIEZA: conexión fuera de las DB efímeras prohibida')
    return raw_connect(dsn,*a,**kw)
psycopg2._connect = psycopg2._psycopg.connect = guarded_pg

import pytest
class Collection:
    def pytest_collection_finish(self,session):
        (dest/'nodeids.txt').write_text('\n'.join(i.nodeid for i in session.items)+'\n',encoding='utf-8')

options = ['-o',f'cache_dir={dest / "pytest_cache"}','-o','faulthandler_timeout=120']
if args.collect:
    options += ['--collect-only','-q']
elif args.quick:
    # Todas las suites y módulos, exceptuando la prueba extensa O(n²) conocida.
    # La corrida completa final sí la ejecuta sin modificarla.
    options += ['-q','-k','not filas_extensas_y_muestras_no_producen_respuestas_gigantes',
                f'--junitxml={dest / "junit.xml"}']
    options += args.paths or ['tests/sprint1/test_infraestructura_y_docker.py',
                             'tests/sprint2/test_ingesta.py',
                             'tests/sprint4/test_kpis_and_catalogs.py']
else:
    options += ['--cov=backend','--cov=pipeline','--cov-report=term',
                f'--cov-report=json:{dest / "coverage.json"}',f'--junitxml={dest / "junit.xml"}']
raise SystemExit(pytest.main(options,plugins=[Collection()]))
