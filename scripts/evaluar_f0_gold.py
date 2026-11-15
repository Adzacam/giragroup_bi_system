"""F0 B-3: existing A/B/C evaluator plus reproducible span counts and 1:1 matching.
No DB connections, training, dataset changes or text exports.
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
TYPES=('PER_ESTUDIANTE','PER_DOCENTE','MODULO','PROGRAMA')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def spans_iob2(tags):
    """Strict IOB2: an orphan I or a type-changing I does not start an entity."""
    spans=[]; current=None
    for i,tag in enumerate(list(tags)+['O']):
        if current is not None and tag!='I-'+current[0]:
            spans.append((current[0],current[1],i)); current=None
        if tag.startswith('B-') and tag[2:] in TYPES: current=(tag[2:],i)
    return spans

def match(gold,pred,relaxed=False):
    """Maximum-cardinality bipartite matching, deterministic traversal in span order."""
    edges={i:[j for j,p in enumerate(pred) if g[0]==p[0] and ((max(g[1],p[1])<min(g[2],p[2])) if relaxed else g[1:]==p[1:])] for i,g in enumerate(gold)}
    assigned={}
    def augment(i,seen):
        for j in edges[i]:
            if j in seen: continue
            seen.add(j)
            if j not in assigned or augment(assigned[j],seen): assigned[j]=i; return True
        return False
    for i in range(len(gold)): augment(i,set())
    return sorted((i,j) for j,i in assigned.items())

def metrics(tp,fp,fn):
    p=tp/(tp+fp) if tp+fp else None; r=tp/(tp+fn) if tp+fn else None
    f=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None
    return {'tp':tp,'fp':fp,'fn':fn,'precision':p,'recall':r,'f1':f,'support':tp+fn,'predicted':tp+fp}

def validate_provenance(metadata, prediction_path, root=ROOT):
    if metadata.get('status') != 'complete':
        raise ValueError('Prediction provenance was not completed')
    model_dir=root/'pipeline/semantic/beto_local'
    if {p.name for p in model_dir.iterdir() if p.is_file()} != set(metadata['model_files']):
        raise ValueError('Provenance model file inventory mismatch')
    checks = [(root/'data/test_gold_real.jsonl', metadata['gold_sha256']),
              (prediction_path, metadata['predictions_sha256']),
              (root/'scripts/ablacion_beto.py', metadata['evaluator_sha256'])]
    checks += [(root/'pipeline/semantic/beto_local'/name, info['sha256'])
               for name,info in metadata['model_files'].items()]
    for path, expected in checks:
        if sha(path) != expected:
            raise ValueError('Provenance hash mismatch: '+path.name)

def run(out, from_predictions=None):
    # Explicit, local-only measurement flags. Do not inherit int8 or download weights.
    os.environ['BETO_INT8']='0'; os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
    from scripts import ablacion_beto as legacy
    import torch,transformers
    original=legacy.classification_report
    captured=[]
    def capture(g,p,**kw):
        captured.append((g,p)); return original(g,p,**kw)
    legacy.classification_report=capture
    if from_predictions:
        from types import SimpleNamespace
        from transformers import BertTokenizerFast
        evaluator=SimpleNamespace(tokenizer=BertTokenizerFast.from_pretrained(str(ROOT/'pipeline/semantic/beto_local'),local_files_only=True))
        saved=json.loads(from_predictions.read_text(encoding='utf8'))
    else:
        evaluator=legacy.EvaluadorAblacion()
    gold_path=ROOT/'data/test_gold_real.jsonl'
    records=[json.loads(s) for s in gold_path.read_text(encoding='utf8').splitlines() if s.strip()]
    metadata={'timestamp':datetime.now(ZoneInfo('America/La_Paz')).isoformat(),'seed':42,'gold_sha256':sha(gold_path),
      'script_sha256':sha(Path(__file__)),'evaluator_sha256':sha(ROOT/'scripts/ablacion_beto.py'),
      'model_files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted((ROOT/'pipeline/semantic/beto_local').glob('*')) if p.is_file()},
      'device':'cpu','threads':torch.get_num_threads(),'torch':torch.__version__,'transformers':transformers.__version__,'BETO_INT8':'0','max_tokens':128,
      'strict':'same type and exact half-open token span, strict IOB2 (orphan I does not start entity)',
      'relaxed':'same type and overlap of at least one token; maximum-cardinality bipartite matching per line; each gold and prediction used at most once; deterministic ordered DFS augmentation',
      'legacy_warning':'Legacy strict report uses seqeval default mode, not explicit strict IOB2. Legacy relaxed uses any-overlap per gold without reserving prediction. Auxiliary counts below are the F0 reference.'}
    out.mkdir(parents=True,exist_ok=True)
    provenance_path=out/'f0_b3_procedencia.json'
    if from_predictions:
        source_path=from_predictions.parent/'f0_b3_procedencia.json'
        source=json.loads(source_path.read_text(encoding='utf8'))
        validate_provenance(source,from_predictions)
        metadata=dict(source)
        metadata['recovery']={'timestamp':datetime.now(ZoneInfo('America/La_Paz')).isoformat(),
                              'collector_script_sha256':sha(Path(__file__)),
                              'source_sidecar_sha256':sha(source_path),'reinference':False}
    else:
        metadata['status']='inference_pending'
        provenance_path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    result={'status':'measured','metadata':metadata,'por_modo':{}}; predictions=[]; rows=[]
    for mode in ('A','B','C'):
        if from_predictions:
            legacy_result={'status':'not recomputed during recovery; consult original inference report'}
            mode_records=next(r['lines'] for r in saved if r['mode']==mode)
            if len(mode_records)!=len(records): raise ValueError('Incomplete prediction population')
            for i,(rec,gold) in enumerate(zip(mode_records,records),1):
                if rec['line_id']!=i or rec['gold']!=[list(s) for s in spans_iob2(gold['tags'])]:
                    raise ValueError('Prediction gold IDs/spans do not match dataset')
                rec['matches']={name:match(rec['gold'],rec['prediction'],rel)
                                for name,rel in [('strict',False),('relaxed',True)]}
        else:
            legacy_result=evaluator.evaluar_dataset_gold(str(gold_path),mode)
            gs,ps=captured.pop()
            mode_records=[]
            for i,(g,p) in enumerate(zip(gs,ps),1):
                gsp=spans_iob2(g); psp=spans_iob2(p)
                rec={'line_id':i,'gold':gsp,'prediction':psp,'matches':{}}
                for name,rel in [('strict',False),('relaxed',True)]: rec['matches'][name]=match(gsp,psp,rel)
                mode_records.append(rec)
        for name in ('strict','relaxed'):
            tp=sum(len(r['matches'][name]) for r in mode_records); ng=sum(len(r['gold']) for r in mode_records); np=sum(len(r['prediction']) for r in mode_records)
            met=metrics(tp,np-tp,ng-tp); per_type={}
            for typ in TYPES:
                t=sum(sum(r['gold'][i][0]==typ for i,j in r['matches'][name]) for r in mode_records)
                g=sum(sum(s[0]==typ for s in r['gold']) for r in mode_records); p=sum(sum(s[0]==typ for s in r['prediction']) for r in mode_records)
                per_type[typ]=metrics(t,p-t,g-t)
            rows.append({'mode':mode,'criterion':name,**met})
            result['por_modo'].setdefault(mode,{})[name]={**met,'by_type':per_type}
        result['por_modo'][mode]['legacy']=legacy_result
        predictions.append({'mode':mode,'lines':mode_records})
        print('completed',mode,flush=True)
    full=Counter(); visible=Counter(); lost=[]; partial=[]
    for i,r in enumerate(records,1):
        tags=r['tags']; spans=spans_iob2(tags); full.update(s[0] for s in spans)
        enc=evaluator.tokenizer(r['tokens'],is_split_into_words=True,truncation=True,max_length=128)
        ids=[w for w in enc.word_ids() if w is not None]; n=max(ids)+1 if ids else 0
        vis=spans_iob2(tags[:n]); visible.update(s[0] for s in vis)
        for typ,start,end in spans:
            item={'line_id':i,'type':typ,'start_token':start,'end_token':end,'visible_word_count':n,'total_words':len(tags)}
            if start>=n: lost.append(item)
            elif end>n: partial.append(item)
    reconciliation={'status':'503_not_reproduced',
      'gold_sha256':metadata['gold_sha256'],'records':len(records),'full_gold_support':sum(full.values()),'full_by_type':dict(full),
      'visible_128_support':sum(visible.values()),'visible_by_type':dict(visible),'fully_omitted_entities':lost,'partially_truncated_entities':partial,
      'definition':'510 counts full saved token annotations. With the current tokenizer all 510 are also visible within 128 tokens; truncation does not explain 503. No source with a reproducible seven-ID exclusion policy was found. Historical 503 reconciliation remains pending.',
      'ids':'1-based nonempty JSONL line IDs, zero-based half-open saved-token spans'}
    out.mkdir(parents=True,exist_ok=True)
    pp=out/'f0_b3_predicciones.json'
    if not from_predictions:
        pp.write_text(json.dumps(predictions,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    metadata['predictions_sha256']=sha(pp)
    if not from_predictions:
        metadata['status']='complete'
        validate_provenance(metadata,pp)
        provenance_path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (out/'f0_b3_ablacion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=lambda v:v.item())+'\n',encoding='utf8')
    (out/'f0_b3_conteos.json').write_text(json.dumps(reconciliation,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with (out/'f0_b3_ablacion.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    md=['# F0 B-3 — conciliación de soporte','',f"Gold completo: **{sum(full.values())}** entidades; gold visible a 128 WordPiece: **{sum(visible.values())}**. Entidades completamente fuera de ventana: **{len(lost)}**; parcialmente truncadas: **{len(partial)}**.",'',reconciliation['definition'],'','La evaluación auxiliar conserva toda la población gold y las predicciones del evaluador vigente. Publica seis filas A/B/C × estricto/relajado, con matching 1:1; no reutiliza predicciones para acreditar dos gold. El estricto usa IOB2 explícito. Los reportes heredados están separados porque seqeval se invoca sin modo estricto y su relajado no garantiza biyección.','', 'No se modificó gold, modelo, umbrales ni longitud. Soporte por tipo: [f0_b3_conteos.json](f0_b3_conteos.json). Spans y enlaces 1:1 sin texto: [f0_b3_predicciones.json](f0_b3_predicciones.json). No existen siete IDs demostrables para justificar 503; B-3 permanece parcialmente pendiente.', '', 'Se ejecutó localmente sobre CPU, en ventana exclusiva coordinada, con pesos/tokenizador locales y descargas desactivadas. No se conectó a ninguna base ni se inició entrenamiento. Resultados: [JSON](f0_b3_ablacion.json), [CSV](f0_b3_ablacion.csv).']
    (out/'f0_b3_conciliacion.md').write_text('\n'.join(md)+'\n',encoding='utf8')
    print(json.dumps({'rows':rows,'full_support':sum(full.values()),'visible_support':sum(visible.values())}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,default=ROOT/'docs/mediciones'); p.add_argument('--from-predictions',type=Path); args=p.parse_args(); run(args.output,args.from_predictions)
