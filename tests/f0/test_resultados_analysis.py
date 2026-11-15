import pytest
from scripts.analizar_f0_resultados import stratified_sample, weighted_rate, statistic, SafeUnpickler
import io,pickle


def test_stratified_sample_covers_small_stratum_and_is_reproducible():
 records=[{'case_id':str(i),'stratum_id':'large' if i<199 else 'rare'} for i in range(200)]
 sample=stratified_sample(records)
 assert len(sample)==100
 assert {r['stratum_id'] for r in sample}=={'large','rare'}
 assert sample==stratified_sample(list(reversed(records)))
 assert all(r['sample_n_h']>=1 for r in sample)


def test_census_has_population_denominators():
 sample=stratified_sample([{'case_id':'1','stratum_id':'a'},{'case_id':'2','stratum_id':'a'}])
 assert all(r['population_n_h']==r['sample_n_h']==2 for r in sample)


def test_weighted_rate_is_not_raw_sample_fraction():
 sample=[{'stratum_id':'large','population_n_h':90,'technical_label':'desacuerdo real'},
         {'stratum_id':'rare','population_n_h':10,'technical_label':'falso por fragmentación'}]
 assert weighted_rate(sample)==pytest.approx(.1)
 sample[0]['technical_label']=''
 assert weighted_rate(sample) is None


def test_zero_denominator_remains_undefined_but_zero_count_is_zero():
 assert statistic(0,0,'fraction','count/total')['value'] is None
 assert statistic(0,1,'rows','count')['value']==0


def test_pickle_loader_denies_arbitrary_classes():
 class Dangerous:
  def __reduce__(self):return (eval,('40+2',))
 with pytest.raises(ValueError,match='Unexpected pickle class'):
  SafeUnpickler(io.BytesIO(pickle.dumps(Dangerous()))).load()
 assert SafeUnpickler(io.BytesIO(pickle.dumps({'safe':[1,2]}))).load()=={'safe':[1,2]}


def test_saved_ner_classification_distinguishes_truncation_type_and_true_disagreement():
 from scripts.analizar_f0_resultados import classify_disagreement
 text='ESTUDIANTE: ANA LUZ'
 assert classify_disagreement('ANA LUZ',text,[])['technical_label']=='desacuerdo real'
 assert classify_disagreement('ANA LUZ',text,[],visible_end=15)['technical_label']=='truncamiento/no evaluable'
 assert classify_disagreement('OTHER',text,[])['verdict']=='NO_EVALUABLE'
 span={'tipo':'PROGRAMA','texto':'ANA LUZ','start':12,'end':19}
 assert classify_disagreement('ANA LUZ',text,[span])['technical_label']=='tipo distinto'


def test_qc_kpi_uses_joined_year_nonnull_denominator_and_nullable_backlog(tmp_path):
 import json
 from scripts.analizar_f0_resultados import qc_metrics
 def rows(name,data):
  p=tmp_path/(name+'.jsonl');p.write_text('\n'.join(json.dumps(r) for r in data),encoding='utf8');return p
 paths={'dim_tiempo.jsonl':rows('time',[{'id_tiempo':1,'gestion':2026},{'id_tiempo':2,'gestion':2025}]),
  'fact_rendimiento_academico.jsonl':rows('academic',[{'id_tiempo':1,'nivel_confianza_ia':.84},{'id_tiempo':1,'nivel_confianza_ia':None},{'id_tiempo':2,'nivel_confianza_ia':1.0}]),
  'stg_entidad_no_resuelta.jsonl':rows('stage',[{'resuelto':False,'created_at':'2025-01-01'}])}
 run={'paths':paths,'foot':{'kpis':{'KPI-10':84,'KPI-11':0,'KPI-18':None}},'revision':{'estadisticas':{}},'result':{}}
 result=qc_metrics(run,2026)
 assert result['KPI-10']['denominator']==1
 assert result['KPI-10']['value']==84
 assert result['KPI-11']['value']==0
 assert result['KPI-18']['value'] is None
 assert all(result[k]['value_matches_endpoint'] for k in ('KPI-10','KPI-11','KPI-18'))
 assert not any(result[k]['endpoint_scope_verified'] for k in ('KPI-10','KPI-11','KPI-18'))
 run['revision']['gestion_scorecard_por_defecto']=2026
 result=qc_metrics(run)
 assert all(result[k]['endpoint_reconciles'] for k in ('KPI-10','KPI-11','KPI-18'))


