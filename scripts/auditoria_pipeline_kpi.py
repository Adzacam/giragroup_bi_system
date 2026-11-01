import os
import sys

from dotenv import load_dotenv

# Credenciales desde .env; solo se redirige al puerto publicado del contenedor (127.0.0.1:5434)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
if os.getenv('DATABASE_URL'):
    os.environ['DATABASE_URL'] = os.environ['DATABASE_URL'].replace('@giragroup_db:5432', '@127.0.0.1:5434')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from core.database import SessionLocal
from models.lote import Lote
from models.dim_origen import DimOrigenDocumental
from models.staging_registro import StagingRegistroCrudo
from models.staging_entidad import StagingEntidadNoResuelta
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from models.fact_rentabilidad import FactRentabilidad
from models.fact_marketing import FactMarketing
from services.kpi_service import KPIService

db = SessionLocal()
print('=== ESTADO DATA WAREHOUSE Y PIPELINE DATAOPS ===')
print('Lotes registrados:', db.query(Lote).count())
print('Documentos Origen:', db.query(DimOrigenDocumental).count())
print('Staging Registros Crudos:', db.query(StagingRegistroCrudo).count())
print('Staging HITL Pendientes:', db.query(StagingEntidadNoResuelta).count())
print('Fact Rendimiento Academico:', db.query(FactRendimientoAcademico).count())
print('Fact Situacion Financiera:', db.query(FactSituacionFinanciera).count())
print('Fact Rentabilidad:', db.query(FactRentabilidad).count())
print('Fact Marketing:', db.query(FactMarketing).count())

svc = KPIService(db)
cmi = svc.obtener_perspectivas_cmi_completo()
print('\n=== CONSOLIDADO CMI (4 PERSPECTIVAS HEFESTO) ===')
for nombre, kpis in cmi.get('perspectivas', {}).items():
    print(f"-- {nombre} --")
    for clave, valor in kpis.items():
        if not isinstance(valor, (list, dict)):
            print(f"   {clave}: {valor}")

print('\n=== 11 KPIs DEL CMI ===')
for clave, valor in cmi.get('kpis', {}).items():
    if isinstance(valor, dict):
        valor = valor.get('valor', valor.get('general', valor.get('aprobacion_global_pct', valor)))
    print(f"   {clave}: {valor}")

db.close()
