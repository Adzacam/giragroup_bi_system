"""
Tarea 5: tiempo de un ciclo mensual típico (filas de UN mes de cada archivo, no el histórico), en CPU.
1) Construye en <salida>/slices/ una copia de cada xlsx de uploads/data con solo las filas del mes (hojas con columna
   de fecha); las hojas sin fecha y de <= 100 filas (catálogos/criterios) se copian completas; las demás sin fecha se omiten.
2) Procesa cada slice con /api/v1/pipeline/process (TestClient en proceso, DB indicada por DATABASE_URL = clon del DW)
   y suma tiempos por etapa (response.tiempos_etapa_ms). Escribe docs/evidencias/tiempos_ciclo_mensual.json
Uso: DATABASE_URL=<clon> python scripts/medir_ciclo_mensual.py [AAAA-MM]
"""
import json, sys, time, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
MES = sys.argv[1] if len(sys.argv) > 1 else "2026-03"
SALIDA = ROOT / "docs" / "evidencias" / "ciclo_mensual_slices"
SALIDA.mkdir(parents=True, exist_ok=True)
(ROOT / "docs" / "evidencias").mkdir(parents=True, exist_ok=True)
EXCLUIR = ()  # sin exclusiones: se mide también [BBDD] ANTIGUO RESPUESTAS (procesado al final)
FILAS_SIN_FECHA = 300  # hojas grandes sin columna de fecha: primeras N filas como muestra del ciclo


def col_fecha(df):
    mejor, n_mejor = None, 0
    for c in df.columns:
        s = df[c]
        if pd.api.types.is_datetime64_any_dtype(s):
            t = s
        elif re.search(r"fecha|marca temporal|mes|date", str(c), re.I) and s.dtype == object:
            t = pd.to_datetime(s, errors="coerce")
        else:
            continue
        t = t[(t.dt.year >= 2022) & (t.dt.year <= 2026)] if hasattr(t, "dt") else t
        if t.notna().sum() > n_mejor:
            mejor, n_mejor = c, int(t.notna().sum())
    return mejor if n_mejor >= 20 else None


def construir_slices():
    info = []
    for f in sorted((ROOT / "uploads" / "data").glob("*.xlsx"), key=lambda q: ("ANTIGUO" in q.name, q.name)):
        if any(k in f.name for k in EXCLUIR):
            info.append({"archivo": f.name, "omitido": "cuelga el pipeline (>30 min) - fuera de la medición"})
            continue
        hojas = pd.read_excel(f, sheet_name=None)
        out, det = {}, []
        for h, df in hojas.items():
            c = col_fecha(df)
            if c is not None:
                t = pd.to_datetime(df[c], errors="coerce")
                sel = df[t.dt.strftime("%Y-%m") == MES]
                mes_usado = MES
                if sel.empty:  # sin filas en el mes pedido: mes más frecuente de los últimos 12 de la hoja
                    ult = t[t >= t.max() - pd.DateOffset(months=12)].dt.strftime("%Y-%m").value_counts()
                    if len(ult):
                        mes_usado = ult.index[0]
                        sel = df[t.dt.strftime("%Y-%m") == mes_usado]
                if not sel.empty:
                    out[h] = sel
                    det.append({"hoja": h, "columna_fecha": str(c), "mes": mes_usado, "filas": len(sel)})
            elif len(df) <= 100:
                out[h] = df
                det.append({"hoja": h, "columna_fecha": None, "mes": None, "filas": len(df), "completa": True})
            else:
                out[h] = df.head(FILAS_SIN_FECHA)
                det.append({"hoja": h, "columna_fecha": None, "mes": None, "filas": min(len(df), FILAS_SIN_FECHA), "muestra_primeras_filas": True})
        if out:
            dest = SALIDA / f.name
            with pd.ExcelWriter(dest) as w:
                for h, df in out.items():
                    df.to_excel(w, sheet_name=h[:31], index=False)
            info.append({"archivo": f.name, "slice": str(dest), "hojas": det, "filas_total": int(sum(len(d) for d in out.values()))})
        else:
            info.append({"archivo": f.name, "hojas": det, "omitido": "sin filas"})
    return info


def main():
    info = construir_slices()
    from fastapi.testclient import TestClient
    try:
        from backend.main import app  # host
    except ImportError:
        from main import app  # dentro del contenedor giragroup_api (/app = backend)
    from core.security import get_current_user
    from models.user import User
    app.dependency_overrides[get_current_user] = lambda: User(id=2, username="auditor", email="a@giragroup.bo", role="AUDITOR_CALIDAD", is_active=True)
    cli = TestClient(app)
    tot = {"lectura_e_ingesta": 0.0, "reglas_y_resto": 0.0, "beto": 0.0, "carga_dw": 0.0}
    t_global = time.perf_counter()
    for it in info:
        if "slice" not in it:
            continue
        t0 = time.perf_counter()
        with open(it["slice"], "rb") as fh:
            r = cli.post("/api/v1/pipeline/process", files={"file": (Path(it["slice"]).name, fh)})
        it["http"] = r.status_code
        it["segundos"] = round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            j = r.json()
            it["tiempos_etapa_ms"] = j.get("tiempos_etapa_ms")
            it["filas_procesadas"] = j.get("total_filas_procesadas")
            it["hechos_cargados_dw"] = j.get("hechos_cargados_dw")
            for k in tot:
                tot[k] += (j.get("tiempos_etapa_ms") or {}).get(k, 0.0)
        else:
            it["error"] = r.text[:300]
        print(it["archivo"], it.get("http"), it.get("segundos"), it.get("tiempos_etapa_ms"), flush=True)
    res = {"mes_objetivo": MES, "cpu": "BETO en el contenedor giragroup_pipeline (docker-compose.yml, sin GPU)",
           "tiempo_total_s": round(time.perf_counter() - t_global, 2),
           "suma_etapas_ms": {k: round(v, 1) for k, v in tot.items()}, "archivos": info}
    (ROOT / "docs" / "evidencias" / "tiempos_ciclo_mensual.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "archivos"}, indent=1))


if __name__ == "__main__":
    main()
