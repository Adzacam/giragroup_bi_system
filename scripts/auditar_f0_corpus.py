"""F0 B-4: audit frozen JSONL bytes without importing generators or exposing text."""
import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
NAMES = {'train': 'train_robusto', 'dev': 'dev_robusto', 'gold': 'test_gold_real'}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def normalize(value):
    value = ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))
    return ' '.join(re.findall(r'\w+', value))

def entity_value(record, span):
    return record['texto'][span['start']:span['end']]

def family(record):
    values = []
    for span in record['spans']:
        value = normalize(entity_value(record, span))
        if span['tipo'] == 'PER_DOCENTE':
            value = re.sub(r'^(lic|ing|msc|dr|dra|prof|mg)\s+', '', value)
        values.append((span['tipo'], value))
    return tuple(sorted(values))

def overlap(left, right, key):
    a, b = defaultdict(list), defaultdict(list)
    for i, r in enumerate(left, 1): a[key(r)].append(i)
    for i, r in enumerate(right, 1): b[key(r)].append(i)
    common = sorted(a.keys() & b.keys(), key=repr)
    return {'unique_shared': len(common), 'left_records': sum(len(a[k]) for k in common),
            'right_records': sum(len(b[k]) for k in common), 'record_pairs': sum(len(a[k])*len(b[k]) for k in common),
            'groups': [{'key_sha256': hashlib.sha256(repr(k).encode()).hexdigest(), 'left_line_ids': a[k], 'right_line_ids': b[k]} for k in common]}

