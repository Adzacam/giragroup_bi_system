"""
Exporta config/mapeo_fuentes.yaml al espejo JSON pipeline/mapeo_fuentes.json (FU-L1).

El contenedor de la API monta solo backend/ y pipeline/ y no instala PyYAML; el lector de
hojas (pipeline/lector_hojas.py) usa este espejo cuando no puede leer el YAML. La fuente de
verdad editable sigue siendo el YAML: después de editarlo, se vuelve a correr este script.
tests/fu_l1/test_lector_hojas.py falla si el espejo no es igual al YAML.

Uso:
    python scripts/auditoria_fuentes/exportar_mapeo_json.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
YAML = RAIZ / "config" / "mapeo_fuentes.yaml"
JSON = RAIZ / "pipeline" / "mapeo_fuentes.json"


def exportar(origen: Path = YAML, destino: Path = JSON) -> Path:
    datos = yaml.safe_load(origen.read_text(encoding="utf-8"))
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return destino


if __name__ == "__main__":
    ruta = exportar()
    print(f"espejo={ruta.relative_to(RAIZ)}")
    sys.exit(0)
