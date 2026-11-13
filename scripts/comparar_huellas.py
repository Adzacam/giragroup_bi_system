"""Compara dos huellas de scripts/huella_dw.py (antes/después de un cambio de código sobre la misma entrada).

Uso: python scripts/comparar_huellas.py <huella_base.json> <huella_nueva.json>
Sale con 0 si conteos, md5 por tabla, bandeja y KPI son idénticos; 1 si hay alguna diferencia (y la lista).
"""
import json
import sys
from pathlib import Path


def main(a, b):
    ha, hb = (json.loads(Path(p).read_text(encoding="utf-8")) for p in (a, b))
    dif = []
    for t in sorted(set(ha["tablas"]) | set(hb["tablas"])):
        x, y = ha["tablas"].get(t, {}), hb["tablas"].get(t, {})
        if (x.get("filas"), x.get("md5")) != (y.get("filas"), y.get("md5")):
            dif.append(f"{t}: filas {x.get('filas')} -> {y.get('filas')}, md5 {str(x.get('md5'))[:10]} -> {str(y.get('md5'))[:10]}")
    for k in ("casos", "grupos", "manuales", "casos_manuales", "firma"):
        if ha["bandeja"].get(k) != hb["bandeja"].get(k):
            dif.append(f"bandeja.{k}: {ha['bandeja'].get(k)} -> {hb['bandeja'].get(k)}" if k != "firma" else "bandeja.firma distinta")
    for k in ha.get("kpis", {}):
        if ha["kpis"].get(k) != hb.get("kpis", {}).get(k):
            dif.append(f"{k}: {ha['kpis'].get(k)} -> {hb['kpis'].get(k)}")
    if dif:
        print("DIFERENCIAS:\n  " + "\n  ".join(dif))
        return 1
    print(f"IDÉNTICAS: {len(ha['tablas'])} tablas, bandeja {ha['bandeja']['casos']} casos / {ha['bandeja']['grupos']} grupos, KPI {ha['kpis']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
