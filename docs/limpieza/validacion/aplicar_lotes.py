"""Lotes aprobados: git mv/rm, commit y smoke obligatorio con revert automático si falla."""
from pathlib import Path
import argparse, ast, csv, hashlib, json, re, subprocess, sys

ROOT=Path(__file__).resolve().parents[3]
DOC=ROOT/'docs/limpieza'
os_args=argparse.ArgumentParser()
os_args.add_argument('tema', choices=['respaldo','generadores','imagenes','archivo','sprint1','sprint2','sprint3','sprint4','sprint5','sprint6','transversales','registro'])
args=os_args.parse_args(); tema=args.tema
def git(*args,**kw):
    return subprocess.run(['git',*args],cwd=ROOT,check=True,**kw)
def output(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8').strip()
assert output('branch','--show-current')=='limpieza-repo'
initial=json.loads((DOC/'PRE_FASE2_MANIFIESTO.json').read_text(encoding='utf-8'))
changes=[]
def edit(r,text):
    p=ROOT/r;assert p.resolve().is_relative_to(ROOT)
    if p.read_text(encoding='utf-8-sig')!=text:
        p.write_text(text,encoding='utf-8');changes.append(r)
def remove(r,reason):
    assert r in initial, r
    git('rm','--',r);changes.append(r)
def move(old,new):
    assert (ROOT/new).resolve().is_relative_to(ROOT)
    (ROOT/new).parent.mkdir(parents=True,exist_ok=True)
    if subprocess.run(['git','ls-files','--error-unmatch',old],cwd=ROOT,capture_output=True).returncode:
        git('add','-f','--',old)
    git('mv','--',old,new);changes.extend((old,new))
def strip_functions(r,names):
    p=ROOT/r;text=p.read_text(encoding='utf-8-sig');tree=ast.parse(text);lines=text.splitlines(keepends=True)
    spans=[(node.lineno-1,node.end_lineno) for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    assert len(spans)==len(names),(r,spans)
    for start,end in sorted(spans,reverse=True):del lines[start:end]
    text=''.join(lines)
    for name in names:text=re.sub(r'^\s{4}'+re.escape(name)+r'\(\)\s*\n','',text,flags=re.M)
    text='\n'.join(line for line in text.splitlines() if not any(n+'.png' in line for n in ()))+'\n'
    ast.parse(text);edit(r,text)

aliases={
 'grafico_4_1_inconsistencias_corpus.png':'grafico_4_1_calidad_corpus.png',
 'grafico_4_2_confianza_probabilistica.png':'grafico_4_2_resoluciones_cascada.png',
 'grafico_4_3_distribucion_archivo_lote_1387.png':'grafico_4_3_vinculacion_por_archivo.png',
 'grafico_4_4_kpis_cmi.png':'grafico_4_4_kpi_cmi_perspectivas.png',
}

if tema=='respaldo':
    git('add','--','docs/limpieza')
elif tema=='generadores':
    # Retirar sólo las funciones aprobadas; no ejecutar ningún generador.
    strip_functions('scripts/generar_figuras_tesis_sprint5_6.py',{'generar_figura_3_34','generar_figura_3_37'})
    strip_functions('scripts/generar_graficos_ronda_final.py',{'generar_figura_3_40_pytest','generar_figura_3_50_cobertura'})
    r='scripts/generar_figuras_tesis_sprint5_6.py'
    text=(ROOT/r).read_text(encoding='utf-8')
    text='\n'.join(line for line in text.splitlines() if not any(n in line for n in ('figura_3_34_captura_pytest_cobertura.png','figura_3_37_captura_docker_ps.png')))+'\n'
    edit(r,text)
    for p in sorted((ROOT/'scripts').glob('generar_graficos*.py')):
        r=p.relative_to(ROOT).as_posix();text=p.read_text(encoding='utf-8-sig')
        if p.name=='generar_graficos_ronda_final.py':
            start=text.index('DIR_EVIDENCIAS_GRAFICOS =');end=text.index('def fmt_coma',start)
            text=text[:start]+'DIR_EVIDENCIAS_GRAFICOS = pathlib.Path("docs/evidencias/graficos_v2")\nDIR_EVIDENCIAS_GRAFICOS.mkdir(parents=True, exist_ok=True)\n\n'+text[end:]
            start=text.index('def guardar(');end=text.index('\n\n#',start)
            text=text[:start]+'''def guardar(fig, nombre_base):
    fig.savefig(DIR_EVIDENCIAS_GRAFICOS / nombre_base, dpi=300, bbox_inches='tight', facecolor='#FFFFFF', edgecolor='none')
    print(f"[OK] Generado: {nombre_base}")
'''+text[end:]
            text=text.replace('"grafico_3_2_distribucion_lote_1387.png", "grafico_4_2_confianza_probabilistica.png", "grafico_4_2_distribucion_lote_1387.png"','"grafico_3_2_distribucion_lote_1387.png", "grafico_4_2_resoluciones_cascada.png"')
            text=text.replace('    guardar(fig, "grafico_4_3_resolucion_por_formato.png")\n','').replace('    guardar(fig, "grafico_4_1_excepciones_calidad_lote.png")\n','')
            text=text.replace('- Destino principal: docs/evidencias/graficos/\n- Destinos réplica: docs/images/ y artefactos.','- Destino único: docs/evidencias/graficos_v2/.')
        elif p.name=='generar_graficos_capitulo4.py':
            text=text.replace('pathlib.Path("docs/images")','pathlib.Path("docs/evidencias/graficos_v2")')
            text=re.sub(r'^ARTIFACT_DIR = .*\n','',text,flags=re.M)
            text=re.sub(r'^    p2 = .*\n','',text,flags=re.M)
            text=re.sub(r'^    fig.savefig\(p2,.*\n','',text,flags=re.M)
            text=text.replace('grafico_4_3_resolucion_por_formato.png','grafico_4_3_vinculacion_por_archivo.png').replace('grafico_4_4_disponibilidad_kpi_cmi.png','grafico_4_4_kpi_cmi_perspectivas.png')
        elif p.name=='generar_graficos_veridicos_sprint3_4.py':
            text=text.replace('os.path.abspath("docs/images")','os.path.abspath("docs/evidencias/graficos_v2")')
            text=re.sub(r'^BRAIN_DIR = .*\n','',text,flags=re.M)
            tree=ast.parse(text)
            nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and 'copiar' in n.name]
            lines=text.splitlines(keepends=True)
            for n in sorted(nodes,key=lambda n:n.lineno,reverse=True):del lines[n.lineno-1:n.end_lineno]
            text=''.join(lines)
            for n in nodes:text=re.sub(r'^    '+re.escape(n.name)+r'\(\)\s*\n','',text,flags=re.M)
        else:
            text=text.replace('os.makedirs("output", exist_ok=True)','os.makedirs("docs/evidencias/graficos_v2", exist_ok=True)').replace('os.makedirs("docs/images", exist_ok=True)','')
            text=text.replace('"output/grafico_','"docs/evidencias/graficos_v2/grafico_')
            text=re.sub(r'^.*brain_dir = .*\n','',text,flags=re.M)
            text=re.sub(r'^fig\d.savefig\("docs/images/.*\n','',text,flags=re.M)
            text=re.sub(r'^if os.path.exists\(brain_dir\):\n    shutil.copy2\([^\n]+\)\n','',text,flags=re.M)
        for old,new in aliases.items():text=text.replace(old,new)
        ast.parse(text);edit(r,text)
    # El generador oficial no vuelve a fabricar alias por copy2.
    r='scripts/graficos_tesis_v2.py';text=(ROOT/r).read_text(encoding='utf-8-sig')
    text=re.sub(r'^    shutil.copy2\(OUTPUT_DIR / [^\n]+,\n\s+OUTPUT_DIR / [^\n]+\)\n','',text,flags=re.M)
    edit(r,text)
    # Otras entradas de gráficos: una sola salida, sin copias en imágenes ni raíz.
    r='scripts/grafico_3_2.py';text=(ROOT/r).read_text(encoding='utf-8-sig')
    text=re.sub(r'^fig.savefig\("grafico_3_2.png"[^\n]+\n','',text,flags=re.M)
    text=text.replace('fig.savefig("docs/images/','from pathlib import Path\nPath("docs/evidencias/graficos_v2").mkdir(parents=True, exist_ok=True)\nfig.savefig("docs/evidencias/graficos_v2/')
    edit(r,text)
    r='scripts/generar_fuente_verdad_doc.py';text=(ROOT/r).read_text(encoding='utf-8-sig')
    text=text.replace('docs/evidencias/graficos/','docs/evidencias/graficos_v2/')
    for old,new in aliases.items():text=text.replace(old,new)
    text=text.replace('with open(\'fuente_verdad_tesis.md\'','with open(\'docs/fuente_verdad_tesis.md\'')
    # Las capturas retiradas no tienen reemplazo válido hasta recaptura real.
    text=re.sub(r'`docs/evidencias/graficos_v2/figura_3_(40|50)_[^`]+`','Pendiente de captura real; consultar docs/limpieza/LIMPIEZA_REGISTRO.md',text)
    edit(r,text)
elif tema=='imagenes':
    assert (DOC/'PREBORRADO_REFERENCIAS.md').exists()
    for r in initial:
        if r.endswith('.png') and Path(r).parent.as_posix() in ('docs/images','docs/figuras','docs/figuras_tesis','docs/evidencias/graficos'):
            remove(r,'Retiro PNG aprobado explícitamente')
    for old,new in aliases.items():
        r='docs/evidencias/graficos_v2/'+old;c='docs/evidencias/graficos_v2/'+new
        assert initial[r]['sha256']==initial[c]['sha256']
        remove(r,'Alias exacto del canónico '+c)
    for name in ('generar_figura_1_40.py','generar_figura_3_37_sprint5_tests.py','generar_figura_3_39_pytest_cobertura.py','generar_figura_3_42_seguridad.py','generar_figura_docker_ps_9_servicios.py'):
        remove('scripts/'+name,'Terminal dibujada; retiro aprobado')
elif tema=='archivo':
    selections=[]
    for r in initial:
        if (r.startswith('docs/INFORME_CONSIDERACIONES_SEGURIDAD') or
            (r.startswith('docs/performance/') and Path(r).suffix=='.md') or
            r.startswith(('docs/testing/','docs/auditoria/','docs/Proyecto de grado/','docs/proyecto de grado/','docs/apendices/csv/'))):
            selections.append(r)
    for p in (ROOT/'docs/Proyecto de grado').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.relative_to(ROOT).as_posix() not in selections:
            selections.append(p.relative_to(ROOT).as_posix())
    for r in selections:move(r,'_archivo/'+r)
    r='.dockerignore';text=(ROOT/r).read_text(encoding='utf-8-sig')
    text+='\n# Archivo histórico y resultados locales de limpieza\n_archivo/\ndocs/limpieza/validacion/\ndocs/limpieza/linea_base/\n'
    edit(r,text)
    r='pyproject.toml';text=(ROOT/r).read_text(encoding='utf-8-sig')
    text=text.replace('testpaths = ["tests"]','testpaths = ["tests"]\nnorecursedirs = ["_archivo", ".git", ".venv", "node_modules", "__pycache__", "dist", "build", "*.egg", ".*", "_darcs", "CVS", "venv", "{arch}"]')
    edit(r,text)
    r='.gitignore';text=(ROOT/r).read_text(encoding='utf-8-sig')
    text+='\n# Perfiles locales; conservar perfiles de evidencia versionada\n*.prof\n!docs/evidencias/**/*.prof\n.coverage.*\n'
    edit(r,text)
elif tema.startswith('sprint') or tema=='transversales':
    with (DOC/'MAPA_TESTS.tsv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f,delimiter='\t'))
    selected=[(row['antiguo'],row['nuevo']) for row in rows if row['antiguo']!=row['nuevo'] and row['nuevo'].startswith('tests/'+tema+'/')]
    for old,new in selected:
        text=(ROOT/old).read_text(encoding='utf-8-sig')
        if new.endswith('.py'):
            # La raíz se encuentra por un marcador independiente de la profundidad.
            text=re.sub(r'Path\(__file__\)\.resolve\(\)\.parent\.parent', 'next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())',text)
            text=re.sub(r'Path\(__file__\)\.resolve\(\)\.parents\[1\]', 'next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())',text)
            text=text.replace('from tests.test_dataops_integridad import','from tests.sprint5.test_dataops_integridad import')
            text=text.replace('os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))','os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))')
        if new.endswith('.mjs'):
            text=text.replace("'../frontend/","'../../frontend/")
            if old.startswith('e2e/'):text=text.replace("'./lib.mjs'","'../../e2e/lib.mjs'")
        edit(old,text);move(old,new)
    for r in ('Makefile','README.md'):
        text=(ROOT/r).read_text(encoding='utf-8-sig')
        for old,new in selected:text=text.replace(old,new)
        edit(r,text)
    # Migración de imports externos al sprint movido.
    if tema=='sprint5':
        for p in (ROOT/'tests').rglob('*.py'):
            text=p.read_text(encoding='utf-8-sig')
            newtext=text.replace('from tests.test_dataops_integridad import','from tests.sprint5.test_dataops_integridad import')
            if text!=newtext:edit(p.relative_to(ROOT).as_posix(),newtext)
        r='.gitignore';text=(ROOT/r).read_text(encoding='utf-8-sig').replace('tests/test_auth_temp.db','tests/sprint5/test_auth_temp.db');edit(r,text)
        r='.github/workflows/ci.yml';text=(ROOT/r).read_text(encoding='utf-8-sig')
        historical_ci=sorted(p for p in initial if re.match(r'tests/sprint[1-4]/test_.*\.py$',p))
        # No ampliar silenciosamente una CI histórica con pruebas DW que antes no ejecutaba.
        # pytest tests/ continúa siendo la suite completa de 652, verificada aparte.
        text=text.replace('pytest tests/sprint1/ tests/sprint2/ tests/sprint3/ tests/sprint4/',
                          'pytest '+(' '+chr(92)+chr(10)+' '*12).join(historical_ci))
        edit(r,text)
    if tema in ('sprint5','sprint6','transversales'):
        marker=ROOT/f'tests/{tema}/__init__.py'
        if not marker.exists():marker.write_text('',encoding='utf-8');changes.append(marker.relative_to(ROOT).as_posix())
elif tema=='registro':
    git('add','--','docs/limpieza','docs/fuente_verdad_tesis.md','fuente_verdad_tesis.md','scripts/generar_fuente_verdad_doc.py','README.md')
    extra=DOC/'DOCUMENTOS_ACTUALIZADOS.json'
    if extra.exists():git('add','--',*json.loads(extra.read_text(encoding='utf-8')))

if tema not in ('respaldo','registro'):
    existing=[r for r in set(changes) if (ROOT/r).exists()]
    if existing:git('add','--',*existing)
# Los TXT/XML de stdout/JUnit se preservan literalmente, incluidos espacios de traceback.
git('diff','--cached','--check','--','.',':(exclude)docs/limpieza/**/*.txt',':(exclude)docs/limpieza/**/*.xml')
if not output('diff','--cached','--name-only'):
    print('Sin cambios para',tema);raise SystemExit(0)
git('commit','-m','chore(limpieza): '+tema)
commit=output('rev-parse','HEAD')
dest=DOC/'validacion/checks'/tema;dest.mkdir(parents=True,exist_ok=True)
command=[sys.executable,str(Path(__file__).with_name('pytest_aislado.py')),'--dest',str(dest),'--quick']
if tema.startswith('sprint') or tema=='transversales':
    command += ['--paths',f'tests/{tema}']
with (dest/'pytest.txt').open('w',encoding='utf-8') as log:
    result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
node_code=0
if tema=='sprint5':
    with (dest/'node.txt').open('w',encoding='utf-8') as log:
        node_code=subprocess.run(['node','--test','tests/sprint5/revision_cola.test.mjs','tests/sprint5/revision_espera.test.mjs'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
reverted=False
if result.returncode or node_code:
    git('revert','--no-edit',commit);reverted=True
record_path=DOC/'COMMITS_FASE2.json'
records=json.loads(record_path.read_text(encoding='utf-8')) if record_path.exists() else []
records.append({'tema':tema,'commit':commit,'quick_exit':result.returncode,'node_exit':node_code,'revertido':reverted,'cambios':output('show','--format=','--name-status','-M',commit).splitlines()})
if tema!='registro':
    record_path.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(records[-1],ensure_ascii=False))
if reverted:raise SystemExit('FALLO: commit revertido; revisar registro antes de continuar.')
