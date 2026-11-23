"""Runner dentro de giragroup_api para medir un modo (A=sin_beto, B=cascada_beto, C=solo_beto)
sobre el lote congelado de 10 archivos (SHA aafde8ad, 12.992 líneas) en una base tmpfs aislada.

Uso (dentro de giragroup_api, con DATABASE_URL apuntando a tmpfs):
    python f3_aporte_runner.py <modo: A|B|C> <salida.json> [dump_beto_entidades.json]
"""
import hashlib
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

os.environ.setdefault("PYTHONHASHSEED", "0")
random.seed(42)
np.random.seed(42)

ROOT = Path("/app")
sys.path[:0] = [str(ROOT), str(ROOT / "pipeline"), "/tmp/flujo/scripts"]

import medir_ciclo_mensual as ciclo  # noqa: E402
import simular_revision as rev  # noqa: E402
from sqlalchemy import text  # noqa: E402

import agregar_flujo_repetido as afr  # noqa: E402
from pipeline.semantic.indice_confianza import clasificar_banda  # noqa: E402
import services.confianza_service as cs  # noqa: E402
import services.beto_integracion as bi  # noqa: E402
import routers.dataops.extraccion as ext  # noqa: E402
import routers.dataops.consolidacion as cons  # noqa: E402

BASE = "/api/v1/dataops"
TIPOS = [
    ("TBL_INSCRITOS", "ADMISION"),
    ("Cobranzas", "COBRANZA"),
    ("Techos", "MARKETING"),
    ("EJECUTADO", "RENTABILIDAD"),
    ("Egresos", "RENTABILIDAD"),
    ("PLANIFICACION", "RENTABILIDAD"),
    ("ANTIGUO", "EVALUACION_DOCENTE"),
    ("Evaluaci", "EVALUACION_DOCENTE"),
    ("Experiencia", "ACTA"),
    ("Base centralizada", "ACTA"),
]


def tipo_fuente(nombre: str) -> str:
    return next((t for k, t in TIPOS if k.lower() in nombre.lower()), "ACTA")


