"""Perfila la lectura (paso ③) y la consolidación (paso ④) del flujo DataOps con los 10 archivos del ciclo mensual.

Uso (en giragroup_api, DATABASE_URL = copia aislada con el DW reiniciado; nunca giragroup_db):
    CICLO_FILAS_SIN_FECHA=0 CICLO_SLICES=/tmp/slices_flujo python scripts/perfilar_flujo_dataops.py <carpeta_salida>
Deja perfil_lectura.prof, perfil_consolidacion.prof, top15 de cada uno (tiempo acumulado) y el número de consultas SQL
por línea consolidada, en <carpeta_salida>/perfil.json.
"""
import cProfile
import io
import json
import pstats
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend"), str(ROOT / "scripts")]
import medir_flujo_dataops as flujo  # noqa: E402
import simular_revision as rev  # noqa: E402
from sqlalchemy import event, text  # noqa: E402

BASE = flujo.BASE


class ContadorSQL:
    """Cuenta sentencias SQL por verbo y por tabla principal (primera palabra tras FROM/INTO/UPDATE)."""

    def __init__(self, engine):
        self.engine, self.total, self.por_forma = engine, 0, Counter()

    def _antes(self, conn, cursor, statement, parameters, context, executemany):
        self.total += 1
        s = " ".join(statement.split())[:400].upper()
        verbo = s.split(" ", 1)[0]
        tabla = ""
        for marca in (" FROM ", " INTO ", "UPDATE "):
            if marca in s:
                tabla = s.split(marca, 1)[1].split(" ", 1)[0].strip('"(,')
                break
        self.por_forma[f"{verbo} {tabla}"] += 1

    def __enter__(self):
        self.total, self.por_forma = 0, Counter()
        event.listen(self.engine, "before_cursor_execute", self._antes)
        return self

    def __exit__(self, *a):
        event.remove(self.engine, "before_cursor_execute", self._antes)


def top(prof, n=15):
    s = io.StringIO()
    pstats.Stats(prof, stream=s).sort_stats("cumulative").print_stats(n)
    return s.getvalue()


def top_interno(prof, n=15):
    s = io.StringIO()
    pstats.Stats(prof, stream=s).sort_stats("tottime").print_stats(n)
    return s.getvalue()


def main(salida):
    out = Path(salida)
    out.mkdir(parents=True, exist_ok=True)
    from core.database import SessionLocal, engine
    info = [i for i in flujo.ciclo.construir_slices() if "slice" in i]
    cli = rev.cliente()
    files, tipos, escalas = [], [], []
    for it in info:
        nombre = Path(it["slice"]).name
        files.append(("files", (nombre, open(it["slice"], "rb").read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")))
        tf = flujo.tipo_fuente(nombre)
        tipos.append(tf)
        escalas.append("CENTESIMAL_100" if tf == "ACTA" else "")
    with SessionLocal() as s:
        cache_antes = s.execute(text("SELECT count(*) FROM cache_indice_beto")).scalar()

    res = {"cache_indice_beto_antes": cache_antes}
    # Paso ①: la lectura (paso ③) corre en un hilo de fondo que cProfile no ve; se anula y se ejecuta aquí, en el hilo principal
    from routers.dataops import ingesta, evaluacion
    ingesta._evaluar_lote_en_segundo_plano = lambda *a, **k: None
    t0 = time.perf_counter()
    r = cli.post(f"{BASE}/upload-batch", files=files, data={"tipos_fuente": tipos, "tipos_escala": escalas, "institucion": "GiraGroup Posgrado"})
    res["carga_s"] = round(time.perf_counter() - t0, 2)
    id_lote = r.json().get("id_lote")
    with SessionLocal() as s:
        doc_ids = [x[0] for x in s.execute(text("SELECT id_documento FROM dim_origen_documental WHERE id_lote=:l"), {"l": id_lote})]
        tarea_id = s.execute(text("SELECT id FROM dataops_tarea WHERE id_lote=:l AND tipo='LECTURA_BETO' ORDER BY id DESC LIMIT 1"), {"l": id_lote}).scalar()
    with ContadorSQL(engine) as c:
        pr = cProfile.Profile()
        t0 = time.perf_counter()
        pr.enable()
        evaluacion._evaluar_lote_en_segundo_plano(doc_ids, id_lote, tarea_id)
        pr.disable()
        res["lectura_s"] = round(time.perf_counter() - t0, 2)
    pr.dump_stats(str(out / "perfil_lectura.prof"))
    res["lectura_sql"] = {"total": c.total, "top": c.por_forma.most_common(15)}
    res["lectura_top15_acumulado"] = top(pr)
    res["lectura_top15_propio"] = top_interno(pr)
    with SessionLocal() as s:
        res["lineas"] = s.execute(text("SELECT total FROM dataops_tarea WHERE id_lote=:l AND tipo='LECTURA_BETO' ORDER BY id DESC LIMIT 1"), {"l": id_lote}).scalar()

    # Paso ④
    with ContadorSQL(engine) as c:
        pr = cProfile.Profile()
        t0 = time.perf_counter()
        pr.enable()
        rc = cli.post(f"{BASE}/confirm-dw-insert", json={"id_lote": id_lote, "en_segundo_plano": False})
        pr.disable()
        res["consolidacion_s"] = round(time.perf_counter() - t0, 2)
    pr.dump_stats(str(out / "perfil_consolidacion.prof"))
    res["consolidacion_http"] = rc.status_code
    res["consolidacion_sql"] = {"total": c.total, "por_linea": round(c.total / max(1, res["lineas"] or 1), 2), "top": c.por_forma.most_common(25)}
    res["consolidacion_top15_acumulado"] = top(pr)
    res["consolidacion_top15_propio"] = top_interno(pr)
    with SessionLocal() as s:
        res["cache_indice_beto_despues"] = s.execute(text("SELECT count(*) FROM cache_indice_beto")).scalar()
    res["dw"] = flujo.conteos()
    (out / "perfil.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if "top15" not in k}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main(sys.argv[1])
