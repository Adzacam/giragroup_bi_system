"""
tests/test_otp_entorno_pruebas.py
---------------------------------
El OTP del login solo se expone con APP_ENV=test y nunca junto a ENVIRONMENT=production.
Se importa el router de auth en un subproceso para evaluar las variables de entorno de forma aislada.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_candidate_auth = Path(__file__).resolve().parent.parent / "services" / "auth-service"
AUTH_DIR = _candidate_auth if _candidate_auth.exists() else Path(__file__).resolve().parent.parent
SONDA = "import os; import routers.auth as a; print(a.OTP_EXPUESTO_EN_PRUEBAS)"


def _importar_auth(**env_extra):
    env = {k: v for k, v in os.environ.items() if k not in ("APP_ENV", "ENVIRONMENT")}
    env.update(env_extra)
    env["PYTHONPATH"] = str(AUTH_DIR)
    return subprocess.run([sys.executable, "-c", SONDA], cwd=AUTH_DIR, env=env, capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("env_extra,esperado", [
    # Vacía y no ausente: el servicio carga .env con load_dotenv, que no pisa variables ya definidas
    ({"APP_ENV": ""}, "False"),
    ({"APP_ENV": "production"}, "False"),
    ({"APP_ENV": "local"}, "False"),
    ({"APP_ENV": "test", "ENVIRONMENT": "local"}, "True"),
])
def test_otp_solo_se_expone_en_pruebas(env_extra, esperado):
    r = _importar_auth(**env_extra)
    if r.returncode != 0 and "ModuleNotFoundError" in r.stderr:
        pytest.skip(f"dependencias del auth-service no instaladas: {r.stderr.strip().splitlines()[-1]}")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().splitlines()[-1] == esperado


def test_app_env_test_en_produccion_no_arranca():
    r = _importar_auth(APP_ENV="test", ENVIRONMENT="production")
    assert r.returncode != 0
    assert "RuntimeError" in r.stderr
    assert "no está permitido con ENVIRONMENT=production" in r.stderr
