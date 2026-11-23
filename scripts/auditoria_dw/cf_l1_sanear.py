"""Sanea el catálogo y sincroniza el DW en la copia PostgreSQL tmpfs.

Las credenciales se leen de las variables CF_DW_DSN y CF_CATALOG_DSN.
Los respaldos del ensayo deben existir en el contenedor antes de ejecutar.
"""

import argparse
import csv
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from backend.services.programa_normalizador import (
    candidato_modulo, clave_nombre, codigo_modulo, es_invalido, normalizar_programa, partes_pos,
)

TABLA_DW = "dw.dim_modulo"
TABLA_LOCAL = "dw.cat_modulo"
TABLA_MAESTRA = "catalog.cat_programa"


def leer(conn, consulta):
    return list(conn.execute(text(consulta)).mappings())


def registrar(filas, tabla, id_, motivo, *, codigo='', antes=None, despues=None, **meta):
    filas.append(dict(tabla=tabla, id=id_, motivo=motivo, codigo=codigo, antes=antes, despues=despues, **meta))


def preparar_programas(mapa_programas, filas):
    programas = defaultdict(list)
    for p in mapa_programas:
        analisis = normalizar_programa(p['nombre_programa'])
        if not analisis.nombre or not partes_pos(p['pos_code'])[0]:
            raise ValueError(f"Oferta maestra inválida: id={p['id_programa']}")
        programas[analisis.clave_familia].append((p, analisis))

    cambios = []
    canonicos = {}
    for clave, ofertas in programas.items():
        # Las discrepancias institucionales se conservan para revisión.
        colision = any(len({p[col] for p, _ in ofertas if p[col] is not None}) > 1
                       for col in ('id_escuela', 'id_tipo_programa'))
        nombres = Counter(analisis.nombre for p, analisis in ofertas)
        nombre_representante = min(nombres, key=lambda nombre: (-nombres[nombre], nombre))
        for p, analisis in ofertas:
            nombre = analisis.nombre if colision else nombre_representante
            canonicos[p['pos_code']] = nombre
            raw = p['nombre_completo_raw'] or p['nombre_programa']
            origen = normalizar_programa(raw)
            version = p['version'] if p['version'] is not None else (origen.version or analisis.version)
            datos = {'nombre_programa': nombre, 'version': version, 'nombre_completo_raw': raw}
            if any(p[k] != v for k, v in datos.items()):
                cambios.append(dict(id=p['id_programa'], **datos))
            registrar(filas, TABLA_MAESTRA, p['id_programa'], 'REVISAR_METADATOS_FAMILIA' if colision else 'OFERTA',
                      codigo=p['pos_code'], antes=p['nombre_programa'], despues=nombre, raw=raw, familia=clave,
                      version=version, edicion=origen.edicion or analisis.edicion, alcance=origen.alcance or analisis.alcance)
    return cambios, canonicos


def sincronizar_modulos(conn, maestro, filas):
    locales = defaultdict(list)
    existentes = leer(conn, 'SELECT * FROM public.cat_modulo ORDER BY id_modulo')
    for local in existentes:
        pos, numero = partes_pos(local['codigo_modulo'])
        if pos is not None and numero is not None:
            locales[pos, numero].append(local)

    por_pos = defaultdict(list)
    cambios = 0
    claves_maestras = set()
    for m in maestro:
        pos, numero, nombre = m['pos_code'], m['nro_modulo'], m['nombre_modulo']
        if (pos, numero) in claves_maestras or es_invalido(nombre):
            raise ValueError(f"Módulo maestro inválido: {pos}, número {numero}")
        claves_maestras.add((pos, numero))
        codigo = codigo_modulo(pos, numero)
        candidatos = locales[pos, numero]
        if len(candidatos) > 1:
            for local in candidatos:
                registrar(filas, TABLA_LOCAL, local['id_modulo'], 'REVISAR_CLAVE_LOCAL_DUPLICADA', codigo=codigo)
                por_pos[pos].append((numero, nombre, local['id_modulo']))
            continue

        parametros = {'codigo': codigo, 'nombre': nombre, 'canonico': nombre[:200]}
        anterior = candidatos[0] if candidatos else None
        if anterior is None:
            id_local = conn.execute(text('''
                INSERT INTO public.cat_modulo (codigo_modulo, nombre_canonico, nombre_modulo)
                VALUES (:codigo, :canonico, :nombre) RETURNING id_modulo
            '''), parametros).scalar_one()
            motivo = 'INSERTADO'
        else:
            id_local = anterior['id_modulo']
            if (anterior['nombre_modulo'], anterior['nombre_canonico']) != (nombre, nombre[:200]):
                conn.execute(text('''
                    UPDATE public.cat_modulo SET nombre_modulo = :nombre, nombre_canonico = :canonico WHERE id_modulo = :id
                '''), dict(parametros, id=id_local))
                motivo = 'ACTUALIZADO'
            else:
                motivo = 'SIN_CAMBIOS'
        cambios += motivo != 'SIN_CAMBIOS'
        registrar(filas, TABLA_LOCAL, id_local, motivo, codigo=codigo,
                  antes=anterior['nombre_modulo'] if anterior else None, despues=nombre, id_maestro=m['id_modulo'])
        por_pos[pos].append((numero, nombre, id_local))
    return existentes, por_pos, cambios


