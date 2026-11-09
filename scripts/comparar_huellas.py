"""Compara dos bases (clones tras el ciclo) tabla por tabla con el contenido en claves naturales (no en ids seriales):
los ids se sustituyen por el módulo (pos_code|nombre), el estudiante (ci_numero|nombre), el docente (nombre) y la fecha; se omiten la PK serial,
las marcas de tiempo (created_at, actualizado_en) y nivel_confianza_ia. Se comparan como multiconjuntos de filas.
Uso: python scripts/comparar_huellas.py <db_a> <db_b> <salida.json>   (host localhost:5434)"""
import collections, json, sys
from sqlalchemy import create_engine, text

URL = "postgresql://giragroup_user:giragroup_secret_2026@localhost:5434/{}"
OMITIR = {"nivel_confianza_ia", "created_at", "actualizado_en", "id_documento"}
SUST = {  # columna id -> expresión SQL (alias x = la fila) que da su clave natural
    "id_modulo": "(SELECT coalesce(m.pos_code,'')||'|'||coalesce(m.nombre_modulo,'') FROM dim_modulo m WHERE m.id_modulo = x.id_modulo)",
    "id_estudiante": "(SELECT coalesce(e.ci_numero,'')||'|'||coalesce(e.nombre_completo,'') FROM dim_estudiante e WHERE e.id_estudiante = x.id_estudiante)",
    "id_docente": "(SELECT d.nombre_completo FROM dim_docente d WHERE d.id_docente = x.id_docente)",
    "id_tiempo": "(SELECT t.fecha::text FROM dim_tiempo t WHERE t.id_tiempo = x.id_tiempo)",
    "id_categoria": "(SELECT c.nombre_categoria FROM dim_categoria_financiera c WHERE c.id_categoria = x.id_categoria)",
}
TABLAS = ["fact_costo_programa", "fact_evaluacion_docente", "fact_forecast", "fact_marketing", "fact_rendimiento_academico", "fact_rentabilidad",
          "fact_situacion_financiera", "fact_techo_convenio", "dim_categoria_financiera", "dim_docente", "dim_estudiante", "dim_modulo", "bridge_modulo_docente"]
a, b, salida = sys.argv[1:4]
ea, eb = create_engine(URL.format(a)), create_engine(URL.format(b))


def contenido(eng, t):
    with eng.connect() as c:
        cols = [r[0] for r in c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=:t ORDER BY ordinal_position"), {"t": t})]
        pk = c.execute(text("SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=i.indkey[0] WHERE i.indrelid=CAST(:t AS regclass) AND i.indisprimary"), {"t": t}).scalar()
        sel = ", ".join(f"{SUST.get(k, 'x.' + k)}::text AS {k}" for k in cols if k != pk and k not in OMITIR)
        filas = [tuple(r) for r in c.execute(text(f"SELECT {sel} FROM {t} x"))]
        return [k for k in cols if k != pk and k not in OMITIR], collections.Counter(filas)


res = {}
for t in TABLAS:
    cols, ca = contenido(ea, t)
    _, cb = contenido(eb, t)
    solo_a, solo_b = ca - cb, cb - ca
    diff_cols = collections.Counter()
    # columnas en las que difieren las filas sobrantes (comparación heurística: primeras 300 de cada lado por clave natural más selectiva)
    la, lb = list(solo_a.elements())[:300], list(solo_b.elements())[:300]
    for ra in la:
        mejor = max(lb, key=lambda rb: sum(1 for x, y in zip(ra, rb) if x == y), default=None)
        if mejor:
            diff_cols.update(cols[i] for i, (x, y) in enumerate(zip(ra, mejor)) if x != y)
    res[t] = {"filas_a": sum(ca.values()), "filas_b": sum(cb.values()), "solo_en_a": sum(solo_a.values()), "solo_en_b": sum(solo_b.values()),
              "columnas_que_difieren_(muestra)": dict(diff_cols.most_common(6))}
    print(t, res[t], flush=True)
open(salida, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
