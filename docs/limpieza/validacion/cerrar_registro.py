"""Cierra mediciones, mapas y referencias sólo después de una suite final verde."""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from pprint import pformat
import ast, csv, hashlib, json, os, re, subprocess
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[3]; doc=root/'docs/limpieza'; val=doc/'validacion'
initial=json.loads((doc/'PRE_FASE2_MANIFIESTO.json').read_text(encoding='utf-8'))
commits=json.loads((doc/'COMMITS_FASE2.json').read_text(encoding='utf-8'))
assert not any(r['revertido'] for r in commits)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()
date=datetime.now(ZoneInfo('America/La_Paz')).isoformat()
with (doc/'MAPA_TESTS.tsv').open(encoding='utf-8-sig') as f: tests=list(csv.DictReader(f,delimiter='\t'))
test_map={r['antiguo']:r['nuevo'] for r in tests}
old_ids=(doc/'linea_base/pytest_nodeids.txt').read_text(encoding='utf-8').splitlines()
new_ids=(val/'despues/nodeids.txt').read_text(encoding='utf-8').splitlines()
normalized=[test_map.get(i.split('::')[0],i.split('::')[0])+('::'+i.split('::',1)[1] if '::' in i else '') for i in old_ids]
assert len(new_ids)==len(set(new_ids))==652
assert set(normalized)==set(new_ids),'IDs perdidos o añadidos'
for old,new in test_map.items():
    assert (root/new).is_file(),new
    if old.endswith('.py') and old.startswith('tests/'):
        previous=subprocess.check_output(['git','show','pre-limpieza:'+old],cwd=root).decode('utf-8-sig')
        current=(root/new).read_text(encoding='utf-8-sig')
        def assertions(text): return [ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Assert)]
        assert assertions(previous)==assertions(current),'Aserción alterada: '+old

tree=ET.parse(val/'despues/junit.xml'); cases=tree.findall('.//testcase')
failed=[c for c in cases if c.find('failure') is not None or c.find('error') is not None]
skips=[c for c in cases if c.find('skipped') is not None]
xf=sum(c.find('skipped').get('type')=='pytest.xfail' for c in skips)
assert not failed
assert len(cases)-len(skips)==634 and len(skips)-xf==11 and xf==7
before=json.loads((val/'antes/coverage.json').read_text(encoding='utf-8'))
after=json.loads((val/'despues/coverage.json').read_text(encoding='utf-8'))
offline=json.loads((doc/'linea_base/coverage.json').read_text(encoding='utf-8'))
assert after['totals']['num_statements']==before['totals']['num_statements']==14066
delta=after['totals']['percent_covered']-before['totals']['percent_covered']
assert abs(delta)<=0.1, f'Cobertura fuera de tolerancia: {delta}'
assert set(after['files'])==set(before['files'])
preserved=[]
for r,meta in initial.items():
    protected=(r.startswith(('backend/','pipeline/','services/','frontend/','db/','data/')) or
               (r.startswith('docs/evidencias/') and not r.startswith('docs/evidencias/graficos/')) or
               r.startswith('docs/figuras_src/'))
    # Única excepción adicional autorizada: cuatro alias de graficos_v2.
    if protected and (root/r).exists():
        assert hashlib.sha256((root/r).read_bytes()).hexdigest()==meta['sha256'],r
        preserved.append(r)
    elif protected:
        assert r.startswith('docs/evidencias/graficos_v2/'),r

actions=[]; path_map={}
for row in commits:
    for change in row['cambios']:
        parts=change.split('\t');status=parts[0]
        if status=='D':
            old=parts[1]; actions.append(('eliminado',old,'',initial[old]['bytes'],row['tema'],row['commit']))
        elif status.startswith('R'):
            old,new=parts[1:3];path_map[old]=new
            actions.append(('archivado' if new.startswith('_archivo/') else 'movido',old,new,initial[old]['bytes'],row['tema'],row['commit']))
        elif status=='A' and parts[1].startswith('_archivo/'):
            new=parts[1];old=new.removeprefix('_archivo/');path_map[old]=new
            actions.append(('archivado (antes ignorado)',old,new,(root/new).stat().st_size,row['tema'],row['commit']))
