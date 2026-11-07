"""Tarea 8: una sola cifra BETO. Registros en banda directa con A (parser) y con B (A + rescate BETO), diferencia,
y cuántos registros directos con entidades BETO tienen esas entidades persistidas en dim_*. Solo lectura."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import reejecutar_lote_1387_uploads_data as L
from scripts.ablacion_beto import EvaluadorAblacion, clasificar_banda, BANDA_CONSOLIDADO
from pipeline.semantic.indice_confianza import calcular_indices

lote = L.cargar_lote_1387_uploads_data()
ev = EvaluadorAblacion()
banda_a, resuelta, spans = [], [], []
for it in lote:
    r = ev.parser.procesar_fila(it["texto"])
    banda_a.append(r["banda"]); resuelta.append(bool(r["resuelta"]))
    toks = it["texto"].split()
    pa = ev.extraer_spans_bio(toks, [{"tipo": e.tipo, "valor": e.valor} for e in r["entidades"]])
    pb, pr = ev.inferir_beto_tokens(toks)
    spans.append(L._spans_beto(toks, pa, pb, pr))
idx_resc = [i for i, ok in enumerate(resuelta) if not ok]
conf_b = dict(zip(idx_resc, calcular_indices([lote[i]["texto"] for i in idx_resc]))) if idx_resc else {}
banda_b = [clasificar_banda(conf_b[i]) if i in conf_b else banda_a[i] for i in range(len(lote))]
dir_a = sum(b == BANDA_CONSOLIDADO for b in banda_a)
dir_b = sum(b == BANDA_CONSOLIDADO for b in banda_b)
dir_b_con_beto = [i for i in range(len(lote)) if banda_b[i] == BANDA_CONSOLIDADO and spans[i]]
valores = sorted({s["valor"] for i in dir_b_con_beto for s in spans[i]})
pres = L._presencia_en_dw(valores) if valores else {}
persist = [i for i in dir_b_con_beto if any(pres.get(s["valor"]) for s in spans[i])]
res = {"total": len(lote), "directo_A": dir_a, "directo_B": dir_b, "diferencia_B_menos_A": dir_b - dir_a,
       "pct_directo_A": round(dir_a / len(lote) * 100, 2), "pct_directo_B": round(dir_b / len(lote) * 100, 2),
       "registros_rescatados_por_BETO(A_no_resuelve)": len(idx_resc),
       "registros_directos_B_con_entidades_BETO": len(dir_b_con_beto),
       "entidades_BETO_en_esos_registros": sum(len(spans[i]) for i in dir_b_con_beto),
       "registros_con_entidad_BETO_persistida_en_dim": len(persist),
       "criterio_persistencia": "valor BETO igual (normalizado) a una celda de dim_estudiante.nombre_completo, dim_docente.nombre_completo, dim_modulo.nombre_modulo/programa/pos_code"}
(ROOT / "docs/evidencias/beto_cifra_unica.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
