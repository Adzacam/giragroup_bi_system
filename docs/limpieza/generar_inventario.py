"""Auditoría estática: sólo lee el proyecto y escribe entregables en docs/limpieza."""
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from zoneinfo import ZoneInfo
import ast, csv, hashlib, json, os, re, subprocess, zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/limpieza'
EXT = {'.py','.csv','.png','.json','.md','.svg','.xlsx','.jsonl','.log','.prof','.txt','.sql','.yml','.yaml','.html','.mjs'}
TEXT = EXT - {'.png','.xlsx','.prof'} | {'.js','.jsx','.ts','.tsx','.toml','.bat','.sh','.conf','.ini','.css','.example','.webmanifest',''}
tracked = set(subprocess.check_output(['git','ls-files','-z'], cwd=ROOT).decode().split('\0')) - {''}
files, deps, empty, totals = {}, [], [], Counter()
for directory, dirs, names in os.walk(ROOT):
    rel = Path(directory).relative_to(ROOT).as_posix()
    dirs[:] = [d for d in dirs if d != '.git' and not (Path(directory)/d).is_symlink()]
    if rel == 'docs':
        dirs[:] = [d for d in dirs if d != 'limpieza']
    if not dirs and not names:
        empty.append(rel)
    for name in names:
        p = Path(directory)/name
        r = p.relative_to(ROOT).as_posix()
        if p.is_symlink():
            continue
        try:
            stat = p.stat()
        except OSError:
            continue
        totals[r.split('/')[0] if '/' in r else '(raíz)'] += stat.st_size
        item = {'ruta':r,'tipo':p.suffix.lower() or '(sin extensión)','bytes':stat.st_size,
                'modificado':datetime.fromtimestamp(stat.st_mtime, ZoneInfo('America/La_Paz')).isoformat(), 'tracked':r in tracked}
        if any(part in {'.venv','venv','node_modules','.pnpm-store'} for part in p.relative_to(ROOT).parts):
            deps.append(item)
        else:
            files[r] = item

