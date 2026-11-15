"""A4 sealed blind packages and explicit human-decision intake. Offline; no auto labels."""
import argparse
import csv
import hashlib
import io
import json
import random
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DECISION_FIELDS=('case_id','decision_kind','candidate_id','reviewer_id','decision_timestamp','blind_package_sha256','blinded_before_decision','exclusion_reason')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def encode(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8')
def opaque(value):return hashlib.sha256(encode(value)).hexdigest()
def parse(value):return json.loads(value) if isinstance(value,str) else value or {}
def rows(path):return [json.loads(s) for s in path.read_text(encoding='utf8').splitlines() if s.strip()] if path else []
def store(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(encode(value))
def csv_bytes(records,fields):
 buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=fields);writer.writeheader();writer.writerows(records);return buf.getvalue().encode('utf8')
def sealed_group(files):
 # Preflight every member before any write; an existing immutable member may never change.
 for path,data in files.items():
  if path.exists() and path.read_bytes()!=data:raise ValueError('Refusing to overwrite sealed package member: '+path.name)
 for path,data in files.items():
  if not path.exists():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)

def validate_sources(runs):
 expected={(c,s,n) for c in ('a3','a123') for s in ('vacia','llena') for n in (1,2,3)}
 actual=[(r['config'],r['cache'],r['repeat']) for r in runs]
 if len(runs)!=12 or set(actual)!=expected:raise ValueError('Sealing A4 requires all12 distinct valid a3/a123 runs')
 identities=set()
 for run in runs:
  match=re.fullmatch(r'f0_(a3|a123)_(vacia|llena)_r([123])(?:_[A-Za-z0-9]+)*',run['id'])
  if not match or (match[1],match[2],int(match[3]))!=(run['config'],run['cache'],run['repeat']):raise ValueError('Warmup or mislabeled source cannot enter sealed A4 population')
  meta=run.get('meta',{})
  if meta.get('valida') is not True:raise ValueError('A4 source is not a valid measured run')
  identity=tuple(meta.get(k) for k in ('lote_sha256','arbol_sha256','modelo_sha256'))
  if not all(isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) for v in identity):raise ValueError('Missing frozen source identity')
  identities.add(identity)
  if not run.get('evidence_sha256'):raise ValueError('Missing immutable source evidence hashes')
 if len(identities)!=1:raise ValueError('Different frozen source identities')
 return list(next(iter(identities)))

def stable_case(row,payload,doc,raw_by_id):
 # Ephemeral database IDs only join exported rows; none enter the stable identity.
 raw=raw_by_id.get(row.get('registro_origen_id'),{})
 context=payload.get('raw_line') or row.get('texto_original') or ''
 line=payload.get('line_number')
 if line is None:
  match=re.fullmatch(r'REG_\d+_(\d+)',str(payload.get('id') or ''))
  if match:line=int(match[1])
 if line is None:
  matching=[r for r in parse(raw.get('payload_json')).get('tuplas',[]) if r.get('raw_line')==context]
  if len(matching)==1:line=matching[0].get('line_number')
 position=(raw.get('fila_inicio')+int(line)-1) if raw.get('fila_inicio') is not None and line is not None else None
 file_id=doc.get('hash_sha256')
 if not file_id:raise ValueError('Stable file hash missing from A4 context')
 # Some loader cases preserve only a name and suggestions. Preserve all available
 # private disambiguation, but label this limitation rather than claiming a row link.
 private_fields={k:v for k,v in payload.items() if k not in ('id','sugerencias','motivo','motivo_llano','estado_resolucion','indice_registro')}
 private_fields['ci_temporal']=row.get('ci_temporal')
 identity={'file_sha256':file_id,'sheet':raw.get('hoja'),'source_row':position,'role':row.get('tipo_entidad'),
           'complete_private_context':context,'private_context_fields':private_fields}
 return opaque(identity),identity

