import csv
import json
from pathlib import Path
import pytest
from scripts.f0_revision_humana import prepare, evaluate_decisions, DECISION_FIELDS, sha


def fixture(tmp_path,n=2):
 private=tmp_path/'private';public=tmp_path/'public';private.mkdir();public.mkdir()
 docs=private/'docs.jsonl';docs.write_text(json.dumps({'id_documento':99,'hash_sha256':'a'*64}),encoding='utf8')
 paths={}
 for config in ('a3','a123'):
  path=private/(config+'.jsonl')
  data=[{'id_staging':i+900,'id_documento':99,'tipo_entidad':'ESTUDIANTE','motivo':'HOMONIMIA' if config=='a3' else 'QC_OTHER',
    'texto_original':'SAME NAME','payload_json':{'raw_line':f'CI: PRIVATE-{i} | ESTUDIANTE: SAME NAME',
    'sugerencias':[{'id':1,'nombre':'RIGHT','score_combinado':.9},{'id':2,'nombre':'WRONG','score_combinado':.7}]}} for i in range(n)]
  path.write_text('\n'.join(json.dumps(r) for r in data),encoding='utf8');paths[config]=path
 runs=[{'id':f'f0_{c}_{s}_r{n}','config':c,'cache':s,'repeat':n,
  'paths':{'dim_origen_documental.jsonl':docs,'stg_entidad_no_resuelta.jsonl':paths[c]},
  'meta':{'valida':True,'lote_sha256':'a'*64,'arbol_sha256':'b'*64,'modelo_sha256':'c'*64},
  'evidence_sha256':{'result':'d'*64,'meta':'e'*64}} for c in ('a3','a123') for s in ('vacia','llena') for n in (1,2,3)]
 return runs,public,private


def inputs(tmp_path,n=2):
 runs,public,private=fixture(tmp_path,n)
 summary=prepare(runs,public,private,final=True)
 package=private/'revision_ciega/final';blind=package/'casos.json';ranking=package/'rankings_privados_no_mostrar.json';manifest=public/'f0_top1_paquete_sellado.json'
 data=json.loads(blind.read_text(encoding='utf8'));decisions=[]
 for case in data['cases']:
  decisions.append({'case_id':case['case_id'],'decision_kind':'choose','candidate_id':next(c['candidate_id'] for c in case['options'] if c['name']=='RIGHT'),
   'reviewer_id':'reviewer_1','decision_timestamp':json.loads(manifest.read_text(encoding='utf8'))['sealed_at'],'blind_package_sha256':sha(blind),'blinded_before_decision':'true','exclusion_reason':''})
 return runs,public,private,blind,ranking,manifest,decisions


def evaluate(data,public,blind,ranking,manifest):
 path=public/'human.csv'
 with path.open('w',newline='',encoding='utf8') as f:
  writer=csv.DictWriter(f,fieldnames=DECISION_FIELDS);writer.writeheader();writer.writerows(data)
 return evaluate_decisions(blind,ranking,manifest,path,public/'evaluated.json')


def test_homonymous_different_complete_contexts_do_not_shrink_population_below100(tmp_path):
 runs,public,private=fixture(tmp_path,101)
 result=prepare(runs,public,private,final=True)
 assert result['eligible_population']==result['unique_staging_contexts']==101
 assert result['sample_size']==100
 assert set(result['source_staging_rows_by_run'].values())=={101}
 assert result['eligible_population_by_config']=={'a3':101,'a123':101}


def test_motive_and_ephemeral_staging_ids_do_not_split_same_source_case(tmp_path):
 runs,public,private=fixture(tmp_path)
 p=runs[6]['paths']['stg_entidad_no_resuelta.jsonl'];data=[json.loads(s) for s in p.read_text().splitlines()]
 for row in data:row['id_staging']+=10000
 p.write_text('\n'.join(json.dumps(r) for r in data),encoding='utf8')
 assert prepare(runs,public,private,final=True)['eligible_population']==2


