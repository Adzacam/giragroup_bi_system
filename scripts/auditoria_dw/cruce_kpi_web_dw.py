"""ADW L0-3: cruza los 23 KPI visibles en el CMI (web) con bi.vw_cmi_scorecard (CSV adw_l0_kpi.csv).
Uso: python scripts/auditoria_dw/cruce_kpi_web_dw.py <web_kpi.txt con lineas gestion|codigo|estado|valor>"""
import csv, re, sys

def num(s):
    s = s.strip()
    if s in ("—", ""): return None
    mult = 1000 if s.endswith(" mil") else 1_000_000 if s.endswith(" M") else 1
    s = re.sub(r"(Bs|%| mil| M)", "", s).strip()
    s = s.replace(".", "").replace(",", ".") if "," in s or re.fullmatch(r"\d{1,3}(\.\d{3})+", s) else s
    return float(s) * mult

dw = {(r["gestion"], r["codigo"]): r for r in csv.DictReader(open("docs/mediciones/adw_l0_kpi.csv", encoding="utf-8"))}
web = [l.rstrip("\n").split("|") for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
out = []
for g, k, estado, v in web:
    r = dw.get((g, k)); d = float(r["valor"]) if r and r["valor"] != "" else None
    w = num(v)
    if w is None and d is None: res = "IGUAL (ambos sin dato)"
    elif w is None or d is None: res = "DIFIERE (uno sin dato)"
    else:
        tol = max(abs(d) * 0.02, 0.06)
        res = "IGUAL" if abs(w - d) <= tol else "DIFIERE"
    out.append([g, k, estado, v, "" if d is None else d, r["semaforo"] if r else "", res])
with open("docs/mediciones/adw_l0_cruce_kpi_web_dw.csv", "w", newline="", encoding="utf-8") as f:
    w_ = csv.writer(f); w_.writerow(["gestion", "codigo", "estado_web", "valor_web", "valor_dw", "semaforo_dw", "resultado"]); w_.writerows(out)
print(len(out), "filas;", sum(1 for o in out if o[-1].startswith("DIFIERE")), "difieren")
for o in out:
    if o[-1].startswith("DIFIERE"): print(o)
