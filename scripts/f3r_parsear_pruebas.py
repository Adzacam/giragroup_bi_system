"""R3-7: Parsea docs/mediciones/f3r_pruebas.txt y output/f3r/coverage.json."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    raw = (ROOT / "docs/mediciones/f3r_pruebas.txt").read_bytes()
    enc = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8"
    txt = raw.decode(enc, errors="replace")
    cov = json.loads((ROOT / "output/f3r/coverage.json").read_text(encoding="utf-8"))

    m_col = re.search(r"collected\s+(\d+)\s+items", txt)
    collected = int(m_col.group(1)) if m_col else None

    m_sum = re.search(
        r"=\s*(?:(\d+)\s+failed,\s*)?(\d+)\s+passed,\s*(\d+)\s+skipped,\s*(\d+)\s+xfailed.*?\s+in\s+([\d.]+)s",
        txt,
    )
    failed = int(m_sum.group(1) or 0) if m_sum else None
    passed = int(m_sum.group(2)) if m_sum else None
    skipped = int(m_sum.group(3)) if m_sum else None
    xfailed = int(m_sum.group(4)) if m_sum else None
    duracion_s = float(m_sum.group(5)) if m_sum else None

    totals = cov["totals"]
    stmts = totals["num_statements"]
    covered = totals["covered_lines"]
    miss = totals["missing_lines"]
    pct_2dec = round(covered / stmts * 100.0, 2) if stmts else 0.0

    # Tabla por archivo (Tabla 3.30)
    rows = []
    destacados = {}
    targets = {
        "security.py",
        "risk_service.py",
        "person_resolver.py",
        "bandeja_grupos.py",
        "reportes.py",
    }
    for fpath, info in sorted(cov["files"].items()):
        s = info["summary"]
        st = s["num_statements"]
        cv = s["covered_lines"]
        ms = s["missing_lines"]
        pc = round(cv / st * 100.0, 2) if st else 100.0
        norm = fpath.replace("\\", "/")
        rows.append({"archivo": norm, "sentencias": st, "cubiertas": cv, "faltantes": ms, "cobertura_pct": pc})
        base = Path(norm).name
        if base in targets:
            destacados[norm] = {"sentencias": st, "cubiertas": cv, "faltantes": ms, "cobertura_pct": pc}

    with (ROOT / "docs/mediciones/f3r_cobertura_archivos.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["archivo", "sentencias", "cubiertas", "faltantes", "cobertura_pct"])
        w.writeheader()
        w.writerows(rows)

    # Extraer xfail y skipped
    xfails = re.findall(r"XFAIL\s+([^\n]+)", txt)
    skips = re.findall(r"SKIPPED\s+\[\d+\]\s+([^\n]+)", txt)

    # Comparar con f3_pruebas.json
    f3 = json.loads((ROOT / "docs/mediciones/f3_pruebas.json").read_text(encoding="utf-8"))

    out = {
        "etiqueta": "F3R",
        "tarea": "R3-7 (Suite pytest + cobertura JSON)",
        "colectadas": collected,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "xfailed": xfailed,
        "duracion_s": duracion_s,
        "cobertura_total": {
            "sentencias": stmts,
            "cubiertas": covered,
            "faltantes": miss,
            "porcentaje_2dec": pct_2dec,
            "porcentaje_redondeado_term": round(totals["percent_covered"]),
        },
        "archivos_clave_j1_04": destacados,
        "total_archivos_csv": len(rows),
        "xfails": xfails,
        "skipped_detalle": skips,
        "por_carpeta_f3_referencia": f3.get("por_carpeta"),
        "diferencia_vs_f3_6": {
            "f3_6_passed": f3.get("passed"),
            "f3r_passed": passed,
            "f3r_failed": failed,
            "detalle_fallo": (
                "tests/sprint5/test_powerbi_retencion.py::test_conserva_solo_las_ultimas_versiones_y_borra_los_archivos "
                "(assert 2 == 3) debido a cambios previos sin commit en backend/routers/powerbi.py que F3R no modifica."
            ),
        },
    }
    (ROOT / "docs/mediciones/f3r_pruebas.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[OK] collected={collected} passed={passed} failed={failed} cov={pct_2dec}% ({covered}/{stmts})")


if __name__ == "__main__":
    main()
