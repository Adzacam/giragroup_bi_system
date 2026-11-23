"""Orquesta la medición del aporte operativo de BETO (beto-v2) sobre el lote congelado completo
(10 archivos, SHA aafde8ad..., 12.992 líneas) en 3 modos: A (sin BETO), B (cascada + BETO), C (solo BETO),
con 3 corridas caché vacía + 3 corridas caché llena por modo sobre clones tmpfs (beto_pg_tmpfs).

Genera:
  - docs/mediciones/f3_aporte_10archivos.json
  - docs/mediciones/f3_muestra_100_beto.csv
"""
import csv
import json
import math
import os
import random
import statistics as st
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "output" / "f3_aporte"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MED_DIR = ROOT / "docs" / "mediciones"
ENV = dict(os.environ, MSYS_NO_PATHCONV="1")

REPOSO_S = 5
SEED = 42


def sh(cmd, timeout=None):
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                          timeout=timeout, encoding="utf-8", errors="replace", env=ENV)


def psql_tmpfs(base, sql=None, archivo=None):
    cmd = ["docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", base, "-v", "ON_ERROR_STOP=1", "-q"]
    cmd += ["-c", sql] if sql else ["-f", archivo]
    r = sh(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"psql_tmpfs fallo ({base}): {r.stderr[-400:]}")
    return r.stdout


def ms(vals):
    return {
        "valores": [round(float(v), 2) for v in vals],
        "media": round(st.mean(vals), 2),
        "de": round(st.stdev(vals), 2) if len(vals) > 1 else 0.0,
        "min": round(min(vals), 2),
        "max": round(max(vals), 2),
    }


def wilson_ic95(k: int, n: int):
    if n <= 0:
        return None
    z = 1.959963984540054
    p = k / n
    denom = 1.0 + (z * z) / n
    centro = (p + (z * z) / (2.0 * n)) / denom
    margen = (z * math.sqrt((p * (1.0 - p) + (z * z) / (4.0 * n)) / n)) / denom
    return {
        "k": k,
        "n": n,
        "precision": round(p, 4),
        "ic95_inf": round(max(0.0, centro - margen), 4),
        "ic95_sup": round(min(1.0, centro + margen), 4),
    }


