"""F3-9: Verifica cada cifra de docs/mediciones/f3_sfv_trazabilidad.json contra su archivo fuente JSON."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRAZA = ROOT / "docs" / "mediciones" / "f3_sfv_trazabilidad.json"


def _resolver_ruta(data, ruta: str):
    cur = data
    for part in ruta.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(f"Ruta no encontrada: {ruta} (falló en '{part}')")
    return cur


def main() -> int:
    doc = json.loads(TRAZA.read_text(encoding="utf-8"))
    discrepancias = 0
    for item in doc["entradas"]:
        p = ROOT / item["archivo"]
        if not p.exists():
            print(f"[ERROR] {item['id']}: archivo ausente {item['archivo']}")
            discrepancias += 1
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        real = _resolver_ruta(data, item["ruta"])
        if real != item["valor"]:
            print(f"[DIFF] {item['id']}: esperado={item['valor']} real={real} ({item['archivo']}::{item['ruta']})")
            discrepancias += 1
        else:
            print(f"[OK] {item['id']}: {real} ({item['archivo']}::{item['ruta']})")
    print(f"RESUMEN: total={len(doc['entradas'])} discrepancias={discrepancias}")
    return 1 if discrepancias else 0


if __name__ == "__main__":
    sys.exit(main())
