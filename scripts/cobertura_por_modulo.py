"""Ronda 10, tarea 1: cobertura por archivo clave y ponderada por modulo funcional (cubiertas / sentencias) desde docs/evidencias/cobertura.json
(una sola corrida de pytest --cov=backend --cov=pipeline). Escribe docs/evidencias/cobertura_por_modulo.json"""
import json
from pathlib import Path
E = Path(__file__).resolve().parent.parent / "docs" / "evidencias"
cov = json.loads((E / "cobertura.json").read_text(encoding="utf-8"))
files = {k.replace("\\", "/"): v["summary"] for k, v in cov["files"].items()}
MODULOS = {
    "Infraestructura y RBAC": ["backend/core/security.py"],
    "Ingesta": ["backend/services/ingestion_service.py"],
    "PLN y resolucion": ["pipeline/semantic/ner_engine.py", "pipeline/semantic/indice_confianza.py", "backend/services/confianza_service.py",
                         "pipeline/normalization/fk_resolver.py", "pipeline/normalization/fuzzy_normalizer.py", "pipeline/normalization/person_resolver.py"],
    "API, alertas y pronostico": ["backend/services/dw_loader.py", "backend/routers/pipeline.py", "backend/services/alert_engine.py",
                                  "backend/services/financial_rules_engine.py", "backend/services/risk_service.py", "pipeline/analytics/forecasting_holtwinters.py",
                                  "pipeline/analytics/forecasting_ols.py", "backend/services/forecast_service.py"],
    "Plataforma, CMI y HITL": ["backend/routers/dataops.py", "backend/services/bandeja_grupos.py", "backend/services/revision_hechos.py",
                               "backend/services/kpi_service.py", "backend/routers/reportes.py"],
}
out, tot_s, tot_c = {}, 0, 0
for m, lst in MODULOS.items():
    filas, s, c = [], 0, 0
    for f in lst:
        v = files.get(f)
        if v is None:
            filas.append({"archivo": f, "error": "no esta en cobertura.json"}); continue
        filas.append({"archivo": f, "sentencias": v["num_statements"], "no_cubiertas": v["missing_lines"], "pct": round(v["percent_covered"], 1)})
        s += v["num_statements"]; c += v["covered_lines"]
    out[m] = {"archivos": filas, "sentencias": s, "cubiertas": c, "pct_ponderado": round(c / s * 100, 1)}
    tot_s += s; tot_c += c
t = cov["totals"]
res = {"modulos": out, "claves_total": {"sentencias": tot_s, "cubiertas": tot_c, "pct": round(tot_c / tot_s * 100, 1)},
       "global": {"sentencias": t["num_statements"], "cubiertas": t["covered_lines"], "pct": round(t["percent_covered"], 1), "alcance": "--cov=backend --cov=pipeline"}}
(E / "cobertura_por_modulo.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
for m, v in out.items():
    print(f"\n{m}: {v['cubiertas']}/{v['sentencias']} = {v['pct_ponderado']} %")
    for f in v["archivos"]:
        print(f"   {f['archivo']:55s} {f.get('sentencias')} sent, {f.get('no_cubiertas')} sin cubrir, {f.get('pct')} %")
print("\nclaves:", res["claves_total"], "global:", res["global"])
