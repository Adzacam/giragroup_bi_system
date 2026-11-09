"""Tarea 3 (ronda 5): vincula las filas ya cargadas de fact_evaluacion_docente con la misma regla del cargador
(docente único del módulo o del programa en bridge_modulo_docente; id_tiempo del último período con actas del programa),
marca para revisión las que no se resuelven y escribe docs/evidencias/evaluacion_docente_vinculacion.json.
Uso: DATABASE_URL=postgresql://...@localhost:5434/giragroup_db python scripts/vincular_evaluacion_docente.py"""
import json, os, sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from services.dw_loader import DWLoaderService

eng = create_engine(os.environ["DATABASE_URL"])
S = sessionmaker(bind=eng)()
L = DWLoaderService(S)
Q = text("SELECT count(*) total, count(*) FILTER (WHERE tipo_pregunta='DOCENTE') docente_pregs, "
         "count(*) FILTER (WHERE tipo_pregunta='DOCENTE' AND id_docente IS NOT NULL) con_docente, count(id_tiempo) con_tiempo, "
         "count(*) FILTER (WHERE requiere_revision) en_revision FROM fact_evaluacion_docente")
antes = dict(S.execute(Q).mappings().one())
mods = [r[0] for r in S.execute(text("SELECT DISTINCT id_modulo FROM fact_evaluacion_docente WHERE id_modulo IS NOT NULL"))]
n_mod_docente = n_mod_tiempo = 0
for m in mods:
    doc = L._docente_unico_del_modulo(m) or L._docente_del_programa(m)
    tie = L._tiempo_del_programa(m)
    if doc:
        n_mod_docente += 1
        S.execute(text("UPDATE fact_evaluacion_docente SET id_docente=:d WHERE id_modulo=:m AND tipo_pregunta='DOCENTE' AND id_docente IS NULL"), {"d": doc, "m": m})
    if tie:
        n_mod_tiempo += 1
        S.execute(text("UPDATE fact_evaluacion_docente SET id_tiempo=:t, motivo_revision='FECHA_ESTIMADA_DEL_PROGRAMA' WHERE id_modulo=:m AND id_tiempo IS NULL"), {"t": tie, "m": m})
S.execute(text("UPDATE fact_evaluacion_docente SET motivo_revision = concat_ws(', ', motivo_revision, 'DOCENTE_SIN_VINCULAR') "
               "WHERE tipo_pregunta='DOCENTE' AND id_docente IS NULL"))
S.execute(text("UPDATE fact_evaluacion_docente SET motivo_revision = concat_ws(', ', motivo_revision, 'SIN_FECHA') WHERE id_tiempo IS NULL"))
S.execute(text("UPDATE fact_evaluacion_docente SET requiere_revision = (motivo_revision IS NOT NULL)"))
S.commit()
despues = dict(S.execute(Q).mappings().one())
grupos = S.execute(text("SELECT count(*) FROM (SELECT 1 FROM fact_evaluacion_docente WHERE requiere_revision GROUP BY id_documento, id_modulo) g")).scalar()
motivos = {r[0]: r[1] for r in S.execute(text("SELECT motivo_revision, count(*) FROM fact_evaluacion_docente WHERE requiere_revision GROUP BY 1 ORDER BY 2 DESC"))}
res = {"antes": antes, "despues": despues, "modulos_evaluados": len(mods), "modulos_con_docente_unico": n_mod_docente, "modulos_con_periodo_del_programa": n_mod_tiempo,
       "pct_filas_docente_vinculadas": round(despues["con_docente"] / despues["docente_pregs"] * 100, 2), "pct_filas_con_tiempo": round(despues["con_tiempo"] / despues["total"] * 100, 2),
       "casos_en_bandeja_(documento,modulo)": grupos, "motivos": motivos}
(ROOT / "docs" / "evidencias" / "evaluacion_docente_vinculacion.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
