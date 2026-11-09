"""Diagnóstico: por hoja de evaluación, cuántas filas dan registros sin fecha / sin módulo / con docente nombrado (extractor real)."""
import sys, glob, warnings, collections
from pathlib import Path
import pandas as pd
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from services.extraccion_por_encabezado import campos_por_encabezado, registros_evaluacion
for p in sorted(glob.glob(str(ROOT / "uploads/data/*.xlsx"))):
    if not any(k in p for k in ("Evaluaci", "Experiencia", "ANTIGUO")):
        continue
    for sh, df in pd.read_excel(p, sheet_name=None).items():
        df = df.dropna(how="all").head(400)
        c = collections.Counter()
        for _, row in df.iterrows():
            celdas = [f"{k}: {v}" for k, v in row.items() if pd.notna(v) and str(v).strip()]
            regs = registros_evaluacion(campos_por_encabezado(celdas))
            if regs:
                c["filas_con_registros"] += 1
                c["sin_fecha"] += regs[0]["fecha"] is None
                c["sin_modulo_ni_pos"] += (regs[0]["modulo"] is None)
                c["con_docente_nombrado"] += regs[0]["docente"] is not None
                c["con_pos"] += regs[0]["programa"] is not None
        print(Path(p).name[:28], "|", sh[:28], "|", dict(c))
