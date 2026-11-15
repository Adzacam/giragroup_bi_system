"""Bounded, read-only Git provenance audit for F0 B3; exports IDs/counts/hashes only."""
import ast
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/mediciones'

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def digest(value):return hashlib.sha256(value).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')
def parse_gold(value):return [json.loads(s) for s in value.decode('utf8').splitlines() if s.strip()]
def audit():
 gold_path='data/test_gold_real.jsonl';current_raw=(ROOT/gold_path).read_bytes();current=parse_gold(current_raw)
 history=[]
 for commit in git('log','-12','--format=%H','--',gold_path).decode().splitlines():
  raw=git('show',commit+':'+gold_path);records=parse_gold(raw)
  changed=[i for i,(a,b) in enumerate(zip(current,records),1) if a!=b]
  if len(current)!=len(records):changed.extend(range(min(len(current),len(records))+1,max(len(current),len(records))+1))
  history.append({'commit':commit,'path':gold_path,'blob_id':git('rev-parse',commit+':'+gold_path).decode().strip(),
    'git_bytes_sha256':digest(raw),'canonical_records_sha256':digest(canonical(records)),'record_count':len(records),
    'span_count':sum(len(r['spans']) for r in records),'begin_tag_count':sum(t.startswith('B-') for r in records for t in r['tags']),
    'changed_line_ids_vs_worktree':changed,'same_parsed_content_as_worktree':records==current,'raw_equal_after_CRLF_to_LF':raw.replace(b'\r\n',b'\n')==current_raw.replace(b'\r\n',b'\n')})
 source_path='scripts/generar_graficos_3_1_3_3.py';source=(ROOT/source_path).read_text(encoding='utf-8-sig');tree=ast.parse(source)
 assignment=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cm_abs' for t in n.targets))
 matrix=ast.literal_eval(assignment.value.args[0]);types=['MODULO','PER_DOCENTE','PER_ESTUDIANTE','PROGRAMA']
 support=Counter(t[2:] for r in current for t in r['tags'] if t.startswith('B-'))
 rows=[{'type':typ,'full_gold_support':support[typ],'historical_matrix_row_sum':sum(row),'missing_from_row':support[typ]-sum(row)} for typ,row in zip(types,matrix)]
 predicted=json.loads((OUT/'f0_b3_predicciones.json').read_text(encoding='utf8'));mode=next(r for r in predicted if r['mode']=='C');unmatched=[]
 for record in mode['lines']:
  matched={i for i,j in record['matches']['strict']}
  for i,g in enumerate(record['gold']):
   if i not in matched and g[0]=='PROGRAMA':
    overlap=[p for p in record['prediction'] if max(g[1],p[1])<min(g[2],p[2])]
    unmatched.append({'line_id':record['line_id'],'gold_span':g,'overlapping_predictions':overlap,'all_tokens_O':not overlap})
 result={'status':'historical_matrix_sum_explained_historical_ID_trace_partial',
  'scope':'At most12 gold-changing commits; current historical graph generator AST and last touching commit; no inference, no figures or product changes.',
  'current_gold':{'path':gold_path,'worktree_bytes_sha256':digest(current_raw),'canonical_records_sha256':digest(canonical(current)),
                  'records':len(current),'support':dict(support),'line_ids':'1-based nonempty JSONL lines'},
  'gold_history':history,'raw_hash_difference':'Git blob stores LF; working tree uses local line endings. Parsed-content equality is checked explicitly, not inferred from raw hash.',
  'historical_matrix':{'path':source_path,'worktree_sha256':digest((ROOT/source_path).read_bytes()),
   'last_touching_commit':git('log','-1','--format=%H','--',source_path).decode().strip(),
   'git_blob_id_at_HEAD':git('rev-parse','HEAD:'+source_path).decode().strip(),'assignment_line':assignment.lineno,'assignment_end_line':assignment.end_lineno,
   'class_order':types,'matrix':matrix,'row_comparison':rows,'sum':sum(sum(r) for r in matrix),'full_gold_sum':sum(support.values()),
   'definition':'Hardcoded4x4 matrix over four NER classes, omitting O/unmatched outside this matrix; program row contributes173 rather than declared support180. The seven-row-count difference explains503=510-7 arithmetically.',
   'limitations':'Matrix generator stores no row IDs, saved prediction artifact hash or matching policy. Its comments attribute seven program FN to O; current predictions do not validate that attribution.'},
  'current_F0_C_unmatched_programs':unmatched,
  'current_vs_historical_ID_warning':'Current7FN IDs are linked only to the hashed current F0 predictions. They are NOT proven to be the same seven historical cases. All current unmatched program entities overlap partial/fragmented program predictions, so treating all as all-O is false for the current run.',
  'historical_ID_trace_status':'not recoverable from hardcoded matrix; pending independent original prediction artifact',
  'prediction_artifact_sha256':digest((OUT/'f0_b3_predicciones.json').read_bytes())}
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'f0_b3_conciliacion_git.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 counts_path=OUT/'f0_b3_conteos.json';counts=json.loads(counts_path.read_text(encoding='utf8'))
 counts['status']='503_explained_by_incomplete_historical_matrix_ID_trace_partial';counts['historical_matrix_evidence']='f0_b3_conciliacion_git.json'
 counts['definition']='Current gold has510 entities, all visible within128. Historical graph hardcodes a4x4 matrix summing503 because its PROGRAMA row has173 instead of full support180. This explains503 by presentation/matrix definition, not a different gold version or current tokenizer truncation. Historical excluded case IDs were not saved.'
 counts['historical_matrix_sum']=result['historical_matrix']['sum'];counts['historical_matrix_missing_by_type']={r['type']:r['missing_from_row'] for r in rows}
 counts_path.write_text(json.dumps(counts,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 md=f'''# F0 B-3 — conciliación 503/510

La suma 503 procede de una matriz histórica incompleta; el gold contiene 510 entidades.

`{source_path}` (asignación `cm_abs`, líneas {assignment.lineno}–{assignment.end_lineno}) fija una matriz 4×4 cuyas filas suman 150 módulos, 50 docentes, 130 estudiantes y 173 programas: **503**. El soporte completo de programas es 180; faltan **7** en esa fila. La matriz no representa toda la población gold. Su normalización por suma de fila, además, oculta esa cobertura incompleta.

La inspección Git acotada encontró una única versión registrada del gold: 180 líneas y 510 spans. Su contenido JSON coincide con el actual; la diferencia de hash bruto corresponde a finales de línea, comprobada mediante igualdad de registros. Por tanto, no hay evidencia de un gold histórico de 503 entidades.

La conciliación por definición y suma queda resuelta. La trazabilidad histórica por ID permanece parcial: la matriz está escrita a mano y no guarda IDs ni huella de predicciones originales. Los siete FN de programa de la corrida F0 C son los IDs 26, 40, 111, 128, 132, 146 y 177, pero **no se afirma que sean los siete casos históricos**. En F0 todos tienen predicciones de programa parciales o fragmentadas que se solapan; clasificarlos como siete salidas completamente O sería incorrecto.

Hashes, commit, líneas, matriz, soporte y spans por ID: [f0_b3_conciliacion_git.json](f0_b3_conciliacion_git.json). Conteos: [f0_b3_conteos.json](f0_b3_conteos.json).

Las seis filas A/B/C × estricto/relajado conservan matching 1:1. El estricto usa IOB2 explícito; el reporte heredado usa seqeval por defecto y se conserva separado. [Resultados](f0_b3_ablacion.json), [CSV](f0_b3_ablacion.csv), [predicciones sin texto](f0_b3_predicciones.json), [procedencia](f0_b3_procedencia.json).

La inferencia inicial invalidada está conservada en [f0_b3_invalidada/README.md](f0_b3_invalidada/README.md). La reinferencia válida fijó hashes antes de inferir y ligó posteriormente las predicciones; sus hashes y seis conteos se verificaron nuevamente. No se ejecutó inferencia en esta auditoría ni se modificó el gráfico final; las figuras corresponden a F4.
'''
 (OUT/'f0_b3_conciliacion.md').write_text(md,encoding='utf8')
 print(json.dumps({'gold_versions':len(history),'all_versions_equal':all(v['same_parsed_content_as_worktree'] for v in history),'gold_support':sum(support.values()),'matrix_sum':result['historical_matrix']['sum'],'missing_by_type':counts['historical_matrix_missing_by_type']}))
if __name__=='__main__':audit()
