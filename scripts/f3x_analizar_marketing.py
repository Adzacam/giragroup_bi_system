"""X-3: Compara fact_marketing entre f3u_completo (clon), pre_w14c (viva anterior) y giragroup_db (viva actual)."""
import json
import os
import sys
import psycopg2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DB_F3U = "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55634/giragroup_dw"
DB_PRE = "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55634/pre_w14c"
DB_VIVA = "postgresql://giragroup_user:giragroup_secret_2026@127.0.0.1:5434/giragroup_db"

SQL = """
SELECT
    fm.id_hecho_mkt,
    COALESCE(m.pos_code, '') AS pos_code,
    COALESCE(m.nombre_modulo, '') AS nombre_modulo,
    COALESCE(m.programa, '') AS programa,
    COALESCE(t.periodo_mes, '') AS periodo_mes,
    fm.leads,
    fm.reservas,
    fm.inscritos,
    fm.leads_captacion,
    fm.inscritos_captacion,
    fm.costo_programa
FROM fact_marketing fm
LEFT JOIN dim_modulo m ON m.id_modulo = fm.id_modulo
LEFT JOIN dim_tiempo t ON t.id_tiempo = fm.id_tiempo
ORDER BY fm.id_hecho_mkt
"""


def fetch(dsn):
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            cur.execute("SELECT COUNT(*) FROM dim_modulo")
            n_mod = cur.fetchone()[0]
            return rows, n_mod


def key_of(r):
    return (r["pos_code"], r["nombre_modulo"], r["periodo_mes"])


def main():
    r_f3u, m_f3u = fetch(DB_F3U)
    r_pre, m_pre = fetch(DB_PRE)
    r_viva, m_viva = fetch(DB_VIVA)

    print(f"Conteos: f3u={len(r_f3u)} (mod={m_f3u}), pre_w14c={len(r_pre)} (mod={m_pre}), viva={len(r_viva)} (mod={m_viva})")

    from collections import Counter
    c_f3u = Counter(key_of(r) for r in r_f3u)
    c_pre = Counter(key_of(r) for r in r_pre)
    c_viva = Counter(key_of(r) for r in r_viva)

    print("Diff viva - pre_w14c:", len(list((c_viva - c_pre).elements())), "vs pre - viva:", len(list((c_pre - c_viva).elements())))
    for k in sorted((c_viva - c_pre).keys() | (c_pre - c_viva).keys()):
        print("  viva vs pre:", k, "viva=", c_viva[k], "pre=", c_pre[k])

    print("Diff pre_w14c - f3u:", len(list((c_pre - c_f3u).elements())), "vs f3u - pre:", len(list((c_f3u - c_pre).elements())))
    diff_pre_f3u = sorted((c_pre - c_f3u).keys() | (c_f3u - c_pre).keys())
    print("  claves distintas pre vs f3u:", len(diff_pre_f3u))
    for k in diff_pre_f3u[:30]:
        print("   ", k, "pre=", c_pre[k], "f3u=", c_f3u[k])


if __name__ == "__main__":
    main()
