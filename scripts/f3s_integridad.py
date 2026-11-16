"""S-7 (F3S): integridad de entrada antes/después de medir. Solo lectura.
Comprueba: sha256 del snapshot (dump), sha256 del modelo BETO, lote f0 (manifiesto recalculado: originales + slices)
y que los 10 slices del contenedor (CICLO_SLICES) sean byte a byte los de output/backups/f0_lote/slices/.
Uso: python scripts/f3s_integridad.py <salida.json> [carpeta_slices_en_giragroup_api]
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOTE = ROOT / "output" / "backups" / "f0_lote"
MANIFEST = ROOT / "docs" / "mediciones" / "f0_lote_manifest.json"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main(salida, slices_cont=None):
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    archivos = []
    difs = []
    for a in man["archivos"]:
        p = LOTE / a["ruta"]
        s = sha(p) if p.exists() else None
        archivos.append({"ruta": a["ruta"], "bytes": p.stat().st_size if p.exists() else None, "sha256": s})
        if s != a["sha256"]:
            difs.append(a["ruta"])
    archivos.sort(key=lambda a: a["ruta"])  # serialización del manifiesto: lista por ruta
    lote_sha = hashlib.sha256(json.dumps(archivos, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    out = {
        "snapshot_sha256": sha(ROOT / "docs" / "evidencias" / "snapshot_dw_20261110_1201.dump"),
        "modelo_beto_sha256": sha(ROOT / "pipeline" / "semantic" / "beto_local" / "model.safetensors"),
        "lote_sha256_recalculado": lote_sha,
        "lote_sha256_manifiesto": man["sha256"],
        "lote_archivos_distintos": difs,
    }
    if slices_cont:
        env = dict(os.environ, MSYS_NO_PATHCONV="1")
        r = subprocess.run(["docker", "exec", "giragroup_api", "sh", "-c", f"cd '{slices_cont}' && sha256sum *.xlsx"],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        cont = {}
        for linea in r.stdout.splitlines():
            h, _, n = linea.partition("  ")
            cont[n.strip()] = h
        ref = {a["ruta"].split("/", 1)[1]: a["sha256"] for a in man["archivos"] if a["ruta"].startswith("slices/")}
        out["slices_contenedor"] = {"carpeta": slices_cont, "n": len(cont),
                                    "iguales_al_manifiesto": cont == ref,
                                    "distintos": sorted(set(cont.items()) ^ set(ref.items()))}
    Path(salida).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, str) else v[:16]) for k, v in out.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