deleted=[a for a in actions if a[0]=='eliminado']; deleted_paths={a[1] for a in deleted}
archive_bytes=sum(a[3] for a in actions if a[0].startswith('archivado'))
deleted_bytes=sum(a[3] for a in deleted)
aliases={'grafico_4_1_inconsistencias_corpus.png':'grafico_4_1_calidad_corpus.png',
         'grafico_4_2_confianza_probabilistica.png':'grafico_4_2_resoluciones_cascada.png',
         'grafico_4_3_distribucion_archivo_lote_1387.png':'grafico_4_3_vinculacion_por_archivo.png',
         'grafico_4_4_kpis_cmi.png':'grafico_4_4_kpi_cmi_perspectivas.png'}
replacement={}
for old in deleted_paths:
    name=aliases.get(Path(old).name,Path(old).name)
    candidate='docs/evidencias/graficos_v2/'+name
    if (root/candidate).exists():replacement[old]=candidate
replacement['docs/evidencias/graficos/figura_3_5_esquema_constelacion_fisico.png']='docs/figuras_src/figura_3_5_constelacion_dw.mmd'

def fmt(n,d=2): return f'{n:,.{d}f}'.replace(',','@').replace('.',',').replace('@','.')
def esc(x):return str(x).replace('|','\\|').replace('\n',' ')
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join('---' for _ in headers)+' |\n'+''.join('| '+' | '.join(esc(x) for x in row)+' |\n' for row in rows)

suite_counts=Counter(i.split('/')[1] for i in new_ids)
tot=after['totals']
dsection='## D. PRUEBAS Y COBERTURA — MEDICIÓN DE LIMPIEZA (13-nov-2026)\n\n'
dsection+=f'Esta medición sustituye las cifras de pruebas de rondas anteriores para el código `{head[:7]}`. No modifica las cifras de negocio del snapshot del 10-nov. PostgreSQL de validación en proyecto Docker aislado con tmpfs; dump copiado por lectura y hash original intacto. Evidencia: `docs/limpieza/validacion/despues_pytest.txt`, `despues/junit.xml`, `despues/coverage.json`.\n\n'
dsection+=table(['Métrica','Resultado medido'],[('Pruebas colectadas','652 IDs únicos'),('Passed','634'),('Skipped','11'),('Xfailed','7'),('Failed / error','0'),('Cobertura backend + pipeline',f"{fmt(tot['percent_covered'],6)} % ({fmt(tot['covered_lines'],0)}/{fmt(tot['num_statements'],0)})"),('Diferencia frente a línea base aislada',fmt(delta,6)+' puntos porcentuales')])
dsection+='\n`f3b37d9` colectaba 650: los dos casos nuevos son `test_el_catalogo_se_prepara_una_vez_y_se_rehace_si_cambia` y `test_preparado_equivale_al_algoritmo_original`, ahora en `tests/sprint3/test_person_resolver_preparado.py`. No se retiraron pruebas ni se cambiaron aserciones. Las cifras 493/475 y 650/632 no son la medición vigente. La línea base offline fue 629 passed / 5 fallos DW / 11 skipped / 7 xfailed, 68,384758 % (9.619/14.066); con la DW aislada las cinco pruebas dependientes de datos pasan.\n\n'
dsection+=table(['Suite','Colectadas'],sorted(suite_counts.items()))
dsection+='\nMapa histórico completo para Tabla 3.29, GCB-42 y matriz de trazabilidad: `docs/limpieza/MAPA_TESTS.tsv`. Los cinco tests Node de UI se miden aparte de pytest. La prueba extensa excluida en verificaciones rápidas sí se ejecutó en esta corrida completa.\n\n### Tabla D.2: Cobertura por componente\n\n'
components=[]
for prefix in ('backend/','pipeline/'):
    summaries=[x['summary'] for r,x in after['files'].items() if r.replace('\\','/').startswith(prefix)]
    total=sum(s['num_statements'] for s in summaries);covered=sum(s['covered_lines'] for s in summaries)
    components.append((prefix,total,covered,fmt(100*covered/total)+' %'))
dsection+=table(['Componente','Sentencias','Cubiertas','Cobertura'],components+[('TOTAL',tot['num_statements'],tot['covered_lines'],fmt(tot['percent_covered'],6)+' %')])
dsection+='\nEl detalle por archivo se conserva en coverage.json. Se mantienen los objetivos `--cov=backend --cov=pipeline`, las reglas omit originales y el denominador de 14.066 sentencias. Las 58 sentencias de diferencia respecto de 14.008 pertenecen a cambios anteriores a la limpieza; no se quitó código de backend/pipeline/services para alterar la métrica.\n\n---\n\n'