def sanear_dimension(conn, dimension, programas, por_pos, filas):
    cambios = []
    for d in dimension:
        codigo, nombre, programa = d['pos_code'], d['nombre_modulo'], d['programa']
        pos, numero = partes_pos(codigo)
        programa_original = normalizar_programa(programa)
        analisis_nombre = normalizar_programa(nombre)
        familia = programa_original.nombre
        nombre_catalogo = programas.get(pos)
        if nombre_catalogo and (not familia or clave_nombre(nombre_catalogo) == programa_original.clave_familia):
            familia = nombre_catalogo
        motivos = []
        if nombre_catalogo and familia != nombre_catalogo:
            motivos.append('REVISAR_TITULO_DISTINTO_DEL_MAESTRO')
        if (numero is None and familia and clave_nombre(nombre) == clave_nombre(programa)
                and analisis_nombre.tiene_marcadores):
            nombre = familia
            motivos.append('TITULO_DE_OFERTA_CONFIRMADO')

        # CF-L0 identifica dos centinelas históricos. Solo POS-5129 tiene título corroborado.
        if (codigo, nombre, programa) == ('POS-3430', 'undefined v. undefined', None):
            nombre = codigo
            motivos.append('REVISAR_TITULO_NO_DOCUMENTADO')
        if (codigo, d['nombre_modulo'], d['programa']) == ('POS--5129', 'undefined v. undefined', None):
            pos = codigo = 'POS-5129'
            if pos not in programas or not any(x['pos_code'] == pos and x['id_modulo'] != d['id_modulo'] for x in dimension):
                raise ValueError('La reparación del centinela POS--5129 requiere corroboración en ambos orígenes')
            nombre = familia = programas[pos]
            motivos.append('CENTINELA_CORROBORADO_EN_AMBOS_ORIGENES')

        if es_invalido(codigo) or es_invalido(nombre) or es_invalido(familia):
            raise ValueError(f"Revisar dato inválido sin evidencia de reparación: dim_modulo {d['id_modulo']}")

        id_cat, motivo_fk = candidato_modulo(nombre, familia, codigo, por_pos.get(pos, []))
        if d['id_cat_modulo'] is not None and d['id_cat_modulo'] != id_cat:
            id_cat = d['id_cat_modulo']
            motivo_fk = f'REVISAR_FK_EXISTENTE_{motivo_fk}'
        nuevo = dict(nombre_modulo=nombre, programa=familia, pos_code=codigo, id_cat_modulo=id_cat)
        if any(d[k] != v for k, v in nuevo.items()):
            cambios.append(dict(id=d['id_modulo'], **nuevo))
        registrar(filas, TABLA_DW, d['id_modulo'], '|'.join(motivos + [motivo_fk]), codigo=codigo,
                  antes=d['nombre_modulo'], despues=nombre, programa_antes=programa, programa_despues=familia,
                  codigo_antes=d['pos_code'], fk_antes=d['id_cat_modulo'], fk_despues=id_cat,
                  familia=clave_nombre(familia), version=programa_original.version, edicion=programa_original.edicion,
                  alcance=programa_original.alcance)
    if cambios:
        conn.execute(text('''
            UPDATE public.dim_modulo SET nombre_modulo=:nombre_modulo, programa=:programa,
                pos_code=:pos_code, id_cat_modulo=:id_cat_modulo WHERE id_modulo=:id
        '''), cambios)
    return len(cambios)


