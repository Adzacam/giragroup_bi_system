"""B-5: consultas y endpoints de producción sobre la copia histórica F0, solo lectura."""
import argparse
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directorio", default=str(ROOT / "docs/mediciones"))
    args = parser.parse_args()
    output = Path(args.directorio)
    urls = {name: os.environ[name] for name in ("DATABASE_URL", "CATALOG_DATABASE_URL")}
    for key, expected in (("DATABASE_URL", "giragroup_db"), ("CATALOG_DATABASE_URL", "catalogo_copia")):
        target = urlparse(urls[key])
        if target.path != "/" + expected or not (
            (target.hostname == "beto_pg_tmpfs" and target.port == 5432)
            or (target.hostname in ("localhost", "127.0.0.1") and target.port == 55432)
        ):
            raise ValueError(f"{key} debe señalar la copia histórica tmpfs F0")
    import psycopg2
    sql_path = output / "f0_b5_consultas.sql"
    sql = sql_path.read_text(encoding="utf-8")
    sql = "\n".join(line.split("--", 1)[0] for line in sql.splitlines() if not line.startswith("\\"))
    results = []
    conn = psycopg2.connect(urls["DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://"),
                            options="-c default_transaction_read_only=on", connect_timeout=5)
    try:
        with conn.cursor() as cursor:
            for statement in sql.split(";"):
                if not statement.strip():
                    continue
                cursor.execute(statement)
                if cursor.description:
                    columns = [c.name for c in cursor.description]
                    results.append([dict(zip(columns, row)) for row in cursor.fetchall()])
    finally:
        conn.close()
    # Reutiliza routers reales sin startup de main (evita seed/migraciones).
    sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from core.database import get_db
    from core.security import get_current_user
    from routers import cmi, forecast
    from services import cache_consultas
    engine = create_engine(urls["DATABASE_URL"], connect_args={"options": "-c default_transaction_read_only=on"})
    factory = sessionmaker(bind=engine)
    def readonly_db():
        with factory() as db:
            yield db
    app = FastAPI()
    app.include_router(cmi.router)
    app.include_router(forecast.router)
    app.dependency_overrides[get_db] = readonly_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="ADMIN", id=-1, is_active=True)
    cache_consultas.invalidar()
    client = TestClient(app)
    endpoints = {}
    for endpoint in ("/api/v1/cmi/scorecard?gestion=2025", "/api/v1/forecast/metas?granularidad=ANUAL&horizonte=2"):
        response = client.get(endpoint)
        endpoints[endpoint] = {"status_code": response.status_code, "body": response.json()}
        if response.status_code != 200:
            raise RuntimeError("Respuesta no válida del endpoint aislado")
    engine.dispose()
    annual = results[1]
    target_2025 = next((item for item in annual if item["anio"] == 2025), None)
    scopes = {item["universo"]: item for item in results[3]}
    kpi = scopes.get("KPI03_INGRESO", {})
    programs = scopes.get("MACRO_PROGRAMAS", {})
    actual_delta = (kpi.get("ejecutado_bs") - programs.get("ejecutado_bs")) if kpi.get("ejecutado_bs") is not None and programs.get("ejecutado_bs") is not None else None
    report = {
        "tarea": "B-5", "estado": "medido", "fecha": datetime.now(ZoneInfo("America/La_Paz")).isoformat(),
        "fuente": "beto_pg_tmpfs/giragroup_db (copia histórica)", "gestion": 2025,
        "sql": sql_path.name, "sql_sha256": hashlib.sha256(sql_path.read_bytes()).hexdigest(),
        "solo_lectura": True, "serie_anual": annual, "comparacion_2025_OLS": target_2025,
        "categorias_2025": results[2], "universos_2025": results[3], "KPI03_vista": results[4],
        "delta_ejecutado_global_menos_programas_bs": actual_delta,
        "delta_ejecutado_global_menos_programas_pct_sobre_programas": float(actual_delta) / float(programs["ejecutado_bs"]) * 100 if actual_delta is not None and programs.get("ejecutado_bs") else None,
        "delta_global_menos_ajustado_ols_2025_bs": float(kpi["ejecutado_bs"]) - float(target_2025["ajustado_ols_bs"]) if target_2025 and target_2025.get("ajustado_ols_bs") is not None and kpi.get("ejecutado_bs") is not None else None,
        "delta_global_menos_ajustado_ols_2025_pct_sobre_ajustado": 100 * (float(kpi["ejecutado_bs"]) / float(target_2025["ajustado_ols_bs"]) - 1) if target_2025 and target_2025.get("ajustado_ols_bs") and kpi.get("ejecutado_bs") is not None else None,
        "respuestas_TestClient": endpoints,
        "protocolo_TestClient": "Routers reales cmi/forecast montados en FastAPI sin startup; rol ADMIN simulado únicamente para acceso de lectura; dependencia get_db con default_transaction_read_only=on; URLs aisladas. No revisión humana ni medición top-1.",
        "razon_discrepancia": "OLS anual usa PROGRAMAS y valor ajustado por recta, mientras KPI-03 usa todas las categorías INGRESO y ejecutado observado; meta_a_la_fecha incluye solo meses con ejecución positiva. El total observado y el valor ajustado son magnitudes diferentes.",
        "invariantes": "OLS anual descriptiva, mensual N=40 y HW sin cambios.",
    }
    def encode(value):
        if isinstance(value, Decimal):
            return float(value)
        if hasattr(value, "isoformat"):
            return value.isoformat()
        raise TypeError(type(value).__name__)
    text = json.dumps(report, ensure_ascii=False, indent=2, default=encode) + "\n"
    (output / "f0_b5_2025.json").write_text(text, encoding="utf-8")
    (output / "f0_b5_consultas.txt").write_text(json.dumps(results, ensure_ascii=False, indent=2, default=encode) + "\n", encoding="utf-8")
    print(json.dumps({"estado": "medido", "consultas": len(results), "endpoints_200": len(endpoints), "n_anual": len(annual)}))


if __name__ == "__main__":
    main()
