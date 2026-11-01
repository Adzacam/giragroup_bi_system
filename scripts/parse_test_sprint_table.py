import re

log_path = r'C:\Users\DAZA\.gemini\antigravity\brain\c67fc3d9-7d86-45c3-be1e-f3bc737860c0\.system_generated\tasks\task-2170.log'
with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

lines = text.splitlines()

file_stats = {}
for line in lines:
    m = re.match(r'^(tests[\\/][^:]+)::(\S+)\s+(PASSED|SKIPPED|FAILED)', line)
    if m:
        fpath, tname, status = m.groups()
        fpath = fpath.replace('\\', '/')
        if fpath not in file_stats:
            file_stats[fpath] = {'total': 0, 'passed': 0, 'skipped': 0, 'failed': 0}
        file_stats[fpath]['total'] += 1
        if status == 'PASSED':
            file_stats[fpath]['passed'] += 1
        elif status == 'SKIPPED':
            file_stats[fpath]['skipped'] += 1
        elif status == 'FAILED':
            file_stats[fpath]['failed'] += 1

def get_sprint(fpath):
    if 'sprint1' in fpath: return 'Sprint 1'
    if 'sprint2' in fpath: return 'Sprint 2'
    if 'sprint3' in fpath: return 'Sprint 3'
    if 'sprint4' in fpath: return 'Sprint 4'
    if 'sprint5' in fpath: return 'Sprint 5'
    if 'sprint6' in fpath: return 'Sprint 6'
    return 'Transversales'

sprints = {}
for fp, st in sorted(file_stats.items()):
    sp = get_sprint(fp)
    if sp not in sprints:
        sprints[sp] = []
    sprints[sp].append((fp, st))

for sp, items in sorted(sprints.items()):
    print(f'### {sp}')
    print('| Archivo de Test | Nº de Pruebas | Pasadas | Omitidas | Fallidas |')
    print('| :--- | :---: | :---: | :---: | :---: |')
    sp_tot = sp_pass = sp_skip = sp_fail = 0
    for fp, st in items:
        sp_tot += st['total']
        sp_pass += st['passed']
        sp_skip += st['skipped']
        sp_fail += st['failed']
        print(f"| `{fp}` | {st['total']} | {st['passed']} | {st['skipped']} | {st['failed']} |")
    print(f"| **Subtotal {sp}** | **{sp_tot}** | **{sp_pass}** | **{sp_skip}** | **{sp_fail}** |\n")

# 2. Parse coverage table
print('=== TABLA DE COBERTURA POR MÓDULO ===')
print('| Módulo | Sentencias | Sin Cubrir | % Cobertura |')
print('| :--- | :---: | :---: | :---: |')

cov_lines = []
in_cov = False
for line in lines:
    if 'Name' in line and 'Stmts' in line and 'Miss' in line:
        in_cov = True
        continue
    if in_cov:
        if line.startswith('--------------------'):
            continue
        if line.startswith('TOTAL'):
            parts = line.split()
            print(f"| **{parts[0]}** | **{parts[1]}** | **{parts[2]}** | **{parts[3]}** |")
            break
        parts = line.split()
        if len(parts) >= 4:
            mod_name = parts[0].replace('\\', '/')
            stmts = parts[1]
            miss = parts[2]
            cover = parts[3]
            print(f"| `{mod_name}` | {stmts} | {miss} | {cover} |")
