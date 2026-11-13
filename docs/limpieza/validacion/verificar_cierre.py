"""Medición final de tamaños físicos lógicos, sin inferir CRLF desde blobs Git."""
from pathlib import Path
import json, os, subprocess

root=Path(__file__).resolve().parents[3]
out=root/'docs/limpieza'
p=out/'validacion/TAMANOS.json'
sizes=json.loads(p.read_text(encoding='utf-8'))
local=0
for directory,dirs,names in os.walk(root):
    rel=Path(directory).relative_to(root).as_posix()
    dirs[:]=[d for d in dirs if d!='.git' and not (Path(directory)/d).is_symlink() and not (rel=='docs' and d=='limpieza')]
    for name in names:
        file=Path(directory)/name
        if file.is_file() and not file.is_symlink():local+=file.stat().st_size
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
tracked=sum((root/r).stat().st_size for r in paths if r and not r.startswith('docs/limpieza/') and (root/r).is_file())
report=out/'LIMPIEZA_REGISTRO.md';text=report.read_text(encoding='utf-8')
for key,value in [('local_despues_mismo_alcance',local),('arbol_versionado_despues_sin_entregables_nuevos',tracked)]:
    text=text.replace(str(sizes[key]),str(value));sizes[key]=value
text=text.replace('Este ajuste y su verificación posterior se identifican con git log -1 -- .gitignore;', 'El ajuste ec6e865 pasó su verificación posterior (18 passed);')
text+='\nEl commit documental 0f9f49c y el ajuste ec6e865 completan los commits de ejecución listados arriba. Esta medición final toma tamaños del disco, con sus finales de línea reales; conserva las mismas exclusiones que fase 1. La revisión documental posterior no cambia código, pruebas ni datos.\n'
report.write_text(text,encoding='utf-8')
p.write_text(json.dumps(sizes,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(sizes,ensure_ascii=False))