def ejecutar(dw, catalogo):
    filas = []
    with catalogo.begin() as cat, dw.begin() as conn:
        cat.exec_driver_sql('LOCK TABLE public.cat_programa, public.cat_modulo IN SHARE ROW EXCLUSIVE MODE')
        programas = leer(cat, 'SELECT * FROM public.cat_programa ORDER BY id_programa')
        maestro = leer(cat, '''
            SELECT p.pos_code, m.id_modulo, m.nro_modulo, m.nombre_modulo FROM public.cat_modulo m
            JOIN public.cat_programa p USING (id_programa) ORDER BY p.pos_code, m.nro_modulo
        ''')
        cambios, canonicos = preparar_programas(programas, filas)
        if cambios:
            cat.execute(text('''
                UPDATE public.cat_programa SET nombre_programa=:nombre_programa, version=:version,
                    nombre_completo_raw=:nombre_completo_raw WHERE id_programa=:id
            '''), cambios)
        pk_programas = {p['id_programa'] for p in programas}
        pk_programas_despues = set(cat.execute(text('SELECT id_programa FROM public.cat_programa')).scalars())
        conn.exec_driver_sql('LOCK TABLE public.cat_modulo, public.dim_modulo IN SHARE ROW EXCLUSIVE MODE')
        dimension = leer(conn, 'SELECT * FROM public.dim_modulo ORDER BY id_modulo')
        locales, por_pos, n_local = sincronizar_modulos(conn, maestro, filas)
        n_dim = sanear_dimension(conn, dimension, canonicos, por_pos, filas)
        controles = leer(conn, '''
            SELECT count(*) FILTER (WHERE d.id_cat_modulo IS NOT NULL AND c.id_modulo IS NULL) AS fk_huerfanas,
                   count(*) FILTER (WHERE upper(d.pos_code) = 'MOD-GEN') AS mod_gen,
                   count(*) FILTER (WHERE d.programa ~* '\\mPOS\\s*[-–—:]?\\s*[0-9]') AS marcadores_pos,
                   count(*) FILTER (WHERE concat_ws(' ',d.pos_code,d.programa,d.nombre_modulo) ~* 'POS--|\\mundefined\\M') AS invalidos
            FROM public.dim_modulo d LEFT JOIN public.cat_modulo c ON c.id_modulo = d.id_cat_modulo
        ''')[0]
        mod_gen_nuevos = controles['mod_gen'] - sum((d['pos_code'] or '').upper() == 'MOD-GEN' for d in dimension)
        pk_antes = {d['id_modulo'] for d in dimension}
        pk_despues = set(conn.execute(text('SELECT id_modulo FROM public.dim_modulo')).scalars())
        pk_locales = {d['id_modulo'] for d in locales}
        pk_locales_despues = set(conn.execute(text('SELECT id_modulo FROM public.cat_modulo')).scalars())
        pk_cambios = len(pk_antes ^ pk_despues) + len(pk_locales - pk_locales_despues) + len(pk_programas ^ pk_programas_despues)
        controles_exigidos = {k: controles[k] for k in ('fk_huerfanas', 'marcadores_pos', 'invalidos')}
        controles_exigidos.update(pk_cambios=pk_cambios, mod_gen_nuevos=mod_gen_nuevos)
        if any(controles_exigidos.values()):
            raise ValueError(f'Controles DW incumplidos: {controles_exigidos}')
    return filas, dict(maestro=len(cambios), sincronizacion=n_local, dimension=n_dim), controles_exigidos


def verificar_respaldo(contenedor, ruta):
    listado = subprocess.check_output(['docker', 'exec', contenedor, 'pg_restore', '--list', ruta], text=True)
    sha = subprocess.check_output(['docker', 'exec', contenedor, 'sha256sum', ruta], text=True).split()[0]
    if 'TABLE DATA' not in listado:
        raise ValueError(f'El respaldo está vacío: {ruta}')
    return dict(ruta=ruta, sha256=sha, lineas_listado=len(listado.splitlines()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contenedor', default='beto_pg_tmpfs')
    parser.add_argument('--dw-respaldo', default='/tmp/cf_pre_saneamiento.dump')
    parser.add_argument('--catalogo-respaldo', default='/tmp/cf_pre_catalog.dump')
    parser.add_argument('--salida', required=True, type=Path)
    args = parser.parse_args()
    dw_url, cat_url = (make_url(os.environ[k]) for k in ('CF_DW_DSN', 'CF_CATALOG_DSN'))
    montaje = json.loads(subprocess.check_output(['docker', 'inspect', args.contenedor], text=True))[0]
    tmpfs = montaje['HostConfig'].get('Tmpfs') or {}
    puertos = montaje['NetworkSettings']['Ports'].get('5432/tcp') or []
    if '/var/lib/postgresql/data' not in tmpfs or dw_url.database == cat_url.database:
        raise ValueError('El ensayo requiere dos bases distintas en el contenedor tmpfs')
    for url in (dw_url, cat_url):
        if url.host != '127.0.0.1' or url.query or not any(p['HostIp'] == url.host and p['HostPort'] == str(url.port) for p in puertos):
            raise ValueError('El DSN debe apuntar al puerto localhost del contenedor tmpfs')
    filas = []
    respaldos = [verificar_respaldo(args.contenedor, ruta) for ruta in (args.dw_respaldo, args.catalogo_respaldo)]
    for url, respaldo in zip((dw_url, cat_url), respaldos):
        registrar(filas, 'respaldo', url.database, 'PG_RESTORE_LIST_Y_SHA256', despues=json.dumps(respaldo))
    dw, catalogo = [create_engine(url, connect_args={'connect_timeout': 5}) for url in (dw_url, cat_url)]
    primera, cambios, controles = ejecutar(dw, catalogo)
    _, reejecucion, _ = ejecutar(dw, catalogo)
    if any(reejecucion.values()):
        raise RuntimeError(f'La segunda ejecución hizo cambios: {reejecucion}')
    for tipo, datos in (('primera', cambios), ('segunda', reejecucion), ('controles', controles)):
        for metrica, valor in datos.items():
            registrar(filas, 'control', metrica, tipo, despues=valor)
    filas += primera
    campos = ('tabla', 'id', 'motivo', 'codigo', 'codigo_antes', 'antes', 'despues', 'programa_antes', 'programa_despues',
              'fk_antes', 'fk_despues', 'id_maestro', 'raw', 'familia', 'version', 'edicion', 'alcance')
    with args.salida.open('w', encoding='utf-8', newline='') as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas)
    print(json.dumps(dict(primera=cambios, segunda=reejecucion, controles=controles)))


if __name__ == '__main__':
    main()
