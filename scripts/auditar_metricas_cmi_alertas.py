"""
Auditoría completa de métricas para la Fuente de Verdad de la Tesis.
Snapshot: snapshot_dw_20261110_1201
"""
import sys
import os
import json
import psycopg2
from collections import Counter
import numpy as np

sys.path.insert(0, '.')
sys.path.insert(0, 'backend')
os.environ['DATABASE_URL'] = 'postgresql://giragroup_user:giragroup_secret_2026@localhost:5434/snapshot_dw_20261110_1201'
from core.database import SessionLocal
from services.kpi_service import KPIService
from services.risk_service import evaluar_alertas_tempranas_deterministicas, get_riesgo_cruzado

db = SessionLocal()
srv_kpi = KPIService(db)

print("="*60)
print("1. CMI 11 KPIS")
print("="*60)
for g in [2025, None]:
    print(f"\n--- GESTION: {g} ---")
    res = srv_kpi.obtener_perspectivas_cmi_completo(gestion=g)
    kpis = res['kpis']
    for k in sorted(kpis.keys()):
        val = kpis[k]
        if isinstance(val, dict):
            desg = val.get("desglose", [])
            print(f"  {k}: {val.get('valor')} (desglose {len(desg)} items)")
            for item in desg[:3]:
                print(f"      - {item}")
        else:
            print(f"  {k}: {val}")

print("\n" + "="*60)
print("2. REGLAS DE ALERTAS TEMPRANAS (Snapshot)")
print("="*60)
r1 = evaluar_alertas_tempranas_deterministicas(db)
print("Total matricula activa:", r1.get('total_matricula_activa'))
print("Tarjetas:", json.dumps(r1.get('tarjetas'), indent=2))
print("Total estudiantes con alerta:", len(r1.get('estudiantes', [])))

print("\n" + "="*60)
print("3. TABLAS POR CAPA Y GESTIONES")
print("="*60)
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Gestiones en cada hecho
for tabla in [
    'fact_rendimiento_academico', 'fact_situacion_financiera', 
    'fact_rentabilidad', 'fact_marketing', 'fact_forecast', 
    'fact_evaluacion_docente', 'fact_costo_programa', 'fact_techo_convenio'
]:
    # chequear si tiene id_tiempo
    cur.execute(f"""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = '{tabla}' AND column_name IN ('id_tiempo', 'gestion');
    """)
    cols = [c[0] for c in cur.fetchall()]
    if 'id_tiempo' in cols:
        cur.execute(f"""
            SELECT dt.gestion, count(*) 
            FROM "{tabla}" f 
            JOIN dim_tiempo dt ON dt.id_tiempo = f.id_tiempo 
            GROUP BY dt.gestion ORDER BY dt.gestion;
        """)
        gest = cur.fetchall()
        print(f"  {tabla} (por dt.gestion): {gest}")
    elif 'gestion' in cols:
        cur.execute(f"""
            SELECT gestion, count(*) 
            FROM "{tabla}" 
            GROUP BY gestion ORDER BY gestion;
        """)
        gest = cur.fetchall()
        print(f"  {tabla} (por gestion direct): {gest}")
    else:
        print(f"  {tabla}: sin columna temporal directa")
