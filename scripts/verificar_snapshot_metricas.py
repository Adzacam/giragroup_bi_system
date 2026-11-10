"""
Verificación de métricas en snapshot_dw_20261110_1201
"""
import psycopg2

URL = "postgresql://giragroup_user:giragroup_secret_2026@localhost:5434/snapshot_dw_20261110_1201"
conn = psycopg2.connect(URL)
cur = conn.cursor()

print("--- REVISIÓN DE PERSONAS Y TABLAS ---")
cur.execute("SELECT count(*), count(DISTINCT ci_numero), count(DISTINCT nombre_completo) FROM dim_estudiante")
print("dim_estudiante (total, ci distintos, nombres distintos):", cur.fetchone())

cur.execute("SELECT count(*), count(DISTINCT id_estudiante) FROM fact_rendimiento_academico")
print("fact_rendimiento_academico (filas, estudiantes distintos):", cur.fetchone())

cur.execute("SELECT count(*), count(DISTINCT id_estudiante) FROM fact_situacion_financiera")
print("fact_situacion_financiera (filas, estudiantes distintos):", cur.fetchone())

print("\n--- STAGING PENDIENTE ---")
cur.execute("""
    SELECT motivo, estado_resolucion, count(*) 
    FROM stg_entidad_no_resuelta 
    WHERE resuelto = false 
    GROUP BY motivo, estado_resolucion;
""")
print("Staging pendiente:", cur.fetchall())

print("\n--- STAGING TOTAL ---")
cur.execute("""
    SELECT motivo, estado_resolucion, resuelto, count(*) 
    FROM stg_entidad_no_resuelta 
    GROUP BY motivo, estado_resolucion, resuelto
    ORDER BY count(*) DESC;
""")
for r in cur.fetchall():
    print(r)

print("\n--- CONFLICTO DE PRECEDENCIA MARZO 2025 ---")
cur.execute("""
    SELECT c.nombre_categoria, fr.monto_ejecutado, dt.periodo_mes
    FROM fact_rentabilidad fr
    JOIN dim_categoria_financiera c ON c.id_categoria = fr.id_categoria
    JOIN dim_tiempo dt ON dt.id_tiempo = fr.id_tiempo
    WHERE dt.periodo_mes = '2025-03';
""")
print("Marzo 2025 en fact_rentabilidad:", cur.fetchall())

cur.execute("""
    SELECT * FROM log_inconsistencias 
    WHERE campo_afectado = 'fact_rentabilidad.monto_ejecutado' 
       OR descripcion LIKE '%2025-03%' 
       OR descripcion LIKE '%PROGRAMAS%';
""")
print("Logs de inconsistencia marzo 2025:", cur.fetchall())

print("\n--- BI.REF_KPI ---")
cur.execute("SELECT count(*) FROM bi.ref_kpi;")
print("Total bi.ref_kpi:", cur.fetchone()[0])
cur.execute("SELECT id_kpi, codigo, nombre_kpi, perspectiva, formula, tabla_origen FROM bi.ref_kpi ORDER BY id_kpi;")
for r in cur.fetchall():
    print(r)

print("\n--- DIM_META Y FACT_RENTABILIDAD.MONTO_META ---")
cur.execute("SELECT count(*) FROM dim_meta;")
print("dim_meta count:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM fact_rentabilidad WHERE monto_meta IS NOT NULL;")
print("fact_rentabilidad con monto_meta no nulo:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM ref_metas_gestion;")
print("ref_metas_gestion count:", cur.fetchone()[0])
