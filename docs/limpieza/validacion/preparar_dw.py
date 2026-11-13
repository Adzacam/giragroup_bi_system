"""Restaura una copia de sólo lectura del dump en el proyecto efímero, nunca en la pila viva."""
from pathlib import Path
import hashlib
import json
import subprocess

root = Path(__file__).resolve().parents[3]
compose = ['docker','compose','-p','giragroup_limpieza_validacion','-f',str(Path(__file__).with_name('compose.yml'))]
def feed(service,command,path):
    with path.open('rb') as source:
        subprocess.run(compose+['exec','-T',service]+command,stdin=source,check=True)
dump = root/'docs/evidencias/snapshot_dw_20261110_1201.dump'
expected = '14d45f5a128f44543927911dc0ad453f681d524ac05037203f5c0c2787e3a2eb'
assert hashlib.sha256(dump.read_bytes()).hexdigest() == expected
feed('db',['pg_restore','--exit-on-error','--no-owner','--no-privileges','-U','giragroup_user','-d','giragroup_db'],dump)
for filename in ('db/schema_catalogos.sql','db/seeds/seed_catalogos.sql'):
    feed('catalog_db',['psql','-v','ON_ERROR_STOP=1','-U','giragroup_user','-d','giragroup_catalog_db'],root/filename)
assert hashlib.sha256(dump.read_bytes()).hexdigest() == expected
print(json.dumps({'proyecto':'giragroup_limpieza_validacion','persistencia':'tmpfs','dump_sha256_antes_despues':expected,'snapshot_original':'sólo lectura de archivo, ninguna conexión a la base original'},ensure_ascii=False))