sources = {}
for r,i in files.items():
    if (Path(r).suffix.lower() in TEXT or Path(r).name.endswith('Dockerfile')) and i['bytes'] < 8_000_000 and r != '.env' and '__pycache__' not in r:
        try:
            t = (ROOT/r).read_text(encoding='utf-8-sig')
            if '\x00' not in t:
                sources[r] = t
        except (OSError, UnicodeError):
            pass
    if r.startswith('docs/') and r.endswith('.docx'):
        # Sólo lectura de párrafos XML; no modificar ni renderizar el documento.
        with zipfile.ZipFile(ROOT/r) as z:
            paragraphs = []
            for name in z.namelist():
                if name.startswith('word/') and name.endswith('.xml') and any(s in name for s in ('document.xml','footnotes','endnotes','header','footer')):
                    xml = ET.fromstring(z.read(name))
                    paragraphs.extend(''.join(p.itertext()) for p in xml.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'))
            sources[r] = '\n'.join(paragraphs)

def group(r):
    if Path(r).name == 'fuente_verdad_tesis.md' or r in {'docs/tablas_v2.md','docs/tablas_v2.docx'}:
        return 'tesis'
    if (r.startswith('docs/') and Path(r).suffix in {'.md','.json','.txt','.docx','.csv'}) or r.endswith('.md'):
        return 'otros docs'
    if r.startswith(('tests/','e2e/')) or Path(r).name.startswith('test_'):
        return 'tests'
    if 'Dockerfile' in r or 'docker-compose' in r or r == '.dockerignore':
        return 'Docker'
    return 'código'

refs = defaultdict(lambda: defaultdict(set))
base_index, stem_index = defaultdict(list), defaultdict(list)
for r in files:
    base_index[Path(r).name].append(r)
    if r.endswith('.py'):
        stem_index[Path(r).stem].append(r)

citations = []
path_pattern = re.compile(r'(?<![\w])(?:[\w.ÁÉÍÓÚáéíóúñ -]+[/\\])+[\w.ÁÉÍÓÚáéíóúñ*() -]+\.(?:py|csv|png|jsonl?|md|svg|xlsx|log|prof|txt|sql|ya?ml|html|mjs|jsx?|dump|toml)(?::\d+(?:-\d+)?)?')
for src,t in sources.items():
    kind = group(src)
    for no,line in enumerate(t.splitlines(),1):
        # Filename references, including slash paths; ambiguous basenames are protected conservatively.
        tokens = set(re.findall(r'[\w.ÁÉÍÓÚáéíóúñ-]+\.[A-Za-z0-9]+', line))
        for token in tokens:
            for dst in base_index.get(token,[]):
                if dst != src:
                    refs[dst][kind].add(f'{src}:{no}')
        if src.endswith('.py') and re.match(r'\s*(from|import)\s',line):
            for token in re.findall(r'\b[A-Za-z_]\w*\b',line):
                for dst in stem_index.get(token,[]):
                    if dst != src:
                        refs[dst][kind].add(f'{src}:{no} (import candidato)')
        if kind == 'tesis' or (kind == 'otros docs' and src.startswith('docs/')):
            for m in path_pattern.finditer(line):
                token = m.group().strip().replace('\\','/')
                found = [r for r in files if r in token or token in r]
                citations.append((src,no,token,'; '.join(found) or 'NO RESUELTA: alias, rango o ruta ausente'))
                for dst in found:
                    if dst != src:
                        refs[dst][kind].add(f'{src}:{no}')

# Directorios citados: conservar su contenido, aunque se seleccionen archivos dinámicamente.
for src,t in sources.items():
    if group(src) not in {'tesis','otros docs','Docker','tests'}:
        continue
    for directory in set(re.findall(r'(?:docs|uploads|data|db|backend|pipeline|tests|scripts|frontend)/[\w./-]*/', t)):
        if '*' in directory or len(directory) < 7:
            continue
        for dst in files:
            if dst.startswith(directory) and src != dst:
                refs[dst][group(src)].add(f'{src} (directorio {directory})')

# Resolución de imports JS relativos; también cubre assets e index de módulos.
for src,t in sources.items():
    if Path(src).suffix not in {'.js','.jsx','.mjs','.ts','.tsx'}:
        continue
    for m in re.finditer(r'(?:from\s*|import\s*\(|import\s*)[\'\"](\.[^\'\"]+)',t):
        target = (ROOT/src).parent/m.group(1)
        for candidate in [target]+[Path(str(target)+e) for e in ('.js','.jsx','.mjs','.ts','.tsx')]+[target/'index.js',target/'index.jsx']:
            try:
                dst = candidate.resolve().relative_to(ROOT).as_posix()
            except ValueError:
                continue
            if dst in files:
                refs[dst]['código'].add(f'{src}:{t[:m.start()].count(chr(10))+1} (import)')

for no,line in enumerate(sources.get('docker-compose.yml','').splitlines(),1):
    if 'env_file: .env' in line and '.env' in files:
        refs['.env']['Docker'].add(f'docker-compose.yml:{no} (env_file)')

size_groups = defaultdict(list)
for r,i in files.items():
    if i['bytes'] and '__pycache__' not in r:
        size_groups[i['bytes']].append(r)
duplicates, hashes = [], {}
for size, paths in size_groups.items():
    if len(paths) < 2:
        continue
    by_hash = defaultdict(list)
    for r in paths:
        h = hashlib.sha256()
        with (ROOT/r).open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):
                h.update(chunk)
        hashes[r] = h.hexdigest()
        by_hash[h.hexdigest()].append(r)
    for h, same in by_hash.items():
        if len(same)>1:
            def rank(r):
                return ('backend/scripts/' in r, not bool(refs[r].get('tesis')), not files[r]['tracked'], r != 'docs/fuente_verdad_tesis.md', len(r),r)
            same.sort(key=rank)
            duplicates.append((h,same[0],same[1:]))
dup_map = {r:(h,c) for h,c,others in duplicates for r in others}
final_names = ('snapshot_dw_20261110_1201','regresion_A/','flujo_repetido_A2/','flujo_A_cache_vacia/','una_pasada/','deshacer_no_bloqueante','holtwinters_recalculo')
final_scripts = {'huella_dw.py','comparar_huellas.py','perfilar_flujo_dataops.py','medir_flujo_repetido.py','recalculo_mape_holtwinters.py'}
fake = set()
fake_png_names = defaultdict(set)
fake_mixed = set()
fake_functions = defaultdict(list)
for r,t in sources.items():
    if not r.startswith('scripts/generar_') or 'matplotlib' not in t:
        continue
    try:
        tree = ast.parse(t)
    except SyntaxError:
        continue
    plotting_functions = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef,ast.AsyncFunctionDef)):
            continue
        body = ast.get_source_segment(t,node) or ''
        if any(s in body for s in ('savefig(', 'guardar(fig,', 'plt.subplots(')):
            plotting_functions.append(node.name)
        if any(s in body for s in ('collected ', 'passed,', 'terminal_lines', 'terminal_header','test session starts','coverage: platform','"HTTP/1.1 200 OK"')) or ('docker compose ps' in body and 'ax.text' in body):
            names = set(re.findall(r'[\w.-]+\.png',body))
            if names:
                fake.add(r)
                fake_png_names[r].update(names)
                fake_functions[r].append(f'{node.name}:{node.lineno}')
    if r in fake and len(plotting_functions)>len(fake_png_names[r]):
        fake_mixed.add(r)
fake.add('scripts/generar_figura_1_40.py')
fake_png_names['scripts/generar_figura_1_40.py'].add('figura_1_40_resumen_pytest.png')
fake_outputs = set()
for r in fake:
    for name in fake_png_names[r]:
        fake_outputs.update(base_index.get(name,[]))

