import os
import sys
import requests
from pathlib import Path

# Configurar sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from core.security import create_access_token

token = create_access_token({"sub": "2", "role": "AUDITOR_CALIDAD"})
headers = {"Authorization": f"Bearer {token}"}

archivos = [
    ("Base_Academica_ARCA_TEST.xlsx", "uploads/test/Base_Academica_ARCA_TEST.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ("BD_Cobranzas_giraGroup.xlsx", "uploads/test/BD_Cobranzas_giraGroup.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ("TBL_INSCRITOS_TEST.xlsx", "uploads/test/TBL_INSCRITOS_TEST.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ("Inscripciones_Google_Forms_TEST.csv", "uploads/test/Inscripciones_Google_Forms_TEST.csv", "text/csv"),
    ("Reporte_Aula_Virtual_Moodle_TEST.csv", "uploads/test/Reporte_Aula_Virtual_Moodle_TEST.csv", "text/csv"),
    ("EJECUTADO VS META.xlsx", "uploads/data/EJECUTADO VS META.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ("Base centralizada Académica ARCA (1).xlsx", "uploads/data/Base centralizada Académica ARCA (1).xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
]

resultados = []
for nombre, ruta_rel, mime in archivos:
    ruta = BASE_DIR / ruta_rel
    if not ruta.exists():
        print(f"NO EXISTE: {ruta}", flush=True)
        continue
    print(f"Procesando {nombre}...", flush=True)
    with open(ruta, "rb") as f:
        files = {"file": (nombre, f, mime)}
        try:
            r = requests.post("http://localhost:8000/api/v1/pipeline/process", headers=headers, files=files, timeout=900)
            if r.status_code == 200:
                data = r.json()
                res = {
                    "archivo": nombre,
                    "filas": data.get("total_filas_procesadas", 0),
                    "cargados_dw": data.get("hechos_cargados_dw", 0),
                    "staged": data.get("entidades_derivadas_staging", 0),
                    "requiere_rev": data.get("requiere_revision_humana", False),
                    "tiempo_ms": data.get("tiempo_total_ms", 0.0)
                }
                print(f"  OK: {res}", flush=True)
                resultados.append(res)
            else:
                print(f"  ERROR {r.status_code}: {r.text[:300]}", flush=True)
        except Exception as e:
            print(f"  EXCEPCION: {e}", flush=True)

print("\n--- RESUMEN PIPELINE ---", flush=True)
for res in resultados:
    print(res, flush=True)
