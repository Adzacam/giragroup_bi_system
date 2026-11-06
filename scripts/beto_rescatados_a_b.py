"""Tarea 6: registros del lote 1.387 que el parser (A) no resolvió y rescata BETO (A -> B), con las entidades BETO
de cada uno y su presencia en dim_*. Solo lectura. Salida: docs/evidencias/beto_rescatados_a_b.json"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import reejecutar_lote_1387_uploads_data as L
from scripts.ablacion_beto import EvaluadorAblacion

lote = L.cargar_lote_1387_uploads_data()
ev = EvaluadorAblacion()
out, n_a_res = [], 0
for it in lote:
    r = ev.parser.procesar_fila(it["texto"])
    if r["resuelta"]:
        n_a_res += 1
        continue
    toks = it["texto"].split()
    ents = [{"tipo": e.tipo, "valor": e.valor} for e in r["entidades"]]
    pa = ev.extraer_spans_bio(toks, ents)
    pb, pr = ev.inferir_beto_tokens(toks)
    eb = L._spans_beto(toks, pa, pb, pr)
    pres = L._presencia_en_dw([e["valor"] for e in eb]) if eb else {}
    out.append({"archivo": it["archivo"], "hoja": it["hoja"], "fila_origen": it["fila_origen"], "registro": it["registro"],
                "entidades_parser": ents, "entidades_beto": [{**e, "persistida_en_dw": pres.get(e["valor"], [])} for e in eb]})
res = {"total_lote": len(lote), "resueltos_por_A": n_a_res, "rescatados_A_a_B": len(out),
       "con_entidades_beto": sum(1 for o in out if o["entidades_beto"]),
       "con_alguna_entidad_beto_en_dw": sum(1 for o in out if any(e["persistida_en_dw"] for e in o["entidades_beto"])),
       "registros": out}
(ROOT / "docs/evidencias/beto_rescatados_a_b.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print({k: v for k, v in res.items() if k != "registros"})