def test_source_row_locator_separates_fully_identical_private_lines(tmp_path):
 runs,public,private=fixture(tmp_path)
 raw=private/'raw.jsonl';raw.write_text('\n'.join(json.dumps({'id':i,'hoja':'H1','fila_inicio':10*i}) for i in (1,2)),encoding='utf8')
 for path in {r['paths']['stg_entidad_no_resuelta.jsonl'] for r in runs}:
  data=[json.loads(s) for s in path.read_text().splitlines()]
  for i,row in enumerate(data,1):
   row['registro_origen_id']=i;row['payload_json']['id']=f'REG_{i}_1';row['payload_json']['raw_line']='FULLY IDENTICAL PRIVATE LINE'
  path.write_text('\n'.join(json.dumps(r) for r in data),encoding='utf8')
 for run in runs:run['paths']['staging_registros_crudos.jsonl']=raw
 assert prepare(runs,public,private,final=True)['eligible_population']==2


def test_sealed_package_is_idempotent_and_never_overwrites_different_material(tmp_path):
 runs,public,private,blind,ranking,manifest,decisions=inputs(tmp_path)
 before={p:sha(p) for p in (blind,ranking,manifest)}
 prepare(list(reversed(runs)),public,private,final=True)
 path=runs[0]['paths']['stg_entidad_no_resuelta.jsonl'];data=[json.loads(s) for s in path.read_text().splitlines()]
 data[0]['payload_json']['raw_line']+=' CHANGED'
 path.write_text('\n'.join(json.dumps(r) for r in data),encoding='utf8')
 with pytest.raises(ValueError,match='overwrite sealed'):prepare(runs,public,private,final=True)
 assert all(sha(p)==value for p,value in before.items())


@pytest.mark.parametrize('bad',['incomplete','identity','warmup'])
def test_sealing_rejects_incomplete_different_identity_and_warmup_sources(tmp_path,bad):
 runs,public,private=fixture(tmp_path)
 if bad=='incomplete':runs.pop()
 elif bad=='identity':runs[0]['meta']['modelo_sha256']='f'*64
 else:runs[0]['id']='f0_warmup_a3'
 with pytest.raises(ValueError):prepare(runs,public,private,final=True)


def test_real_decision_contract_counts_top1_and_explicit_rejections_with_coverage(tmp_path):
 runs,public,private,blind,ranking,manifest,decisions=inputs(tmp_path)
 decisions[1].update({'decision_kind':'reject_all','candidate_id':'','exclusion_reason':'Reviewer rejects all suggestions'})
 result=evaluate(decisions,public,blind,ranking,manifest)
 for row in result['per_configuration'].values():
  assert row['valid_human_decisions']==row['coincidences']==1
  assert row['top1']==1
  assert row['review_coverage_of_eligible_population']==1
  assert row['valid_decision_coverage']==.5
  assert row['exclusions'][0]['kind']=='reject_all'
 assert result['human_validation_pending'] is False
 # Preparing the same sealed sample again cannot erase received decisions.
 output=public/'f0_top1_resumen.json';output.write_text(json.dumps(result),encoding='utf8')
 assert prepare(runs,public,private,final=True)['status']=='human_decisions_imported'


def test_zero_human_decisions_are_undefined_not_zero_accuracy(tmp_path):
 runs,public,private,blind,ranking,manifest,decisions=inputs(tmp_path)
 result=evaluate([],public,blind,ranking,manifest)
 assert result['received_decisions']==0
 assert result['human_validation_pending']
 assert all(v['top1'] is None and v['top1_display']=='N/D' for v in result['per_configuration'].values())


@pytest.mark.parametrize('field,value',[
 ('blind_package_sha256','wrong'),('blinded_before_decision','false'),('reviewer_id',''),
 ('decision_timestamp','2026-11-14T10:00:00'),('candidate_id','unknown'),('case_id','unknown'),
 ('decision_kind','SIMULATED_APPROVAL'),('exclusion_reason','invalid choose exclusion'),
])
def test_invalid_independent_decision_contract_is_rejected(tmp_path,field,value):
 runs,public,private,blind,ranking,manifest,decisions=inputs(tmp_path)
 decisions[0][field]=value
 with pytest.raises(ValueError):evaluate(decisions,public,blind,ranking,manifest)