def prepare(runs,public,private,final=False):
 runs=sorted((r for r in runs if r['config'] in ('a3','a123')),key=lambda r:r['id'])
 identity=validate_sources(runs) if final else None
 cases={};all_contexts=set();source_rows=Counter();eligible_by_config={c:set() for c in ('a3','a123')}
 for run in runs:
  docs={r['id_documento']:r for r in rows(run['paths'].get('dim_origen_documental.jsonl'))}
  raw_by_id={r['id']:r for r in rows(run['paths'].get('staging_registros_crudos.jsonl'))}
  export=run['paths'].get('stg_entidad_no_resuelta.jsonl');export_sha=sha(export) if export else None;seen=set()
  for row in rows(export):
   payload=parse(row.get('payload_json'));doc=docs.get(row.get('id_documento'),{})
   case_id,stable=stable_case(row,payload,doc,raw_by_id)
   if case_id in seen:raise ValueError('Ambiguous duplicated source context within run; export stable sheet/row locator, do not silently merge cases')
   seen.add(case_id);source_rows[run['id']]+=1;all_contexts.add(case_id)
   suggestions=payload.get('sugerencias') or []
   if not suggestions:continue
   eligible_by_config[run['config']].add(case_id)
   context_status='raw_line_saved' if payload.get('raw_line') else 'original_text_only_no_raw_source_link'
   entry=cases.setdefault(case_id,{'case_id':case_id,'file_id':stable['file_sha256'],'type':stable['role'],'context':stable['complete_private_context'],
       'context_status':context_status,'source_locator':stable,'candidates':{},'rankings':[]})
   ranking=[]
   for rank,candidate in enumerate(suggestions,1):
    candidate_id=opaque([candidate.get('id'),candidate.get('nombre'),stable['role']])
    entry['candidates'][candidate_id]=candidate.get('nombre')
    ranking.append({'candidate_id':candidate_id,'rank':rank,'score':candidate.get('score_combinado')})
   entry['rankings'].append({'run_id':run['id'],'staging_id':row.get('id_staging'),'config':run['config'],'cache':run['cache'],'repeat':run['repeat'],
      'export_sha256':export_sha,'ranking_sha256':opaque(suggestions),'candidates':ranking})
 chosen=sorted(cases);chosen=chosen if len(chosen)<=100 else sorted(random.Random(42).sample(chosen,100))
 blind=[];public_rows=[]
 for case_id in chosen:
  entry=cases[case_id];options=[{'candidate_id':cid,'name':name} for cid,name in sorted(entry['candidates'].items())]
  random.Random(opaque(['42',case_id])).shuffle(options)
  blind.append({'case_id':case_id,'context':entry['context'],'private_context_fields':entry['source_locator']['private_context_fields'],
                'context_status':entry['context_status'],'source_locator_available':entry['source_locator']['source_row'] is not None,'options':options})
  for ranking in entry['rankings']:
   for candidate in ranking['candidates']:
    public_rows.append({'run_id':ranking['run_id'],'case_id':case_id,'file_id':entry['file_id'],'type':entry['type'],'candidate_id':candidate['candidate_id'],
       'rank':candidate['rank'],'score':candidate['score'],'ranking_artifact_sha256':ranking['export_sha256'],'ranking_sha256':ranking['ranking_sha256']})
 package=private/'revision_ciega'/('final' if final else 'parcial');stem='f0_top1' if final else 'f0_top1_parcial'
 population={'unique_staging_contexts':len(all_contexts),'eligible_population':len(cases),'sample_size':len(chosen),
   'eligible_population_by_config':{c:len(ids) for c,ids in eligible_by_config.items()},'source_staging_rows_by_run':dict(source_rows),
   'eligible_context_completeness':dict(Counter(c['context_status'] for c in cases.values())),
   'source_population_unit':'Saved review-tray staging cases, not count of original source rows/persons; product staging may already group repeated original rows.',
   'identity_definition':'SHA256 of file hash, source sheet/row when available, role, complete available private context and CI fields. Motive and ephemeral DB IDs excluded. Missing raw source context is explicit; identical saved rows without distinguishable stable locators fail closed.'}
 source_evidence={r['id']:r.get('evidence_sha256',{}) for r in runs}
 blind_document={'status':'sealed_for_independent_review' if final else 'provisional_do_not_review_yet','seed':42,'population':population,'source_identity':identity,
   'source_evidence':source_evidence,'instructions':'Choose candidate_id, reject_all, no_candidate, insufficient_information or exclude BEFORE viewing any ranking or score. Submit reviewer ID, timezone-aware timestamp, package SHA and explicit blinded-before-decision attestation. Non-choose decisions require a reason. No live database actions.','cases':blind}
 ranking_document={'source_identity':identity,'source_evidence':source_evidence,'population':population,'cases':[cases[i] for i in chosen]}
 files={package/'casos.json':encode(blind_document),package/'rankings_privados_no_mostrar.json':encode(ranking_document)}
 if public_rows:files[public/(stem+'_candidatos.csv')]=csv_bytes(public_rows,list(public_rows[0]))
 if final:
  seal_path=public/'f0_top1_paquete_sellado.json'
  sealed_at=json.loads(seal_path.read_text(encoding='utf8')).get('sealed_at') if seal_path.exists() else datetime.now(ZoneInfo('America/La_Paz')).isoformat()
  manifest={'status':'sealed','blind_package_sha256':hashlib.sha256(files[package/'casos.json']).hexdigest(),
    'ranking_package_sha256':hashlib.sha256(files[package/'rankings_privados_no_mostrar.json']).hexdigest(),'sealed_at':sealed_at,'source_identity':identity,'source_evidence':source_evidence,**population}
  files[public/'f0_top1_paquete_sellado.json']=encode(manifest)
  files[public/'f0_top1_decisiones_plantilla.csv']=csv_bytes([],DECISION_FIELDS)
  sealed_group(files)
 else:
  for path,data in files.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
 summary={'status':'pending_independent_human_decisions','source_runs':[r['id'] for r in runs],'source_runs_expected':12,**population,
   'coverage_of_staging_contexts':len(cases)/len(all_contexts) if all_contexts else None,'case_ids':chosen,'valid_human_decisions':0,'coincidences':None,'top1':None,'top1_display':'N/D',
   'private_blind_package':str(package),'blind_package_sha256':sha(package/'casos.json'),'ranking_package_sha256':sha(package/'rankings_privados_no_mostrar.json'),
   'final_population':final,'human_validation_pending':True,'sampling':'Census if N<=100, otherwise100 unique source contexts with seed42; source rows retained per run, cache/repetition copies never multiply decisions.'}
 # A rerun of package preparation must not erase decisions already imported for the same sealed package.
 summary_path=public/(stem+'_resumen.json')
 if summary_path.exists():
  previous=json.loads(summary_path.read_text(encoding='utf8'))
  if previous.get('status')=='human_decisions_imported' and previous.get('blind_package_sha256')==summary['blind_package_sha256']:return previous
 store(summary_path,summary)
 return summary

