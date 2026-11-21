"""L6-0: cifras candidatas de KPI-06 desde fact_planificacion_programa (copia tmpfs), solo SELECT.

Regla de pareja (migracion 014 / dw_loader): leads > 0, inscritos entre 0 y leads, mismo registro.
Uso: python -I adw_l6_0_kpi06.py <csv_salida>
"""
import csv
import subprocess
import sys

CONTENEDOR = "adw_pg_tmpfs"
BASE = ["docker", "exec", CONTENEDOR, "psql", "-U", "giragroup_user", "-d", "giragroup_db", "-At", "-F", "|"]

SQL_GESTION = """
SELECT (id_tiempo_plan/10000) AS gestion,
       count(*) FILTER (WHERE leads_fuente IS NOT NULL) AS filas_con_leads,
       count(DISTINCT id_tiempo_plan/100) FILTER (WHERE leads_fuente IS NOT NULL) AS meses_con_leads,
       count(*) FILTER (WHERE leads_fuente>0 AND inscritos_fuente>=0 AND inscritos_fuente<=leads_fuente) AS pares_validos,
       sum(leads_fuente) FILTER (WHERE leads_fuente>0 AND inscritos_fuente>=0 AND inscritos_fuente<=leads_fuente) AS leads_pares,
       sum(inscritos_fuente) FILTER (WHERE leads_fuente>0 AND inscritos_fuente>=0 AND inscritos_fuente<=leads_fuente) AS inscritos_pares,
       sum(reservas_fuente) FILTER (WHERE leads_fuente>0 AND inscritos_fuente>=0 AND inscritos_fuente<=leads_fuente) AS reservas_pares,
       round(100.0*sum(inscritos_fuente) FILTER (WHERE leads_fuente>0 AND inscritos_fuente>=0 AND inscritos_fuente<=leads_fuente)
             / NULLIF(sum(leads_fuente) FILTER (WHERE leads_fuente>0 AND inscritos_fuente>=0 AND inscritos_fuente<=leads_fuente),0),2) AS kpi06_insc_sobre_leads_pct,
       round(100.0*sum(reservas_fuente) FILTER (WHERE leads_fuente>0 AND inscritos_fuente>=0 AND inscritos_fuente<=leads_fuente)
             / NULLIF(sum(leads_fuente) FILTER (WHERE leads_fuente>0 AND inscritos_fuente>=0 AND inscritos_fuente<=leads_fuente),0),2) AS alt_reservas_sobre_leads_pct
FROM public.fact_planificacion_programa
WHERE id_tiempo_plan IS NOT NULL
GROUP BY 1 ORDER BY 1
"""

SQL_HOJA = """
SELECT hoja, count(*) FILTER (WHERE leads_fuente IS NOT NULL) AS filas_leads,
       sum(leads_fuente) AS leads, sum(inscritos_fuente) AS inscritos_todas_filas,
       count(*) FILTER (WHERE leads_fuente>0 AND inscritos_fuente IS NOT NULL) AS filas_con_par
FROM public.fact_planificacion_programa
WHERE leads_fuente IS NOT NULL
GROUP BY 1 ORDER BY min(id_tiempo_plan)
"""


def consulta(sql):
    out = subprocess.run(BASE + ["-c", sql], capture_output=True, text=True, check=True, encoding="utf-8")
    return [l.split("|") for l in out.stdout.splitlines() if l.strip()]


def main(salida):
    filas_g = consulta(SQL_GESTION)
    filas_h = consulta(SQL_HOJA)
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["seccion"] + ["c%d" % i for i in range(10)])
        for r in filas_g:
            w.writerow(["GESTION"] + r)
        for r in filas_h:
            w.writerow(["HOJA"] + r)
    for r in filas_g:
        print("GESTION", r)
    for r in filas_h:
        print("HOJA", r)


if __name__ == "__main__":
    main(sys.argv[1])
