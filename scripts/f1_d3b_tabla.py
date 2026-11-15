#!/usr/bin/env python
"""D-T: Tabla unica v1 vs v2 vs Delta, resultado D-B y huellas del DW."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MED = ROOT / "docs/mediciones"


def sha256_archivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def fmt_delta(v1, v2, dec=4):
    if v1 is None or v2 is None:
        return "—"
    d = round(v2 - v1, dec)
    if d == 0:
        return "0"
    signo = "+" if d > 0 else ""
    return f"{signo}{d}"


def main() -> None:
    da = json.loads((MED / "f1_d3b_calidad.json").read_text(encoding="utf-8"))
    db = json.loads((MED / "f1_d3b_validez.json").read_text(encoding="utf-8"))
    dc = json.loads((MED / "f1_d3b_operativo.json").read_text(encoding="utf-8"))
    klm = json.loads((MED / "f1_d3b_klm.json").read_text(encoding="utf-8"))

    h_v1_p = MED / "f1_d3b_corrida_v1_vacia_r1.json.huella.json"
    h_v2_p = MED / "f1_d3b_corrida_v2_vacia_r1.json.huella.json"
    h_v1 = json.loads(h_v1_p.read_text(encoding="utf-8"))
    h_v2 = json.loads(h_v2_p.read_text(encoding="utf-8"))

    tablas_difieren_v1_v2 = []
    for t in sorted(set(h_v1["tablas"]) | set(h_v2["tablas"])):
        t1 = h_v1["tablas"].get(t)
        t2 = h_v2["tablas"].get(t)
        if t1 != t2:
            tablas_difieren_v1_v2.append(
                {
                    "tabla": t,
                    "v1_filas": t1["filas"] if t1 else None,
                    "v2_filas": t2["filas"] if t2 else None,
                    "delta_filas": (t2["filas"] - t1["filas"]) if (t1 and t2) else None,
                    "v1_md5": t1["md5"] if t1 else None,
                    "v2_md5": t2["md5"] if t2 else None,
                }
            )

    # Indexar D-A
    idx_da = {
        (f["version"], f["dataset"], f["modo"], f["criterio"]): f
        for f in da["filas"]
    }

    filas_tabla = []
    # Seccion A: calidad sin pipeline
    for ds in ("gold_510", "layouts_5"):
        for modo in ("A", "B", "C"):
            for crit in ("strict", "relaxed"):
                r1 = idx_da[("beto-v1", ds, modo, crit)]
                r2 = idx_da[("beto-v2", ds, modo, crit)]
                fuente = f"{Path(r1['fuente_json']).name} / {Path(r2['fuente_json']).name} (f1_d3b_calidad.json)"
                filas_tabla.append(
                    {
                        "grupo": "D-A (Calidad sin pipeline)",
                        "metrica": f"{ds} Modo {modo} ({crit}) F1 [P / R | TP/FP/FN]",
                        "v1": f"{r1['f1']:.4f} [P={r1['precision']:.4f}, R={r1['recall']:.4f} | {r1['tp']}/{r1['fp']}/{r1['fn']}]",
                        "v2": f"{r2['f1']:.4f} [P={r2['precision']:.4f}, R={r2['recall']:.4f} | {r2['tp']}/{r2['fp']}/{r2['fn']}]",
                        "delta": fmt_delta(r1["f1"], r2["f1"], 4),
                        "fuente": fuente,
                    }
                )

    # Seccion C: operativo
    o1 = dc["versiones"]["v1"]
    o2 = dc["versiones"]["v2"]
    k1 = klm["versiones"]["v1"]
    k2 = klm["versiones"]["v2"]

    filas_tabla.append(
        {
            "grupo": "D-C (Pipeline operativo)",
            "metrica": "Lineas leidas por BETO",
            "v1": o1["lineas_leidas_beto"],
            "v2": o2["lineas_leidas_beto"],
            "delta": fmt_delta(o1["lineas_leidas_beto"], o2["lineas_leidas_beto"], 0),
            "fuente": "f1_d3b_operativo.json",
        }
    )

    for t in sorted(o1["tablas_dw_staging"]):
        f1_n = o1["tablas_dw_staging"][t]["filas"]
        f2_n = o2["tablas_dw_staging"][t]["filas"]
        filas_tabla.append(
            {
                "grupo": "D-C (Tablas DW y staging)",
                "metrica": f"Filas {t}",
                "v1": f1_n,
                "v2": f2_n,
                "delta": fmt_delta(f1_n, f2_n, 0),
                "fuente": "f1_d3b_operativo.json",
            }
        )

    for k, label in (
        ("casos", "Bandeja: casos totales"),
        ("grupos", "Bandeja: grupos totales"),
        ("manuales", "Bandeja: grupos manuales"),
        ("casos_manuales", "Bandeja: casos manuales"),
    ):
        v1_b = o1["bandeja"][k]
        v2_b = o2["bandeja"][k]
        filas_tabla.append(
            {
                "grupo": "D-C (Bandeja)",
                "metrica": label,
                "v1": v1_b,
                "v2": v2_b,
                "delta": fmt_delta(v1_b, v2_b, 0),
                "fuente": "f1_d3b_operativo.json",
            }
        )

    for kpi in sorted(o1["kpis"]):
        v1_k = o1["kpis"][kpi]
        v2_k = o2["kpis"][kpi]
        filas_tabla.append(
            {
                "grupo": "D-C (KPIs)",
                "metrica": kpi,
                "v1": v1_k,
                "v2": v2_k,
                "delta": fmt_delta(v1_k, v2_k, 4) if isinstance(v1_k, (int, float)) else ("igual" if v1_k == v2_k else "distinto"),
                "fuente": "f1_d3b_operativo.json",
            }
        )

    for key_t, label_t in (
        ("maquina_vacia", "Tiempo maquina cache vacia (media +/- DE, s, n=3)"),
        ("pared_vacia", "Tiempo pared cache vacia (media +/- DE, s, n=3)"),
        ("maquina_llena", "Tiempo maquina cache llena (media +/- DE, s, n=3)"),
        ("pared_llena", "Tiempo pared cache llena (media +/- DE, s, n=3)"),
    ):
        t1 = o1["tiempos"][key_t]
        t2 = o2["tiempos"][key_t]
        filas_tabla.append(
            {
                "grupo": "D-C (Tiempos)",
                "metrica": label_t,
                "v1": f"{t1['media_s']:.2f} +/- {t1['de_s']:.2f}",
                "v2": f"{t2['media_s']:.2f} +/- {t2['de_s']:.2f}",
                "delta": fmt_delta(t1["media_s"], t2["media_s"], 2),
                "fuente": "f1_d3b_operativo.json",
            }
        )

    filas_tabla.extend(
        [
            {
                "grupo": "D-C (KLM y Total)",
                "metrica": "klm_estimado_d3b con espera W=10s (s)",
                "v1": k1["con_espera_W_10s"]["total_s"],
                "v2": k2["con_espera_W_10s"]["total_s"],
                "delta": fmt_delta(k1["con_espera_W_10s"]["total_s"], k2["con_espera_W_10s"]["total_s"], 1),
                "fuente": "f1_d3b_klm.json",
            },
            {
                "grupo": "D-C (KLM y Total)",
                "metrica": "klm_estimado_d3b sin espera W=0s (s)",
                "v1": k1["sin_espera_W_0s"]["total_s"],
                "v2": k2["sin_espera_W_0s"]["total_s"],
                "delta": fmt_delta(k1["sin_espera_W_0s"]["total_s"], k2["sin_espera_W_0s"]["total_s"], 1),
                "fuente": "f1_d3b_klm.json",
            },
            {
                "grupo": "D-C (KLM y Total)",
                "metrica": "Tiempo total (maquina vacia + KLM W=10s) (s)",
                "v1": k1["tiempo_total_con_W_10s"],
                "v2": k2["tiempo_total_con_W_10s"],
                "delta": fmt_delta(k1["tiempo_total_con_W_10s"], k2["tiempo_total_con_W_10s"], 1),
                "fuente": "f1_d3b_klm.json",
            },
            {
                "grupo": "D-C (KLM y Total)",
                "metrica": "Tiempo total (maquina vacia + KLM W=0s) (s)",
                "v1": k1["tiempo_total_sin_W_0s"],
                "v2": k2["tiempo_total_sin_W_0s"],
                "delta": fmt_delta(k1["tiempo_total_sin_W_0s"], k2["tiempo_total_sin_W_0s"], 1),
                "fuente": "f1_d3b_klm.json",
            },
        ]
    )

    fuga_resumen = {}
    for cruce, datos in db["fuga_4_niveles"].items():
        fuga_resumen[cruce] = {
            "a_oracion_exacta": datos["a_oracion_exacta"]["coincidencias"],
            "b_texto_normalizado": datos["b_texto_normalizado"]["coincidencias"],
            "c_variantes_unicas": datos["c_variantes"]["coincidencias_total_unicas"],
            "d_personas_compartidas": datos["d_personas_normalizadas_compartidas"]["personas_unicas_compartidas"],
        }

    comparacion = {
        "tarea": "D-T",
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "tabla_unica": filas_tabla,
        "validez_reentrenamiento_D_B": {
            "fuente": "f1_d3b_validez.json",
            "separa_antes_de_aumentar": db["orden_aumento_separacion"]["separa_antes_de_aumentar"],
            "personas_compartidas_train_dev": db["orden_aumento_separacion"]["prueba_empirica_train_vs_dev"],
            "fuga_4_niveles_x_2_trains": fuga_resumen,
        },
        "huellas_dw": {
            "v1_huella_archivo": h_v1_p.name,
            "v1_huella_sha256": sha256_archivo(h_v1_p),
            "v2_huella_archivo": h_v2_p.name,
            "v2_huella_sha256": sha256_archivo(h_v2_p),
            "tablas_que_difieren_v1_vs_v2": tablas_difieren_v1_v2,
        },
    }
    (MED / "f1_d3b_comparacion.json").write_text(json.dumps(comparacion, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Markdown
    md = [
        "# F1D3B — Comparación lado a lado: `beto-v1` vs `beto-v2`",
        "",
        "## 1. Tabla única de comparación (D-A y D-C)",
        "",
        "| Bloque | Métrica | `beto-v1` | `beto-v2` | Δ (`v2 - v1`) | Fuente |",
        "|---|---|---|---|---|---|",
    ]
    for f in filas_tabla:
        md.append(f"| {f['grupo']} | {f['metrica']} | {f['v1']} | {f['v2']} | {f['delta']} | `{f['fuente']}` |")

    md += [
        "",
        "## 2. Validez del reentrenamiento (D-B, fuente: `f1_d3b_validez.json`)",
        "",
        f"- **Orden aumento / separación:** `separa_antes_de_aumentar = {db['orden_aumento_separacion']['separa_antes_de_aumentar']}` (`scripts/preparar_corpus_robusto.py` l.101-110 y l.334-344).",
        f"- **Personas compartidas train vs dev (spans / IOB2):** `beto-v1` = {db['orden_aumento_separacion']['prueba_empirica_train_vs_dev']['beto-v1']['personas_compartidas_train_dev_spans']} / {db['orden_aumento_separacion']['prueba_empirica_train_vs_dev']['beto-v1']['personas_compartidas_train_dev_iob2']}; `beto-v2` = {db['orden_aumento_separacion']['prueba_empirica_train_vs_dev']['beto-v2']['personas_compartidas_train_dev_spans']} / {db['orden_aumento_separacion']['prueba_empirica_train_vs_dev']['beto-v2']['personas_compartidas_train_dev_iob2']}.",
        "",
        "| Cruce | a) Oración exacta | b) Texto normalizado | c) Variantes (plantilla / Jaccard≥0.8) | d) Personas compartidas |",
        "|---|---:|---:|---:|---:|",
    ]
    for cruce, vals in fuga_resumen.items():
        md.append(
            f"| `{cruce}` | {vals['a_oracion_exacta']} | {vals['b_texto_normalizado']} | {vals['c_variantes_unicas']} | {vals['d_personas_compartidas']} |"
        )

    md += [
        "",
        "## 3. Huellas del DW (`v1` vs `v2`)",
        "",
        f"- **`beto-v1` (`{h_v1_p.name}`):** sha256 `{comparacion['huellas_dw']['v1_huella_sha256']}`",
        f"- **`beto-v2` (`{h_v2_p.name}`):** sha256 `{comparacion['huellas_dw']['v2_huella_sha256']}`",
        "",
        "### Tablas que difieren entre `beto-v1` y `beto-v2`",
        "",
        "| Tabla | Filas `v1` | Filas `v2` | Δ filas | MD5 `v1` | MD5 `v2` |",
        "|---|---:|---:|---:|---|---|",
    ]
    for t in tablas_difieren_v1_v2:
        md.append(f"| `{t['tabla']}` | {t['v1_filas']} | {t['v2_filas']} | {t['delta_filas']} | `{t['v1_md5']}` | `{t['v2_md5']}` |")

    (MED / "f1_d3b_comparacion.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("[OK] Generados f1_d3b_comparacion.json y f1_d3b_comparacion.md")


if __name__ == "__main__":
    main()
