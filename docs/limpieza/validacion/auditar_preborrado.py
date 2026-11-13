"""Evidencia previa de citas, hashes y funciones dibujadas; no modifica archivos originales."""
from collections import defaultdict
from pathlib import Path
import ast, hashlib, json, re, subprocess, zipfile
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[3]
out = root/'docs/limpieza'
paths = subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
manifest = {r:{'bytes':(root/r).stat().st_size,'sha256':hashlib.sha256((root/r).read_bytes()).hexdigest()} for r in paths if r and (root/r).is_file()}
(out/'PRE_FASE2_MANIFIESTO.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
sources = {}
for r in manifest:
    if r.startswith('docs/limpieza/'):
        continue
    p=root/r
    if p.suffix in ('.md','.mmd'):
        sources[r]=p.read_text(encoding='utf-8-sig')
    elif p.suffix=='.docx':
        with zipfile.ZipFile(p) as z:
            xml=ET.fromstring(z.read('word/document.xml'))
            sources[r]='\n'.join(''.join(el.itertext()) for el in xml.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'))

candidates = [r for r in manifest if Path(r).suffix=='.png' and str(Path(r).parent).replace('\\','/') in ('docs/images','docs/figuras','docs/figuras_tesis','docs/evidencias/graficos')]
rows=[]
for r in sorted(candidates):
    direct,basename,numbers=[],[],[]
    fig=re.search(r'figura_(\d+)_(\d+)',r)
    for src,t in sources.items():
        for no,line in enumerate(t.splitlines(),1):
            where=f'{src}:{no}'
            if r in line: direct.append(where)
            elif Path(r).name in line: basename.append(where)
            elif fig and re.search(r'Figura\s*\**\s*'+fig[1]+r'\.'+fig[2]+r'\b',line,re.I): numbers.append(where)
    rows.append((r,direct,basename,numbers))

v2=defaultdict(list)
for r,v in manifest.items():
    if r.startswith('docs/evidencias/graficos_v2/') and r.endswith('.png'):
        v2[v['sha256']].append(r)
pairgroups=[(h,rs) for h,rs in v2.items() if len(rs)>1]
old=set((out/'validacion/colecta_f3b37d9/nodeids.txt').read_text(encoding='utf-8').splitlines())
new=set((out/'linea_base/pytest_nodeids.txt').read_text(encoding='utf-8').splitlines())
lines=['# Comprobaciones antes del borrado\n',
       'Commit inicial: `5850dd4`. Comparación por recolección real con `f3b37d9`: '+str(len(old))+' → '+str(len(new))+'; sin IDs retirados.\n',
       '## Dos IDs añadidos\n']+['- `'+r+'`' for r in sorted(new-old)]
lines+=['\nSe incorporaron en `ac9ea1f`; el MJS de cola también se añadió, pero Node no forma parte de la colección pytest.\n',
        '## Citas de imágenes\n\nLa columna ruta señala la presencia literal de la ruta completa; basename señala un nombre de archivo; la última columna registra sólo el número de figura, sin referencia de archivo en esa línea. Índices de DOCX = párrafo XML. Las citas históricas se preservan y la tesis debe actualizar sus rutas/pies; no se considera que una cita numérica garantice una captura existente.\n',
        '| Imagen | Ruta de archivo citada | Nombre de archivo citado | Sólo número de figura |\n| --- | --- | --- | --- |']
for r,d,b,n in rows:
    lines.append('| '+r+' | '+('; '.join(d) or 'no')+' | '+('; '.join(b) or 'no')+' | '+('; '.join(n) or 'no')+' |')
lines+=['\n## Alias SHA-256 en graficos_v2\n\nSe encontraron '+str(sum(len(rs)-1 for h,rs in pairgroups))+' alias exactos, no cinco. No se inventa un quinto borrado.\n']
for h,rs in pairgroups: lines.append('- `'+h+'`: '+'; '.join('`'+r+'`' for r in rs))
lines+=['\n## E2E\n\n`e2e/lib.mjs` no contiene lectura ni ruta a graficos/: lee OTP desde docker logs y escribe capturas en E2E_SALIDA (por defecto docs/evidencias/e2e). Estos PNG/JPG se conservan. No se ejecutaron acciones E2E sobre datos vivos.\n',
        '## Productores adicionales, sólo revisión\n\nSe conservan sin retirar estas funciones/scripts, por instrucción expresa.\n']
for r in ('scripts/generar_figuras_tesis_sprint2_3.py','scripts/generar_figuras_tesis_sprint4.py','scripts/generar_figura_3_17_logs.py','scripts/generar_figura_3_25_json.py','scripts/generar_figuras_tesis_sprint5_6.py'):
    text=(root/r).read_text(encoding='utf-8-sig');tree=ast.parse(text)
    for node in tree.body:
        if not isinstance(node,ast.FunctionDef):continue
        body=ast.get_source_segment(text,node) or ''
        if not any(s in body for s in ('3_15','3_17','3_22','3_25','3_35','3_36')):continue
        markers=[s for s in ('log_text','json.dumps','json_response','curl_output','HTTP/1.1','log_lines','log_data','response_json','run_results') if s in body]
        lines.append('- `'+r+':'+str(node.lineno)+'` '+node.name+': '+('texto/carga fija a revisar ('+', '.join(markers)+')' if markers else 'revisar cuerpo: diagrama/mockup o valores fijados en ax.text; no se consulta un servicio en ejecución')+'.')
assert 'graficos/' not in (root/'e2e/lib.mjs').read_text(encoding='utf-8')
(out/'PREBORRADO_REFERENCIAS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'png_retirables':len(candidates),'alias_v2_exactos':sum(len(rs)-1 for h,rs in pairgroups),'ids_extra':sorted(new-old),'tracked_antes':len(manifest)},ensure_ascii=False))