def test_blind_top1_package_deduplicates_replicas_and_hides_rank_and_scores(tmp_path):
 import json
 from scripts.analizar_f0_resultados import prepare_top1
 private=tmp_path/'private';public=tmp_path/'public';private.mkdir();public.mkdir()
 docs=private/'docs.jsonl';docs.write_text(json.dumps({'id_documento':1,'hash_sha256':'abc','tipo_fuente':'ACADEMICO'}),encoding='utf8')
 stages=private/'stage.jsonl';stages.write_text(json.dumps({'id_staging':1,'id_documento':1,'tipo_entidad':'ESTUDIANTE','motivo':'HOMONIMIA','texto_original':'PRIVATE PERSON',
  'payload_json':{'raw_line':'PRIVATE CONTEXT','sugerencias':[{'id':2,'nombre':'PRIVATE CANDIDATE','score_combinado':.9}]}}),encoding='utf8')
 run={'config':'a3','cache':'vacia','repeat':1,'id':'f0_a3_vacia_r1','paths':{'dim_origen_documental.jsonl':docs,'stg_entidad_no_resuelta.jsonl':stages}}
 other={**run,'repeat':2,'id':'f0_a3_vacia_r2'}
 summary=prepare_top1([run,other],public,private)
 assert summary['eligible_population']==summary['sample_size']==1
 blind=json.loads((private/'revision_ciega/parcial/casos.json').read_text(encoding='utf8'))
 assert 'rank' not in json.dumps(blind['cases'])
 assert 'score' not in json.dumps(blind['cases'])
 assert 'PRIVATE CANDIDATE' in json.dumps(blind['cases'])
 assert 'PRIVATE CANDIDATE' not in (public/'f0_top1_parcial_candidatos.csv').read_text(encoding='utf8')
 assert summary['top1'] is None


def test_exact_ed_gar_person_spans_suggest_fragmentation_without_changing_code_verdict():
 from scripts.analizar_f0_resultados import classify_disagreement
 text='ESTUDIANTE: ED | GAR TORRES'
 first=text.index('ED');second=text.index('GAR')
 entities=[{'tipo':'ESTUDIANTE','texto':'ED','start':first,'end':first+2},
           {'tipo':'ESTUDIANTE','texto':'GAR TORRES','start':second,'end':len(text)}]
 result=classify_disagreement('EDGAR TORRES',text,entities,visible_end=len(text))
 assert result['technical_label']=='falso por fragmentación'
 assert result['fragment_spans']==[(first,first+2),(second,len(text))]
 assert result['verdict']=='NO_EVALUABLE'  # Product comparison is preserved, technical diagnosis is distinct.
 assert result['label_status']=='automatic_suggestion_not_reviewed'
 assert classify_disagreement('EDGAR TORRES',text,entities,visible_end=second+2)['technical_label']=='truncamiento/no evaluable'


@pytest.mark.parametrize('text,surfaces',[
 ('ED | GAR', ['ED','GAR']),
 ('ED | OTRO: X | GAR TORRES',['ED','GAR TORRES']),
 ('GAR | ED TORRES',['GAR','ED TORRES']),
 ('FED | GAR TORRES',['ED','GAR TORRES']),
 ('ED | GAR TORRES',['ED','WRONG SURFACE']),
])
def test_fragmentation_does_not_invent_missing_reordered_intervening_or_wrong_offset_evidence(text,surfaces):
 from scripts.analizar_f0_resultados import classify_disagreement
 entities=[]
 for surface in surfaces:
  actual=surface if surface in text else 'GAR TORRES'
  start=text.index(actual)
  entities.append({'tipo':'ESTUDIANTE','texto':surface,'start':start,'end':start+len(actual)})
 result=classify_disagreement('EDGAR TORRES',text,entities)
 assert result['technical_label']=='truncamiento/no evaluable'
 assert result['verdict']=='NO_EVALUABLE'


def test_names_in_separate_cells_with_real_full_word_matches_are_not_false_disagreements():
 from scripts.analizar_f0_resultados import classify_disagreement
 text='EDGAR | TORRES'
 entities=[{'tipo':'ESTUDIANTE','texto':'EDGAR','start':0,'end':5},
           {'tipo':'ESTUDIANTE','texto':'TORRES','start':8,'end':14}]
 result=classify_disagreement('EDGAR TORRES',text,entities)
 assert result['verdict']=='ACUERDO'
 assert result['technical_label']=='indeterminado'


def test_fragment_diagnosis_requires_person_spans_and_nonempty_name():
 from scripts.analizar_f0_resultados import classify_disagreement
 text='ED | GAR TORRES'
 entities=[{'tipo':'PROGRAMA','texto':'ED','start':0,'end':2},
           {'tipo':'PROGRAMA','texto':'GAR TORRES','start':5,'end':15}]
 assert classify_disagreement('EDGAR TORRES',text,entities)['technical_label']=='truncamiento/no evaluable'
 assert classify_disagreement('',text,[])['verdict']=='NO_EVALUABLE'


