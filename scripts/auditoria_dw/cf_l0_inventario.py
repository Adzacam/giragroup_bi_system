"""Inventario heurístico reproducible sobre cf_l0_tmpfs, sin datos de personas."""
import csv
import io
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path('docs/mediciones/cf_l0_familias_residuales.csv')

def leer(db, tabla):
    out = subprocess.check_output(['docker', 'exec', 'cf_l0_tmpfs', 'psql', '-U', 'postgres', '-d', db, '-c', f'COPY (SELECT * FROM {tabla} ORDER BY 1) TO STDOUT WITH CSV HEADER'])
    return list(csv.DictReader(io.StringIO(out.decode('utf-8'))))

def normal(s):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', s.upper()) if not unicodedata.combining(c)).split())

def familia(s):
    s = re.sub(r'(?i)\bPOS\s*[-:]?\s*\d+\b', '', s)
    s = re.sub(r'(?i)\bV\s*\.?\s*\d+\b', '', s)
    s = re.sub(r'(?i)\b\d+\s*(?:RA|DA|TA|RO|DO|TO)\.?\s*(?:EDICION)?\b', '', s)
    s = re.sub(r'(?i)\s*[-–—]\s*NAL\b', '', s)
    return normal(s).strip(' -–—.,')

dim = leer('cf_dw', 'dim_modulo')
local = leer('cf_dw', 'cat_modulo')
programas = leer('cf_catalog', 'cat_programa')
maestro = leer('cf_catalog', 'cat_modulo')
por_id = {p['id_programa']: p for p in programas}
por_pos = {normal(p['pos_code']): p for p in programas}
modulos = defaultdict(list)
for m in maestro:
    modulos[normal(por_id[m['id_programa']]['pos_code'])].append(m)
familias = defaultdict(set)
for p in programas:
    familias[familia(p['nombre_programa'])].add(p['pos_code'])

rows = []
def agregar(tipo, id_, codigo='', texto='', referencia='', categoria='', detalle=''):
    rows.append(dict(tipo=tipo, id=id_, codigo=codigo, texto=texto, referencia=referencia, categoria=categoria, detalle=detalle))

for table, data, expected in [('dw.dim_modulo', dim, 3930), ('dw.cat_modulo', local, 0), ('catalog.cat_programa', programas, 1229), ('catalog.cat_modulo', maestro, 1747)]:
    agregar('conteo', table, categoria=str(len(data)), detalle=f'entrada={expected}; diferencia={len(data)-expected}')

for d in dim:
    nombre, programa, pos = d['nombre_modulo'], d['programa'], normal(d['pos_code'])
    codigo = re.fullmatch(r'(POS-\d+)(?:-M(\d+))?', pos)
    valido = bool(codigo)
    oferta = codigo.group(1) if codigo else ''
    mismo = bool(nombre and programa and normal(nombre) == normal(programa))
    marcador = bool(re.search(r'(?i)\bPOS\s*[-:]?\s*\d+\b|\bV\s*\.?\s*\d+\b|\b\d+\s*(?:RA|DA|TA|RO|DO|TO)\b', nombre))
    clase = 'titulo_oferta_marcado' if mismo and marcador else ('titulo_oferta_sin_marcador' if mismo else 'asignatura_o_revision')
    candidatos = []
    if valido and not mismo:
        nro_texto = re.search(r'(?i)\bM[ÓO]DULO\s*(?:N[°ºO.]\s*)?(\d+)\b', nombre)
        nro = codigo.group(2) or (nro_texto.group(1) if nro_texto else None)
        candidatos = [m for m in modulos[oferta] if normal(m['nombre_modulo']) == normal(nombre) or (nro and int(m['nro_modulo']) == int(nro))]
    motivo = 'oferta_completa' if mismo else ('codigo_invalido' if not valido else ('sin_candidato' if not candidatos else ('candidato_unico' if len(candidatos)==1 else 'ambiguo')))
    agregar('dim_modulo', d['id_modulo'], d['pos_code'], nombre, programa, clase, f'fk={d["id_cat_modulo"] or "NULL"}; candidato={motivo}; ids_maestros={"|".join(m["id_modulo"] for m in candidatos)}; familia_heuristica={familia(programa)}')