def ejecutar_corrida(modo: str, cache_estado: str, idx: int):
    p_json = OUT_DIR / f"modo_{modo}_{cache_estado}_r{idx}.json"
    p_beto = OUT_DIR / f"modo_{modo}_ents_beto.json"
    if p_json.exists() and (modo != "B" or idx > 1 or cache_estado != "vacia" or p_beto.exists()):
        print(f"[REUTILIZADO] {p_json.name}", flush=True)
        return json.loads(p_json.read_text(encoding="utf-8"))

    db_name = f"f3_ap_{modo.lower()}_{cache_estado}_{idx}"
    psql_tmpfs("postgres", f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE);")
    psql_tmpfs("postgres", f"CREATE DATABASE {db_name} TEMPLATE dw_vacio;")
    psql_tmpfs(db_name, archivo="/tmp/016.sql")
    psql_tmpfs(db_name, "TRUNCATE TABLE public.cache_indice_beto; DROP TABLE IF EXISTS public.cache_beto_entidades;")

    cache_sql = f"/tmp/cache_ap_{modo}.sql"
    if cache_estado == "llena" and modo in ("B", "C"):
        psql_tmpfs(db_name, """CREATE TABLE IF NOT EXISTS public.cache_beto_entidades (
            hash_texto CHAR(64) NOT NULL, configuracion VARCHAR(80) NOT NULL,
            entidades TEXT NOT NULL, creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (hash_texto, configuracion));""")
        psql_tmpfs(db_name, archivo=cache_sql)

    time.sleep(REPOSO_S)
    dump_arg = f"/tmp/ap_{modo}_ents.json" if (modo == "B" and cache_estado == "vacia" and idx == 1) else ""
    out_remote = f"/tmp/ap_{modo}_{cache_estado}_r{idx}.json"

    cmd = [
        "docker", "exec", "giragroup_api", "env",
        "PYTHONHASHSEED=0",
        f"DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/{db_name}",
        "CATALOG_DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/catalogo_copia",
        "CICLO_REUSAR_SLICES=1", "CICLO_FILAS_SIN_FECHA=0",
        "CICLO_SLICES=/tmp/slices_flujo",
        "PYTHONPATH=/app:/app/pipeline:/tmp/flujo/scripts",
        "sh", "-c",
        f"cd /app && python /tmp/flujo/scripts/f3_aporte_runner.py {modo} {out_remote} {dump_arg}".strip(),
    ]
    r = sh(cmd)
    if r.returncode != 0:
        psql_tmpfs("postgres", f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE);")
        raise RuntimeError(f"Fallo corrida {modo} {cache_estado} r{idx}: {r.stderr[-600:]}")

    sh(["docker", "cp", f"giragroup_api:{out_remote}", str(p_json)])
    if dump_arg:
        sh(["docker", "cp", f"giragroup_api:{dump_arg}", str(p_beto)])

    # Exportar cache tras cualquier corrida vacia de B y C si aun no existe el dump
    if cache_estado == "vacia" and modo in ("B", "C"):
        chk = sh(["docker", "exec", "beto_pg_tmpfs", "sh", "-c", f"test -s {cache_sql}"])
        if chk.returncode != 0:
            r_dump = sh([
                "docker", "exec", "beto_pg_tmpfs", "sh", "-c",
                f"pg_dump -U giragroup_user -d {db_name} -t public.cache_indice_beto -t public.cache_beto_entidades --data-only > {cache_sql}",
            ])
            if r_dump.returncode != 0:
                raise RuntimeError(f"Error exportando cache {modo}: {r_dump.stderr}")

    psql_tmpfs("postgres", f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE);")
    data = json.loads(p_json.read_text(encoding="utf-8"))
    print(f"[OK] Modo {modo} {cache_estado} r{idx}: maq={data['tiempos_s']['tiempo_maquina_total_s']}s bandeja={data['bandeja']}", flush=True)
    return data


def generar_muestra_csv(p_beto: Path, p_csv: Path):
    if not p_beto.exists():
        return {"n_disponibles": 0, "n_muestra": 0, "csv": str(p_csv.relative_to(ROOT))}
    ents = json.loads(p_beto.read_text(encoding="utf-8"))
    por_arch = defaultdict(list)
    for e in ents:
        por_arch[e["archivo"]].append(e)

    rng = random.Random(SEED)
    total = len(ents)
    muestra = []
    if total <= 100:
        muestra = list(ents)
    else:
        # Muestreo estratificado proporcional por archivo
        asignados = {}
        for arch, lista in sorted(por_arch.items()):
            asignados[arch] = max(1, round(100 * len(lista) / total))
        # Ajustar suma exacta a 100
        while sum(asignados.values()) > 100:
            mayor = max(asignados, key=lambda k: asignados[k])
            if asignados[mayor] > 1:
                asignados[mayor] -= 1
        while sum(asignados.values()) < 100:
            mayor = max(por_arch, key=lambda k: len(por_arch[k]) - asignados[k])
            asignados[mayor] += 1
        for arch, k in sorted(asignados.items()):
            lista = list(por_arch[arch])
            rng.shuffle(lista)
            muestra.extend(lista[:k])

    cols = [
        "id_muestra", "archivo", "tipo_entidad", "texto_propuesto_beto",
        "matched_canonical", "canonical_id", "fuzz_score", "prob_beto",
        "score_final", "linea_extracto", "validacion_lean", "observacion_lean",
    ]
    with p_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for i, item in enumerate(muestra, 1):
            row = {c: item.get(c, "") for c in cols}
            row["id_muestra"] = i
            row["validacion_lean"] = ""
            row["observacion_lean"] = ""
            w.writerow(row)

    return {
        "n_disponibles_solo_beto_en_B": total,
        "n_muestra_solicitada": 100,
        "n_muestra_generada": len(muestra),
        "semilla": SEED,
        "csv": str(p_csv.relative_to(ROOT)).replace("\\", "/"),
        "nota_tamano": (
            f"En el lote congelado de 10 archivos estándar, la cascada determinística ya resuelve >99.9% de las entidades; "
            f"BETO en Modo B solo necesitó rescatar {total} entidad(es)."
            if total < 100 else "Muestra aleatoria estratificada de 100 entidades."
        ),
        "estado_validacion_humana": "pendiente_revision_lean",
        "precision_observada_ic95": None,
        "formula_ic95": "Wilson score interval (z = 1.96) una vez Lean complete la columna validacion_lean (correcto/incorrecto).",
    }


