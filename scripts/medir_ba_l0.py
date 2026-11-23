#!/usr/bin/env python3
"""
scripts/medir_ba_l0.py
----------------------
BA-L0: Línea base con los 4 flags de BETO apagados (a0) sobre el lote 1 en beto_pg_tmpfs.
Mide por documento/fuente:
  - lineas_totales, lineas_ruido, lineas_evaluadas
  - pendientes_indice (las que llegan a indices_cascada) y aciertos de caché
  - entidades por etapa (CI_EXACTA, ENCABEZADO, FUZZY, REGEX, BETO) y total_entidades
  - distribución por bandas (>=0.85, [0.60,0.85), <0.60) y casos a revisión
  - tiempo de ciclo (extracción + índice)

Salida: docs/mediciones/ba_l0_linea_base.csv
"""
import csv
import hashlib
import os
import sys
import time
from pathlib import Path

os.environ["BETO_CASCADA_FINAL"] = "0"
os.environ["BETO_ACUERDO_QC"] = "0"
os.environ["BETO_SUGERENCIA_HITL"] = "0"
os.environ["BETO_VENTANA"] = "0"

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_origen import DimOrigenDocumental
from models.staging_registro import StagingRegistroCrudo
from pipeline.semantic.indice_confianza import (
    BANDA_CONSOLIDADO,
    BANDA_REVISION,
    BANDA_STAGING,
    texto_para_indice,
)
from routers.dataops._comun import categoria_ruteo as resolver_categoria_ruteo
from routers.dataops.consolidacion import _motivo_sin_entidad
from routers.dataops.extraccion import (
    _docentes_con_contexto,
    extract_entities_from_line,
)
from services import encuesta_canonica
from services.confianza_service import banda_de, obtener_indices
from services.extraccion_por_encabezado import campos_por_encabezado, fila_resuelta_por_regla

DB_URL = os.environ.get(
    "BA_TMPFS_DB_URL",
    "postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/ba_base",
)
OUT_CSV = Path(os.environ.get("BA_L0_OUT", "/tmp/ba_l0_linea_base.csv"))

ETAPAS = ("CI_EXACTA", "ENCABEZADO", "FUZZY", "REGEX", "BETO")


