import subprocess
from datetime import datetime

blocks = {
    "Sprint 1 (Infraestructura, DB y Modelos)": ["docker-compose.yml", "db", "backend/models"],
    "Sprint 2 (Ingesta y Asymmetric Flattener)": [
        "pipeline/ingesta.py", "pipeline/bloques_detector.py", 
        "pipeline/categorizacion_y_cierre.py", "pipeline/normalization/asymmetric_flattener.py",
        "backend/services/ingestion_service.py"
    ],
    "Sprint 3 (Pipeline Semántico y Normalización)": ["pipeline/semantic", "pipeline/normalization"],
    "Sprint 4 (Routers Backend, Alertas y Forecast)": [
        "backend/routers", "backend/services/alert_engine.py", 
        "backend/services/risk_service.py", "backend/services/forecast_service.py", 
        "pipeline/analytics"
    ],
    "Sprint 5 (Frontend Web SPA React)": ["frontend/src"],
    "Sprint 6 (Batería de Pruebas y Despliegue)": ["tests", "infrastructure"]
}

print("Sprint | Primer Commit | Último Commit | N° Commits")
print("-" * 75)

for name, paths in blocks.items():
    cmd = ["git", "log", "--reverse", '--format=%ad | %h | %s', "--date=short", "--"] + paths
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    lines = [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
    if lines:
        first = lines[0]
        last = lines[-1]
        count = len(lines)
        first_date = first.split(" | ")[0]
        first_msg = first.split(" | ")[2][:35]
        last_date = last.split(" | ")[0]
        last_msg = last.split(" | ")[2][:35]
        print(f"{name} | {first_date} ({first_msg}...) | {last_date} ({last_msg}...) | {count}")
    else:
        print(f"{name} | N/A | N/A | 0")
