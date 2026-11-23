#!/usr/bin/env python3
"""
scripts/medir_ba_l1b_regex.py
-----------------------------
BA-L1b (H6): Muestra estratificada de 100 entidades resueltas por la etapa REGEX
sobre el lote 1 (en beto_pg_tmpfs/ba_base), evaluando si la entidad extraída es
válida o un falso positivo que debería pasar a BETO.

Salida: docs/mediciones/ba_l1b_regex.csv (sin PII: tokens de persona enmascarados).
"""
import csv
import os
import random
import re
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_origen import DimOrigenDocumental
from models.staging_registro import StagingRegistroCrudo
from routers.dataops._comun import categoria_ruteo as resolver_categoria_ruteo
from routers.dataops.consolidacion import _motivo_sin_entidad
from routers.dataops.extraccion import _docentes_con_contexto, extract_entities_from_line
from services import encuesta_canonica
from services.dataops_evaluation_service import NON_PERSON_WORDS, strip_accents
from services.extraccion_por_encabezado import campos_por_encabezado

DB_URL = os.environ.get(
    "BA_TMPFS_DB_URL",
    "postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/ba_base",
)
OUT_CSV = Path(os.environ.get("BA_L1B_OUT", "/tmp/ba_l1b_regex.csv"))
SEMILLA = 42


def _es_persona_valida(tok: str) -> tuple[bool, str]:
    t = (tok or "").strip()
    if not t or len(t) < 4:
        return False, "muy_corto"
    if re.search(r"\d", t):
        return False, "contiene_digitos"
    if "@" in t or "http" in t.lower():
        return False, "correo_o_url"
    palabras = [p for p in re.split(r"\s+", strip_accents(t).upper()) if p]
    if len(palabras) < 2:
        return False, "una_sola_palabra"
    if any(p in NON_PERSON_WORDS for p in palabras):
        return False, "palabra_no_persona"
    return True, "nombre_valido"


def _evaluar_regex(label: str, ent: dict) -> tuple[bool, str]:
    tok = str(ent.get("token") or "").strip()
    if label in ("ESTUDIANTE", "DOCENTE"):
        return _es_persona_valida(tok)
    if label == "DOCUMENTO / CI":
        dig = re.sub(r"[^0-9]", "", tok)
        ok = 5 <= len(dig) <= 10 and "?" not in tok
        return ok, "ci_valido" if ok else "ci_invalido"
    if label == "CALIFICACIÓN":
        nota = ent.get("notaNormalizada")
        ok = nota is not None and 0.0 <= float(nota) <= 100.0
        return ok, "nota_valida" if ok else "nota_fuera_rango"
    if label == "MONTO":
        val = ent.get("valorNumerico")
        ok = val is not None and float(val) >= 0.0
        return ok, "monto_valido" if ok else "monto_invalido"
    if label in ("MÓDULO", "PROGRAMA"):
        ok = len(tok) >= 3 and not tok.isdigit()
        return ok, "catalogo_valido" if ok else "catalogo_invalido"
    if label == "ASISTENCIA":
        ok = bool(re.search(r"\d", tok))
        return ok, "asistencia_valida" if ok else "asistencia_invalida"
    ok = len(tok) >= 1
    return ok, "ok" if ok else "vacio"


def main() -> None:
    rng = random.Random(SEMILLA)
    engine = create_engine(DB_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        docs = db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_lote == 1).all()
        doc_map = {d.id_documento: d for d in docs}
        stgs = (
            db.query(StagingRegistroCrudo)
            .filter(StagingRegistroCrudo.id_documento.in_(list(doc_map.keys())))
            .order_by(StagingRegistroCrudo.id.asc())
            .all()
        )
        estudiantes = db.query(DimEstudiante).filter(DimEstudiante.deprecado == False).all()
        docentes = _docentes_con_contexto(db)
        modulos = db.query(DimModulo).all()

        candidatos = []
        for stg in stgs:
            d = doc_map[stg.id_documento]
            doc_fuente = (d.tipo_fuente or "ACTA").upper().strip()
            if (stg.categoria or "").strip().lower() == "evaluacion_docente":
                doc_fuente = "EVALUACION_DOCENTE"
            if doc_fuente == "PLANIFICACION":
                continue
            doc_escala = None if doc_fuente in ("COBRANZA", "ADMISION") else (d.tipo_escala or "CENTESIMAL_100")
            cat_ruteo = resolver_categoria_ruteo(doc_fuente, stg.categoria)
            lines = [l.strip() for l in (stg.texto_plano or "").splitlines() if l.strip()]
            campos_l = [campos_por_encabezado([c.strip() for c in l.split("|")]) for l in lines]
            perfil = encuesta_canonica.perfilar(campos_l) if cat_ruteo == "evaluacion_docente" else None
            for idx, (line, c_l) in enumerate(zip(lines, campos_l)):
                if _motivo_sin_entidad(c_l, cat_ruteo, perfil):
                    continue
                ents, _, _ = extract_entities_from_line(
                    line, estudiantes, docentes, modulos, tipo_escala=doc_escala, tipo_fuente=doc_fuente
                )
                for e in ents:
                    if str(e.get("fuente_resolucion") or "").upper() == "REGEX":
                        lbl = str(e.get("label") or "")
                        ok, detalle = _evaluar_regex(lbl, e)
                        candidatos.append({
                            "id_documento": d.id_documento,
                            "tipo_fuente": doc_fuente,
                            "hoja": stg.hoja or "",
                            "fila": (stg.fila_inicio or 0) + idx,
                            "label": lbl,
                            "matched_canonical": bool(e.get("matchedCanonical")),
                            "es_nuevo_perfil": bool(e.get("es_nuevo_perfil")),
                            "longitud_token": len(str(e.get("token") or "")),
                            "correcta": int(ok),
                            "motivo_eval": detalle,
                        })

        muestra = rng.sample(candidatos, min(100, len(candidatos)))
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(muestra[0].keys()))
            writer.writeheader()
            writer.writerows(muestra)

        correctas = sum(m["correcta"] for m in muestra)
        prec = round(100.0 * correctas / len(muestra), 2) if muestra else 0.0
        print(f"BA-L1b OK: total_regex={len(candidatos)}, muestra={len(muestra)}, correctas={correctas}, precision={prec}%")
    finally:
        db.close()


if __name__ == "__main__":
    main()
