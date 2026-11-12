import json

with open("docs/evidencias/cobertura.json", "r", encoding="utf-8") as f:
    cov = json.load(f)

tot = cov["totals"]
print("=== COBERTURA GLOBAL ===")
print("Sentencias totales:", tot["num_statements"])
print("Cubiertas:", tot["covered_lines"])
print("Sin cubrir:", tot["missing_lines"])
print("Porcentaje:", f"{tot['percent_covered']:.2f}% ({round(tot['percent_covered'], 1)}%)")

print("\n=== MODULOS SOLICITADOS ===")
files = {k.replace("\\\\", "/").replace("\\", "/"): v for k, v in cov["files"].items()}

print("-- DATAOPS --")
dataops_total_stmts = 0
dataops_total_cov = 0
dataops_total_miss = 0

for k, v in sorted(files.items()):
    if "backend/routers/dataops" in k or "dataops.py" in k:
        s = v["summary"]
        dataops_total_stmts += s["num_statements"]
        dataops_total_cov += s["covered_lines"]
        dataops_total_miss += s["missing_lines"]
        pct = s["percent_covered"]
        print(f"{k}: Stmts={s['num_statements']}, Miss={s['missing_lines']}, Covered={s['covered_lines']}, Pct={pct:.1f}%")

if dataops_total_stmts > 0:
    dataops_pct = (dataops_total_cov / dataops_total_stmts) * 100
    print(f"TOTAL DATAOPS (paquete): Stmts={dataops_total_stmts}, Miss={dataops_total_miss}, Covered={dataops_total_cov}, Pct={dataops_pct:.1f}%")

targets = [
    ("forecasting_holtwinters.py", "pipeline/analytics/forecasting_holtwinters.py"),
    ("forecast_service", "backend/services/forecast_service.py"),
    ("ner_engine", "pipeline/semantic/ner_engine.py"),
    ("dw_loader", "backend/services/dw_loader.py"),
    ("person_resolver", "pipeline/normalization/person_resolver.py")
]

print("\n-- OTROS MODULOS CORE --")
for label, t in targets:
    found = False
    for k, v in files.items():
        if t in k:
            s = v["summary"]
            pct = s["percent_covered"]
            print(f"{label} ({k}): Stmts={s['num_statements']}, Miss={s['missing_lines']}, Covered={s['covered_lines']}, Pct={pct:.1f}%")
            found = True
            break
    if not found:
        print(f"{label}: NO ENCONTRADO")