def main() -> None:
    engine = create_engine(DB_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        # Limpiar cache_indice_beto en tmpfs para medir con caché vacía
        db.execute(text("TRUNCATE TABLE public.cache_indice_beto"))
        db.commit()

        docs = (
            db.query(DimOrigenDocumental)
            .filter(DimOrigenDocumental.id_lote == 1)
            .order_by(DimOrigenDocumental.id_documento.asc())
            .all()
        )
        doc_map = {d.id_documento: d for d in docs}
        stgs = (
            db.query(StagingRegistroCrudo)
            .filter(StagingRegistroCrudo.id_documento.in_(list(doc_map.keys())))
            .order_by(StagingRegistroCrudo.id_documento.asc(), StagingRegistroCrudo.id.asc())
            .all()
        )
        estudiantes = db.query(DimEstudiante).filter(DimEstudiante.deprecado == False).all()
        docentes = _docentes_con_contexto(db)
        modulos = db.query(DimModulo).all()

        por_doc = {}
        for d in docs:
            por_doc[d.id_documento] = {
                "id_lote": d.id_lote,
                "id_documento": d.id_documento,
                "nombre_archivo": d.nombre_archivo,
                "tipo_fuente": (d.tipo_fuente or "ACTA").upper(),
                "lineas_totales": 0,
                "lineas_ruido": 0,
                "lineas_evaluadas": 0,
                "pendientes_indice": 0,
                "cache_hits_vacia": 0,
                "CI_EXACTA": 0,
                "ENCABEZADO": 0,
                "FUZZY": 0,
                "REGEX": 0,
                "BETO": 0,
                "total_entidades": 0,
                "banda_consolidado": 0,
                "banda_revision": 0,
                "banda_staging": 0,
                "casos_a_revision_actual": 0,
                "casos_a_revision_nuevo": 0,
                "tiempo_extraccion_s": 0.0,
                "tiempo_indice_s": 0.0,
                "tiempo_total_s": 0.0,
            }

        # Cache en memoria para simular cache_indice_beto sobre tmpfs sin tocar giragroup_db
        cache_simulada = {}

        def _obtener_indices_tmpfs(lineas_pend):
            textos = [texto_para_indice(l) for l in lineas_pend]
            hashes = [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in textos]
            hits = sum(1 for h in hashes if h in cache_simulada)
            faltan = {h: t for h, t in zip(hashes, textos) if h not in cache_simulada}
            if faltan:
                from services.confianza_service import _inferir
                vals = _inferir(list(faltan.values()))
                for h, v in zip(faltan.keys(), vals):
                    if v is not None:
                        cache_simulada[h] = v
            return [cache_simulada.get(h) for h in hashes], hits

        t_global_0 = time.perf_counter()
        for stg in stgs:
            d = doc_map[stg.id_documento]
            row = por_doc[d.id_documento]
            doc_fuente = (d.tipo_fuente or "ACTA").upper().strip()
            if (stg.categoria or "").strip().lower() == "evaluacion_docente":
                doc_fuente = "EVALUACION_DOCENTE"
            doc_escala = d.tipo_escala or "CENTESIMAL_100"
            if doc_fuente in ("COBRANZA", "ADMISION"):
                doc_escala = None

            raw_text = (stg.texto_plano or "").strip()
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
            if not lines:
                continue
            row["lineas_totales"] += len(lines)

            stg_cat = (stg.categoria or "").strip().lower()
            if stg_cat in ("planificacion", "planificacion_meta") or doc_fuente == "PLANIFICACION":
                t0 = time.perf_counter()
                row["lineas_evaluadas"] += len(lines)
                row["banda_consolidado"] += len(lines)
                row["tiempo_extraccion_s"] += time.perf_counter() - t0
                continue

            cat_ruteo = resolver_categoria_ruteo(doc_fuente, stg.categoria)
            t0 = time.perf_counter()
            campos_por_linea = [campos_por_encabezado([c.strip() for c in l.split("|")]) for l in lines]
            perfil_encuesta = encuesta_canonica.perfilar(campos_por_linea) if cat_ruteo == "evaluacion_docente" else None
            resueltas_regla = [fila_resuelta_por_regla(c, cat_ruteo) for c in campos_por_linea]

            pendientes_idx = [i for i, r in enumerate(resueltas_regla) if not r]
            row["pendientes_indice"] += len(pendientes_idx)
            t1 = time.perf_counter()
            indices_linea = [None] * len(lines)
            if pendientes_idx:
                vals, hits = _obtener_indices_tmpfs([lines[i] for i in pendientes_idx])
                row["cache_hits_vacia"] += hits
                for i, v in zip(pendientes_idx, vals):
                    indices_linea[i] = v
            t_ind = time.perf_counter() - t1
            row["tiempo_indice_s"] += t_ind

            t_ext_0 = time.perf_counter()
            for k_fila, (line, indice, campos_linea) in enumerate(zip(lines, indices_linea, campos_por_linea)):
                motivo_ruido = _motivo_sin_entidad(campos_linea, cat_ruteo, perfil_encuesta)
                if motivo_ruido:
                    row["lineas_ruido"] += 1
                    continue
                row["lineas_evaluadas"] += 1
                ents, score, req_rev = extract_entities_from_line(
                    line, estudiantes, docentes, modulos, tipo_escala=doc_escala, tipo_fuente=doc_fuente
                )
                for ent in ents:
                    origen = str(ent.get("origen_confianza") or ent.get("fuente_resolucion") or "").upper()
                    if origen == "REGLA_ENCABEZADO":
                        origen = "ENCABEZADO"
                    if origen in ETAPAS:
                        row[origen] += 1
                    row["total_entidades"] += 1

                banda = BANDA_CONSOLIDADO if resueltas_regla[k_fila] else banda_de(indice)
                if banda == BANDA_CONSOLIDADO:
                    row["banda_consolidado"] += 1
                    if req_rev:
                        row["casos_a_revision_actual"] += 1
                        row["casos_a_revision_nuevo"] += 1
                elif banda == BANDA_REVISION:
                    row["banda_revision"] += 1
                    row["casos_a_revision_actual"] += 1
                    row["casos_a_revision_nuevo"] += 1
                else:
                    row["banda_staging"] += 1
                    row["casos_a_revision_actual"] += 1
                    row["casos_a_revision_nuevo"] += 1

            row["tiempo_extraccion_s"] += (time.perf_counter() - t0) - t_ind
            row["tiempo_total_s"] = round(row["tiempo_extraccion_s"] + row["tiempo_indice_s"], 3)

        total_t = round(time.perf_counter() - t_global_0, 3)

        rows = list(por_doc.values())
        for r in rows:
            r["tiempo_extraccion_s"] = round(r["tiempo_extraccion_s"], 3)
            r["tiempo_indice_s"] = round(r["tiempo_indice_s"], 3)
            r["tiempo_total_s"] = round(r["tiempo_extraccion_s"] + r["tiempo_indice_s"], 3)
            suma_etapas = sum(r[e] for e in ETAPAS)
            assert suma_etapas == r["total_entidades"], f"Descuadre en doc {r['id_documento']}: {suma_etapas} != {r['total_entidades']}"

        tot = {
            "id_lote": 1,
            "id_documento": "TOTAL",
            "nombre_archivo": "TOTAL_LOTE_1",
            "tipo_fuente": "TODAS",
        }
        for k in (
            "lineas_totales", "lineas_ruido", "lineas_evaluadas", "pendientes_indice", "cache_hits_vacia",
            "CI_EXACTA", "ENCABEZADO", "FUZZY", "REGEX", "BETO", "total_entidades",
            "banda_consolidado", "banda_revision", "banda_staging",
            "casos_a_revision_actual", "casos_a_revision_nuevo",
        ):
            tot[k] = sum(r[k] for r in rows)
        tot["tiempo_extraccion_s"] = round(sum(r["tiempo_extraccion_s"] for r in rows), 3)
        tot["tiempo_indice_s"] = round(sum(r["tiempo_indice_s"] for r in rows), 3)
        tot["tiempo_total_s"] = total_t
        rows.append(tot)

        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        print(f"BA-L0 OK -> {OUT_CSV} (tiempo_total_s={total_t}, total_entidades={tot['total_entidades']}, pendientes_indice={tot['pendientes_indice']})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