# Una versión histórica por tema, además de todo lo protegido/citado.
historic = {'docs/evidencias/RESUMEN_RONDA10.md','docs/evidencias/perfil_dataops/perfil.json','docs/evidencias/flujo_repetido/resumen.json','docs/architecture/auditoria_loops_sprint4.md','docs/auditoria/production_readiness_2026-11-01.md'}
current_docs = {'README.md','docs/fuente_verdad_tesis.md','docs/apendices/diccionario_datos.md','docs/architecture/forecasting_metodologia_cap4_cap5.md','docs/medicion-flujo-dataops.md','docs/medicion-flujo-dataops-repetida.md','docs/optimizacion-flujo-dataops-A.md'}
for r,i in files.items():
    rr = refs[r]
    protected = bool(rr.get('tesis') or rr.get('tests') or rr.get('Docker') or any(v.startswith('docs/') for v in rr.get('otros docs',[]))) or r.startswith(('db/','backend/scripts/migrations/')) or Path(r).name in final_scripts or any(n in r for n in final_names)
    cls, action, why = 'DUDOSO','mi decisión','Sin referencia estática concluyente; puede usarse por CLI, ruta dinámica o fuera del repositorio.'
    if r in fake or r in fake_outputs:
        cls,action,why = 'GENERADO','mi decisión' if protected or r in fake_mixed else 'eliminar','Terminal/resultado dibujado desde texto fijo: retirar imagen y función simulada; revisar cita antes de retirar evidencia protegida.'
        if r in fake_mixed:
            why += ' SCRIPT MIXTO: conserva figuras conceptuales/mediciones legítimas; no borrar el archivo completo, retirar sólo las funciones señaladas y sus llamadas.'
    elif Path(r).name in final_scripts or any(n in r for n in final_names):
        cls,action,why = 'EVIDENCIA FINAL','conservar','Reproducibilidad final solicitada; inmutable en esta limpieza.'
    elif any(p in r.split('/') for p in ('__pycache__','.pytest_cache','htmlcov','dist')) or Path(r).suffix in {'.pyc','.pyo','.log'} or Path(r).name == '.coverage':
        cls,action,why = 'GENERADO','mi decisión' if protected else 'eliminar','Artefacto regenerable; excluir de Git. Nunca borrar por extensión si es evidencia citada.'
    elif Path(r).name == '__init__.py':
        cls,action,why = 'USADO','conservar','Marcador de paquete: su ruta tiene función propia aunque el contenido/hash coincida con otro paquete.'
    elif r.startswith('frontend/public/') or r in {'.env','.env.example','iniciar_sistema.bat','apagar_sistema.bat','reconstruir_sistema.bat'}:
        cls,action,why = 'USADO','conservar','Contrato de arranque/configuración o asset público servido por Vite/PWA; preservar ubicación aunque comparta hash o el nombre se resuelva dinámicamente.'
    elif r in dup_map:
        h,c = dup_map[r]
        cls,action,why = 'DUPLICADO','mi decisión' if protected else 'archivar','Igualdad SHA-256; canónico propuesto '+c+'; hash '+h+'. Validar rutas y consumidor antes de consolidar.'
    elif r in current_docs or r in historic:
        cls,action,why = ('USADO' if r in current_docs else 'EVIDENCIA ANTIGUA'),'conservar',('Documento vigente o metodología final.' if r in current_docs else 'Única referencia histórica propuesta para este tema; las adicionales protegidas requieren decisión expresa.')
    elif rr.get('tesis') and r.startswith('docs/evidencias/'):
        cls,action,why = 'EVIDENCIA FINAL','conservar','Citado por documentación de tesis (protección conservadora; una cita antigua no certifica vigencia numérica).'
    elif r.startswith('docs/evidencias/') and rr.get('otros docs'):
        cls,action,why = 'EVIDENCIA ANTIGUA','mi decisión','Citado por reportes anteriores; evaluar contra medición final e historia elegida. Avisar y actualizar enlaces antes de archivar a _archivo/'+r+'.'
    elif r.startswith(('tests/','e2e/')) or r in {'conftest.py','pyproject.toml','README.md','.gitignore','.dockerignore'} or r.startswith(('db/','backend/scripts/migrations/')) or rr.get('código') or rr.get('tests') or rr.get('Docker'):
        cls,action,why = 'USADO','conservar','Consumidor estático o contrato de ejecución, pruebas, migración o configuración.'
    elif r.startswith('docs/') and r.endswith('.md'):
        cls,action,why = 'EVIDENCIA ANTIGUA','mi decisión' if protected else 'archivar','Reporte de iteración/propuesta o vigencia pendiente; destino _archivo/'+r+'; requiere actualización de enlaces antes de archivar.'
    elif rr.get('tesis'):
        cls,action,why = 'USADO','conservar','Ruta citada en tesis o reportes: lista blanca.'
    elif Path(r).suffix == '.prof' or r.startswith('backend/scripts/'):
        cls,action,why = 'DUDOSO','mi decisión','Perfil/copia potencial: comprobar productor, hash y arranque; backend/scripts/run_migrations.py y migraciones se conservan.'
    i.update(clasificacion=cls,accion=action,motivo=why,protegido=protected,referencias={k:sorted(v) for k,v in rr.items()})