def instalar_instrumentacion(modo: str):
    """Instrumenta extract_entities_from_line y configura el modo A, B o C sin modificar archivos del repo."""
    stats_por_archivo = defaultdict(lambda: Counter())
    entidades_solo_beto = []

    orig_extract = ext.extract_entities_from_line
    orig_obtener = cs.obtener_indices
    orig_indices_cascada = cs.indices_cascada

    # Modo A: sin BETO en absoluto (ni /indice ni /infer-batch)
    if modo == "A":
        os.environ["BETO_CASCADA_FINAL"] = "0"
        os.environ["BETO_ACUERDO_QC"] = "0"
        os.environ["BETO_SUGERENCIA_HITL"] = "0"
        os.environ["BETO_VENTANA"] = "0"

        def sin_beto_indices(lineas, al_avanzar=None):
            if al_avanzar:
                al_avanzar(len(lineas))
            return [None] * len(lineas)

        def sin_beto_cascada(lineas, resueltas, obtener=None, al_avanzar=None):
            if al_avanzar:
                al_avanzar(len(lineas))
            return [None] * len(lineas)

        cs.obtener_indices = sin_beto_indices
        cs.indices_cascada = sin_beto_cascada
        cons.obtener_indices = sin_beto_indices
        cons.indices_cascada = sin_beto_cascada
        # En consolidacion, cuando indice es None y Modo A no usa BETO, usar el score deterministico
        cons.banda_de = lambda idx: clasificar_banda(idx) if idx is not None else "REVISION"

    elif modo == "B":
        os.environ["BETO_CASCADA_FINAL"] = "1"
        os.environ["BETO_ACUERDO_QC"] = "0"
        os.environ["BETO_SUGERENCIA_HITL"] = "0"
        os.environ["BETO_VENTANA"] = "0"

    elif modo == "C":
        os.environ["BETO_CASCADA_FINAL"] = "1"
        os.environ["BETO_ACUERDO_QC"] = "0"
        os.environ["BETO_SUGERENCIA_HITL"] = "0"
        os.environ["BETO_VENTANA"] = "0"

    # Rastrear archivo actual durante consolidacion (en los 3 modos)
    archivo_actual = {"nombre": "DESCONOCIDO"}
    linea_a_archivo = {}

    def _cargar_mapa_lineas():
        if linea_a_archivo:
            return
        from core.database import SessionLocal
        with SessionLocal() as s:
            rows = s.execute(text(
                "SELECT s.texto_plano, d.nombre_archivo FROM staging_registros_crudos s "
                "JOIN dim_origen_documental d ON d.id_documento = s.id_documento"
            )).fetchall()
            for txt, nom in rows:
                for l in (txt or "").splitlines():
                    ls = l.strip()
                    if ls and ls not in linea_a_archivo:
                        linea_a_archivo[ls] = nom

    orig_refinar = bi.refinar_lineas

    def wrapped_refinar(lines, extractor, **kwargs):
        archivo_actual["nombre"] = kwargs.get("archivo") or "DESCONOCIDO"
        return orig_refinar(lines, extractor, **kwargs)

    bi.refinar_lineas = wrapped_refinar

    prev_cascada = cons.indices_cascada

    def wrapped_cascada(lines, resueltas, obtener=None, al_avanzar=None):
        _cargar_mapa_lineas()
        if lines and lines[0] in linea_a_archivo:
            archivo_actual["nombre"] = linea_a_archivo[lines[0]]
        return prev_cascada(lines, resueltas, obtener=obtener, al_avanzar=al_avanzar)

    cons.indices_cascada = wrapped_cascada

    def wrapped_extract(line, estudiantes, docentes, modulos, *args, **kwargs):
        if modo == "C":
            # En Modo C (solo BETO), se deshabilita la resolucion deterministica previa de personas (CI y encabezados)
            # manteniendo montos/notas/fechas para que dw_loader pueda cargar hechos y BETO proponga estudiante/docente
            import re
            line_sin_hdr = re.sub(
                r"(?i)\b(C[EÉ]DULA(?:\s+DE\s+IDENTIDAD)?|C\.?I\.?|CI_ESTUDIANTE|IDNUMBER|DOC_IDENTIDAD/CI|ESTUDIANTE|ALUMNO|NOMBRE\s+COMPLETO|NOMBRES\s+Y\s+APELLIDOS|APELLIDOS\s+Y\s+NOMBRES|APELLIDO\s+PATERNO|APELLIDO\s+MATERNO|NOMBRES|DOCENTE|PROFESOR|CATEDR[AÁ]TICO|FACILITADOR|TUTOR)\s*:",
                "CAMPO:",
                line,
            )
            ents, score, req_rev = orig_extract(line_sin_hdr, estudiantes, docentes, modulos, *args, **kwargs)
        else:
            ents, score, req_rev = orig_extract(line, estudiantes, docentes, modulos, *args, **kwargs)

        # En Modo A sin BETO, si no hubo score de /indice, usar score deterministico de extract_entities_from_line
        arch = archivo_actual["nombre"]
        for e in ents:
            lbl = e.get("label", "")
            fr = e.get("fuente_resolucion")
            algo = str(e.get("algorithm") or "")
            if lbl == "DOCUMENTO / CI" and not fr:
                fr = "REGEX"
            elif lbl in ("NOTA", "FECHA", "MONTO") and not fr:
                fr = "ENCABEZADO"
            # Corregir etiqueta en extraccion.py L313: solo es BETO si realmente vino de BETO
            if fr == "BETO" and "propuesto por BETO" not in algo:
                fr = "ENCABEZADO" if e.get("es_nuevo_perfil") else "FUZZY"
            if fr in ("CI_EXACTA", "ENCABEZADO", "FUZZY", "REGEX", "BETO"):
                stats_por_archivo[arch][fr] += 1
            if fr == "BETO" and "propuesto por BETO" in algo:
                entidades_solo_beto.append({
                    "archivo": arch,
                    "tipo_entidad": lbl,
                    "texto_propuesto_beto": e.get("token"),
                    "matched_canonical": e.get("matchedCanonical"),
                    "canonical_id": e.get("canonicalId"),
                    "fuzz_score": e.get("fuzzScore"),
                    "prob_beto": e.get("lecturaModelo"),
                    "score_final": e.get("betoConfidence"),
                    "linea_extracto": line[:240],
                })
        return ents, score, req_rev

    ext.extract_entities_from_line = wrapped_extract
    cons.extract_entities_from_line = wrapped_extract

    if modo == "A":
        # Parchear banda_de en consolidacion usando el score de extract_entities_from_line cuando indice is None
        # Hacemos un wrapper ligero sobre evaluar_banda via score
        pass

    return stats_por_archivo, entidades_solo_beto


