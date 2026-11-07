"""Tarea 4: pares de miembros fk_estado='C' (docentes, y estudiantes como referencia) con similitud >= 0,92 entre sí.
Miembros C = personas del lote 1.387 sin candidatos en la dimensión (regla de la corrida final); similitud = max(token_sort, token_set)/100
sobre el nombre sin títulos (la misma que usa el resolver). Además cuenta los C ya existentes en el DW."""
import json, sys, itertools
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import reejecutar_lote_1387_uploads_data as L
from scripts.ablacion_beto import EvaluadorAblacion
from pipeline.normalization.person_resolver import resolver_persona_detalle, cargar_personas_dw, quitar_titulos, _tokens, es_correo, parece_nombre_propio
from rapidfuzz import fuzz
from sqlalchemy import create_engine, text
import os

ev = EvaluadorAblacion()
est, doc = cargar_personas_dw("dim_estudiante"), cargar_personas_dw("dim_docente")
nuevos = {"docente": [], "estudiante": []}
for it in L.cargar_lote_1387_uploads_data():
    toks = it["texto"].split()
    r = ev.parser.procesar_fila(it["texto"])
    ents = [(e.tipo, e.valor) for e in r["entidades"]]
    pa = ev.extraer_spans_bio(toks, [{"tipo": t, "valor": v} for t, v in ents]); pb, pr = ev.inferir_beto_tokens(toks)
    ents += [(e["tipo"], e["valor"]) for e in L._spans_beto(toks, pa, pb, pr)]
    ci = next((v for t, v in ents if t == "CI"), None)
    ctx = [v for t, v in ents if t in ("PROGRAMA", "MODULO", "POS")]; ctx_m = [v for t, v in ents if t == "MODULO"]
    for t, v in ents:
        if t not in ("PER_ESTUDIANTE", "PER_DOCENTE") or es_correo(v):
            continue
        e_ = t == "PER_ESTUDIANTE"
        d = resolver_persona_detalle(v, ci if e_ else None, est if e_ else doc, contexto=ctx, ctx_modulo=ctx_m)
        if d["resultado"] is None and d["motivo"] == "sin_candidatos" and len(_tokens(quitar_titulos(v))) >= 2 and parece_nombre_propio(v):
            nuevos["estudiante" if e_ else "docente"].append(v)

def pares(nombres):
    # un miembro C por nombre canónico distinto (la misma persona repetida en filas = 1 miembro)
    uni = sorted({quitar_titulos(n) for n in nombres})
    out = []
    for a, b in itertools.combinations(uni, 2):
        s = max(fuzz.token_sort_ratio(a, b), fuzz.token_set_ratio(a, b)) / 100.0
        if s >= 0.92:
            out.append((a, b, round(s, 4)))
    return uni, out

res = {}
for k, v in nuevos.items():
    uni, p = pares(v)
    res[k] = {"entidades_C": len(v), "miembros_C_nombres_distintos": len(uni), "pares_similitud_ge_092": len(p), "ejemplos": p[:15], "miembros": uni}
with create_engine(os.environ["DATABASE_URL"]).connect() as c:
    res["miembros_C_ya_en_el_DW"] = {t: c.execute(text(f"select count(*) from {t} where fk_estado='C'")).scalar() for t in ("dim_docente", "dim_estudiante")}
(ROOT / "docs/evidencias/duplicados_estado_c.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk != "ejemplos"} if isinstance(v, dict) and "ejemplos" in v else v) for k, v in res.items()}, ensure_ascii=False, indent=1))
