"""F3R-12: Verifica docs/mediciones/f3_sfv_trazabilidad.json y audita docs/fuente_verdad_tesis.md (0 / 0 / 0)."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRAZA = ROOT / "docs" / "mediciones" / "f3_sfv_trazabilidad.json"
SFV = ROOT / "docs" / "fuente_verdad_tesis.md"


def _resolver_ruta(data, ruta: str):
    cur = data
    if isinstance(cur, dict) and ruta in cur:
        return cur[ruta]
    parts = ruta.split(".")
    i = 0
    while i < len(parts):
        part = parts[i]
        if isinstance(cur, dict):
            if part in cur:
                cur = cur[part]
                i += 1
                continue
            # Soporta claves con punto como "public.stg_entidad_no_resuelta"
            matched = False
            for j in range(len(parts), i, -1):
                joined = ".".join(parts[i:j])
                if joined in cur:
                    cur = cur[joined]
                    i = j
                    matched = True
                    break
            if matched:
                continue
            raise KeyError(f"Ruta no encontrada: {ruta} (falló en '{part}')")
        if isinstance(cur, list) and part.isdigit():
            idx = int(part)
            if 0 <= idx < len(cur):
                cur = cur[idx]
                i += 1
                continue
            raise IndexError(f"Índice fuera de rango en {ruta}: {idx}")
        raise KeyError(f"Ruta no encontrada: {ruta} (falló en '{part}')")
    return cur


def _verificar_trazabilidad() -> int:
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
    return discrepancias


def _verificar_cifras_sin_fuente() -> int:
    texto = SFV.read_text(encoding="utf-8")
    lineas = texto.splitlines()
    sin_fuente = 0

    # 1. Verificar que todo archivo citado en docs/mediciones/ exista en disco
    for m in re.finditer(r"docs/mediciones/[A-Za-z0-9_.\-]+", texto):
        rel = m.group(0)
        if not (ROOT / rel).exists():
            print(f"[SIN_FUENTE] Archivo citado inexistente: {rel}")
            sin_fuente += 1

    # 2. Verificar que cada fila de tabla con columna Fuente tenga fuente válida
    i = 0
    while i < len(lineas):
        line = lineas[i].strip()
        if line.startswith("|") and i + 1 < len(lineas) and re.match(r"^\|[\s\-:|]+\|$", lineas[i + 1].strip()):
            headers = [h.strip().lower() for h in line.strip("|").split("|")]
            fuente_idx = next((idx for idx, h in enumerate(headers) if "fuente" in h), None)
            i += 2
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                row_raw = lineas[i].strip()
                cells = [c.strip() for c in row_raw.strip("|").split("|")]
                if fuente_idx is None:
                    has_num = any(re.search(r"\d", c) for c in cells)
                    if has_num:
                        print(f"[SIN_FUENTE] Línea {i + 1}: tabla sin columna Fuente -> {row_raw}")
                        sin_fuente += 1
                elif fuente_idx < len(cells):
                    fuente_cell = cells[fuente_idx]
                    has_num = any(re.search(r"\d", c) for idx, c in enumerate(cells) if idx != fuente_idx)
                    valid_src = bool(
                        re.search(r"(docs/mediciones/|docs/evidencias/|backend/|pipeline/|docker-compose\.yml|N/D)", fuente_cell)
                    )
                    if has_num and not valid_src:
                        print(f"[SIN_FUENTE] Línea {i + 1}: fila sin fuente válida -> {row_raw}")
                        sin_fuente += 1
                i += 1
            continue
        i += 1
    return sin_fuente


def _verificar_v1_v2() -> int:
    texto = SFV.read_text(encoding="utf-8")
    hallazgos = 0
    patron = re.compile(r"(?<![a-z0-9])(v[12]|beto-v[12])(?![a-z0-9])|modelo\s+anterior|comparaci[oó]n\s+entre\s+modelos", re.IGNORECASE)
    for num, line in enumerate(texto.splitlines(), start=1):
        # Permitir únicamente el prefijo de ruta HTTP /api/v1/
        limpia = line.replace("/api/v1/", "/api/PATH/")
        for m in patron.finditer(limpia):
            print(f"[V1_V2] Línea {num}: mención prohibida '{m.group(0)}' -> {line.strip()}")
            hallazgos += 1
    return hallazgos


def main() -> int:
    discrepancias = _verificar_trazabilidad()
    sin_fuente = _verificar_cifras_sin_fuente()
    menciones_v1_v2 = _verificar_v1_v2()
    total = len(json.loads(TRAZA.read_text(encoding="utf-8"))["entradas"])
    print(
        f"RESUMEN: total={total} discrepancias={discrepancias} "
        f"cifras_sin_fuente={sin_fuente} menciones_v1_v2={menciones_v1_v2} "
        f"({discrepancias} / {sin_fuente} / {menciones_v1_v2})"
    )
    return 1 if (discrepancias or sin_fuente or menciones_v1_v2) else 0


if __name__ == "__main__":
    sys.exit(main())