def sprint(r):
    n = Path(r).name
    if '/readiness/' in r: return 'readiness','puertas de salida'
    if '/load/' in r or 'verification_loops' in n: return 'sprint6','carga, seguridad y validación de calidad'
    m = re.search(r'/sprint([1-6])/',r)
    if m: return 'sprint'+m[1],'conservar suite existente'
    if n in {'conftest.py','__init__.py','dataops_parches.py'}: return '', 'infraestructura compartida; conservar ruta'
    if n == 'test_agnostic_classifier_and_dw_reset.py': return 'transversales','archivo mixto: ingesta (2), NER (3) y seguridad del reset DW (4/6); conservar entero para evitar dividir IDs'
    if any(s in n for s in ('esquema','migraciones')): return 'sprint1','esquema e infraestructura'
    if any(s in n for s in ('dataops','bandeja','revision_','ingesta_sin_timeout','powerbi','reportes_export','email_redesign','elegir_tipo_fuente','dedup_por_contenido','evaluacion_docente_revision','catalogo_modulos')): return 'sprint5','plataforma web y DataOps'
    if any(s in n for s in ('otp_','auth_and_rbac')): return ('sprint6','seguridad y entorno de pruebas') if 'otp_' in n else ('sprint4','identidad de acceso y RBAC')
    if any(s in n for s in ('person_','cedula','extractor_estudiante','pipeline_financiero','fk_resolver','coherencia','fecha_fuera','reduccion_hitl')): return 'sprint3','identidad, normalización, reglas financieras y calidad de entidades'
    if any(s in n for s in ('formatos','fecha_corte','datos_reales')): return 'sprint2','lectura e ingesta de fuentes'
    return 'sprint4','DW, KPI, CMI, alertas, pronósticos y staging'

test_map = []
for r in sorted(files):
    if r in {'backend/test_upload.py','backend/tests/test_lote_estado_flujo.py'}:
        test_map.append((r,r,'fuera de testpaths actual; conservar hasta decisión expresa','No introducir en tests/: cambia colección; test_upload ejecuta peticiones al importar. No ejecutar en fase 1.'))
        continue
    if r in {'e2e/ciclo_ui.mjs','e2e/mapeo_ui.mjs'}:
        test_map.append((r,'tests/sprint5/'+Path(r).name,'plataforma web/DataOps E2E','Actualizar import ./lib.mjs a ../../e2e/lib.mjs y comandos/documentos; no ejecutar contra base viva en esta auditoría.'))
        continue
    if (r.startswith('tests/') and (Path(r).name.startswith('test_') and r.endswith('.py') or r.endswith('.test.mjs'))) or (r.startswith('tests/load/') and r.endswith('.py')) or (r.startswith('frontend/') and r.endswith('.mjs') and re.search(r'test|spec',Path(r).name)):
        sp, reason = sprint(r)
        name = Path(r).name.replace('test_sprint4_verification_loops.py','test_seguridad_y_resiliencia_api.py')
        dest = f'tests/{sp}/{name}' if sp else r
        hazards = []
        for no,line in enumerate(sources.get(r,'').splitlines(),1):
            if any(s in line for s in ('parents[','parent.parent','tests.','test_auth_temp.db','sys.path')):
                hazards.append(f'{r}:{no}')
        test_map.append((r,dest,reason,'; '.join(hazards) or 'Validar imports relativos y fixtures en fase 2'))

def esc(x): return str(x).replace('|','\\|').replace('\n',' ')
def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(esc(x) for x in row)+' |\n' for row in rows)
def ref_text(i):
    return '; '.join(k+': '+('sí, '+', '.join(i['referencias'][k]) if i['referencias'].get(k) else 'no detectado') for k in ('código','tests','Docker','tesis','otros docs'))

with (OUT/'INVENTARIO_DATOS.json').open('w',encoding='utf-8') as f:
    json.dump({'archivos':list(files.values()),'dependencias':{'archivos':len(deps),'bytes':sum(i['bytes'] for i in deps)},'vacias':empty,'totales_por_carpeta':dict(totals),'duplicados':duplicates,'tests':test_map},f,ensure_ascii=False,indent=2)
