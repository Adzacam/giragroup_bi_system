"""T-1: Verifica BD Techos.xlsx completo en tmpfs (f3t_techos) y guarda docs/mediciones/f3t_d_t1.json."""
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = os.environ.get(
    "F3T_TECHOS_DSN", "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55632/f3t_techos"
)
os.environ["CATALOG_DATABASE_URL"] = os.environ.get(
    "F3T_CAT_DSN", "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55632/catalogo_copia"
)
os.environ["BETO_CASCADA_FINAL"] = "0"
os.environ["BETO_ACUERDO_QC"] = "0"
os.environ["BETO_SUGERENCIA_HITL"] = "0"
os.environ["BETO_VENTANA"] = "0"

sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from core.database import SessionLocal
from models.fact_techo_convenio import FactTechoConvenio
from models.log_inconsistencia import LogInconsistencia
from models.lote import Lote
from models.staging_entidad import StagingEntidadNoResuelta
from models.staging_registro import StagingRegistroCrudo
from routers import dataops
from services.ingestion_service import IngestionService


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    xlsx = ROOT / "uploads/data/BD Techos.xlsx"
    df = pd.read_excel(xlsx, sheet_name="BD Techos").dropna(how="all")
    con_pos_inst = int(
        sum(
            1
            for _, r in df.iterrows()
            if pd.notna(r.get("POS")) and str(r.get("POS")).strip() and pd.notna(r.get("Insitución")) and str(r.get("Insitución")).strip()
        )
    )

    db = SessionLocal()
    try:
        lote = Lote(institucion="GiraGroup", periodo="2024")
        db.add(lote)
        db.commit()
        db.refresh(lote)

        IngestionService.procesar_archivo(
            db,
            str(xlsx),
            xlsx.name,
            id_lote=lote.id_lote,
            institucion="GiraGroup",
        )
        res_cons = dataops._consolidar(
            dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote),
            db,
            SimpleNamespace(id=1, username="admin_general", role="ADMIN"),
        )
        stg_total = db.query(StagingRegistroCrudo).count()
        convenios = db.query(FactTechoConvenio).count()
        stg_est = db.query(StagingEntidadNoResuelta).filter_by(tipo_entidad="ESTUDIANTE").count()
        stg_otros = db.query(StagingEntidadNoResuelta).count()
        logs = db.query(LogInconsistencia).count()
        sin_explicar = len(df) - (convenios + stg_otros + logs)

        out = {
            "etiqueta": "F3T",
            "tarea": "T-1 (D-T1: BD Techos.xlsx completo en tmpfs)",
            "archivo": "uploads/data/BD Techos.xlsx",
            "sha256_archivo": sha256_file(xlsx),
            "filas_no_vacias_excel": len(df),
            "filas_con_pos_e_institucion": con_pos_inst,
            "staging_registros_crudos": stg_total,
            "fact_techo_convenio": convenios,
            "stg_entidad_no_resuelta_estudiante": stg_est,
            "stg_entidad_no_resuelta_total": stg_otros,
            "log_inconsistencias": logs,
            "sin_explicar": sin_explicar,
            "consolidacion_respuesta": res_cons if isinstance(res_cons, dict) else str(res_cons),
        }
        (ROOT / "docs/mediciones/f3t_d_t1.json").write_text(
            json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
        print(f"[OK] T-1 excel={len(df)} pos_inst={con_pos_inst} convenios={convenios} stg_est={stg_est} stg_tot={stg_otros}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
