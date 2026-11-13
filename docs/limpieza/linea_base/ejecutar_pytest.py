"""Línea base sin acceso a bases ni servicios de red; no cambia tests/configuración."""
import os
import socket
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
os.chdir(ROOT)
sys.path[:0] = [str(ROOT), str(ROOT / 'backend')]
DEST = Path(__file__).resolve().parent
os.environ['COVERAGE_FILE'] = str(DEST / '.coverage')
os.environ['PGOPTIONS'] = '-c default_transaction_read_only=on'
for key in ('READINESS_TOKEN', 'READINESS_TOKEN_2', 'READINESS_DB_URL', 'READINESS_BETO_URL'):
    os.environ[key] = ''

# Permitir connect sólo dentro de la llamada síncrona a socketpair, por hilo.
# El código de aplicación/pruebas no puede abrir conexiones, tampoco a loopback.
_pair_state = threading.local()
_socketpair = socket.socketpair
_connect = socket.socket.connect
_connect_ex = socket.socket.connect_ex
def local_socketpair(*args, **kwargs):
    _pair_state.active = True
    try:
        return _socketpair(*args, **kwargs)
    finally:
        _pair_state.active = False
def internal_pair(address):
    return (getattr(_pair_state, 'active', False) and isinstance(address, tuple)
            and address[0] in ('127.0.0.1', '::1') and address[1] > 0)
def guarded_connect(self, address):
    if internal_pair(address):
        return _connect(self, address)
    raise OSError('LIMPIEZA: toda conexión de aplicación bloqueada')
def guarded_connect_ex(self, address):
    if internal_pair(address):
        return _connect_ex(self, address)
    raise OSError('LIMPIEZA: toda conexión de aplicación bloqueada')
socket.socketpair = local_socketpair
socket.socket.connect = guarded_connect
socket.socket.connect_ex = guarded_connect_ex
def deny_connection(*args, **kwargs):
    raise OSError('LIMPIEZA: conexión a servicio bloqueada')
socket.create_connection = deny_connection
import psycopg2
def deny_postgres(*args, **kwargs):
    raise psycopg2.OperationalError('LIMPIEZA: conexión PostgreSQL bloqueada; base viva y snapshot intactos')
psycopg2.connect = deny_postgres
psycopg2._connect = deny_postgres
psycopg2._psycopg.connect = deny_postgres

if '--verificar-aislamiento' in sys.argv:
    # Comprobar los bloqueos sin usar ninguna dirección ni credencial del proyecto.
    for fn in (psycopg2.connect, psycopg2._connect, psycopg2._psycopg.connect):
        try:
            fn('host=127.0.0.1 port=1 dbname=NO_CONECTAR')
        except psycopg2.OperationalError as e:
            assert 'LIMPIEZA' in str(e)
        else:
            raise AssertionError('Conexión PostgreSQL no bloqueada')
    for method in ('connect', 'connect_ex'):
        with socket.socket() as probe:
            try:
                getattr(probe, method)(('127.0.0.1',1))
            except OSError as e:
                assert 'LIMPIEZA' in str(e)
            else:
                raise AssertionError('Conexión TCP no bloqueada')
    a,b = socket.socketpair()
    a.sendall(b'OK')
    assert b.recv(2) == b'OK'
    a.close(); b.close()
    print('OK: 3 entradas psycopg2 y connect/connect_ex bloqueadas; socketpair interno funcional.')
    raise SystemExit(0)

import pytest
class Collection:
    def pytest_collection_finish(self, session):
        (DEST / 'pytest_nodeids.txt').write_text('\n'.join(item.nodeid for item in session.items)+'\n', encoding='utf-8')
raise SystemExit(pytest.main([
    '--cov=backend', '--cov=pipeline', '--cov-report=term',
    f'--cov-report=json:{DEST / "coverage.json"}',
    f'--junitxml={DEST / "pytest_junit.xml"}',
    '-o', 'cache_dir=docs/limpieza/linea_base/pytest_cache',
    '-o', 'faulthandler_timeout=60',
], plugins=[Collection()]))
