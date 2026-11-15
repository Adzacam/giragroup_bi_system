"""Offline F0 analysis primitives. Never imports product services or connects to a DB."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import pickle
import random
import sys
import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
PRIVATE=ROOT/'output/backups/f0_lote'
PUBLIC=ROOT/'docs/mediciones'
RUN_RE=re.compile(r'f0_(a0|a1|a2|a3|a12|a123|a2w)_(vacia|llena)_r([123])(?:_[a-zA-Z0-9]+)*$')
CONTRASTS=(('a0','a2','QC'),('a1','a12','QC'),('a2','a2w','ventana'),('a3','a123','opciones 1+2 combinadas'))

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def token(value):return hashlib.sha256(str(value).encode('utf8')).hexdigest()
def parse(value):
 if isinstance(value,str):
  try:return json.loads(value)
  except (ValueError,TypeError):return {}
 return value if value is not None else {}
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf8')
def read_rows(path):
 if path is None:return []
 return [json.loads(s) for s in path.read_text(encoding='utf8').splitlines() if s.strip()]

def stratified_sample(records,target=100,seed=42):
 """At least one in every nonempty stratum, then deterministic size/allocation quotient allocation."""
 groups=defaultdict(list)
 for r in records:groups[r['stratum_id']].append(r)
 size=min(len(records),max(target,len(groups)))
 if size==len(records):
  return sorted(({**r,'population_n_h':len(groups[r['stratum_id']]),'sample_n_h':len(groups[r['stratum_id']]),'seed':seed} for r in records),key=lambda r:r['case_id'])
 allocation={k:1 for k in groups}; remaining=size-len(groups)
 while remaining:
  candidates=[k for k in sorted(groups) if allocation[k]<len(groups[k])]
  selected=max(candidates,key=lambda k:(len(groups[k])/allocation[k],k))
  allocation[selected]+=1; remaining-=1
 rng=random.Random(seed);sample=[]
 for k in sorted(groups):
  values=sorted(groups[k],key=lambda r:r['case_id'])
  for r in rng.sample(values,allocation[k]):sample.append({**r,'population_n_h':len(values),'sample_n_h':allocation[k],'seed':seed})
 return sorted(sample,key=lambda r:r['case_id'])

def weighted_rate(records,label_field='technical_label',positive='falso por fragmentación'):
 strata=defaultdict(list)
 for r in records:strata[r['stratum_id']].append(r)
 total=sum(rows[0]['population_n_h'] for rows in strata.values())
 if not total:return None
 result=0
 for rows in strata.values():
  reviewed=[r for r in rows if r.get(label_field)]
  if len(reviewed)!=len(rows):return None
  result+=rows[0]['population_n_h']/total*sum(r[label_field]==positive for r in rows)/len(reviewed)
 return result

class SafeUnpickler(pickle.Unpickler):
 def find_class(self,module,name):
  if (module,name)==('decimal','Decimal'):return Decimal
  if module=='datetime' and name in ('datetime','date','time','timedelta','timezone'):
   import datetime as dt
   return getattr(dt,name)
  raise ValueError('Unexpected pickle class '+module+'.'+name)

def read_pickle(path):
 with gzip.open(path,'rb') as f:return SafeUnpickler(f).load()

def discover(public=PUBLIC,private=PRIVATE,selected_ids=None,selected_configs=None):
 runs=[]
 for p in sorted(public.glob('f0_a*.meta.json')):
  stem=p.name.removesuffix('.meta.json'); m=RUN_RE.fullmatch(stem)
  if not m or (selected_ids is not None and stem not in selected_ids) or (selected_configs is not None and m[1] not in selected_configs):continue
  meta=json.loads(p.read_text(encoding='utf8'))
  if meta.get('valida') is not True:continue
  if meta.get('configuracion')!=m[1] or meta.get('estado')!=m[2]:raise ValueError('Run name/metadata configuration mismatch')
  result=public/(stem+'.json');revision=public/(stem+'.revision.json');foot=public/(stem+'.json.huella.json')
  if not all(f.is_file() for f in (result,revision,foot)):raise ValueError('Incomplete valid run '+stem)
  manifest=json.loads(revision.read_text(encoding='utf8'));paths={}
  for entry in manifest['exports_privados']:
   f=(private/entry['archivo']).resolve()
   if not f.is_relative_to(private.resolve()):raise ValueError('Export outside private root')
   if f.stat().st_size!=entry['bytes'] or sha(f)!=entry['sha256']:raise ValueError('Changed export '+stem+'/'+f.name)
   paths[f.name]=f
  runs.append({'id':stem,'config':m[1],'cache':m[2],'repeat':int(m[3]),'paths':paths,'meta':meta,'revision':manifest,
               'result':json.loads(result.read_text(encoding='utf8')),'foot':json.loads(foot.read_text(encoding='utf8')),
               'evidence_sha256':{'meta':sha(p),'revision':sha(revision),'result':sha(result),'footprint':sha(foot)}})
 keys=[(r['config'],r['cache'],r['repeat']) for r in runs]
 if len(set(keys))!=len(keys):raise ValueError('Multiple valid runs for the same configuration/cache/repetition; resolve selection explicitly')
 identities={(r['meta'].get('lote_sha256'),r['meta'].get('arbol_sha256'),r['meta'].get('modelo_sha256')) for r in runs}
 if len(identities)>1:raise ValueError('Different frozen input/code/model identities across runs')
 return runs

def statistic(numerator,denominator,unit,formula,scale=1,null_reason=None):
 value=scale*numerator/denominator if numerator is not None and denominator else None
 return {'numerator':numerator,'denominator':denominator,'unit':unit,'value':value,'formula':formula,
         'null_reason':null_reason or ('denominator zero or population unavailable' if value is None else None)}

def api_flow_metrics(result):
 """API counters retain their native event/line units; never infer table-row totals."""
 counters={
  'inserted_dw':('loaded routing outcomes (academic bucket + financial)',
    'inserted_academico + inserted_financiero; admission outcomes excluded. Loaded outcomes may insert or update, so this is not a count of newly persisted rows.'),
  'inserted_academico':('loaded outcomes in broad academic API bucket',
    'Loaded non-financial/non-admission outcomes: includes academic, teacher evaluation, profitability and marketing routes; not just fact_rendimiento_academico.'),
  'inserted_financiero':('loaded financial routing outcomes','One increment per loader result loaded with tipo financiero; not a distinct persisted-row count.'),
  'inserted_admision':('loaded admission routing outcomes','Admission route may update a student or aggregated marketing record; excluded from inserted_dw.'),
  'inserted_revision':('loaded reg_item outcomes flagged for review at caller',
    'Increments after status loaded when reg_item.calidad.requiere_revision. Loader may independently force review (e.g. missing date); repeated updates/expansion also prevent equality with persisted requires_review rows.'),
  'sent_hitl':('API HITL path increments (mixed line/outcome granularity)',
    'Increments per non-loaded expanded reg_item, or per unapproved input line. Not the number of staging rows, distinct people or review-tray cases.'),
  'descartados_ruido':('nonempty consolidation input lines discarded for semantic noise',
    'One increment before loading when motivo_fila_sin_entidad is nonempty; applies to queried staging blocks with es_ruido FALSE. Not a fact-row count.')}
 metrics={}
 for field,(unit,meaning) in counters.items():
  value=result.get('consolidacion',{}).get(field)
  if isinstance(value,bool) or not isinstance(value,(int,float)):value=None
  metrics['consolidacion.'+field]=statistic(value,1,unit,'Count of consolidacion.'+field,
      null_reason='Expected API consolidation counter missing; no zero imputed' if value is None else None)
  metrics['consolidacion.'+field].update({'source':'result.consolidacion.'+field,'measurement_layer':'API consolidation counters',
    'interpretation':meaning,'denominator_basis':'Constant1 expresses a count; no compatible population denominator is established. Do not divide by ingestion records, facts or review cases.'})
 for field,unit in [('archivos_exitosos','ingestion API successful files'),('archivos_fallidos','ingestion API failed files'),('registros_detectados','ingestion API reported detected records')]:
  value=result.get('carga',{}).get(field)
  if isinstance(value,(int,float)) and not isinstance(value,bool):
   metrics['carga.'+field]=statistic(value,1,unit,'Count of carga.'+field)
   metrics['carga.'+field].update({'source':'result.carga.'+field,'measurement_layer':'API ingestion counters',
      'denominator_basis':'Constant1 expresses a count; ingestion records are not a proven denominator for expanded consolidation outcomes or semantic-noise line counts.'})
 return metrics

def qc_metrics(run,gestion=None):
 actual_gestion=run['revision'].get('gestion_scorecard_por_defecto')
 if gestion is None:
  if actual_gestion is None:raise ValueError('Actual default CMI gestion not exported; do not assume2026')
  gestion=int(actual_gestion)
 scope_verified=actual_gestion is not None and int(actual_gestion)==gestion
 paths=run['paths'];metrics={};times={r['id_tiempo']:r.get('gestion') for r in read_rows(paths.get('dim_tiempo.jsonl'))}
 academic=read_rows(paths.get('fact_rendimiento_academico.jsonl'))
 if not times and academic:raise ValueError('dim_tiempo missing for KPI scope')
 scoped=[r for r in academic if times.get(r.get('id_tiempo'))==gestion]
 scores=[Decimal(str(r['nivel_confianza_ia'])) for r in scoped if r.get('nivel_confianza_ia') is not None]
 confidence_sum=sum(scores,Decimal(0)); exact_mean=100*confidence_sum/len(scores) if scores else None
 metrics['KPI-10']=statistic(float(confidence_sum),len(scores),'percent','100 * SUM(academic.nivel_confianza_ia) / COUNT(non-null confidence), inner join dim_tiempo, gestion='+str(gestion),100)
 metrics['KPI-10'].update({'value':float(exact_mean) if exact_mean is not None else None,
                         'exact_decimal_numerator':str(confidence_sum),'exact_decimal_value':str(exact_mean) if exact_mean is not None else None})
 metrics['KPI-11']=statistic(sum(v>=Decimal('.85') for v in scores),len(scores),'percent','100 * COUNT(confidence >= .85) / COUNT(non-null confidence), same academic/date scope',100)
 exact_automatic=Decimal(100)*metrics['KPI-11']['numerator']/len(scores) if scores else None
 metrics['KPI-11']['exact_decimal_value']=str(exact_automatic) if exact_automatic is not None else None
 stage=read_rows(paths.get('stg_entidad_no_resuelta.jsonl'))
 backlog=[r for r in stage if r.get('resuelto') is False and str(r.get('created_at',''))[:4]==str(gestion)]
 # SQL backlog has no row for a year absent from pending staging: NULL, never imputed zero.
 metrics['KPI-18']=statistic(len(backlog) if backlog else None,1,'pending entities','COUNT(stg_entidad_no_resuelta WHERE resuelto=FALSE), created_at year='+str(gestion),null_reason='No backlog group for this year (SQL returns NULL)' if not backlog else None)
 for k in ('casos','grupos','manuales','casos_manuales'):
  v=run['foot'].get('bandeja',{}).get(k)
  metrics['bandeja.'+k]=statistic(v,1,'cases' if 'casos' in k else 'groups','saved footprint bandeja count')
  metrics['bandeja.'+k].update({'source':'footprint.bandeja.'+k,'measurement_layer':'review-tray cases/groups','denominator_basis':'Constant1 expresses a saved tray count; not equivalent to API HITL increments or staging rows'})
 for table,summary in run['revision']['estadisticas'].items():
  for field in ('total','requiere_revision','ruido','banda_alta','banda_media','banda_baja','confianza_null'):
   if field in summary:
    total=summary.get('total'); n=summary[field]
    metrics[table+'.'+field]=statistic(n,total,'fraction of '+table+' rows',field+' / total table rows')
    metrics[table+'.'+field+'.count']=statistic(n,1,'rows of '+table,'count '+field)
    for metric_name in (table+'.'+field,table+'.'+field+'.count'):
     metrics[metric_name].update({'source':'revision.estadisticas.'+table+'.'+field,
       'measurement_layer':'persisted table rows','denominator_basis':'All rows of the same named persisted table' if not metric_name.endswith('.count') else 'Constant1 expresses a persisted-row count; API outcomes are a separate population'})
 # Huella endpoint is rounded to 2 decimals; retain unrounded formula and flag discrepancies.
 for k in ('KPI-10','KPI-11','KPI-18'):
  observed=run['foot'].get('kpis',{}).get(k); v=metrics[k]['value']
  exact=metrics[k].get('exact_decimal_value') or str(v)
  rounded=float(Decimal(exact).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)) if v is not None else None
  metrics[k]['rounded_recomputed_value']=rounded
  metrics[k]['endpoint_key_present']=k in run['foot'].get('kpis',{})
  metrics[k]['endpoint_value']=observed;metrics[k]['value_matches_endpoint']=observed==rounded
  metrics[k]['endpoint_scope_verified']=scope_verified;metrics[k]['gestion']=gestion
  metrics[k]['endpoint_reconciles']=observed==rounded and scope_verified and metrics[k]['endpoint_key_present']
  if not scope_verified:metrics[k]['scope_warning']='Actual endpoint default year not proven equal to chosen year; do not infer reconciliation from matching values alone.'
  metrics[k]['reconciliation_warning']=None if metrics[k]['endpoint_reconciles'] else (
   'KPI key missing from footprint endpoint evidence' if not metrics[k]['endpoint_key_present'] else
   'Recomputed rounded KPI differs from saved endpoint; explanation/validation required before accepting this contrast' if observed!=rounded else
   'Endpoint scope is not verified')
  metrics[k].update({'source':'SQL014 CMI formula recomputed from private academic/time/staging exports; compared to footprint.kpis.'+k,
                    'measurement_layer':'CMI scoped population','denominator_basis':'Exact SQL population recorded in formula and gestion'})
 metrics.update(api_flow_metrics(run['result']))
 return metrics

def impact(runs,gestion=None,public=PUBLIC,final=False):
 keyed={(r['config'],r['cache'],r['repeat']):r for r in runs};computed={r['id']:qc_metrics(r,gestion) for r in runs};rows=[];missing=[]
 discrepancies=[{'run_id':run_id,'metric':code,'recomputed':values[code]['rounded_recomputed_value'],
                  'endpoint':values[code]['endpoint_value'],'reason':values[code]['reconciliation_warning']}
                for run_id,values in computed.items() for code in ('KPI-10','KPI-11','KPI-18') if not values[code]['endpoint_reconciles']]
 for source,target,interpretation in CONTRASTS:
  for cache in ('vacia','llena'):
   for repeat in (1,2,3):
    a=keyed.get((source,cache,repeat));b=keyed.get((target,cache,repeat))
    if not(a and b):missing.append([source,target,cache,repeat]);continue
    for metric in sorted(computed[a['id']].keys()|computed[b['id']].keys()):
     av=computed[a['id']].get(metric);bv=computed[b['id']].get(metric)
     same_scope=not(av and bv and 'gestion' in av and 'gestion' in bv and av['gestion']!=bv['gestion'])
     reconciled=metric not in ('KPI-10','KPI-11','KPI-18') or bool(av and bv and av['endpoint_reconciles'] and bv['endpoint_reconciles'])
     comparable=same_scope and reconciled
     delta=bv['value']-av['value'] if comparable and av and bv and av['value'] is not None and bv['value'] is not None else None
     rows.append({'source_run':a['id'],'target_run':b['id'],'cache_state':cache,'repeat':repeat,'contrast':source+'→'+target,'interpretation':interpretation,
      'metric':metric,'source_gestion':av.get('gestion') if av else None,'target_gestion':bv.get('gestion') if bv else None,'same_scope':same_scope,'endpoint_reconciled':reconciled,'unit':av['unit'] if av else bv['unit'],
      'measurement_layer':(av or bv).get('measurement_layer'),'source_metric_source':av.get('source') if av else None,'target_metric_source':bv.get('source') if bv else None,
      'source_denominator_basis':av.get('denominator_basis') if av else None,'target_denominator_basis':bv.get('denominator_basis') if bv else None,
      'source_numerator':av['numerator'] if av else None,'source_denominator':av['denominator'] if av else None,'source_value':av['value'] if av else None,
      'target_numerator':bv['numerator'] if bv else None,'target_denominator':bv['denominator'] if bv else None,'target_value':bv['value'] if bv else None,'delta_absolute':delta,
      'delta_relative':delta/av['value'] if delta is not None and av['value'] else None,'null_reason':('Metric absent from one run; no population imputed' if av is None or bv is None else 'Different CMI year scopes; no causal delta computed' if not same_scope else 'KPI endpoint reconciliation unresolved; no accepted endpoint delta computed' if not reconciled else '; '.join(str(x['null_reason']) for x in (av,bv) if x and x['null_reason']) or None)})
 stem='f0_impacto_qc' if final else 'f0_impacto_qc_parcial'
 write(public/(stem+'.json'),{'status':'requires_kpi_reconciliation' if discrepancies else 'measured_formulas_human_validation_pending' if final else 'incremental_incomplete','kpi_reconciliation_passed':not discrepancies,'endpoint_discrepancies':discrepancies,'gestion_override':gestion,'gestion_protocol':'Use actual exported endpoint default year independently for each run unless an explicit override is supplied; retain scope and require same year for KPI deltas','rows':rows,'missing_pairs':missing,'run_metrics':computed,
   'warning':'Only same frozen F0 population is compared. a3→a123 is combined options1+2. Reading/consolidation, API outcomes, persisted requires_revision rows, staging rows and review-tray cases/groups are separate units and are never summed or forced to reconcile. Count/1 is used when no compatible denominator is proven. Pending A3/A4 human validation is independent of these arithmetic contrasts.',
   'formula_source':{'path':'backend/scripts/migrations/014_conversion_captacion_comprobable.sql','sha256':sha(ROOT/'backend/scripts/migrations/014_conversion_captacion_comprobable.sql')},
   'evidence':{r['id']:r['evidence_sha256'] for r in runs}})
 if rows:
  with (public/(stem+'.csv')).open('w',newline='',encoding='utf8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 return len(rows)

def intervals_for_name(name,text):
 if not name.strip():return []
 def search(v):return re.search(r'(?<!\w)'+re.escape(v)+r'(?!\w)',text,re.I)
 found=search(name)
 if found:return [(found.start(),found.end())]
 intervals=[]
 for word in name.split():
  found=search(word)
  if not found:return []
  intervals.append((found.start(),found.end()))
 return intervals

def exact_person_fragment_chain(name,text,entities):
 """Prove reconstruction from disjoint saved spans; never fuzzy-match or skip words."""
 compact=lambda value:re.sub(r'[\s|]+','',value).casefold()
 target=compact(name)
 if not target:return None
 spans=[]
 for e in entities:
  if e.get('tipo') not in ('ESTUDIANTE','DOCENTE'):continue
  start,end=int(e['start']),int(e['end'])
  if not(0<=start<end<=len(text)):continue
  # An emitted surface is evidence only if its offsets point to that same surface.
  if not compact(e.get('texto','')) or compact(text[start:end])!=compact(e.get('texto','')):continue
  spans.append((start,end,compact(text[start:end])))
 spans=sorted(set(spans))
 for first in range(len(spans)):
  start,end,value=spans[first];chain=[(start,end)]
  if start and re.match(r'\w',text[start-1]):continue
  for following in spans[first+1:]:
   other_start,other_end,part=following
   if other_start<end:continue
   # Whitespace/cell separators may split a name; intervening field content may not.
   if re.fullmatch(r'[\s|]*',text[end:other_start]) is None:break
   value+=part;end=other_end;chain.append((other_start,other_end))
   if not target.startswith(value):break
   if value==target and (end==len(text) or not re.match(r'\w',text[end])):
    return {'spans':chain,'end':end,'parts':len(chain)}
 return None

def classify_disagreement(name,text,entities,visible_end=None):
 intervals=intervals_for_name(name.strip(),text)
 fragments=exact_person_fragment_chain(name,text,entities)
 if not intervals:
  if fragments and (visible_end is None or fragments['end']<=visible_end):
   return {'technical_label':'falso por fragmentación','basis':'At least two disjoint saved person spans match their literal input offsets and concatenate exactly to the whole rule name, across whitespace/cell separators only; suggested diagnosis, not human validation',
           'verdict':'NO_EVALUABLE','fragment_parts':fragments['parts'],'fragment_spans':fragments['spans'],'label_status':'automatic_suggestion_not_reviewed'}
  return {'technical_label':'truncamiento/no evaluable','basis':'Rule name not present intact and no complete visible exact person-span reconstruction','verdict':'NO_EVALUABLE','label_status':'automatic_suggestion_not_reviewed'}
 indexes={i for a,b in intervals for i in range(a,b)}
 coverage={};overlaps=[]
 for kind,types in [('person',('ESTUDIANTE','DOCENTE')),('other',('MODULO','PROGRAMA','POS'))]:
  covered=set()
  for e in entities:
   if e.get('tipo') in types:
    common=indexes.intersection(range(int(e['start']),int(e['end'])))
    covered.update(common)
    if kind=='person' and common:overlaps.append(e)
  coverage[kind]=len(covered)/len(indexes)
 verdict='ACUERDO' if coverage['person']>=.5 else 'TIPO_DISTINTO' if coverage['other']>=.5 else 'DESACUERDO'
 if visible_end is not None and max(indexes)>=visible_end:
  label='truncamiento/no evaluable';basis='Rule name extends beyond the actual first128 tokenizer offsets'
 elif verdict=='TIPO_DISTINTO':label='tipo distinto';basis='Non-person spans cover at least50% of rule name'
 elif verdict=='ACUERDO':label='indeterminado';basis='Per-person reconstruction agrees; exported row-level disagreement may have come from another role'
 else:
  label='desacuerdo real';basis='Full visible rule name present; cached person span coverage below50%; automatic suggested diagnosis only'
 return {'technical_label':label,'basis':basis,'verdict':verdict,'person_coverage':coverage['person'],'other_coverage':coverage['other'],'name_parts':len(intervals),'overlapping_person_spans':len(overlaps),'label_status':'automatic_suggestion_not_reviewed'}

def resolved_rule_people(entities):
 """Product entidad() uses the FIRST entity per role, not every matching label."""
 people=[]
 for role in ('ESTUDIANTE','DOCENTE'):
  person=next((e for e in entities if e.get('label')==role),None)
  if person and person.get('matchedCanonical') and person.get('fuente_resolucion') in ('CI_EXACTA','ENCABEZADO','FUZZY'):people.append(person)
 return people

def individual_product_verdict(person,detail,reconstructed):
 """acuerdo_beto is a ROW marker in current product; never promote it to per-role truth."""
 known={'ACUERDO','DESACUERDO','TIPO_DISTINTO','NO_EVALUABLE'}
 role=person.get('label');mapping=detail.get('acuerdo_beto_por_rol') or detail.get('lectura',{}).get('acuerdo_beto_por_rol') or {}
 explicit=mapping.get(role) if isinstance(mapping,dict) else None
 if person.get('acuerdo_beto_scope')=='persona':explicit=person.get('acuerdo_beto')
 computed=reconstructed.get('verdict')
 if explicit in known:
  if computed in known and computed!=explicit:return None,'explicit/reconstructed individual verdict conflict'
  return explicit,'explicit saved per-role verdict'
 if person.get('acuerdo_beto') not in known and detail.get('motivo')!='DESACUERDO_REGLA_BETO':
  return None,'No proof that this reading row actually underwent QC; cache presence alone is insufficient'
 if computed in known:return computed,'pure reconstruction from original private text and saved NER spans'
 return None,'Saved row-level marker cannot establish individual verdict without private reconstruction'

def reconcile_person_census(observed,expected,partial=False):
 fields={'acuerdos':'ACUERDO','desacuerdos':'DESACUERDO','no_evaluables':'NO_EVALUABLE','tipo_distinto':'TIPO_DISTINTO'}
 counts={field:observed.get(verdict,0) for field,verdict in fields.items()}
 counts['comparadas_acuerdo']=counts['acuerdos']+counts['desacuerdos']+counts['tipo_distinto']
 differences={k:{'observed':v,'expected':expected.get(k),'delta':v-expected[k] if isinstance(expected.get(k),(int,float)) else None} for k,v in counts.items()}
 complete=not partial and not observed.get('UNKNOWN',0) and all(v['expected'] is not None and v['delta']==0 for v in differences.values())
 return {'observed_individual_counts':counts,'unknown_individual_observations':observed.get('UNKNOWN',0),'comparisons':differences,
         'reconciled_complete_census':complete,'partial_log_population':partial,
         'proven_D_coverage_of_counter':counts['desacuerdos']/expected['desacuerdos'] if isinstance(expected.get('desacuerdos'),(int,float)) and expected['desacuerdos'] else None,
         'unrepresented_D_counter_observations':expected['desacuerdos']-counts['desacuerdos'] if isinstance(expected.get('desacuerdos'),(int,float)) else None,
         'coverage_unit':'Proven per-role observations divided by productive per-person disagreement counter; not unique people across stages or repetitions',
         'warning':'Single-name logs cover only a subset of individuals; counts are coverage diagnostics, not forced equality' if partial else None}

def prepare_disagreements(runs,public=PUBLIC,private=PRIVATE,final=False):
 population={};limitations=[];tokenizer=None;census_by_run={};excluded_non_disagreements=[]
 for run in runs:
  if run['config'] not in ('a2','a12','a123','a2w'):continue
  if run.get('meta',{}).get('valida') is not True or not RUN_RE.fullmatch(run['id']):raise ValueError('A3 requires a valid measured run, never a warmup')
  census={'lectura':defaultdict(int),'consolidacion':defaultdict(int)};by_file={};log_by_file={};logs_seen=0
  docs={r['id_documento']:r for r in read_rows(run['paths'].get('dim_origen_documental.jsonl'))}
  originals={};line_lookup=[]
  for raw in read_rows(run['paths'].get('staging_registros_crudos.jsonl')):
   for row in parse(raw.get('payload_json')).get('tuplas',[]):
    if row.get('id') and row.get('raw_line'):originals[row['id']]=row['raw_line']
   for i,text in enumerate([t.strip() for t in (raw.get('texto_plano') or '').splitlines() if t.strip()]):
    if text.strip():line_lookup.append((raw.get('id_documento'),(raw.get('fila_inicio') or 0)+i,text.strip()))
  ner={}
  for row in read_rows(run['paths'].get('cache_beto_entidades.jsonl')):
   ner[str(row['hash_texto']).strip()]=parse(row.get('entidades'))
  details={}
  for name,path in run['paths'].items():
   if name.endswith('.pkl.gz'):
    cached=read_pickle(path)
    if isinstance(cached,dict):
     for row in cached.get('detalles',[]):details[row.get('id')]=row
  for detail in details.values():
   raw=originals.get(detail.get('id'));doc=docs.get(detail.get('id_documento'),{})
   entities=detail.get('lectura',{}).get('entidades') or []
   people=resolved_rule_people(entities)
   marked=detail.get('motivo')=='DESACUERDO_REGLA_BETO' or detail.get('acuerdo_beto_por_rol') or detail.get('lectura',{}).get('acuerdo_beto_por_rol') or any('acuerdo_beto' in p for p in people)
   if not marked:continue
   if not people:limitations.append({'run_id':run['id'],'row_id':detail.get('id'),'reason':'QC-marked row lacks resolved per-role rule entity state'});continue
   for person in people:
    name=person.get('token') or '';role=person.get('label');fulltext=raw or detail.get('raw_text') or ''
    text=fulltext.strip() if run['config']=='a2w' else ' | '.join(c.strip() for c in fulltext.split('|') if c.strip())
    if run['config']!='a2w':text=' | '.join(text.split(' | ')[:8])
    cached=ner.get(token(text));end=None
    if cached is not None and run['config']!='a2w':
     if tokenizer is None:
      from tokenizers import Tokenizer
      tokenizer=Tokenizer.from_file(str(ROOT/'pipeline/semantic/beto_local/tokenizer.json'));tokenizer.enable_truncation(max_length=128)
     end=max((b for a,b in tokenizer.encode(text).offsets),default=0)
    classification=classify_disagreement(name,text,cached,end) if cached is not None and raw else {'technical_label':'indeterminado','basis':'Missing original text or matching private NER cache; no inference substituted','verdict':None}
    verdict,verdict_source=individual_product_verdict(person,detail,classification)
    file_id=doc.get('hash_sha256') or token(detail.get('id_documento'));kind=doc.get('tipo_fuente') or detail.get('tipo_fuente') or 'unknown'
    key=(file_id,str(kind).upper().strip());file_census=by_file.setdefault(key,{'file_id':file_id,'type':key[1],'counter_key':str(doc.get('nombre_archivo') or 'sin_archivo')+' | '+key[1],'verdicts':defaultdict(int)})
    census['lectura'][verdict or 'UNKNOWN']+=1;file_census['verdicts'][verdict or 'UNKNOWN']+=1
    if verdict!='DESACUERDO':
     excluded_non_disagreements.append({'run_id':run['id'],'stage':'lectura','file_id':file_id,'row_id':detail.get('id'),'role':role,
       'individual_verdict':verdict,'verdict_source':verdict_source,'saved_row_marker':person.get('acuerdo_beto'),
       'reason':'Not an individually proven productive disagreement; excluded from false-disagreement denominator'})
     continue
    case_id=token(json.dumps(['lectura',file_id,detail.get('id'),role,name,run['config']],ensure_ascii=False))
    entry=population.setdefault(case_id,{'case_id':case_id,'stage':'lectura','file_id':file_id,'type':kind,'role':role,'config':run['config'],
      'stratum_id':'lectura|'+file_id+'|'+kind+'|'+role,'source_runs':[],'row_id':detail.get('id'),'technical_label':classification['technical_label'],'label_status':'automatic_suggestion_not_reviewed',
      'basis':classification['basis'],'recomputed_verdict':classification['verdict'],'individual_product_verdict':verdict,'individual_verdict_source':verdict_source,'saved_row_marker':person.get('acuerdo_beto'),
      'human_label':'','reviewer_id':'','review_timestamp':'','technical_evidence':classification,
      'private_context':{'original':fulltext,'rule_name':name,'beto_input':text,'ner_entities':cached}})
    entry['source_runs'].append(run['id'])
  # Consolidation evidence is a distinct population; a log does not persist the per-role verdict or every line entity.
  for log in read_rows(run['paths'].get('log_inconsistencias.jsonl')):
   if log.get('tipo_regla')!='DESACUERDO_REGLA_BETO':continue
   logs_seen+=1
   doc=docs.get(log.get('id_documento'),{});file_id=doc.get('hash_sha256') or token(log.get('id_documento'));kind=doc.get('tipo_fuente') or 'unknown'
   name=log.get('valor_recibido') or '';matching=[text for did,line,text in line_lookup if did==log.get('id_documento') and line==log.get('fila_origen')]
   fulltext=matching[0] if len(matching)==1 else '';text=fulltext.strip() if run['config']=='a2w' else ' | '.join([c.strip() for c in fulltext.split('|') if c.strip()][:8]);cached=ner.get(token(text))
   end=None
   if fulltext and cached is not None and run['config']!='a2w':
    if tokenizer is None:
     from tokenizers import Tokenizer
     tokenizer=Tokenizer.from_file(str(ROOT/'pipeline/semantic/beto_local/tokenizer.json'));tokenizer.enable_truncation(max_length=128)
    end=max((b for a,b in tokenizer.encode(text).offsets),default=0)
   classification=classify_disagreement(name,text,cached,end) if fulltext and cached is not None else {'technical_label':'indeterminado','basis':'Saved consolidation log lacks a unique line/role or matching NER cache','verdict':None}
   verdict=classification.get('verdict');census['consolidacion'][verdict or 'UNKNOWN']+=1
   log_key=(file_id,str(kind).upper().strip());log_file_census=log_by_file.setdefault(log_key,{'file_id':file_id,'type':log_key[1],
      'counter_key':str(doc.get('nombre_archivo') or 'sin_archivo')+' | '+log_key[1],'verdicts':defaultdict(int)})
   log_file_census['verdicts'][verdict or 'UNKNOWN']+=1
   if verdict!='DESACUERDO':
    excluded_non_disagreements.append({'run_id':run['id'],'stage':'consolidacion','file_id':file_id,'row_id':log.get('fila_origen'),
      'individual_verdict':verdict,'reason':'Single-name row log is not proof this person disagreed; no dilution by other roles or unknown mappings'})
    continue
   case_id=token(json.dumps(['consolidacion',file_id,log.get('fila_origen'),name,run['config']],ensure_ascii=False));role='persona_log_no_desagregada'
   entry=population.setdefault(case_id,{'case_id':case_id,'stage':'consolidacion','file_id':file_id,'type':kind,'role':role,'config':run['config'],'stratum_id':'consolidacion|'+file_id+'|'+kind+'|'+role,
       'source_runs':[],'row_id':log.get('fila_origen'),'technical_label':classification['technical_label'],'label_status':'automatic_suggestion_not_reviewed','basis':classification['basis'],'recomputed_verdict':classification['verdict'],
       'individual_product_verdict':verdict,'individual_verdict_source':'pure reconstruction for the single logged name only; role not persisted',
       'human_label':'','reviewer_id':'','review_timestamp':'','technical_evidence':classification,'private_context':{'original':fulltext,'rule_name':name,'beto_input':text,'ner_entities':cached}})
   entry['source_runs'].append(run['id'])
  reading_expected=run['result'].get('lectura_beto_contadores') or {};consolidation_expected=run['result'].get('consolidacion_beto_contadores') or {}
  files=[];expected_by_file=reading_expected.get('desacuerdos_por_archivo_y_tipo')
  for item in by_file.values():
   expected_count=expected_by_file.get(item['counter_key'],0) if isinstance(expected_by_file,dict) else None
   observed_count=item['verdicts'].get('DESACUERDO',0)
   files.append({'file_id':item['file_id'],'type':item['type'],'individual_verdicts':dict(item['verdicts']),'expected_disagreements':expected_count,
      'observed_proven_disagreements':observed_count,'delta':observed_count-expected_count if expected_count is not None else None,
      'reconciles':expected_count==observed_count and not item['verdicts'].get('UNKNOWN',0)})
  known_counter_keys={item['counter_key'] for item in by_file.values()}
  for counter_key,expected_count in (expected_by_file or {}).items():
   if counter_key in known_counter_keys:continue
   matching_doc=next((d for d in docs.values() if str(d.get('nombre_archivo') or 'sin_archivo')+' | '+str(d.get('tipo_fuente') or 'unknown').upper().strip()==counter_key),{})
   files.append({'file_id':matching_doc.get('hash_sha256') or token(counter_key),'counter_stratum_id':token(counter_key),
     'type':matching_doc.get('tipo_fuente'),'individual_verdicts':{},'expected_disagreements':expected_count,'observed_proven_disagreements':0,
     'delta':-expected_count,'reconciles':False,'warning':'Counter stratum has no traced reading-person observations; no correspondence invented'})
  log_files=[];expected_log_files=consolidation_expected.get('desacuerdos_por_archivo_y_tipo') or {}
  for item in log_by_file.values():
   expected_count=expected_log_files.get(item['counter_key'])
   observed_count=item['verdicts'].get('DESACUERDO',0)
   log_files.append({'file_id':item['file_id'],'type':item['type'],'logged_name_verdicts':dict(item['verdicts']),
     'proven_logged_name_disagreements':observed_count,'expected_productive_person_disagreements':expected_count,
     'unrepresented_counter_observations':expected_count-observed_count if expected_count is not None else None,
     'partial_log_population':True,'reconciled_complete_person_census':False})
  for counter_key,expected_count in expected_log_files.items():
   if counter_key not in {item['counter_key'] for item in log_by_file.values()}:
    log_files.append({'counter_stratum_id':token(counter_key),'proven_logged_name_disagreements':0,
      'expected_productive_person_disagreements':expected_count,'unrepresented_counter_observations':expected_count,
      'partial_log_population':True,'reconciled_complete_person_census':False,'warning':'No logs trace this productive person-counter stratum'})
  census_by_run[run['id']]={'lectura':reconcile_person_census(census['lectura'],reading_expected),'lectura_by_file_type':files,
      'consolidacion':reconcile_person_census(census['consolidacion'],consolidation_expected,partial=True),'consolidacion_by_file_type':log_files,'consolidation_log_rows_seen':logs_seen,
      'scope_warning':'Reading counters are per resolved person. Product acuerdo_beto fields hold an aggregated row verdict. Consolidation logs may omit another disagreeing role and unapproved rows; they do not establish a full person census.'}
 selected=stratified_sample(list(population.values()));stem='f0_desacuerdos' if final else 'f0_desacuerdos_parcial'
 private_path=private/'revision_desacuerdos'/('final.json' if final else 'parcial.json');write(private_path,{'sample':selected,'limitations':limitations,'excluded_non_disagreements':excluded_non_disagreements})
 columns=['case_id','stage','file_id','type','role','config','stratum_id','row_id','source_runs','population_n_h','sample_n_h','seed','technical_label','label_status','basis','recomputed_verdict','individual_product_verdict','individual_verdict_source','human_label','reviewer_id','review_timestamp']
 if selected:
  with (public/(stem+'_muestra.csv')).open('w',newline='',encoding='utf8') as f:
   w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows({k:(json.dumps(r[k]) if k=='source_runs' else r.get(k)) for k in columns} for r in selected)
 strata={}
 for r in selected:
  x=strata.setdefault(r['stratum_id'],{'population':r['population_n_h'],'sample':r['sample_n_h'],'labels':defaultdict(int)})
  x['labels'][r['technical_label']]+=1
 for x in strata.values():x['label_rates']={label:n/x['sample'] for label,n in x['labels'].items()}
 write(public/(stem+'_resumen.json'),{'status':'automatic_technical_suggestions_review_pending','final_population':final,'population':len(population),'sample_size':len(selected),
   'population_definition':'Only individually proven productive DESACUERDO contexts enter this frame. ACUERDO, NO_EVALUABLE, TIPO_DISTINTO and untraceable row-level markers stay outside its false-disagreement denominator. Reading per-person reconstructed verdict and suggested technical diagnosis remain separate. Identical cache/repetition contexts merged with source run IDs retained; consolidation single-name logs establish only partial coverage.',
   'census_by_run':census_by_run,'excluded_non_disagreement_observations':len(excluded_non_disagreements),
   'stages_separate':True,'seed':42,'strata':strata,'weighted_suggested_false_fragmentation_rate_by_stage':{stage:weighted_rate([r for r in selected if r['stage']==stage]) for stage in ('lectura','consolidacion')},'population_by_stage':{stage:sum(r['stage']==stage for r in population.values()) for stage in ('lectura','consolidacion')},'sample_by_stage':{stage:sum(r['stage']==stage for r in selected) for stage in ('lectura','consolidacion')},
   'technical_suggestions_count':len(selected),'manual_technical_reviewed':0,'human_reviewed':0,'human_validation_pending':True,'automatic_technical_inspection':'Automatic recomputation supplies suggested labels only, not completed manual review. Deterministic examination of saved rule name, raw text, exact cached NER spans and tokenizer offset coverage; no fresh inference and no human labels invented.',
   'private_sample_sha256':sha(private_path),'private_sample_path':str(private_path.relative_to(ROOT)) if private_path.is_relative_to(ROOT) else str(private_path),'limitations':limitations,
   'technical_warning':'Consolidation log does not save original per-person rule state; ambiguous mapping remains indeterminate. Technical rates are not independently human validated.'})
 return len(population),len(selected)


def prepare_top1(runs,public=PUBLIC,private=PRIVATE,final=False):
 from scripts.f0_revision_humana import prepare
 return prepare(runs,public,private,final)


def main():
 p=argparse.ArgumentParser();p.add_argument('--gestion',type=int);p.add_argument('--final',action='store_true');p.add_argument('--sellar-top1',action='store_true',help='Seal A4 only after all12 valid a3/a123 sources are complete');p.add_argument('--runs',help='Comma separated complete run IDs for lightweight incremental inspection');args=p.parse_args()
 runs=discover(selected_ids=set(args.runs.split(',')) if args.runs else None,selected_configs={'a3','a123'} if args.sellar_top1 else None)
 if args.sellar_top1:
  summary=prepare_top1(runs,final=True)
  print(json.dumps({'status':summary['status'],'sample_size':summary['sample_size']}));return
 if args.final and len(runs)!=42:raise ValueError('Final analysis requires exactly42 complete immutable valid runs')
 if not runs:print('No complete F0 runs yet; existing pending artifacts preserved');return
 n=impact(runs,args.gestion,final=args.final)
 prepare_top1(runs,final=args.final)
 prepare_disagreements(runs,final=args.final)
 write(PUBLIC/'f0_analisis_avance.json',{'complete_valid_runs':len(runs),'expected':42,'impact_rows':n,'run_ids':[r['id'] for r in runs]})
 if args.final and not json.loads((PUBLIC/'f0_impacto_qc.json').read_text(encoding='utf8'))['kpi_reconciliation_passed']:
  raise ValueError('Final KPI reconciliation failed; inspect f0_impacto_qc.json endpoint_discrepancies')
 print(json.dumps({'complete_runs':len(runs),'impact_rows':n}))
if __name__=='__main__':main()
