"""B-10: las conexiones no arrancan con credenciales implícitas."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULES = ["backend/core/database.py", *[f"services/{name}/core/database.py" for name in
    ("auth-service", "audit-service", "notifications-service")]]


@pytest.mark.parametrize("module", MODULES)
@pytest.mark.parametrize("missing", ["DATABASE_URL", "CATALOG_DATABASE_URL", None])
def test_urls_explicitas_sin_fallback(module, missing):
    env = os.environ.copy()
    env.update(DATABASE_URL="postgresql://test:test_only@127.0.0.1:1/isolated_dw",
               CATALOG_DATABASE_URL="postgresql://test:test_only@127.0.0.1:1/isolated_catalog")
    env.pop("DOCKER_ENV", None)
    if missing:
        env.pop(missing, None)
    # Impedir que el .env personal o del runner oculte una configuración incompleta.
    code = ("import dotenv,runpy; dotenv.load_dotenv=lambda *a,**k: None; "
            f"runpy.run_path({str(ROOT / module)!r})")
    result = subprocess.run([sys.executable, "-c", code], env=env,
                            capture_output=True, text=True, cwd=ROOT)
    if missing:
        assert result.returncode != 0
        assert f"KeyError: '{missing}'" in result.stderr
    else:
        assert result.returncode == 0, result.stderr