def consultar_metricas_por_archivo(db, id_lote: int):
    """Consulta hechos, directo, HITL, staging, fk_estado por cada dim_origen_documental del lote."""
    docs = db.execute(
        text("SELECT id_documento, nombre_archivo, tipo_fuente FROM dim_origen_documental ORDER BY id_documento")
    ).fetchall()

    por_archivo = {}
    for id_doc, nombre, tf in docs:
        stg_lineas = db.execute(
            text("SELECT COALESCE(SUM(array_length(string_to_array(trim(texto_plano), E'\\n'), 1)), 0) "
                 "FROM staging_registros_crudos WHERE id_documento = :d"),
            {"d": id_doc},
        ).scalar() or 0
        stg_no_res = db.execute(
            text("SELECT count(*) FROM stg_entidad_no_resuelta WHERE id_documento = :d"),
            {"d": id_doc},
        ).scalar() or 0

        # Hechos por tabla con id_documento
        hechos_total = 0
        directo = 0
        hitl = 0
        tablas_con_rev = [
            "fact_rendimiento_academico",
            "fact_situacion_financiera",
            "fact_evaluacion_docente",
            "fact_costo_programa",
            "fact_techo_convenio",
        ]
        for tbl in tablas_con_rev:
            row = db.execute(
                text(f"SELECT count(*), "
                     f"COALESCE(SUM(CASE WHEN requiere_revision = false THEN 1 ELSE 0 END), 0), "
                     f"COALESCE(SUM(CASE WHEN requiere_revision = true THEN 1 ELSE 0 END), 0) "
                     f"FROM {tbl} WHERE id_documento = :d"),
                {"d": id_doc},
            ).first()
            hechos_total += int(row[0] or 0)
            directo += int(row[1] or 0)
            hitl += int(row[2] or 0)

        rent = db.execute(
            text("SELECT count(*) FROM fact_rentabilidad WHERE id_documento = :d"),
            {"d": id_doc},
        ).scalar() or 0
        hechos_total += int(rent)
        directo += int(rent)

        # Personas fk_estado A/B/C en hechos con columna fk_estado
        fk_counts = {"A": 0, "B": 0, "C": 0}
        for tbl in ("fact_rendimiento_academico", "fact_situacion_financiera"):
            rows_fk = db.execute(
                text(f"SELECT COALESCE(fk_estado, 'C'), count(*) FROM {tbl} WHERE id_documento = :d GROUP BY fk_estado"),
                {"d": id_doc},
            ).fetchall()
            for est, cnt in rows_fk:
                k = str(est or "C").strip().upper()
                if k in fk_counts:
                    fk_counts[k] += int(cnt)

        # Para fact_evaluacion_docente contar fk_estado desde dim_docente
        rows_ev_doc = db.execute(
            text("SELECT COALESCE(d.fk_estado, 'C'), count(*) FROM fact_evaluacion_docente f "
                 "JOIN dim_docente d ON d.id_docente = f.id_docente "
                 "WHERE f.id_documento = :d GROUP BY d.fk_estado"),
            {"d": id_doc},
        ).fetchall()
        for est, cnt in rows_ev_doc:
            k = str(est or "C").strip().upper()
            if k in fk_counts:
                fk_counts[k] += int(cnt)

        # KPI-10 por archivo (promedio nivel_confianza_ia en rendimiento y financiero)
        conf_vals = []
        for tbl in ("fact_rendimiento_academico", "fact_situacion_financiera"):
            r_conf = db.execute(
                text(f"SELECT count(nivel_confianza_ia), COALESCE(SUM(nivel_confianza_ia), 0) "
                     f"FROM {tbl} WHERE id_documento = :d AND nivel_confianza_ia IS NOT NULL"),
                {"d": id_doc},
            ).first()
            if r_conf and r_conf[0]:
                conf_vals.append((int(r_conf[0]), float(r_conf[1])))
        n_conf = sum(c[0] for c in conf_vals)
        kpi_10_arch = round(sum(c[1] for c in conf_vals) / n_conf, 4) if n_conf else None

        # Grupos HITL aproximados por archivo (motivos distintos en stg_entidad_no_resuelta pendientes o hechos en revision)
        hitl_grupos_arch = db.execute(
            text("SELECT count(DISTINCT motivo) FROM stg_entidad_no_resuelta "
                 "WHERE id_documento = :d AND COALESCE(resuelto, false) = false"),
            {"d": id_doc},
        ).scalar() or 0

        pct_dir = round(100.0 * directo / hechos_total, 2) if hechos_total else 0.0
        por_archivo[nombre] = {
            "id_documento": id_doc,
            "tipo_fuente": tf,
            "lineas_staging": int(stg_lineas),
            "hechos_cargados": hechos_total,
            "directo": directo,
            "directo_pct": pct_dir,
            "hitl_casos": hitl,
            "hitl_grupos_staging": int(hitl_grupos_arch),
            "staging": int(stg_no_res),
            "personas_fk_estado": fk_counts,
            "kpis": {
                "KPI-10": kpi_10_arch,
                "KPI-11": pct_dir if hechos_total else None,
                "KPI-18": hitl,
            },
        }
    return por_archivo


