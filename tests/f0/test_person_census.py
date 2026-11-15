import gzip
import json
import pickle
import pytest
from scripts.analizar_f0_resultados import (individual_product_verdict,resolved_rule_people,reconcile_person_census,prepare_disagreements,token)


def fixture(tmp_path,other='ACUERDO',missing_cache=False):
 private=tmp_path/'private';public=tmp_path/'public';private.mkdir();public.mkdir()
 text='ESTUDIANTE: ANA | DOCENTE: LUZ'
 people=[{'label':'ESTUDIANTE','token':'ANA','matchedCanonical':'ANA','fuente_resolucion':'ENCABEZADO','acuerdo_beto':'DESACUERDO'},
         {'label':'DOCENTE','token':'LUZ' if other!='NO_EVALUABLE' else 'MISSING','matchedCanonical':'LUZ','fuente_resolucion':'ENCABEZADO','acuerdo_beto':'DESACUERDO'}]
 start=text.index('LUZ');ner=[] if other=='NO_EVALUABLE' else [{'tipo':'DOCENTE' if other=='ACUERDO' else 'PROGRAMA','texto':'LUZ','start':start,'end':start+3}]
 def path(name,records):
  p=private/name;p.write_text('\n'.join(json.dumps(r) for r in records),encoding='utf8');return p
 paths={'dim_origen_documental.jsonl':path('docs.jsonl',[{'id_documento':1,'hash_sha256':'f'*64,'nombre_archivo':'file.xlsx','tipo_fuente':'ACTA'}]),
  'staging_registros_crudos.jsonl':path('raw.jsonl',[{'id':1,'id_documento':1,'fila_inicio':10,'texto_plano':text,'payload_json':{'tuplas':[{'id':'REG_1_1','raw_line':text}]}}]),
  'cache_beto_entidades.jsonl':path('ner.jsonl',[] if missing_cache else [{'hash_texto':token(text),'entidades':json.dumps(ner)}])}
 detail={'id':'REG_1_1','id_documento':1,'tipo_fuente':'ACTA','motivo':'OTHER_PRIORITY_REASON','lectura':{'entidades':people}}
 pkl=private/'cache.pkl.gz'
 with gzip.open(pkl,'wb') as f:pickle.dump({'detalles':[detail]},f)
 paths[pkl.name]=pkl
 expected={'acuerdos':int(other=='ACUERDO'),'desacuerdos':1,'no_evaluables':int(other=='NO_EVALUABLE'),'tipo_distinto':int(other=='TIPO_DISTINTO'),
  'comparadas_acuerdo':1+int(other!='NO_EVALUABLE'),'desacuerdos_por_archivo_y_tipo':{'file.xlsx | ACTA':1}}
 run={'id':'f0_a2w_vacia_r1','config':'a2w','cache':'vacia','repeat':1,'meta':{'valida':True},'paths':paths,'result':{'lectura_beto_contadores':expected,'consolidacion_beto_contadores':{}}}
 return run,public,private


@pytest.mark.parametrize('other',['ACUERDO','NO_EVALUABLE','TIPO_DISTINTO'])
def test_only_proven_disagreeing_role_enters_denominator_even_if_both_saved_markers_disagree(tmp_path,other):
 run,public,private=fixture(tmp_path,other)
 assert prepare_disagreements([run],public,private)==(1,1)
 report=json.loads((public/'f0_desacuerdos_parcial_resumen.json').read_text(encoding='utf8'))
 assert report['population_by_stage']['lectura']==1
 assert report['excluded_non_disagreement_observations']==1
 census=report['census_by_run'][run['id']]['lectura']
 assert census['reconciled_complete_census']
 assert report['census_by_run'][run['id']]['lectura_by_file_type'][0]['reconciles']
 sample=json.loads((private/'revision_desacuerdos/parcial.json').read_text(encoding='utf8'))
 assert sample['sample'][0]['role']=='ESTUDIANTE'
 assert sample['sample'][0]['individual_product_verdict']=='DESACUERDO'
 assert sample['excluded_non_disagreements'][0]['individual_verdict']==other


def test_aggregated_marker_without_raw_ner_does_not_become_a_real_disagreement(tmp_path):
 run,public,private=fixture(tmp_path,missing_cache=True)
 assert prepare_disagreements([run],public,private)==(0,0)
 report=json.loads((public/'f0_desacuerdos_parcial_resumen.json').read_text(encoding='utf8'))
 census=report['census_by_run'][run['id']]['lectura']
 assert census['unknown_individual_observations']==2
 assert not census['reconciled_complete_census']
 assert report['weighted_suggested_false_fragmentation_rate_by_stage']['lectura'] is None


def test_product_uses_first_entity_per_role_not_all_label_duplicates():
 def person(name,resolved=True):return {'label':'ESTUDIANTE','token':name,'matchedCanonical':name if resolved else None,'fuente_resolucion':'FUZZY'}
 assert resolved_rule_people([person('A'),person('B')])[0]['token']=='A'
 assert resolved_rule_people([person('A',False),person('B')])==[]


def test_explicit_individual_verdict_is_used_but_conflict_is_untraceable():
 person={'label':'DOCENTE','acuerdo_beto':'DESACUERDO'}
 detail={'acuerdo_beto_por_rol':{'DOCENTE':'ACUERDO'}}
 assert individual_product_verdict(person,detail,{'verdict':'ACUERDO'})[0]=='ACUERDO'
 assert individual_product_verdict(person,detail,{'verdict':'DESACUERDO'})[0] is None
 assert individual_product_verdict(person,{},{} )[0] is None


def test_no_evaluables_are_outside_comparadas_and_log_rows_cannot_prove_full_census():
 actual={'ACUERDO':4,'DESACUERDO':2,'TIPO_DISTINTO':1,'NO_EVALUABLE':3}
 expected={'acuerdos':4,'desacuerdos':2,'tipo_distinto':1,'no_evaluables':3,'comparadas_acuerdo':7}
 assert reconcile_person_census(actual,expected)['reconciled_complete_census']
 assert not reconcile_person_census(actual,expected,partial=True)['reconciled_complete_census']


def test_counter_file_stratum_without_person_trace_is_reported_not_omitted(tmp_path):
 run,public,private=fixture(tmp_path)
 run['result']['lectura_beto_contadores']['desacuerdos_por_archivo_y_tipo']['other.xlsx | ACTA']=3
 prepare_disagreements([run],public,private)
 report=json.loads((public/'f0_desacuerdos_parcial_resumen.json').read_text(encoding='utf8'))
 missing=next(r for r in report['census_by_run'][run['id']]['lectura_by_file_type'] if r.get('warning'))
 assert missing['expected_disagreements']==3
 assert missing['observed_proven_disagreements']==0
 assert not missing['reconciles']


def test_warmup_is_rejected_even_if_passed_with_qc_configuration(tmp_path):
 run,public,private=fixture(tmp_path);run['id']='f0_warmup_a2w'
 with pytest.raises(ValueError,match='never a warmup'):prepare_disagreements([run],public,private)
