import sys,os,collections
sys.path[:0]=['.','scripts']
import reejecutar_lote_1387_uploads_data as L
from scripts.ablacion_beto import EvaluadorAblacion
from pipeline.normalization.person_resolver import *
ev=EvaluadorAblacion(); est=cargar_personas_dw("dim_estudiante"); doc=cargar_personas_dw("dim_docente")
lote=L.cargar_lote_1387_uploads_data()[:1387]
c=collections.Counter(); ej=collections.defaultdict(list)
for it in lote:
    toks=it["texto"].split(); r=ev.parser.procesar_fila(it["texto"])
    ents=[(e.tipo,e.valor) for e in r["entidades"]]
    pa=ev.extraer_spans_bio(toks,[{"tipo":t,"valor":v} for t,v in ents]); pb,pr=ev.inferir_beto_tokens(toks)
    ents+= [(e["tipo"],e["valor"]) for e in L._spans_beto(toks,pa,pb,pr)]
    ci=next((v for t,v in ents if t=="CI"),None)
    for t,v in ents:
        if t not in("PER_ESTUDIANTE","PER_DOCENTE"): continue
        e_=t=="PER_ESTUDIANTE"; d=resolver_persona_detalle(v,ci if e_ else None,est if e_ else doc)
        if d["resultado"] is None:
            n=len(L._tokens(quitar_titulos(v))) if hasattr(L,"_tokens") else 0
            k=("estudiante" if e_ else "docente","1_token" if n<2 else "2+_tokens",d["motivo"]); c[k]+=1
            if len(ej[k])<3: ej[k].append(v)
for k,v in sorted(c.items()): print(k,v,ej[k])
