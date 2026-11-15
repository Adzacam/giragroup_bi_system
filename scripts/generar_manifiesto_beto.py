#!/usr/bin/env python
"""
scripts/generar_manifiesto_beto.py
==================================
Genera docs/evidencias/beto_manifiesto.json: SHA-256 de data/*.jsonl y del modelo vigente
(pipeline/semantic/beto_local/model.safetensors, fuera de Git por .gitignore) más las
instrucciones para obtener o regenerar el modelo. Solo lee; no entrena ni modifica datos.

Uso: python scripts/generar_manifiesto_beto.py [--modelo <dir>] [--salida <json>]
"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATOS = ("train_robusto.jsonl", "dev_robusto.jsonl", "test_gold_real.jsonl")
INSTRUCCIONES = {
    "estado": "El modelo NO está versionado en Git (.gitignore:75 excluye pipeline/semantic/beto_local/).",
    "obtener": "Copiar beto_local/ desde el respaldo de la máquina de entrenamiento y verificar el SHA-256 de model.safetensors contra este manifiesto.",
    "regenerar": [
        "make beto-reproducir   # corpus -> entrenamiento a directorio temporal -> evaluación (no pisa el vigente)",
        "PYTHONHASHSEED=0 python scripts/preparar_corpus_robusto.py --salida <dir>",
        "PYTHONHASHSEED=0 python scripts/entrenar_beto_robusto.py --datos <dir> --salida <dir_modelo>",
    ],
    "advertencia": "Un reentrenamiento produce otro SHA-256 si cambian versiones de librerías, hardware o corpus; la promoción del modelo requiere una tarea posterior explícita y actualizar este manifiesto.",
    "dependencias": "requirements-lock.txt (pip freeze del .venv)",
}


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def construir(modelo_dir: Path, datos_dir: Path) -> dict:
    if not (modelo_dir / "model.safetensors").is_file():
        raise FileNotFoundError("Modelo fuera de Git: indique --modelo <directorio del checkpoint vigente>")
    datos = {n: {"sha256": sha256(datos_dir / n), "bytes": (datos_dir / n).stat().st_size,
                 "lineas": sum(1 for _ in open(datos_dir / n, encoding="utf-8"))} for n in sorted(p.name for p in datos_dir.glob("*.jsonl"))}
    modelo = {}
    for n in ("model.safetensors", "config.json", "tokenizer.json", "tokenizer_config.json", "training_info.json"):
        if (modelo_dir / n).exists():
            modelo[n] = {"sha256": sha256(modelo_dir / n), "bytes": (modelo_dir / n).stat().st_size}
    info = modelo_dir / "training_info.json"
    ti = json.loads(info.read_text(encoding="utf-8")) if info.exists() else {}
    fuentes = [BASE_DIR / n for n in (
        "uploads/data/Experiencia Docente 2.0.xlsx",
        "uploads/data/Base centralizada Académica ARCA (1).xlsx",
        "uploads/data/TBL_INSCRITOS.xlsx",
        "uploads/test/Base_Academica_ARCA_TEST.xlsx",
        "uploads/test/TBL_INSCRITOS_TEST.xlsx",
        "db/seeds/seed_catalogos.sql",
        "uploads/test/layouts_adversarios/gold_layouts_adversarios.json",
        "data/ner/test.conll")]
    return {
        "fuentes_y_evaluacion": {p.relative_to(BASE_DIR).as_posix(): {"sha256": sha256(p), "bytes": p.stat().st_size} for p in fuentes},
        "lock_sha256": sha256(BASE_DIR / "requirements-lock.txt"),
        "generado": datetime.now().isoformat(timespec="seconds"),
        "datos": datos,
        "modelo_vigente": {"ruta": "pipeline/semantic/beto_local", "archivos": modelo,
                           "entrenado": ti.get("timestamp"), "semilla": ti.get("seed"),
                           "tiene_hash_en_training_info": "sha256" in ti},
        "instrucciones": INSTRUCCIONES,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelo", default=str(BASE_DIR / "pipeline" / "semantic" / "beto_local"))
    ap.add_argument("--datos", default=str(BASE_DIR / "data"))
    ap.add_argument("--salida", default=str(BASE_DIR / "docs" / "evidencias" / "beto_manifiesto.json"))
    a = ap.parse_args()
    m = construir(Path(a.modelo), Path(a.datos))
    Path(a.salida).write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Manifiesto escrito en {a.salida}")