def main():
    modo = sys.argv[1].upper()
    salida = Path(sys.argv[2])
    dump_beto = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    stats_etapas, ents_beto = instalar_instrumentacion(modo)

    info = [i for i in ciclo.construir_slices() if "slice" in i]
    cli = rev.cliente()

    files, tipos, escalas = [], [], []
    for it in info:
        nombre = Path(it["slice"]).name
        files.append(("files", (nombre, open(it["slice"], "rb").read(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")))
        tf = tipo_fuente(nombre)
        tipos.append(tf)
        escalas.append("CENTESIMAL_100" if tf == "ACTA" else "")

    t0 = time.perf_counter()
    r = cli.post(f"{BASE}/upload-batch", files=files, data={
        "tipos_fuente": tipos, "tipos_escala": escalas, "institucion": "GiraGroup Posgrado"
    })
    t_carga_lectura = round(time.perf_counter() - t0, 2)
    j = r.json()
    id_lote = j.get("id_lote")
    if not id_lote:
        raise RuntimeError(f"upload-batch fallo: {j}")

    # Esperar LECTURA_BETO
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 1800:
        tarea = cli.get(f"{BASE}/lote/{id_lote}/tarea", params={"tipo": "LECTURA_BETO"}).json()
        if (tarea or {}).get("estado") != "EN_CURSO":
            break
        time.sleep(1)
    t_espera = round(time.perf_counter() - t0, 2)

    # En Modo A sin BETO, asegurar que confirm-dw-insert use el score deterministico si indice es None
    if modo == "A":
        orig_banda = cons.banda_de
        # Patch consolidacion to use extract_entities_from_line score when indice is None
        src_orig_extract = cons.extract_entities_from_line
        last_score = {"val": 0.90}

        def capture_extract(*a, **kw):
            res = src_orig_extract(*a, **kw)
            last_score["val"] = res[1]
            return res

        cons.extract_entities_from_line = capture_extract
        cons.banda_de = lambda idx: clasificar_banda(idx if idx is not None else last_score["val"])

    t0 = time.perf_counter()
    rc = cli.post(f"{BASE}/confirm-dw-insert", json={"id_lote": id_lote, "en_segundo_plano": False})
    t_consolidacion = round(time.perf_counter() - t0, 2)
    if rc.status_code != 200:
        raise RuntimeError(f"confirm-dw-insert fallo ({rc.status_code}): {rc.text[:500]}")

    # Bandeja antes de simular revision
    primera, grupos = rev._todos_los_grupos(cli, {})
    revision = rev.simular(cli, str(id_lote))
    eventos = revision["eventos"]
    k_con, _ = afr.klm(eventos, True)
    k_sin, _ = afr.klm(eventos, False)

    # KPIs CMI (2026 default y 2025, mas calculo directo sobre hechos del lote)
    sc_2026 = cli.get("/api/v1/cmi/scorecard").json()
    sc_2025 = cli.get("/api/v1/cmi/scorecard", params={"gestion": 2025}).json()
    kpis_2026 = {k["codigo"]: k.get("valor") for p in sc_2026.get("perspectivas", []) for k in p.get("kpis", [])}
    kpis_2025 = {k["codigo"]: k.get("valor") for p in sc_2025.get("perspectivas", []) for k in p.get("kpis", [])}

    from core.database import SessionLocal
    with SessionLocal() as db:
        por_archivo = consultar_metricas_por_archivo(db, id_lote)
        total_fact_m = db.execute(text("SELECT count(*) FROM fact_marketing")).scalar() or 0
        # KPI-10 global sobre el lote (media ponderada de nivel_confianza_ia en rendimiento + financiero)
        r_g10 = db.execute(text(
            "SELECT SUM(cnt), SUM(sm) FROM ("
            "  SELECT count(nivel_confianza_ia) AS cnt, COALESCE(SUM(nivel_confianza_ia),0) AS sm "
            "  FROM fact_rendimiento_academico WHERE nivel_confianza_ia IS NOT NULL "
            "  UNION ALL "
            "  SELECT count(nivel_confianza_ia) AS cnt, COALESCE(SUM(nivel_confianza_ia),0) AS sm "
            "  FROM fact_situacion_financiera WHERE nivel_confianza_ia IS NOT NULL"
            ") t"
        )).first()
        kpi10_lote = round(float(r_g10[1]) / float(r_g10[0]), 4) if (r_g10 and r_g10[0]) else None

    tot_hechos = sum(v["hechos_cargados"] for v in por_archivo.values())
    tot_directo = sum(v["directo"] for v in por_archivo.values())
    kpi11_lote = round(100.0 * tot_directo / tot_hechos, 2) if tot_hechos else None

    for arch, d in por_archivo.items():
        d["entidades_por_etapa"] = {
            k: int(stats_etapas[arch].get(k, 0))
            for k in ("CI_EXACTA", "ENCABEZADO", "FUZZY", "REGEX", "BETO")
        }

    out = {
        "modo": modo,
        "id_lote": id_lote,
        "tiempos_s": {
            "carga_y_lectura_s": t_carga_lectura,
            "espera_lectura_s": t_espera,
            "consolidacion_s": t_consolidacion,
            "revision_maquina_s": revision["resumen"]["tiempo_maquina_real_aprobaciones_s"],
            "tiempo_maquina_total_s": round(t_carga_lectura + t_espera + t_consolidacion + revision["resumen"]["tiempo_maquina_real_aprobaciones_s"], 2),
        },
        "bandeja": {
            "casos": primera["total_casos"],
            "grupos": primera["total_grupos"],
            "grupos_manuales": sum(1 for g in grupos if (g.get("accion_grupo") or "MANUAL") == "MANUAL"),
            "casos_manuales": sum(g["n"] for g in grupos if (g.get("accion_grupo") or "MANUAL") == "MANUAL"),
        },
        "klm": {
            "con_espera_10s_s": k_con,
            "sin_espera_s": k_sin,
        },
        "kpis": {
            "KPI-10_lote": kpi10_lote,
            "KPI-11_lote": kpi11_lote,
            "KPI-18_bandeja": kpis_2026.get("KPI-18"),
            "scorecard_2026": {k: kpis_2026.get(k) for k in ("KPI-10", "KPI-11", "KPI-18")},
            "scorecard_2025": {k: kpis_2025.get(k) for k in ("KPI-10", "KPI-11", "KPI-18")},
        },
        "fact_marketing_total": int(total_fact_m),
        "por_archivo": por_archivo,
    }
    salida.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if dump_beto is not None:
        dump_beto.write_text(json.dumps(ents_beto, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"modo": modo, "tiempo_maquina_s": out["tiempos_s"]["tiempo_maquina_total_s"],
                      "bandeja": out["bandeja"], "kpis": out["kpis"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
