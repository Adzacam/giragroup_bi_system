"""S-7 (F3S): lote 1.387 con scripts/reejecutar_lote_1387_uploads_data.py SIN cambios (mismos topes 450/350/250/150/110/53/24),
contra una copia tmpfs de f3s_base (DATABASE_URL), modelo BETO vigente, 4 flags BETO en False, sin BETO_INT8.
El script original escribe en docs/evidencias/ (archivos versionados): se respaldan antes y se restauran después;
su salida se copia a docs/mediciones/<salida>.
Uso: python scripts/f3s_lote_1387.py <dsn> <salida.json>
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "docs" / "evidencias"
ARCH = ["lote_1387_uploads_data_arquitectura_b.json", "muestra_50_entidades_beto_semilla42.json"]
BK = ROOT / "output" / "f3s" / "s7" / "bk_evidencias"


def main(dsn, salida):
    BK.mkdir(parents=True, exist_ok=True)
    for a in ARCH:
        shutil.copy2(EVID / a, BK / a)
    env = dict(os.environ, DATABASE_URL=dsn, PYTHONIOENCODING="utf-8", PYTHONHASHSEED="0",
               BETO_CASCADA_FINAL="0", BETO_ACUERDO_QC="0", BETO_SUGERENCIA_HITL="0", BETO_VENTANA="0")
    env.pop("BETO_INT8", None)
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "scripts/reejecutar_lote_1387_uploads_data.py"], cwd=str(ROOT), env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        nombre = Path(salida).stem
        (ROOT / "output/f3s/s7" / f"{nombre}.log").write_text(
            f"duracion_s={time.time() - t0:.1f}\n{r.stdout}\n--- stderr ---\n{r.stderr[-20000:]}", encoding="utf-8")
        if r.returncode == 0:
            shutil.copy2(EVID / ARCH[0], ROOT / "docs" / "mediciones" / salida)
            shutil.copy2(EVID / ARCH[1], ROOT / "output/f3s/s7" / f"{nombre}_muestra50.json")
        print("returncode", r.returncode, "duracion_s", round(time.time() - t0, 1))
    finally:
        for a in ARCH:
            shutil.copy2(BK / a, EVID / a)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