def audit(output):
    datasets = {n: [json.loads(line) for line in (ROOT/'data'/f'{stem}.jsonl').read_text(encoding='utf8').splitlines() if line.strip()] for n,stem in NAMES.items()}
    results = {'timestamp': datetime.now(ZoneInfo('America/La_Paz')).isoformat(), 'status': 'audited_with_provenance_limits',
               'normalization': 'NFKD, casefold, remove combining marks, Unicode word tokens joined by one space; normalized tokens preserve original token boundaries.',
               'family_definition': 'Sorted (entity type, normalized span text), removing a leading teacher title. Inferred signature, not proof of original source-row family.',
               'datasets': {}, 'crosses': {}}
    for n, records in datasets.items():
        p=ROOT/'data'/f'{NAMES[n]}.jsonl'
        results['datasets'][n]={'path': str(p.relative_to(ROOT)), 'bytes':p.stat().st_size, 'sha256':sha(p), 'records':len(records),
           'entity_support':dict(Counter(s['tipo'] for r in records for s in r['spans'])), 'tabular_records':sum(' | ' in r['texto'] for r in records),
           'records_with_source_id':sum(any(k in r for k in ('source_id','source_row','parent_id','family_id')) for r in records),
           'inconsistent_token_tag_lengths':sum(len(r['tokens'])!=len(r['tags']) for r in records),
           'invalid_spans':sum(not(0<=s['start']<s['end']<=len(r['texto'])) for r in records for s in r['spans'])}
    keys = {'exact_text':lambda r:r['texto'], 'normalized_text':lambda r:normalize(r['texto']), 'exact_tokens':lambda r:tuple(r['tokens']),
            'normalized_tokens':lambda r:tuple(normalize(t) for t in r['tokens']), 'inferred_entity_family': family}
    for a,b in [('train','dev'),('train','gold'),('dev','gold')]:
        cross = {k:overlap(datasets[a],datasets[b],f) for k,f in keys.items()}
        cross['entity_values']={}
        for typ in ('PER_ESTUDIANTE','PER_DOCENTE','MODULO','PROGRAMA'):
            def ents(records):
                return [{'texto':entity_value(r,s)} for r in records for s in r['spans'] if s['tipo']==typ]
            cross['entity_values'][typ]=overlap(ents(datasets[a]),ents(datasets[b]),lambda r:normalize(r['texto']))
        results['crosses'][a+'_'+b]=cross
    results['generation']={'script':'scripts/preparar_corpus_robusto.py','sha256':sha(ROOT/'scripts/preparar_corpus_robusto.py'),
       'seed':42,'order':'Gold from head(100) experience, head(50) ARCA TEST, head(30) inscritos TEST; collect names; exclude names from train pools; generate 1750 augmented records; shuffle augmented records; split first 1400 train, last 350 dev.',
       'augmentation':['header synonyms','column permutation','teacher titles','accent removal','header casing','support/noise columns','tabular and prose templates'],
       'declared_but_unused':['apply_typo function is defined but never called','two prose branches (i % 4 = 1 or 3) cannot occur when i % 6 = 0'],
       'determinism_limit':'list(set(...)) precedes random.shuffle; random.seed(42) does not fix Python hash iteration order. Source IDs, parent IDs and original source hashes are not persisted.',
       'family_split_status':'not verifiable from provenance; augmentation occurs BEFORE train/dev split, with shared entity pools. Exact/normalized counts above do not establish family independence.'}
    results['training']={'script':'scripts/entrenar_beto_robusto.py','sha256':sha(ROOT/'scripts/entrenar_beto_robusto.py'),
       'seed':42,'max_tokens':128,'selection':'3 epochs; checkpoint selected by best dev F1; gold loaded but evaluated after training; comment says early stopping but no stopping branch is implemented.'}
    review=ROOT/'output/test_gold_revision.csv'
    with review.open(encoding='utf-8-sig') as f:
        reader=csv.DictReader(f); review_columns=reader.fieldnames; review_rows=sum(1 for _ in reader)
    results['annotation']={'origin':'programmatic span construction and token-overlap IOB2 in preparar_corpus_robusto.py; no annotator or adjudication IDs in JSONL.',
       'review_file':{'path':str(review.relative_to(ROOT)),'sha256':sha(review),'columns':review_columns,'rows':review_rows,'status':'automatic labels only; does not demonstrate independent human review'},
       'independent_human_review':'not verifiable; no signed decisions, reviewer ID, before/after annotation or review log linked to gold IDs found in inspected sources.',
       'source_reproduction':'not attempted: would regenerate datasets and require live catalog; existing dataset bytes were read only.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['# F0 B-4 — auditoría de corpus','', 'Auditoría de los bytes existentes; no se regeneró ni entrenó. Las intersecciones por texto/tokens son verificables; la independencia de familias y la revisión humana del gold no son verificables con la procedencia conservada.','', '| Cruce | Texto exacto (pares) | Texto normalizado (pares) | Tokens exactos (pares) | Tokens normalizados (pares) | Firma familiar inferida (pares) |','|---|---:|---:|---:|---:|---:|']
    for k,v in results['crosses'].items(): lines.append('| '+k+' | '+' | '.join(str(v[t]['record_pairs']) for t in keys)+' |')
    lines+=['', 'Las firmas familiares comparan el conjunto de entidades de cada registro, sin títulos docentes. No sustituyen IDs de padre/origen. Los cruces por valor individual de entidad en el JSON permiten detectar personas o entidades institucionales compartidas, sin publicar sus nombres.', '', 'El generador aumenta antes de dividir 80/20, con semilla 42 y un único pool de entidades para train/dev. `list(set(...))` impide garantizar reproducción solo con esa semilla. No se guardan IDs de origen ni familias. Los nombres de gold se excluyen mediante coincidencia lowercase, sin normalización robusta; los cruces observados se informan sin inferir ausencia de fuga.', '', 'Aumentos reales: sinónimos, permutación, títulos, tildes, casing de encabezado, ruido y plantillas. `apply_typo` no se invoca. De cuatro plantillas declaradas solo dos son alcanzables. El checkpoint se selecciona por dev F1 entre tres épocas; no hay early stopping implementado.', '', '`output/test_gold_revision.csv` contiene únicamente línea, token y etiqueta automática. No demuestra anotación o revisión humana independiente. La afirmación histórica de revisión de layouts adversarios no acredita revisión del gold real.', '', 'Hashes, tamaños, soporte y grupos de IDs: [f0_b4_auditoria.json](f0_b4_auditoria.json). No se publica texto ni CI.']
    person_overlap=results['crosses']['train_dev']['entity_values']
    lines+=['',f"En train–dev se comparten valores normalizados de **{person_overlap['PER_ESTUDIANTE']['unique_shared']} estudiante(s)** y **{person_overlap['PER_DOCENTE']['unique_shared']} docente(s)**. Esto evidencia reutilización de personas/pools entre particiones aunque no haya filas textualmente duplicadas. Los cruces por persona ausentes en gold no demuestran independencia de procedencia."]
    output.with_suffix('.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps({'datasets':{k:v['records'] for k,v in results['datasets'].items()},'crosses':{k:{t:v[t]['record_pairs'] for t in keys} for k,v in results['crosses'].items()}}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,default=ROOT/'docs/mediciones/f0_b4_auditoria.json'); audit(parser.parse_args().output)