updated=json.loads((doc/'DOCUMENTOS_ACTUALIZADOS.json').read_text(encoding='utf-8')) if (doc/'DOCUMENTOS_ACTUALIZADOS.json').exists() else []
# Mantener también la fuente de Tabla 3.29/3.30 y su generador, sin ejecutar Word.
generator=root/'scripts/generar_tablas_tesis_v2.py'
generator_text=generator.read_text(encoding='utf-8-sig')
for old,new in path_map.items():generator_text=generator_text.replace(old,new)
parsed=ast.parse(generator_text)
assignments={n.targets[0].id:n for n in parsed.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
rows29=[]
for suite in ['sprint1','sprint2','sprint3','sprint4','sprint5','sprint6','readiness','transversales']:
    count=suite_counts[suite];sk,xx=(11,7) if suite=='readiness' else (0,0)
    rows29.append([suite,'tests/'+suite+'/',str(count-sk-xx),str(sk),str(xx),str(count),'100,0 % operativo' if sk+xx else '100,0 %'])
rows29.append(['TOTAL CONSOLIDADO','DW aislada; --cov=backend --cov=pipeline','634','11','7','652',fmt(100*634/652)+' %; 100 % operativo'])
rows30=ast.literal_eval(assignments['T3_30_DATA'].value)
normalized_cov={r.replace('\\','/'):v for r,v in after['files'].items()}
for row in rows30:
    path=row[0]
    if path=='TOTAL SISTEMA':summ=tot
    elif path in normalized_cov:summ=normalized_cov[path]['summary']
    elif path=='backend/routers/dataops.py':
        row[0]='backend/routers/dataops/'
        metrics=[v['summary'] for p,v in normalized_cov.items() if p.startswith(row[0])]
        n=sum(s['num_statements'] for s in metrics);c=sum(s['covered_lines'] for s in metrics)
        summ={'num_statements':n,'covered_lines':c,'missing_lines':n-c,'percent_covered':100*c/n}
    else:continue
    row[1:5]=[fmt(summ['num_statements'],0),fmt(summ['covered_lines'],0),fmt(summ['missing_lines'],0),fmt(summ['percent_covered'])+' %']
measured=f"652 pruebas (634 passed, 11 skipped, 7 xfailed, 0 failed; 13-nov-2026)"
cov_text=fmt(tot['percent_covered'],6)+f" % ({fmt(tot['covered_lines'],0)} de 14.066 sentencias)"
nota='Medición real del 13-nov-2026, commit '+head[:7]+': '+cov_text+'. Readiness: 11 omitidas condicionales y 7 fallos esperados documentados; sin fallos inesperados. Evidencia: docs/limpieza/validacion/despues/.'
values={'T3_29_DATA':rows29,'T3_30_DATA':rows30,'T3_29_NOTA':nota,
        'T3_4_NOTA':'382 pruebas corresponden al cierre histórico del Sprint 6. Medición vigente de limpieza: '+measured+'.'}
values['T3_34_HDR']=[s.replace('Valor Observado en Ronda 8','Valor Observado (Ronda 8; pruebas actualizadas 13-nov-2026)') for s in ast.literal_eval(assignments['T3_34_HDR'].value)]
for name in ('T3_34_DATA','T3_36_DATA','T4_1_DATA'):
    rows=ast.literal_eval(assignments[name].value)
    for row in rows:
        if row[0]=='Aseguramiento de software':row[2]=measured
        elif row[0].startswith('Obj. 6:'):row[2]=measured+'; '+cov_text
        elif 'Cobertura de pruebas automatizadas' in row[1]:row[3]=cov_text;row[-1]='Cumple (652 pruebas totales; medición 13-nov-2026)'
    values[name]=rows
lines=generator_text.splitlines(keepends=True)
for name,node in sorted(((n,assignments[n]) for n in values),key=lambda pair:pair[1].lineno,reverse=True):
    lines[node.lineno-1:node.end_lineno]=[name+' = '+pformat(values[name],width=140,sort_dicts=False)+'\n']
generator_text=''.join(lines)
generator_text=generator_text.replace('493 pruebas','652 pruebas').replace('475/11/7/0','634/11/7/0')
generator_text=generator_text.replace('TOTAL 493 / 475 / 60,7 % (8.062 de 13.278)','TOTAL 652 / 634 / '+cov_text)
generator_text=generator_text.replace('382 pruebas (493 tras estabilización)','382 históricas; 652 en limpieza 13-nov-2026')
manifest_tree=ast.parse(generator_text)
manifest_node=next(n for n in manifest_tree.body if isinstance(n,ast.FunctionDef) and n.name=='generar_manifiesto')
items_node=next(n for n in manifest_node.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='items')
items=ast.literal_eval(items_node.value)
for row in items:
    if row[0]=='Tabla 3.29':row[3]=' · '.join(s+' '+str(n) for s,n in sorted(suite_counts.items()))+' · TOTAL 652 / 634 / '+cov_text
    if row[0]=='Tabla 3.30':row[3]=str(len(rows30)-1)+' componentes seleccionados + TOTAL; '+cov_text+'; detalle completo en coverage.json'
manifest_lines=generator_text.splitlines(keepends=True)
manifest_lines[items_node.lineno-1:items_node.end_lineno]=['    items = '+pformat(items,width=140,sort_dicts=False).replace('\n','\n    ')+'\n']
generator_text=''.join(manifest_lines)
ast.parse(generator_text);generator.write_text(generator_text,encoding='utf-8');updated.append('scripts/generar_tablas_tesis_v2.py')

active=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
for r in active:
    if not r or not r.endswith('.md') or r.startswith(('_archivo/','docs/limpieza/','docs/evidencias/')):continue
    p=root/r;text=p.read_text(encoding='utf-8-sig');new=text
    for old,target in sorted(path_map.items(),key=lambda kv:-len(kv[0])):new=new.replace(old,target)
    for old,target in replacement.items():new=new.replace(old,target)
    for old in deleted_paths-replacement.keys():
        # Conservar la cita histórica en evidencias y en el registro, no como una ruta vigente.
        new=new.replace('`'+old+'`','Pendiente de recaptura/regeneración real (ver registro de limpieza)')
    if Path(r).name=='fuente_verdad_tesis.md':
        new=re.sub(r'## D\.[\s\S]*?(?=## E\.)',lambda m:dsection,new,count=1)
        new=new.replace('(475 passed)','(634 passed; medición 13-nov-2026)').replace('(60,8 %)','(medición vigente en sección D)')
    if r=='README.md':
        new=new.split('\n## Limpieza del repositorio (13-nov-2026)')[0]
        new+='\n## Limpieza del repositorio (13-nov-2026)\n\nPruebas en tests/sprint1 … sprint6, tests/readiness y tests/transversales. Resultado medido: 652 colectadas, 634 passed, 11 skipped, 7 xfailed, sin fallos, con PostgreSQL de validación aislado. Los cinco tests Node son adicionales.\n\nEl archivo histórico se conserva en [_archivo/](_archivo/), excluido del contexto Docker y de pytest. Gráficos vigentes: docs/evidencias/graficos_v2/. Mapa de rutas, commits, cobertura y capturas pendientes: [registro de limpieza](docs/limpieza/LIMPIEZA_REGISTRO.md). Las dependencias locales y la base viva se conservaron.\n'
    if r=='docs/tablas_v2.md':
        block29='### Tabla 3.29 Distribución de la suite de pruebas automatizadas por módulo y sprint\n\n'+table(['Suite','Directorio / componente','Passed','Skipped','Xfailed','Total','Éxito'],rows29)+'\nFuente: corrida real del 13-nov-2026; '+head[:7]+'.\n\n> '+nota+'\n\n---\n'
        block30='### Tabla 3.30 Reporte de cobertura de código por componente del sistema analítico\n\n'+table(['Módulo / archivo','Sentencias','Cubiertas','Sin cubrir','Cobertura','Responsabilidad'],rows30)+'\nSelección de componentes; el total corresponde al alcance completo. Detalle: docs/limpieza/validacion/despues/coverage.json.\n\n---\n'
        new=re.sub(r'### Tabla 3\.29[\s\S]*?(?=### Tabla 3\.30)',lambda m:block29,new,count=1)
        new=re.sub(r'### Tabla 3\.30[\s\S]*?(?=### Tabla 3\.34)',lambda m:block30,new,count=1)
        new=new.replace('493 pruebas (475 passed, 11 skipped, 7 xfailed, 0 failed)',measured)
        new=new.replace('493 pruebas automatizadas (475 passed, 11 skipped, 7 xfail, 0 failed); 60,7 % cobertura (8.062 de 13.278 sentencias)',measured+'; '+cov_text)
        new=new.replace('60,7 % (8.062 de 13.278 sentencias)',cov_text).replace('Cumple (493 pruebas totales)','Cumple (652 pruebas totales; medición 13-nov-2026)')
        new=new.replace('Valor Observado en Ronda 8','Valor Observado (Ronda 8; pruebas actualizadas 13-nov-2026)')
    if new!=text:p.write_text(new,encoding='utf-8');updated.append(r)
r='scripts/generar_fuente_verdad_doc.py';p=root/r;text=p.read_text(encoding='utf-8-sig')
text=re.sub(r'## D\.[\s\S]*?(?=## E\.)',lambda m:dsection,text,count=1)
text=text.replace('(475 passed)','(634 passed; medición 13-nov-2026)').replace('(60,8 %)','(medición vigente en sección D)')
text=text.replace('`docs/evidencias/graficos_v2/figura_3_5_esquema_constelacion_fisico.png`','`docs/figuras_src/figura_3_5_constelacion_dw.mmd` (PNG pendiente de regenerar)')
ast.parse(text);p.write_text(text,encoding='utf-8');updated.append(r)
makefile=root/'Makefile';make_text=makefile.read_text(encoding='utf-8-sig').replace('# docs/testing/Makefile','# Makefile')
makefile.write_text(make_text,encoding='utf-8');updated.append('Makefile')
(doc/'DOCUMENTOS_ACTUALIZADOS.json').write_text(json.dumps(sorted(set(updated)),ensure_ascii=False,indent=2),encoding='utf-8')

inventory=json.loads((doc/'INVENTARIO_DATOS.json').read_text(encoding='utf-8'))
by_path={x['ruta']:x for x in inventory['archivos']}
citation_rows=[]
for old in sorted(set(path_map)|deleted_paths):
    refs=by_path.get(old,{}).get('referencias',{})
    for kind in ('tesis','otros docs'):
        for src in refs.get(kind,[]):
            citation_rows.append((old,path_map.get(old,replacement.get(old,'retirada; pendiente recaptura/regeneración')),kind,src))
with (doc/'RUTAS_CITADAS_CAMBIADAS.tsv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f,delimiter='\t');writer.writerow(['ruta anterior','ruta actual o estado','tipo de cita','ubicación previa']);writer.writerows(citation_rows)

summary={'fecha':date,'commit_codigo_validado':head,'collected':652,'passed':634,'skipped':11,'xfailed':7,'failed':0,'coverage':tot,'delta_cobertura_vs_aislada_pp':delta,'delta_vs_offline_pp':tot['percent_covered']-offline['totals']['percent_covered'],'ids_perdidos':0,'ids_nuevos_en_limpieza':0,'aserciones_sin_cambios':True,'archivos_protegidos_hash_verificado':len(preserved),'bytes_retirados':deleted_bytes,'bytes_archivados_sin_liberacion_local':archive_bytes,'archivos_movidos':len([x for x in actions if x[0]=='movido'])}
(val/'DESPUES_RESUMEN.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')

report=['# Registro de limpieza — fase 2\n',f'Autorización explícita del usuario; rama `limpieza-repo`. Respaldo `pre-limpieza` = `5850dd4b81b429cceafc3cbfb45aaa38ebdba524`. Fecha de cierre: {date}. Código validado en `{head}`; el commit documental posterior contiene este registro y la actualización de referencias. Ningún historial se reescribió.\n',
        '## Resultados antes y después\n',table(['Control','Offline inicial','DW aislada antes','DW aislada después'],[
            ('Pytest','629 passed, 5 failed, 11 skipped, 7 xfailed','634 passed, 0 failed, 11 skipped, 7 xfailed','634 passed, 0 failed, 11 skipped, 7 xfailed'),
            ('Colección','652 únicas','652 únicas','652 únicas; mismo conjunto por mapa'),
            ('Cobertura',fmt(offline['totals']['percent_covered'],6)+' % (9.619/14.066)',fmt(before['totals']['percent_covered'],6)+' % (9.628/14.066)',fmt(tot['percent_covered'],6)+f" % ({tot['covered_lines']}/14.066)"),
            ('Node','5 passed','5 passed en verificación de sprint5','5 passed; independientes de pytest'),
            ('Frontend build','exit 0','sin cambios de código frontend','exit 0; frontend_build_despues.txt'),
            ('Compose config','exit 0','compose.yml aislado exit 0','config original y stack aislado exit 0'),
            ('Contenedores','no se levantaron','2 DB tmpfs saludables','9/9 healthchecks saludables, proyecto separado')]),
        f'\nDiferencia de cobertura controlada: **{fmt(delta,6)} puntos**, dentro de ±0,1. Frente al offline: {fmt(summary["delta_vs_offline_pp"],6)} puntos; este contraste además cambia disponibilidad del DW. Comparación decisiva: misma copia de datos y mismos flags antes/después. No cambió omit ni el denominador (14.066). Las 58 sentencias frente a 14.008 son anteriores a esta limpieza; backend, pipeline y microservicios se conservaron por hash.\n',
        'Los cinco fallos offline eran cuatro casos de test_forecasting y el contrato antes llamado test_loop4_validacion_estricta_contratos. Esperaban datos/método/horizonte y recibían sin_datos. Pasan con la copia aislada del snapshot. No se ocultaron con skip ni se modificaron sus aserciones.\n',
        '## Conciliación de 650 y 652\n\n`pytest --collect-only -q` contra una extracción temporal de `f3b37d9` dio 650 (collect_f3b37d9.txt). Los dos IDs nuevos de `ac9ea1f`, medidos antes de limpiar en `5850dd4`, son:\n\n- `tests/test_person_resolver_preparado.py::test_el_catalogo_se_prepara_una_vez_y_se_rehace_si_cambia`\n- `tests/test_person_resolver_preparado.py::test_preparado_equivale_al_algoritmo_original`\n\nDespués ambos están en tests/sprint3/test_person_resolver_preparado.py. No se añadieron/retiraron casos durante la limpieza; cero IDs perdidos/duplicados después de normalizar sólo rutas. Las aserciones AST originales y nuevas coinciden en todos los archivos de tests del mapa. La extracción/ZIP temporales de referencia se retiraron tras conservar la colección.\n',
        '## Commits y verificaciones\n\nCada commit de ejecución tuvo una verificación posterior. Las rápidas por sprint omiten únicamente la prueba de filas extensas por su costo; la suite completa final sí la ejecuta. Las verificaciones de otros temas usan 18 pruebas smoke de infraestructura, ingesta y KPI. No fue necesario revertir ningún commit.\n',
        table(['Tema','Commit','Suite rápida posterior','Node','Revertido'],[(c['tema'],c['commit'], 'exit '+str(c['quick_exit']), 'exit '+str(c['node_exit']), 'sí' if c['revertido'] else 'no') for c in commits]),
        '\nLos logs por tema y JUnit están en validacion/checks/. El commit de cierre documental puede identificarse con `git log -1 -- docs/limpieza/LIMPIEZA_REGISTRO.md`; también recibe smoke posterior.\n',
        '## Eliminado, archivado y movido\n\nLos borrados y movimientos versionados se realizaron con git rm/git mv. Se retiraron 83 PNG de las cuatro carpetas aprobadas, cuatro alias v2 exactos (se hallaron cuatro, no cinco) y cinco scripts de terminal. No se regeneraron ni alteraron cifras de gráficos existentes. Archivos archivados conservan bytes/hash; Jira_Proyecto.csv era local e ignorado y se incorporó directamente en su ubicación archivada.\n',
        table(['Acción','Ruta anterior','Ruta actual','Bytes originales','Motivo/tema','Commit'],actions),
        '\nLos cuatro alias retirados tienen igualdad SHA-256 verificada con su canónico en PREBORRADO_REFERENCIAS.md. Los diez PNG canónicos de graficos_v2 conservan sus hashes originales. Se mantienen todos los otros PNG/JPG en evidencias, incluidos E2E.\n',
        '## Mapa completo de tests\n\nConftest raíz y soporte tests/dataops_parches.py permanecen en su ruta. Ajustados imports de fixtures, búsqueda de raíz, SQLite temporal, Makefile, imports MJS y README. CI conserva explícitamente los mismos 26 archivos históricos y sus flags, para evitar ampliar silenciosamente su selección al mover tests; la validación de 652 se hizo con toda la suite. backend/test_upload.py y backend/tests/test_lote_estado_flujo.py siguen fuera de testpaths y no se incorporaron a la colección.\n',
        table(['Archivo anterior','Archivo actual','Tema'],[(r['antiguo'],r['nuevo'],r['tema']) for r in tests]),
        '## Figuras que requieren captura real o regeneración\n\nLa última autorización permitió retirar los PNG y scripts enumerados sin generar reemplazos ficticios. No hay nuevas capturas PNG en este trabajo: las salidas reales TXT, JUnit, JSON y healthchecks son verificables y sirven de origen para las capturas pendientes.\n',
        table(['Figura','Estado y fuente real requerida'],[
            ('1.40; 3.39; 3.40; 3.50','Capturar terminal real de la suite completa y coverage; archivos despues_pytest.txt / despues/coverage.json. No reutilizar paneles 650/632 ni 493/475.'),
            ('3.37 sprint5','Capturar la corrida real de tests/sprint5 y Node; validacion/checks/sprint5/.'),
            ('3.42','Capturar cabeceras HTTP reales y comprobaciones de seguridad; no dibujar respuestas cURL.'),
            ('Docker ps / 3.37 en mixto','Capturar docker compose ps del proyecto aislado con 9 healthchecks; healthchecks.jsonl y stack_up.txt.'),
            ('3.15','mostrar_logs_figura_3_15.py emite logging.info/warning con valores fijos: sí, simulación. Se conserva; sustituir por logs reales de ingesta.'),
            ('3.17','mostrar_logs_figura_3_17.py y generar_figura_3_17_logs.py usan líneas fijas: sí. El diagrama de secuencia homónimo de sprint4 es conceptual y se conserva.'),
            ('3.22','generar_figuras_tesis_sprint4.py::generar_figura_3_22 usa json_alumnos/json_metas literales: sí. Se conserva, recapturar API real.'),
            ('3.25','generar_figura_3_25_json.py usa JSON literal: sí. El mockup HITL de sprint5 es conceptual; ambos productores se conservan sin retiro adicional.'),
            ('3.35','runner_text contiene 18/18 Tests Passed y duraciones fijas: sí. Se conserva; requiere Postman/Newman real.'),
            ('3.36','curl_output contiene HTTP/1.1 y cabeceras fijas: sí. Se conserva; requiere HTTP real.'),
            ('Diagramas PNG retirados','Regenerar desde los scripts de diagramas conservados; la constelación mantiene docs/figuras_src/figura_3_5_constelacion_dw.mmd.')]),
        '\nLos productores generar_graficos_* y el oficial graficos_tesis_v2 escriben sólo en graficos_v2, sin copias a images/output/artefactos externos ni creación de los alias retirados. Se retiraron únicamente las funciones 3.34/3.37 del mixto sprint5_6 y 3.40/3.50 de ronda_final. e2e/lib.mjs no lee graficos/: se conservaron sus capturas. El generador de la fuente de verdad usa las rutas canónicas y las métricas reales de esta ejecución. Los productores históricos conservan sus datos previos; no fueron ejecutados para sobrescribir gráficos finales.\n',
        '## Tamaño y conservación\n',table(['Métrica','Bytes'],[
            ('Árbol original versionado (pre-limpieza)',sum(x['bytes'] for x in initial.values())),
            ('Retirados del árbol de trabajo por borrado',deleted_bytes),
            ('Archivados; sin ahorro local',archive_bytes),
            ('Árbol original después, descontando sólo borrados',sum(x['bytes'] for x in initial.values())-deleted_bytes),
            ('Total local de referencia fase1 (sin .git/entregables)',sum(inventory['totales_por_carpeta'].values())),
            ('Local comparable estimado sin nuevos entregables',sum(inventory['totales_por_carpeta'].values())-deleted_bytes)]),
        '\nLos entregables/logs de auditoría y los builds temporales agregan bytes; “retirados” no afirma ahorro neto del disco. Git conserva todos los objetos históricos y no se compactó ni reescribió. Archivar no libera espacio local. No se borraron entornos/dependencias del disco: los regenerables ya estaban ignorados y no tenían entradas versionadas que quitar con git rm --cached. Se añadieron patrones de perfiles y exclusiones, con excepción para perfiles de evidencia.\n',
        f'\nSe verificaron por SHA-256 **{len(preserved)} archivos protegidos** conservados. Microservicios completos, backend/pipeline, modelo/fixtures versionados, seeds/migraciones, figuras_src y evidencias finales se mantienen. Las seis copias backend/scripts se conservaron: además de sus referencias históricas, retirarlas cambia el alcance/denominador de cobertura. Makefile y .env se conservaron; .env sigue fuera de Git. Se conservan inventario_tablas*.json, tiempos_ciclo_mensual*.json (incluida corrida3 previa a A), root diccionario_datos.csv por compatibilidad y todos los __init__.py. Los CSV de apendices (los nueve duplicados y los restantes) se archivaron por aprobación expresa.\n',
        '## Cambios para la tesis y citas\n\nPREBORRADO_REFERENCIAS.md distingue rutas de archivo, basename y simples números de figura antes de borrar. RUTAS_CITADAS_CAMBIADAS.tsv enumera cada ruta afectada y todas sus ubicaciones previas. Las referencias en evidencias históricas/JSON y el DOCX de tablas se conservan como evidencia: no se reescribieron binarios ni mediciones. Las referencias en Markdown vigente se actualizaron; las capturas sin reemplazo quedan expresamente pendientes.\n\n1. Tabla 3.29, GCB-42 y matriz de trazabilidad: aplicar MAPA_TESTS.tsv y el desglose actual por sprint; total 652, 634/11/7/0, con commit y fecha.\n2. Tabla 3.30 y cobertura: usar 14.066 y la cobertura medida aquí, sin mezclar el denominador 14.008 o cifras 493/475. Se actualizó la sección D de ambas fuentes de verdad y su generador.\n3. Actualizar referencias a docs históricos y CSV a _archivo/<ruta-original>; el diccionario textual vigente permanece en docs/apendices/diccionario_datos.md.\n4. Actualizar las referencias gráficas a los nombres canónicos y obtener las capturas reales listadas arriba antes de publicar la tesis. El DOCX tablas_v2 y los pies/citas numéricas deben revisarse editorialmente.\n5. No cambian las cifras finales de negocio del snapshot, sus huellas ni los informes de medición finales. El dump original conserva SHA-256 14d45f5a128f44543927911dc0ad453f681d524ac05037203f5c0c2787e3a2eb. No se conectó a la DW viva ni se tocaron sus contenedores/volúmenes.\n']
local_after=0
for directory,dirs,names in os.walk(root):
    relative=Path(directory).relative_to(root).as_posix()
    dirs[:]=[d for d in dirs if d!='.git' and not (Path(directory)/d).is_symlink() and not (relative=='docs' and d=='limpieza')]
    for name in names:
        p=Path(directory)/name
        if p.is_file() and not p.is_symlink():local_after+=p.stat().st_size
future_paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
tracked_after=sum((root/r).stat().st_size for r in future_paths if r and not r.startswith('docs/limpieza/') and (root/r).is_file())
size_report={'local_antes_sin_git_ni_entregables':sum(inventory['totales_por_carpeta'].values()),'local_despues_mismo_alcance':local_after,'bytes_retirados_por_git_rm':deleted_bytes,'bytes_archivados_sin_ahorro_local':archive_bytes,'arbol_versionado_original_antes':sum(x['bytes'] for x in initial.values()),'arbol_versionado_despues_sin_entregables_nuevos':tracked_after,'exclusiones':['.git/','docs/limpieza/'],'unidad':'bytes lógicos; no espacio asignado en disco'}
(val/'TAMANOS.json').write_text(json.dumps(size_report,ensure_ascii=False,indent=2),encoding='utf-8')
report+=['\n### Medición efectiva después\n\nMismo alcance local que fase 1: se excluyen .git y docs/limpieza; incluye dependencias y cachés conservadas. La variación neta también refleja bytes de documentación modificada y cachés de pruebas; no equivale sólo a los borrados.\n',table(['Medición','Bytes'],[('Local antes',size_report['local_antes_sin_git_ni_entregables']),('Local después, medido',local_after),('Árbol versionado después, sin entregables de limpieza',tracked_after)]),'\nDetalle reproducible: validacion/TAMANOS.json. Los entregables nuevos se mantienen separados para no presentar su crecimiento como ahorro.\n']
(doc/'LIMPIEZA_REGISTRO.md').write_text('\n'.join(report),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
