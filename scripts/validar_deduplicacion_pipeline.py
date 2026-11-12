"""Carga dos veces el mismo archivo (bytes idénticos) por /api/v1/pipeline/process y muestra los contadores de marketing.
Uso, dentro de giragroup_api y apuntando DATABASE_URL a una base aislada: python scripts/validar_deduplicacion_pipeline.py
Nunca apuntar a giragroup_db."""
import sys,hashlib
sys.path[:0]=['/app','/app/backend']
from fastapi.testclient import TestClient
from main import app
from core.security import get_current_user
from models.user import User
from core.database import SessionLocal
from sqlalchemy import text
app.dependency_overrides[get_current_user]=lambda: User(id=2,username="auditor",email="a@giragroup.bo",role="AUDITOR_CALIDAD",is_active=True)
cli=TestClient(app); ruta='/tmp/slices_completo/TBL_INSCRITOS.xlsx'
b=open(ruta,'rb').read(); print('sha256 del archivo',hashlib.sha256(b).hexdigest()[:12])
def estado():
    with SessionLocal() as s:
        r=s.execute(text("select count(*),coalesce(sum(inscritos),0) from fact_marketing")).one()
        d=s.execute(text("select count(*) from dim_origen_documental where nombre_archivo like 'TBL%'")).scalar()
        return {'filas':r[0],'inscritos':int(r[1]),'docs_TBL':d}
print('antes      ',estado())
for i in (1,2):
    r=cli.post('/api/v1/pipeline/process',files={'file':('TBL_INSCRITOS.xlsx',b)})
    print(f'tras carga idéntica {i} (HTTP {r.status_code})',estado())