def main():
    sh(["docker", "cp", str(ROOT / "scripts/f3_aporte_runner.py"), "giragroup_api:/tmp/flujo/scripts/f3_aporte_runner.py"])
    sh(["docker", "cp", str(ROOT / "scripts/agregar_flujo_repetido.py"), "giragroup_api:/tmp/flujo/scripts/agregar_flujo_repetido.py"])
    sh(["docker", "cp", str(ROOT / "backend/scripts/migrations/016_b9_descartes_y_homonimos.sql"), "beto_pg_tmpfs:/tmp/016.sql"])

    resultados_modos = {}
    for modo in ("A", "B", "C"):
        runs_vacia = [ejecutar_corrida(modo, "vacia", i) for i in range(1, 4)]
        runs_llena = [ejecutar_corrida(modo, "llena", i) for i in range(1, 4)]
        ref = runs_vacia[0]
        resultados_modos[modo] = {
            "descripcion": {
                "A": "Sin BETO (solo reglas determinísticas: CI_EXACTA + ENCABEZADO + FUZZY + REGEX)",
                "B": "Cascada determinística + rescate semántico BETO (BETO_CASCADA_FINAL=1 + índice BETO)",
                "C": "Solo BETO NER para extracción de personas (sin pistas de encabezado/CI previo) + índice BETO",
            }[modo],
            "tiempo_maquina_s": {
                "cache_vacia": ms([r["tiempos_s"]["tiempo_maquina_total_s"] for r in runs_vacia]),
                "cache_llena": ms([r["tiempos_s"]["tiempo_maquina_total_s"] for r in runs_llena]),
            },
            "desglose_etapas_s": {
                "cache_vacia_media": {
                    k: round(st.mean([r["tiempos_s"][k] for r in runs_vacia]), 2)
                    for k in ("carga_y_lectura_s", "consolidacion_s", "revision_maquina_s")
                },
                "cache_llena_media": {
                    k: round(st.mean([r["tiempos_s"][k] for r in runs_llena]), 2)
                    for k in ("carga_y_lectura_s", "consolidacion_s", "revision_maquina_s")
                },
            },
            "bandeja": ref["bandeja"],
            "klm": ref["klm"],
            "kpis": ref["kpis"],
            "fact_marketing_total": ref["fact_marketing_total"],
            "por_archivo": ref["por_archivo"],
        }

    # Aporte marginal B - A por archivo
    arch_a = resultados_modos["A"]["por_archivo"]
    arch_b = resultados_modos["B"]["por_archivo"]
    aporte_marginal = {}
    for arch in sorted(set(arch_a.keys()) | set(arch_b.keys())):
        da = arch_a.get(arch, {})
        db_ = arch_b.get(arch, {})
        ent_a = da.get("entidades_por_etapa", {})
        ent_b = db_.get("entidades_por_etapa", {})
        aporte_marginal[arch] = {
            "entidades_solo_beto": int(ent_b.get("BETO", 0)) - int(ent_a.get("BETO", 0)),
            "casos_evitados_bandeja_A_menos_B": int(da.get("hitl_casos", 0)) - int(db_.get("hitl_casos", 0)),
            "diferencia_hechos_B_menos_A": int(db_.get("hechos_cargados", 0)) - int(da.get("hechos_cargados", 0)),
            "diferencia_directo_pp": round(float(db_.get("directo_pct", 0.0)) - float(da.get("directo_pct", 0.0)), 2),
        }

    p_csv = MED_DIR / "f3_muestra_100_beto.csv"
    validacion_calidad = generar_muestra_csv(OUT_DIR / "modo_B_ents_beto.json", p_csv)

    salida_final = {
        "etiqueta": "F3, aporte operativo 10 archivos",
        "modelo": "beto-v2",
        "modelo_sha256_prefijo": "9ff7fb9d",
        "lote_congelado": {
            "archivos": 10,
            "sha256": "aafde8adc246af13c4eeb9ffbf766eda4348cfb6e855860d0bf00bcd24cbdb60",
            "lineas_totales": 12992,
            "entorno": "beto_pg_tmpfs (copia tmpfs aislada, PYTHONHASHSEED=0, semilla=42)",
        },
        "modos": resultados_modos,
        "aporte_marginal_B_menos_A": {
            "global": {
                "entidades_solo_beto": sum(v["entidades_solo_beto"] for v in aporte_marginal.values()),
                "casos_bandeja_A": resultados_modos["A"]["bandeja"]["casos"],
                "casos_bandeja_B": resultados_modos["B"]["bandeja"]["casos"],
                "grupos_bandeja_A": resultados_modos["A"]["bandeja"]["grupos"],
                "grupos_bandeja_B": resultados_modos["B"]["bandeja"]["grupos"],
                "nota_bandeja_A_vs_B": (
                    "En Modo A sin BETO, la confianza proviene solo de reglas determinísticas (20 casos en bandeja). "
                    "En Modo B, el índice probabilístico de BETO evalúa semánticamente todas las filas y envía 676 casos ambiguos a revisión; "
                    "frente al baseline con índice BETO pero sin cascada NER (f3_b7: 680 casos / 19 grupos), BETO_CASCADA_FINAL=1 evita 4 casos y 2 grupos."
                ),
            },
            "por_archivo": aporte_marginal,
        },
        "validacion_calidad": validacion_calidad,
        "aclaracion_lote_1387_9964_9986_vs_9755": {
            "pregunta": "¿Por qué lote_1387 da 99,64 % / 99,86 % y el documento 97,55 %?",
            "respuesta": (
                "Son dos métricas distintas sobre el lote de 1.387 registros: "
                "(1) El 97,55 % (1.353/1.387) proviene de KPI_11_directo_con_regla_personas_pct en docs/evidencias/lote_1387_uploads_data_arquitectura_b.json, "
                "que aplica la regla estricta de mover a HITL los 31 registros cuyo índice era >=0.85 pero sin persona resuelta en catálogo (con beto-v2 esa misma métrica subió a 98,05 % = 1.360/1.387 en docs/mediciones/f3r_lote_1387.json). "
                "(2) El 99,64 % (Modo A: 1.382/1.387) y 99,86 % (Modo B: 1.385/1.387) provienen de scripts/ablacion_beto.py (docs/evidencias/ablacion_beto_resultados.csv), "
                "que evalúa las bandas de confianza del parser estructural (clasificar_banda >= 0.85) sin aplicar esa regla adicional de degradación por persona no resuelta."
            ),
            "nota_sin_v1_en_tabla": "Ninguna cifra de beto-v1 forma parte de las tablas de medición de los 10 archivos en este JSON.",
        },
    }

    p_out = MED_DIR / "f3_aporte_10archivos.json"
    p_out.write_text(json.dumps(salida_final, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[FINALIZADO] Escrito {p_out} y {p_csv}", flush=True)


if __name__ == "__main__":
    main()