for p in programas:
    fam = familia(p['nombre_programa'])
    agregar('cat_programa', p['id_programa'], p['pos_code'], p['nombre_programa'], p['nombre_completo_raw'], 'familia_compartida' if len(familias[fam]) > 1 else 'familia_unica', f'familia_heuristica={fam}; ofertas={len(familias[fam])}; version={p["version"]}')
for m in maestro:
    p = por_id[m['id_programa']]
    agregar('cat_modulo_maestro', m['id_modulo'], p['pos_code'], m['nombre_modulo'], p['nombre_programa'], 'modulo_maestro', f'nro_modulo={m["nro_modulo"]}')

dim_rows = [r for r in rows if r['tipo'] == 'dim_modulo']
for clase, cantidad in Counter(r['categoria'] for r in dim_rows).items():
    agregar('resumen', clase, categoria=str(cantidad), detalle='Clasificacion heuristica; requiere revision')
for clase, cantidad in Counter(r['detalle'].split('; ')[1] for r in dim_rows).items():
    agregar('resumen', clase, categoria=str(cantidad), detalle='Coincidencia por oferta y numero o nombre exacto normalizado; no crea FK')
agregar('resumen', 'pos_sin_sufijo', categoria=str(sum(bool(re.fullmatch(r'POS-\d+', normal(d['pos_code']))) for d in dim)), detalle='Subconjunto propuesto 1549; no equivale necesariamente a titulos con marcadores')
agregar('resumen', 'pos_con_sufijo_modulo', categoria=str(sum(bool(re.fullmatch(r'POS-\d+-M\d+', normal(d['pos_code']))) for d in dim)))
agregar('resumen', 'fuera_patron_pos', categoria=str(sum(not re.fullmatch(r'POS-\d+(?:-M\d+)?', normal(d['pos_code'])) for d in dim)), detalle='Incluye codigos no POS; no implica que todos sean invalidos')
agregar('resumen', 'familias_compartidas_heuristicas', categoria=str(sum(len(v)>1 for v in familias.values())), detalle='No demuestra colision semantica; revisar agrupaciones')
agregar('procedencia', 'metodo', texto='cf_l0_tmpfs: cf_dw y cf_catalog; cuatro tablas institucionales; fuente copiada con COPY SELECT; sin lote ni precalentamiento aplicable', detalle='Reproduccion: docker run -d --name cf_l0_tmpfs --tmpfs /var/lib/postgresql/data:rw,size=512m -e POSTGRES_HOST_AUTH_METHOD=trust postgres:16-alpine; crear bases cf_dw y cf_catalog; python scripts/auditoria_dw/cf_l0_copia.py; python scripts/auditoria_dw/cf_l0_inventario.py')

with OUT.open('w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['tipo','id','codigo','texto','referencia','categoria','detalle'])
    writer.writeheader()
    writer.writerows(rows)
print('dim categorias:', dict(Counter(r['categoria'] for r in rows if r['tipo']=='dim_modulo')))
print('dim candidatos:', dict(Counter(r['detalle'].split('; ')[1] for r in rows if r['tipo']=='dim_modulo')))
print('codigos fuera de patron POS:', sum(not re.fullmatch(r'POS-\d+(?:-M\d+)?', normal(d['pos_code'])) for d in dim))
print('familias compartidas heuristicas:', sum(len(v)>1 for v in familias.values()))
print('subconjunto POS sin sufijo:', sum(bool(re.fullmatch(r'POS-\d+', normal(d['pos_code']))) for d in dim))
print('archivo:', OUT)