def evaluate_decisions(blind_path,ranking_path,manifest_path,decisions_path,output):
 manifest=json.loads(manifest_path.read_text(encoding='utf8'));blind=json.loads(blind_path.read_text(encoding='utf8'));ranking=json.loads(ranking_path.read_text(encoding='utf8'))
 if manifest.get('status')!='sealed' or blind.get('status')!='sealed_for_independent_review':raise ValueError('Human review requires a sealed complete A4 package')
 if sha(blind_path)!=manifest['blind_package_sha256'] or sha(ranking_path)!=manifest['ranking_package_sha256']:raise ValueError('Sealed package hash mismatch')
 cases={r['case_id']:r for r in blind['cases']};rankings={r['case_id']:r for r in ranking['cases']}
 accepted={}
 with decisions_path.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f)
  if not reader.fieldnames or not set(DECISION_FIELDS)<=set(reader.fieldnames):raise ValueError('Missing human decision CSV fields')
  for row in reader:
   case_id=row['case_id'];kind=row['decision_kind'];candidate=row['candidate_id']
   if case_id not in cases or case_id in accepted:raise ValueError('Unknown or duplicated decision case ID')
   if row['blind_package_sha256']!=manifest['blind_package_sha256']:raise ValueError('Decision references a different blind package')
   if row['blinded_before_decision'].strip().lower() not in ('true','1','yes','si','sí'):raise ValueError('Independent blind-before-decision declaration required')
   if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',row['reviewer_id']):raise ValueError('Opaque reviewer ID required')
   try:timestamp=datetime.fromisoformat(row['decision_timestamp'])
   except ValueError:raise ValueError('Valid decision timestamp required') from None
   if timestamp.tzinfo is None or timestamp.utcoffset() is None:raise ValueError('Decision timestamp must contain timezone')
   if not manifest.get('sealed_at') or timestamp<datetime.fromisoformat(manifest['sealed_at']):raise ValueError('Decision predates sealed review package')
   if kind not in ('choose','reject_all','no_candidate','insufficient_information','exclude'):raise ValueError('Invalid decision kind')
   if kind=='choose':
    if candidate not in {c['candidate_id'] for c in cases[case_id]['options']}:raise ValueError('Chosen candidate not in blinded package')
    if row['exclusion_reason'].strip():raise ValueError('Chosen valid candidate cannot carry an exclusion reason')
   elif candidate or not row['exclusion_reason'].strip():raise ValueError('Non-choose decision requires no candidate and an explicit reason')
   accepted[case_id]=row
 per_config={}
 for config in ('a3','a123'):
  valid=correct=reviewed=eligible_sample=0;exclusions=[]
  for case_id,case in rankings.items():
   observations=[r for r in case['rankings'] if r['config']==config]
   if not observations:continue
   eligible_sample+=1
   decision=accepted.get(case_id)
   if not decision:continue
   reviewed+=1
   if decision['decision_kind']!='choose':
    exclusions.append({'case_id':case_id,'kind':decision['decision_kind'],'reason':decision['exclusion_reason']});continue
   top_ids={r['candidates'][0]['candidate_id'] for r in observations if r['candidates']}
   candidate_sets={tuple(sorted(c['candidate_id'] for c in r['candidates'])) for r in observations}
   if len(top_ids)!=1 or len(candidate_sets)!=1:raise ValueError('Ranking varies across replicas/cache for one configuration/context; inspect per-run evidence before aggregating')
   if decision['candidate_id'] not in set(next(iter(candidate_sets))):
    exclusions.append({'case_id':case_id,'kind':'no_candidate_in_configuration','reason':'Reviewer selected a valid blind-union candidate absent from this configuration ranking'});continue
   valid+=1;correct+=decision['candidate_id']==next(iter(top_ids))
  population=manifest['eligible_population_by_config'][config]
  per_config[config]={'eligible_population':population,'eligible_sample':eligible_sample,'reviewed_sample':reviewed,'valid_human_decisions':valid,'coincidences':correct,
    'top1':correct/valid if valid else None,'top1_display':str(correct/valid) if valid else 'N/D','review_coverage_of_eligible_population':reviewed/population if population else None,
    'review_coverage_of_sample':reviewed/eligible_sample if eligible_sample else None,'valid_decision_coverage':valid/population if population else None,'exclusions':exclusions}
 result={'status':'human_decisions_imported','blind_package_sha256':sha(blind_path),'ranking_package_sha256':sha(ranking_path),'human_decisions_csv_sha256':sha(decisions_path),
   'source_manifest_sha256':sha(manifest_path),'received_decisions':len(accepted),'sample_size':len(cases),'decision_kinds':dict(Counter(r['decision_kind'] for r in accepted.values())),
   'reviewer_ids':sorted({r['reviewer_id'] for r in accepted.values()}),'independence_evidence':'Explicit reviewer attestation bound to sealed package; CSV validation cannot independently prove actual human behavior.',
   'per_configuration':per_config,'population':blind['population'],'human_validation_pending':len(accepted)<len(cases)}
 store(output,result);return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--package',required=True,type=Path);p.add_argument('--rankings',required=True,type=Path);p.add_argument('--manifest',required=True,type=Path);p.add_argument('--decisions',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 result=evaluate_decisions(a.package,a.rankings,a.manifest,a.decisions,a.output)
 print(json.dumps({'received_decisions':result['received_decisions'],'top1':{c:r['top1'] for c,r in result['per_configuration'].items()}}))
if __name__=='__main__':main()
