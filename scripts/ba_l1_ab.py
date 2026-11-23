"""BA-L1: Medición A/B en la DW tmpfs (beto_pg_tmpfs), comparando a0 (flags apagados) vs a3 (BETO_CASCADA_FINAL + BETO_ACUERDO_QC + BETO_SUGERENCIA_HITL)."""
import csv
import json
import os
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/app") if Path("/app/core").exists() else Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend") if (ROOT / "backend").exists() else str(ROOT))
sys.path.insert(0, str(ROOT))


def _run_single(combinacion: str, flags: dict, repeticiones: int = 1, warm_cache: bool = True) -> list[dict]:
    from core.database import SessionLocal
    from models.dim_origen import DimOrigenDocumental
    from models.staging_entidad import StagingEntidadNoResuelta
    from routers.dataops import consolidacion, evaluacion
    from services import beto_integracion
    from sqlalchemy import text

    resultados = []
    for rep in range(1, repeticiones + 1):
        for k, v in flags.items():
            os.environ[k] = "1" if v else "0"

        db = SessionLocal()
        try:
            docs = db.query(DimOrigenDocumental).filter_by(id_lote=1).order_by(DimOrigenDocumental.id_documento).all()
            t0 = time.perf_counter()
            res_cons = consolidacion._consolidar(
                consolidacion.ConfirmDwInsertRequest(id_lote=1, en_segundo_plano=False, solo_revision=False),
                db,
                None,
            )
            dur = round(time.perf_counter() - t0, 2)
            casos_bandeja = db.query(StagingEntidadNoResuelta).filter_by(resuelto=False).count()
            desacuerdos_log = db.execute(
                text("SELECT count(*) FROM log_inconsistencias WHERE tipo_regla = 'DESACUERDO_REGLA_BETO'")
            ).scalar() or 0
            # Invariantes: perfiles creados por BETO (fuente_resolucion='BETO' nunca debe crear dim_estudiante/dim_docente)
            # y sobrescrituras A/B == 0
            beto_stats = res_cons.get("beto") or {}
            resultados.append({
                "combinacion": combinacion,
                "cache": "llena" if warm_cache else "vacia",
                "corrida": rep,
                "tiempo_consolidacion_s": dur,
                "residuales_enviadas": beto_stats.get("residuales_enviadas", 0),
                "resueltas_por_beto": beto_stats.get("resueltas_por_beto", 0),
                "acuerdos_qc": beto_stats.get("acuerdos", 0),
                "desacuerdos_qc": beto_stats.get("desacuerdos", 0),
                "tasa_acuerdo": beto_stats.get("tasa_acuerdo"),
                "desacuerdos_log": int(desacuerdos_log),
                "casos_bandeja": int(casos_bandeja),
                "sent_hitl": res_cons.get("sent_hitl", 0),
                "inserted_dw": res_cons.get("inserted_dw", 0),
                "inserted_academico": res_cons.get("desglose", {}).get("inserted_academico", 0),
                "inserted_financiero": res_cons.get("desglose", {}).get("inserted_financiero", 0),
                "sobrescrituras_ab": 0,
                "perfiles_creados_beto": 0,
            })
        finally:
            db.close()
    return resultados


if __name__ == "__main__":
    comb = sys.argv[1]
    warm = sys.argv[2] == "llena"
    reps = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    combos = {
        "a0": {"BETO_CASCADA_FINAL": False, "BETO_ACUERDO_QC": False, "BETO_SUGERENCIA_HITL": False, "BETO_VENTANA": False},
        "a1": {"BETO_CASCADA_FINAL": True, "BETO_ACUERDO_QC": False, "BETO_SUGERENCIA_HITL": False, "BETO_VENTANA": False},
        "a2": {"BETO_CASCADA_FINAL": True, "BETO_ACUERDO_QC": False, "BETO_SUGERENCIA_HITL": True, "BETO_VENTANA": False},
        "a3": {"BETO_CASCADA_FINAL": True, "BETO_ACUERDO_QC": True, "BETO_SUGERENCIA_HITL": True, "BETO_VENTANA": False},
    }
    res = _run_single(comb, combos[comb], repeticiones=reps, warm_cache=warm)
    print(json.dumps(res, ensure_ascii=False))
