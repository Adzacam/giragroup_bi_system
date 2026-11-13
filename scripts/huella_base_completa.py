"""Huella de TODAS las tablas del esquema public de una base (conteo y md5 de las filas ordenadas). Solo SELECT; no importa la aplicación.

Sirve para comprobar que la copia aislada es idéntica al snapshot y que el snapshot no cambió.
Uso: python scripts/huella_base_completa.py <url_postgresql> <salida.json>
"""
import hashlib
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


def main(url, salida):
    eng = create_engine(url)
    out = {}
    with eng.connect() as c:
        tablas = [r[0] for r in c.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY 1"))]
        for t in tablas:
            cols = [r[0] for r in c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=:t ORDER BY ordinal_position"), {"t": t})]
            lista = ", ".join(f'"{k}"::text' for k in cols)
            h, n = hashlib.md5(), 0
            for fila in c.execution_options(stream_results=True).execute(text(f'SELECT {lista} FROM public."{t}" ORDER BY {lista}')):
                h.update(("|".join("" if v is None else v for v in fila) + "\n").encode("utf-8"))
                n += 1
            out[t] = {"filas": n, "md5": h.hexdigest()}
    Path(salida).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out)} tablas, {sum(v['filas'] for v in out.values())} filas, md5 global {hashlib.md5(json.dumps(out, sort_keys=True).encode()).hexdigest()}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
