"""BA-L1b: Revisión de la etapa 'Patrón' (REGEX) sobre muestra estratificada de 100 entidades en lote 1."""
import csv
import os
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path("/app") if Path("/app/core").exists() else Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend") if (ROOT / "backend").exists() else str(ROOT))
sys.path.insert(0, str(ROOT))

from core.database import SessionLocal
from models.dim_origen import DimOrigenDocumental
from routers.dataops.evaluacion import _evaluacion_lectura


def evaluar_extraccion_regex(tipo_fuente: str, label: str, token: str, canonical: str, raw_line: str) -> tuple[bool, str]:
    tok = (token or "").strip()
    if label == "DOCUMENTO / CI":
        if tok == "No provisto" and "TEMP-ID" in (canonical or ""):
            return True, "TEMP-ID correcto cuando no hay CI"
        if re.search(r"[0-9•*]{3,}", tok):
            return True, "CI/documento con patrón numérico válido"
        return False, "CI sin patrón numérico"
    if label == "MONTO":
        if re.search(r"\d+(?:\.\d+)?", tok):
            return True, "Monto numérico válido"
        return False, "Monto sin valor numérico"
    if label == "CALIFICACIÓN":
        m = re.search(r"\d+(?:\.\d+)?", tok)
        if m and 0 <= float(m.group(0)) <= 100:
            return True, "Calificación en rango 0-100"
        return False, "Calificación fuera de rango"
    if label == "ESTUDIANTE":
        # En EVALUACION_DOCENTE, REGEX extrae nombre con >=2 palabras pero sin match en catálogo
        if len(tok.split()) >= 2 and re.match(r"^[A-ZÁÉÍÓÚÑa-záéíóúñ\s.\-]+$", tok):
            return True, "Nombre de estudiante válido (pasa a BETO si sin match)"
        return False, "Falso positivo de nombre por REGEX"
    if label == "PROGRAMA":
        if "NO SE ENCUENTRAN" in tok.upper():
            return False, "Encabezado/nota capturada como PROGRAMA"
        return True, "Programa válido"
    return True, "Válido"


def main():
    id_lote = int(os.getenv("BA_ID_LOTE", "1"))
    out_path = Path(os.getenv("BA_L1B_OUT", str(ROOT / "docs" / "mediciones" / "ba_l1b_regex.csv")))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        docs = db.query(DimOrigenDocumental).filter_by(id_lote=id_lote).all()
        res = _evaluacion_lectura(db, docs)
        por_grupo = defaultdict(list)
        for r in res["detalles"]:
            tf = r.get("tipo_fuente")
            raw = r.get("raw_line") or ""
            for e in (r.get("lectura") or {}).get("entidades") or r.get("entidades") or []:
                if str(e.get("origen_confianza") or e.get("fuente_resolucion") or "").upper() == "REGEX":
                    por_grupo[(tf, e.get("label"))].append({
                        "id_documento": r.get("id_documento"),
                        "tipo_fuente": tf,
                        "label": e.get("label"),
                        "token": e.get("token"),
                        "matchedCanonical": e.get("matchedCanonical"),
                        "raw_preview": raw[:140],
                    })

        rng = random.Random(42)
        total_n = sum(len(v) for v in por_grupo.values())
        muestra = []
        # Garantizar al menos 1 de cada grupo y completar 100 proporcionalmente
        for k in sorted(por_grupo.keys()):
            items = por_grupo[k]
            cuota = max(1, round(100 * len(items) / total_n))
            elegidos = rng.sample(items, min(cuota, len(items)))
            muestra.extend(elegidos)
        if len(muestra) > 100:
            muestra = muestra[:100]
        elif len(muestra) < 100:
            usados = {(m["id_documento"], m["label"], m["token"], m["raw_preview"]) for m in muestra}
            resto = [x for v in por_grupo.values() for x in v if (x["id_documento"], x["label"], x["token"], x["raw_preview"]) not in usados]
            muestra.extend(rng.sample(resto, min(100 - len(muestra), len(resto))))

        correctas = 0
        for i, m in enumerate(muestra, 1):
            ok, obs = evaluar_extraccion_regex(m["tipo_fuente"], m["label"], m["token"], m["matchedCanonical"], m["raw_preview"])
            m["nro"] = i
            m["correcta"] = 1 if ok else 0
            m["observacion"] = obs
            correctas += int(ok)

        cols = ["nro", "id_documento", "tipo_fuente", "label", "token", "matchedCanonical", "correcta", "observacion", "raw_preview"]
        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(muestra)

        precision = round(correctas * 100.0 / len(muestra), 2)
        print(f"BA-L1b: muestra={len(muestra)}, correctas={correctas}, precision={precision}% -> {out_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