def test_duplicate_decisions_and_tampered_sealed_artifacts_are_rejected(tmp_path):
 runs,public,private,blind,ranking,manifest,decisions=inputs(tmp_path)
 with pytest.raises(ValueError,match='duplicated'):evaluate(decisions+[decisions[0]],public,blind,ranking,manifest)
 blind.write_text(blind.read_text(encoding='utf8')+' ',encoding='utf8')
 with pytest.raises(ValueError,match='hash mismatch'):evaluate(decisions,public,blind,ranking,manifest)


def test_decision_cannot_predate_the_sealed_package(tmp_path):
 runs,public,private,blind,ranking,manifest,decisions=inputs(tmp_path)
 decisions[0]['decision_timestamp']='2000-01-01T00:00:00+00:00'
 with pytest.raises(ValueError,match='predates'):evaluate(decisions,public,blind,ranking,manifest)


@pytest.mark.parametrize('kind',['reject_all','no_candidate','insufficient_information','exclude'])
def test_rejection_no_candidate_and_exclusion_require_explicit_reason(tmp_path,kind):
 runs,public,private,blind,ranking,manifest,decisions=inputs(tmp_path)
 decisions[0].update({'decision_kind':kind,'candidate_id':'','exclusion_reason':''})
 with pytest.raises(ValueError,match='explicit reason'):evaluate(decisions,public,blind,ranking,manifest)


def test_ambiguous_identical_rows_without_stable_locator_are_not_silently_merged(tmp_path):
 runs,public,private=fixture(tmp_path)
 path=runs[0]['paths']['stg_entidad_no_resuelta.jsonl'];data=[json.loads(s) for s in path.read_text().splitlines()]
 data[1]['payload_json']['raw_line']=data[0]['payload_json']['raw_line']
 path.write_text('\n'.join(json.dumps(r) for r in data),encoding='utf8')
 with pytest.raises(ValueError,match='Ambiguous duplicated'):prepare(runs,public,private,final=True)


def test_different_ci_fields_remain_distinct_when_loader_saved_only_name_and_suggestions(tmp_path):
 runs,public,private=fixture(tmp_path)
 for path in {r['paths']['stg_entidad_no_resuelta.jsonl'] for r in runs}:
  data=[json.loads(s) for s in path.read_text().splitlines()]
  for i,row in enumerate(data):
   row['payload_json'].pop('raw_line');row['ci_temporal']=f'PRIVATE-CI-{i}'
  path.write_text('\n'.join(json.dumps(r) for r in data),encoding='utf8')
 result=prepare(runs,public,private,final=True)
 assert result['eligible_population']==2
 assert result['eligible_context_completeness']=={'original_text_only_no_raw_source_link':2}
 blind=json.loads((private/'revision_ciega/final/casos.json').read_text(encoding='utf8'))
 assert all(c['context_status']=='original_text_only_no_raw_source_link' for c in blind['cases'])
 assert all(c['source_locator_available'] is False for c in blind['cases'])
 assert 'PRIVATE-CI' not in (public/'f0_top1_candidatos.csv').read_text(encoding='utf8')


def test_insufficient_information_stays_in_coverage_but_not_top1_denominator(tmp_path):
 runs,public,private,blind,ranking,manifest,decisions=inputs(tmp_path)
 for decision in decisions:
  decision.update({'decision_kind':'insufficient_information','candidate_id':'','exclusion_reason':'Saved export has no unique row/CI context to distinguish homonyms'})
 result=evaluate(decisions,public,blind,ranking,manifest)
 for row in result['per_configuration'].values():
  assert row['reviewed_sample']==2
  assert row['review_coverage_of_sample']==1
  assert row['valid_human_decisions']==0
  assert row['top1'] is None
  assert len(row['exclusions'])==2
  assert all(r['kind']=='insufficient_information' for r in row['exclusions'])
