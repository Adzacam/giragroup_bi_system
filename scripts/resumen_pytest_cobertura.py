"""Resumen por suite (junit) y cobertura de líneas por archivo (coverage json). Escribe docs/evidencias/pytest_por_suite_y_cobertura.json"""
import json, collections
import xml.etree.ElementTree as ET
from pathlib import Path
E = Path(__file__).resolve().parent.parent / "docs" / "evidencias"
def suite(cn):
    p = cn.split(".")
    if len(p) > 1 and p[1] in ("sprint1", "sprint2", "sprint3", "sprint4", "readiness", "load"): return p[1]
    if "test_sprint4_verification_loops" in cn: return "loops"
    return "transversales"
c = collections.defaultdict(lambda: collections.Counter())
for tc in ET.parse(E / "pytest_junit.xml").getroot().iter("testcase"):
    s = suite(tc.get("classname", ""))
    k = "fallidas" if (tc.find("failure") is not None or tc.find("error") is not None) else ("omitidas" if tc.find("skipped") is not None else "pasadas")
    # xfail aparece como skipped con type pytest.xfail
    sk = tc.find("skipped")
    if sk is not None and "xfail" in (sk.get("type") or "") + (sk.get("message") or "").lower(): k = "xfail"
    c[s][k] += 1; c[s]["pruebas"] += 1
cov = json.loads((E / "cobertura.json").read_text(encoding="utf-8"))
objetivo = {"security": "backend/core/security.py", "ingestion_service": "backend/services/ingestion_service.py", "fk_resolver": "pipeline/normalization/fk_resolver.py",
            "fuzzy_normalizer": "pipeline/normalization/fuzzy_normalizer.py", "person_resolver": "pipeline/normalization/person_resolver.py",
            "alert_engine": "backend/services/alert_engine.py", "financial_rules_engine": "backend/services/financial_rules_engine.py", "risk_service": "backend/services/risk_service.py",
            "forecasting_holtwinters": "pipeline/analytics/forecasting_holtwinters.py", "forecasting_ols": "pipeline/analytics/forecasting_ols.py",
            "forecast_service": "backend/services/forecast_service.py", "kpi_service": "backend/services/kpi_service.py", "reportes": "backend/routers/reportes.py", "dataops": "backend/routers/dataops.py"}
files = {k.replace("\\", "/"): v for k, v in cov["files"].items()}
cob = {}
for n, f in objetivo.items():
    v = files.get(f)
    cob[n] = {"archivo": f, "lineas": v["summary"]["num_statements"], "cubiertas": v["summary"]["covered_lines"], "pct": round(v["summary"]["percent_covered"], 1)} if v else None
t = cov["totals"]
out = {"por_suite": {k: dict(v) for k, v in sorted(c.items())}, "cobertura_por_archivo": cob,
       "cobertura_global": {"lineas": t["num_statements"], "cubiertas": t["covered_lines"], "pct": round(t["percent_covered"], 1), "alcance": "--cov=backend --cov=pipeline"}}
(E / "pytest_por_suite_y_cobertura.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