def test_kpi_decimal_rounding_and_endpoint_mismatch_are_explicit(tmp_path):
 import json
 from scripts.analizar_f0_resultados import qc_metrics, impact
 def rows(name,data):
  p=tmp_path/(name+'.jsonl');p.write_text('\n'.join(json.dumps(r) for r in data),encoding='utf8');return p
 paths={'dim_tiempo.jsonl':rows('time',[{'id_tiempo':1,'gestion':2026}]),
  'fact_rendimiento_academico.jsonl':rows('academic',[{'id_tiempo':1,'nivel_confianza_ia':'.8400'},{'id_tiempo':1,'nivel_confianza_ia':'.8401'}])}
 run={'id':'f0_a0_vacia_r1','config':'a0','cache':'vacia','repeat':1,'paths':paths,
      'foot':{'kpis':{'KPI-10':84.01,'KPI-11':0,'KPI-18':None}},
      'revision':{'estadisticas':{},'gestion_scorecard_por_defecto':2026},'result':{},'evidence_sha256':{}}
 result=qc_metrics(run)
 assert result['KPI-10']['exact_decimal_value']=='84.0050'
 assert result['KPI-10']['endpoint_reconciles']
 run['foot']['kpis']['KPI-10']=84
 result=qc_metrics(run)
 assert not result['KPI-10']['endpoint_reconciles']
 assert 'differs' in result['KPI-10']['reconciliation_warning']
 other={**run,'id':'f0_a2_vacia_r1','config':'a2'}
 public=tmp_path/'public';public.mkdir()
 impact([run,other],public=public)
 report=json.loads((public/'f0_impacto_qc_parcial.json').read_text(encoding='utf8'))
 assert report['status']=='requires_kpi_reconciliation'
 assert report['kpi_reconciliation_passed'] is False
 assert len(report['endpoint_discrepancies'])==2
 row=next(r for r in report['rows'] if r['metric']=='KPI-10')
 assert row['delta_absolute'] is None
 assert 'reconciliation unresolved' in row['null_reason']
 del run['foot']['kpis']['KPI-18']
 assert qc_metrics(run)['KPI-18']['reconciliation_warning']=='KPI key missing from footprint endpoint evidence'


def test_real_consolidation_counters_keep_native_units_and_count_denominators():
 from scripts.analizar_f0_resultados import api_flow_metrics
 result={'carga':{'http':200,'archivos_exitosos':10,'archivos_fallidos':0,'registros_detectados':11956},
  'consolidacion':{'inserted_dw':100,'inserted_academico':80,'inserted_financiero':20,'inserted_admision':7,'inserted_revision':13,'sent_hitl':3,'descartados_ruido':5455}}
 values=api_flow_metrics(result)
 for key,value in result['consolidacion'].items():
  metric=values['consolidacion.'+key]
  assert metric['numerator']==value
  assert metric['denominator']==1
  assert metric['value']==value
  assert metric['source']=='result.consolidacion.'+key
  assert metric['measurement_layer']=='API consolidation counters'
 assert 'input lines' in values['consolidacion.descartados_ruido']['unit']
 assert 'mixed' in values['consolidacion.sent_hitl']['unit']
 assert values['consolidacion.inserted_dw']['value']==100 # Admission outcomes must not become107.
 assert values['carga.registros_detectados']['value']==11956
 assert 'carga.http' not in values
 assert 'carga.descartados' not in values


def test_missing_consolidation_counter_is_not_imputed_as_zero():
 from scripts.analizar_f0_resultados import api_flow_metrics
 metric=api_flow_metrics({'carga':{'registros_detectados':11956}})['consolidacion.descartados_ruido']
 assert metric['numerator'] is metric['value'] is None
 assert metric['denominator']==1
 assert 'missing' in metric['null_reason']


def test_api_events_persisted_review_rows_staging_and_tray_remain_distinct(tmp_path):
 import json
 from scripts.analizar_f0_resultados import qc_metrics
 time=tmp_path/'time.jsonl';time.write_text('',encoding='utf8')
 run={'paths':{'dim_tiempo.jsonl':time},'revision':{'gestion_scorecard_por_defecto':2026,
   'estadisticas':{'fact_rendimiento_academico':{'total':20,'requiere_revision':2},'stg_entidad_no_resuelta':{'total':5}}},
   'foot':{'kpis':{'KPI-10':None,'KPI-11':None,'KPI-18':None},'bandeja':{'casos':9,'grupos':4}},
   'result':{'consolidacion':{'inserted_revision':13,'sent_hitl':3,'descartados_ruido':5455}}}
 result=qc_metrics(run)
 assert result['consolidacion.inserted_revision']['value']==13
 assert result['fact_rendimiento_academico.requiere_revision.count']['value']==2
 assert result['stg_entidad_no_resuelta.total.count']['value']==5
 assert result['bandeja.casos']['value']==9
 assert result['consolidacion.sent_hitl']['value']==3
 assert result['consolidacion.descartados_ruido']['value']==5455
 assert result['fact_rendimiento_academico.requiere_revision']['denominator']==20
 assert result['consolidacion.inserted_revision']['denominator']==1
 assert 'persisted' in result['fact_rendimiento_academico.requiere_revision.count']['measurement_layer']
 assert 'review-tray' in result['bandeja.casos']['measurement_layer']
