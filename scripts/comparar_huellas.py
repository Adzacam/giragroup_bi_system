"""Compara dos bases (clones tras el ciclo) tabla por tabla y fila por fila (por PK), sin nivel_confianza_ia:
filas solo en A, solo en B y filas con la misma PK pero distinto contenido (con las columnas que cambian).
Uso: python scripts/comparar_huellas.py <db_a> <db_b> <salida.json>   (host localhost:5434)"""
import json, sys, collections
from sqlalchemy import create_engine, text

TABLAS = ["fact_costo_programa", "fact_evaluacion_docente", "fact_forecast", "fact_marketing", "fact_rendimiento_academico", "fact_rentabilidad",
          "fact_situacion_financiera", "fact_techo_convenio", "dim_categoria_financiera", "dim_docente", "dim_estudiante", "dim_modulo", "dim_tiempo", "bridge_modulo_docente"]
URL = "postgresql://giragroup_user:giragroup_secret_2026@localhost:5434/{}"
a, b, salida = sys.argv[1:4]
ea, eb = create_engine(URL.format(a)), create_engine(URL.format(b))


def filas(eng, t, pk):
    with eng.connect() as c:
        return {r[0]: r[1] for r in c.execute(text(f"SELECT {pk}::text, (to_jsonb(x) - 'nivel_confianza_ia')::text FROM {t} x"))}


res = {}
for t in TABLAS:
    with ea.connect() as c:
        pk = c.execute(text("SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=i.indkey[0] WHERE i.indrelid=:t::regclass AND i.indisprimary"), {"t": t}).scalar()
    fa, fb = filas(ea, t, pk), filas(eb, t, pk)
    solo_a, solo_b = set(fa) - set(fb), set(fb) - set(fa)
    cambian = [k for k in set(fa) & set(fb) if fa[k] != fb[k]]
    cols = collections.Counter()
    for k in cambian[:5000]:
        ja, jb = json.loads(fa[k]), json.loads(fb[k])
        cols.update(c for c in set(ja) | set(jb) if ja.get(c) != jb.get(c))
    res[t] = {"filas_a": len(fa), "filas_b": len(fb), "solo_en_a": len(solo_a), "solo_en_b": len(solo_b), "cambian": len(cambian), "columnas_que_cambian": dict(cols.most_common(6))}
    print(t, res[t], flush=True)
open(salida, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