with (OUT/'RUTAS_CITADAS_TESIS.tsv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f,delimiter='\t');w.writerow(['documento','línea','ruta citada','resolución']);w.writerows(citations)
with (OUT/'MAPA_TESTS.tsv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f,delimiter='\t');w.writerow(['antiguo','nuevo','tema','dependencias a ajustar']);w.writerows(test_map)

external = [i for i in deps if i['tipo'] in EXT]
with (OUT/'INVENTARIO_DEPENDENCIAS.md').open('w',encoding='utf-8') as f:
    f.write('# Dependencias instaladas (sólo metadatos)\n\nNo son código propio ni candidatas a limpieza. Se conservan completas .venv y node_modules; ya están ignoradas. No se analiza el grafo interno de paquetes de terceros. Tamaños en bytes, fechas America/La_Paz.\n\n')
    f.write(table(['ruta','tipo','tamaño','última modificación','referenciado por','clasificación','acción propuesta'],((i['ruta'],i['tipo'],i['bytes'],i['modificado'],'Entorno instalado; referencias internas no auditadas','USADO','conservar') for i in external)))

report = ['# Inventario y propuesta de limpieza — Fase 1\n',
    'Estado: **sólo inventario; fase 2 NO autorizada ni ejecutada**. Se crearon únicamente respaldo Git y entregables/línea base. No se movió ni eliminó código, evidencia o documentación previa.\n',
    'Respaldo: rama `limpieza-repo`, etiqueta `pre-limpieza`, commit `5850dd4b81b429cceafc3cbfb45aaa38ebdba524`. Árbol inicial limpio. Fecha: '+datetime.now(ZoneInfo('America/La_Paz')).isoformat()+'.\n',
    '## Alcance y límites\n',
    'Se recorrieron todos los directorios, incluidos archivos ignorados y ocultos. `.git` se excluye por ser metadatos de Git; no seguir enlaces. `docs/limpieza/` se excluye para evitar auto-inventario. El anexo INVENTARIO_DEPENDENCIAS.md contiene una fila por extensión solicitada dentro de .venv/node_modules; no se eliminan. La tabla principal incluye además YAML y MJS, configuraciones, assets y otros tipos para no ocultar consumidores. Los tamaños son lógicos en bytes, no espacio asignado ni tamaño histórico Git. No se accedió a bases, snapshots por SQL, volúmenes o contenedores. El dump se lee sólo como archivo para hash si procede.\n',
    'Referencias: búsqueda estática en texto UTF-8, nombres de archivo, imports Python candidatos y resolución relativa JS; se informa documento:línea. Las coincidencias de nombre ambiguas y directorios se protegen conservadoramente. “No detectado” no prueba desuso. No se analizan contenidos de binarios DOCX/PDF/XLSX: cualquier cita adicional de tesis debe contrastarse antes de fase 2. Los patrones/rangos no resueltos están en RUTAS_CITADAS_TESIS.tsv. Las referencias en reportes intermedios también bloquean retirada automática. No se ejecutaron scripts de medición, semillas, reset o reparación.\n',
    '## Línea base\n\nVer linea_base/pytest_completo.txt, pytest_junit.xml, coverage.json, frontend_build.txt y docker_compose_config.txt. La suite usa ejecutar_pytest.py: bloquea sockets Python y psycopg2 y desactiva readiness live, sin cambiar archivos de pruebas. Los subprocesos reciben PGOPTIONS read-only; no se habilitan pruebas live. Resultados reales y diferencias con 650 se completan tras finalizar. Build Vite se dirige a docs/limpieza/linea_base/frontend-dist para no sobrescribir frontend/dist. Compose se valida con --quiet para no guardar secretos expandidos. No se ejecuta compose up en fase 1.\n',
    '## Lista blanca y decisiones\n\nRUTAS_CITADAS_TESIS.tsv enumera citas y resoluciones de todos los reportes de texto de docs/ y ambas fuentes de verdad. Cada fila de inventario conserva los lugares que la protegen. Conservar migraciones y seeds, fixtures, assets/imports del frontend, configuración y scripts usados por arranque. No retirar backend/scripts/ en bloque: run_migrations.py y migrations/ son infraestructura. Las copias exactas sólo se consolidan después de revisar su consumidor.\n\nSe conservan huella_dw.py, comparar_huellas.py, perfilar_flujo_dataops.py, medir_flujo_repetido.py, recalculo_mape_holtwinters.py y las salidas finales indicadas por el usuario (snapshot 10-nov, regresion_A, flujo_repetido_A2, flujo_A_cache_vacia, una_pasada, deshacer_no_bloqueante, holtwinters_recalculo*).\n',
    'Documentación vigente propuesta: README, fuente de verdad, arquitectura/metodología, diccionario y reportes finales de medición. Historia por tema: RESUMEN_RONDA10 (snapshot/tesis), auditoria_loops_sprint4 (DW/KPI), production_readiness_2026-11-01 (calidad/seguridad), perfil_dataops/perfil.json (perfil inicial), flujo_repetido/resumen.json (medición previa a optimización A). Archivar adicionales sólo si dejan de estar citados; las excepciones protegidas se someten a decisión. No se asume que un nombre v2 o loop implique obsolescencia.\n',
    '### Evidencia simulada o terminal dibujada\n\nEstos scripts contienen texto fijo de resultados/terminal; no se ejecutaron. Propuesta: retirar junto con imágenes, sustituyendo cualquier cita por evidencia real de la línea base. `mi decisión` indica colisión con la lista blanca. No implica que toda figura conceptual sea evidencia simulada.\n',
    table(['script / funciones con línea','salidas PNG detectadas','alcance'],((r+' — '+', '.join(fake_functions[r]),', '.join(sorted(p for p in fake_outputs if Path(p).name in fake_png_names[r])),'mixto: retirar funciones y llamadas, conservar resto' if r in fake_mixed else 'retirar productor de terminal dibujada') for r in sorted(fake))),
    '## Duplicados exactos\n\nCanónico propuesto por referencias, pertenencia a Git y ubicación; un hash idéntico no autoriza borrar una ruta. Archivos vacíos no cuentan como duplicados funcionales.\n',
    table(['SHA-256','canónico propuesto','otras rutas'],((h,c,'; '.join(o)) for h,c,o in duplicates)),
    '## Reorganización propuesta de tests\n\nSin movimientos en esta fase. Se mantienen temas en nombres. Sólo el archivo verification_loops se renombra por seguridad/resiliencia. Las suites existentes conservan sprint; tests/load pasa a sprint6; readiness conserva ruta. Los MJS son pruebas Node del frontend y no forman parte del total pytest esperado de 650. No mover módulos MJS de implementación. conftest.py permanece en la raíz; tests/dataops_parches.py y tests/__init__.py permanecen como soporte compartido. El único archivo propuesto para transversales mezcla ingesta, NER y seguridad del reset del DW; conservarlo entero evita dividir o perder IDs.\n',
    table(['archivo antiguo','archivo nuevo','tema','ajustes obligatorios'],test_map),
    'Condiciones antes de cada commit: actualizar imports como tests.test_dataops_integridad (también importado por dedup_por_contenido), recalcular ROOT/RAIZ con búsqueda de marcador pyproject.toml, mantener tests.dataops_parches y conftest raíz; ajustar ignore de test_auth_temp.db al nuevo sprint; rutas relativas de imports MJS y cualquier comando/CI/documento que invoque rutas anteriores. testpaths=["tests"] y pythonpath=[".","backend"] siguen cubriendo las suites. Revisar --cov omit antes/después sin cambiar su alcance. Comparar IDs colectados normalizados mediante este mapa: mismo conjunto y cardinalidad, sin duplicados; exigir 650 y 632 passed/11 skipped/7 xfailed sólo tras conciliar línea base real. Comparar coverage.json totals.percent_covered con tolerancia absoluta 0,1 punto, mismo entorno/flags/red/datos y versión de dependencias. Ejecutar Node --test además de pytest. Una promesa de equivalencia no sustituye la corrida posterior.\n',
    '## Tamaño y acciones estimadas\n']
counts=Counter(i['clasificacion'] for i in files.values())
before=sum(totals.values()); delete=sum(i['bytes'] for i in files.values() if i['accion']=='eliminar'); archive=sum(i['bytes'] for i in files.values() if i['accion']=='archivar'); tracked_delete=sum(i['bytes'] for i in files.values() if i['accion']=='eliminar' and i['tracked'])
report.append(table(['métrica','bytes'], [('Total local antes (sin .git ni entregables nuevos)',before),('Dependencias conservadas',sum(i['bytes'] for i in deps)),('Eliminar propuesto (requiere aprobación)',delete),('Archivar propuesto a _archivo/ (sin ahorro local)',archive),('Total local después estimado si se aprueban eliminaciones',before-delete),('Reducción del árbol versionado por eliminaciones',tracked_delete),('Tamaño histórico Git después','sin reducción: no reescribir historial')]))
report += ['_archivo/ conserva jerarquía original y debe quedar fuera del contexto Docker, build y descubrimiento pytest con cambios explícitos en .dockerignore/pytest; no basta cambiar el nombre de carpeta. Vite sigue construyendo desde frontend/. Archivar no libera espacio local; ahorra contexto de build si se excluye. Las decisiones pendientes no se cuentan como ahorro. No se borran .venv, node_modules ni snapshot. Añadir *.prof sólo con excepciones explícitas para perfiles finales/citados, _archivo/ al contexto Docker, y artefactos de línea base al ignore; no ignorar evidencias por patrón global.\n',
    table(['carpeta','bytes locales'],sorted(totals.items())),
    table(['clasificación','archivos'],sorted(counts.items())),
    '## Veinte archivos más pesados\n',
    table(['ruta','bytes','versionado'],((i['ruta'],i['bytes'],'sí' if i['tracked'] else 'no') for i in sorted(list(files.values())+deps,key=lambda i:i['bytes'],reverse=True)[:20])),
    '### Veinte archivos versionados más pesados\n',
    table(['ruta','bytes'],((i['ruta'],i['bytes']) for i in sorted((i for i in files.values() if i['tracked']),key=lambda i:i['bytes'],reverse=True)[:20])),
    '## Carpetas vacías\n', '\n'.join('- `'+r+'`' for r in sorted(empty))+'\n',
    '## Cambios que debe reflejar la tesis\n\n1. Tabla 3.29, GCB-42 y matriz de trazabilidad: aplicar el mapa antiguo → nuevo sólo cuando exista commit aprobado; conservar el mapa como referencia histórica.\n2. Actualizar comandos pytest/Node, pies de figuras y citas de pruebas que cambien. El estado inicial tiene fuente de verdad que aún cita 493/475 y otros scripts que dibujan 650/632: no reconciliar usando capturas fabricadas. Registrar resultados reales, fecha, commit, cobertura y condiciones.\n3. Sustituir capturas de terminal dibujadas por salidas verificables; revisar Figura 1.40, 3.39/3.40/3.50 y capturas Docker según productor indicado arriba.\n4. Para documentos archivados, actualizar enlaces y referencias sólo tras aprobar la ruta destino _archivo/<ruta-original>; nunca mover evidencia final por deduplicación. Las citas resueltas por archivo constan en INVENTARIO_DATOS.json y en la tabla por carpeta.\n5. No modificar cifras finales de negocio ni snapshot. Documentar por separado que las mediciones de pruebas posteriores corresponden al commit de limpieza.\n',
    '## Secuencia propuesta para fase 2 (pendiente aprobación)\n\nUn commit por tema: (1) ignore/artefactos regenerables, (2) retirar evidencia dibujada con autorización de citas, (3) pruebas por sprint con imports/rutas y mapa, (4) docs históricos y enlaces, (5) copias/scripts dudosos que el usuario decida. Usar git mv/git rm para rutas versionadas; ningún borrado de ignorados/dependencias salvo aprobación específica. Suite rápida por tema tras cada commit; si falla, git revert de ese commit y registrar fallo. Final: suite completa con cobertura, Node, build, compose config y healthchecks. Compose up sólo con estrategia aprobada que no ejecute migraciones/semillas ni afecte bases/volúmenes vivos: usar proyecto aislado y almacenamiento efímero; no arrancar automáticamente el compose de producción. Crear LIMPIEZA_REGISTRO.md en fase 2 con commits, tamaño, mapas y resultados. No hay commits de ejecución en fase 1.\n',
    '## Inventario por carpeta\n\nColumnas: tamaño en bytes; hora Bolivia. Las propuestas son conservadoras y no autorizan acciones. Lista completa de referencias por archivo sin truncar.\n']
folders=defaultdict(list)
for r,i in files.items():
    folders[r.split('/')[0] if '/' in r else '(raíz)'].append(i)
for folder,items in sorted(folders.items()):
    report.append('### '+folder+'\n')
    report.append(table(['ruta','tipo','tamaño','última modificación','referenciado por','clasificación','acción propuesta / motivo'],((i['ruta'],i['tipo'],i['bytes'],i['modificado'],ref_text(i),i['clasificacion'],i['accion']+' — '+i['motivo']+(' [LISTA BLANCA]' if i['protegido'] else '')+(' [no versionado]' if not i['tracked'] else '')) for i in sorted(items,key=lambda i:i['ruta']))))
document = '\n'.join(report)
document = document.replace('No se analizan contenidos de binarios DOCX/PDF/XLSX: cualquier cita adicional de tesis debe contrastarse antes de fase 2.', 'Se extraen párrafos XML del DOCX de docs/ (sus índices se informan como línea/párrafo); no se altera ni renderiza ese documento. No hay PDF en docs/ al escanear. No se interpretan celdas de XLSX como documentación: se conservan datos/fixtures y cualquier cita binaria adicional exige contraste antes de fase 2.')
document = document.replace('bloquea sockets Python y psycopg2', 'bloquea connect/connect_ex y las tres entradas de conexión de psycopg2; permite únicamente connect dentro del socketpair local de Windows')
document = document.replace('No hay commits de ejecución en fase 1.', 'No hay commits de ejecución en fase 1. Si archivar/eliminar código backend/pipeline cambia el denominador de cobertura y supera ±0,1 punto, conservar esas rutas y reportar la incompatibilidad: no modificar omit/targets para maquillar la métrica.')
document = document.replace('Los MJS son pruebas Node del frontend', 'Los dos *.test.mjs se verificaron con Node; los E2E ciclo_ui/mapeo_ui requieren pila viva y no se ejecutaron. backend/test_upload.py y backend/tests/test_lote_estado_flujo.py están fuera de testpaths; se conservan en su ruta hasta decisión expresa para evitar añadir pruebas/efectos al colector. Los MJS son pruebas Node del frontend')
document = document.replace('## Duplicados exactos', '## Decisiones previas a fase 2\n\n- Conciliar 652 IDs únicos observados con el requisito de 650: no hay autorización para eliminar pruebas que expliquen la diferencia.\n- Acordar una base de validación aislada con datos para las pruebas de forecasting dependientes del DW, o aceptar explícitamente una línea base offline distinta. No usar base viva ni snapshot activo. Los cinco fallos observados esperan serie/datos/método/horizonte y reciben origen=sin_datos por el bloqueo de PostgreSQL; no se corrigieron ni omitieron esas pruebas.\n- Revisar las filas “mi decisión”, en particular evidencia dibujada citada y documentación histórica protegida. Aprobar rutas exactas antes de retirar o archivar.\n- No aprobar eliminaciones/archivados de backend/pipeline que alteren cobertura más de ±0,1 punto sin resolver esa incompatibilidad. Mantener mismo alcance de cobertura.\n\n## Duplicados exactos',1)

baseline = OUT/'linea_base'
if (baseline/'pytest_junit.xml').exists() and (baseline/'coverage.json').exists():
    tree = ET.parse(baseline/'pytest_junit.xml')
    cases = tree.findall('.//testcase')
    failures = [c.get('classname','')+'::'+c.get('name','') for c in cases if c.find('failure') is not None or c.find('error') is not None]
    skipped = [c for c in cases if c.find('skipped') is not None]
    xf = sum(c.find('skipped').get('type')=='pytest.xfail' for c in skipped)
    cov = json.loads((baseline/'coverage.json').read_text(encoding='utf-8'))['totals']
    ids = (baseline/'pytest_nodeids.txt').read_text(encoding='utf-8').splitlines()
    summary = {'collected':len(ids),'unique_ids':len(set(ids)),'passed':len(cases)-len(failures)-len(skipped),'failed_or_errors':len(failures),'skipped':len(skipped)-xf,'xfailed':xf,'coverage_percent':cov['percent_covered'],'covered_lines':cov['covered_lines'],'num_statements':cov['num_statements'],'failures':failures,'frontend_build_exit':0,'compose_config_exit':0,'node_passed':5,'fase2_autorizada':False}
    (baseline/'RESUMEN.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    summary_md = '\n### Resultado observado (aislamiento verificado)\n\n'+table(['control','resultado'],[
        ('pytest',f"{summary['passed']} passed, {len(failures)} failed/error, {summary['skipped']} skipped, {xf} xfailed; {len(ids)} colectadas"),
        ('IDs únicos',len(set(ids))),('Cobertura backend + pipeline',f"{cov['percent_covered']:.6f} % ({cov['covered_lines']}/{cov['num_statements']})"),
        ('Frontend build','exit 0'),('Docker compose config --quiet','exit 0'),('Node frontend','5 passed, 0 failed'),
        ('Aislamiento','aislamiento_verificado.txt: exit 0; no conexión PostgreSQL'),
        ('Fallos observados','; '.join(failures) or 'ninguno'),
    ])+'\n**Precondición 650 NO satisfecha:** la recolección real contiene 652 IDs únicos. No retirar dos pruebas ni alterar marcas para alcanzar la cifra solicitada. Conciliar el manifiesto esperado con pytest_nodeids.txt antes de autorizar/ejecutar fase 2. La comparación de cobertura posterior debe usar esta línea base y el mismo aislamiento; una prueba que requiere DW real no se interpreta como regresión de limpieza.\n\nEl intento_1 documenta fallos del primer interceptor de sockets; intentos 2/3 se detuvieron al bloquear el sandbox el socketpair de Windows. No son la línea base válida. La revisión automática rechazó una ejecución sin aislamiento de red suficiente; se reforzaron y verificaron connect/connect_ex y las tres entradas psycopg2 antes de repetir. No se cambió código del producto ni tests para resolver el entorno.\n'
    document = document.replace('## Lista blanca y decisiones',summary_md+'\n## Lista blanca y decisiones',1)
    document = document.replace('Resultados reales y diferencias con 650 se completan tras finalizar.', 'Resultados reales y diferencias con 650 se detallan a continuación y en linea_base/RESUMEN.json.')
(OUT/'LIMPIEZA_INVENTARIO.md').write_text(document,encoding='utf-8')
print(json.dumps({'archivos_propios':len(files),'dependencias':len(deps),'bytes_antes':before,'bytes_eliminar':delete,'duplicados':len(duplicates),'tests_mapeados':len(test_map),'clasificaciones':dict(counts)},ensure_ascii=False))
