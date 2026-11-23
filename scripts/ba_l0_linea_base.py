"""BA-L0: Línea base con flags apagados sobre el lote recargado (id_lote=1) en giragroup_db (solo lectura)."""
import csv
import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path("/app") if Path("/app/core").exists() else Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend") if (ROOT / "backend").exists() else str(ROOT))
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from core.database import SessionLocal
from models.dim_origen import DimOrigenDocumental
from models.staging_registro import StagingRegistroCrudo
from models.staging_entidad import StagingEntidadNoResuelta
from pipeline.semantic.indice_confianza import texto_para_indice
from routers.dataops._comun import categoria_ruteo as resolver_categoria_ruteo
from routers.dataops.evaluacion import _evaluacion_lectura
from routers.dataops.lectura import _ETAPAS_CASCADA
from services.extraccion_por_encabezado import campos_por_encabezado, fila_resuelta_por_regla


def main():
    id_lote = int(os.getenv("BA_ID_LOTE", "1"))
    out_path = Path(os.getenv("BA_L0_OUT", str(ROOT / "docs" / "mediciones" / "ba_l0_linea_base.csv")))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        docs = db.query(DimOrigenDocumental).filter_by(id_lote=id_lote).order_by(DimOrigenDocumental.id_documento).all()
        if not docs:
            raise RuntimeError(f"No hay documentos para id_lote={id_lote}")

        # 1. Tiempos de ciclo de dataops_tarea
        tareas = db.execute(
            text("""
                SELECT tipo, estado,
                       EXTRACT(EPOCH FROM (actualizado_en - iniciado_en))::numeric(10,2) AS dur_s
                  FROM dataops_tarea
                 WHERE id_lote = :lote
                 ORDER BY id
            """),
            {"lote": id_lote},
        ).fetchall()
        tiempos = {t.tipo: float(t.dur_s or 0.0) for t in tareas}
        tiempo_ciclo_s = round(sum(tiempos.values()), 2)

        # 2. Evaluación de lectura (conteo de entidades por etapa y fuente)
        eval_res = _evaluacion_lectura(db, docs)
        por_doc_etapas = defaultdict(lambda: {e: 0 for e in _ETAPAS_CASCADA})
        por_doc_beto_leidas = defaultdict(int)
        por_doc_tuplas = defaultdict(int)
        for reg in eval_res["detalles"]:
            doc_id = reg.get("id_documento")
            por_doc_tuplas[doc_id] += 1
            lectura = reg.get("lectura") or {}
            entidades = lectura.get("entidades") or reg.get("entidades") or []
            beto_ents = lectura.get("beto_ents") or reg.get("beto_ents") or []
            por_doc_beto_leidas[doc_id] += len(beto_ents)
            for ent in entidades:
                if not isinstance(ent, dict):
                    continue
                origen = str(ent.get("origen_confianza") or ent.get("fuente_resolucion") or "").upper()
                if origen == "REGLA_ENCABEZADO":
                    origen = "ENCABEZADO"
                if origen in por_doc_etapas[doc_id]:
                    por_doc_etapas[doc_id][origen] += 1

        # 3. Staging lines -> pendientes de indices_cascada y aciertos de cache_indice_beto
        doc_ids = [d.id_documento for d in docs]
        stgs = (
            db.query(StagingRegistroCrudo)
            .filter(StagingRegistroCrudo.id_documento.in_(doc_ids), StagingRegistroCrudo.es_ruido == False)  # noqa: E712
            .all()
        )
        hashes_por_doc = defaultdict(list)
        pendientes_por_doc = defaultdict(int)
        resueltas_regla_por_doc = defaultdict(int)
        lineas_stg_por_doc = defaultdict(int)

        doc_map = {d.id_documento: d for d in docs}
        for s in stgs:
            d = doc_map[s.id_documento]
            cat = resolver_categoria_ruteo(d.tipo_fuente, s.categoria)
            lines = [ln.strip() for ln in (s.texto_plano or "").split("\n") if ln.strip()]
            lineas_stg_por_doc[s.id_documento] += len(lines)
            if cat == "planificacion":
                resueltas_regla_por_doc[s.id_documento] += len(lines)
                continue
            for ln in lines:
                campos = campos_por_encabezado([c.strip() for c in ln.split("|")])
                if fila_resuelta_por_regla(campos, cat):
                    resueltas_regla_por_doc[s.id_documento] += 1
                else:
                    pendientes_por_doc[s.id_documento] += 1
                h = hashlib.sha256(texto_para_indice(ln).encode("utf-8")).hexdigest()
                hashes_por_doc[s.id_documento].append(h)

        all_hashes = sorted({h for hs in hashes_por_doc.values() for h in hs})
        en_cache = set()
        for i in range(0, len(all_hashes), 5000):
            rows = db.execute(
                text("SELECT hash_texto FROM cache_indice_beto WHERE hash_texto = ANY(:h)"),
                {"h": all_hashes[i:i + 5000]},
            ).fetchall()
            en_cache.update(str(r[0]).strip() for r in rows)

        cache_hits_por_doc = {
            doc_id: sum(1 for h in hs if h in en_cache)
            for doc_id, hs in hashes_por_doc.items()
        }

        # 4. Casos a revisión en stg_entidad_no_resuelta
        rev_rows = db.execute(
            text("""
                SELECT id_documento, count(*) AS n
                  FROM stg_entidad_no_resuelta
                 WHERE id_documento = ANY(:ids)
                 GROUP BY id_documento
            """),
            {"ids": doc_ids},
        ).fetchall()
        rev_por_doc = {r.id_documento: int(r.n) for r in rev_rows}

        # 5. Agrupar por tipo_fuente
        por_fuente = defaultdict(lambda: {
            "archivos": 0, "lineas_stg": 0, "tuplas_evaluadas": 0,
            "pendientes_indice_beto": 0, "resueltas_regla": 0, "aciertos_cache_indice": 0,
            "CI_EXACTA": 0, "ENCABEZADO": 0, "FUZZY": 0, "REGEX": 0, "BETO": 0,
            "beto_leidas": 0, "beto_aceptadas": 0, "total_entidades": 0, "casos_revision": 0,
        })
        for d in docs:
            f = por_fuente[d.tipo_fuente]
            f["archivos"] += 1
            f["lineas_stg"] += lineas_stg_por_doc[d.id_documento]
            f["tuplas_evaluadas"] += por_doc_tuplas[d.id_documento]
            f["pendientes_indice_beto"] += pendientes_por_doc[d.id_documento]
            f["resueltas_regla"] += resueltas_regla_por_doc[d.id_documento]
            f["aciertos_cache_indice"] += cache_hits_por_doc.get(d.id_documento, 0)
            for et in _ETAPAS_CASCADA:
                f[et] += por_doc_etapas[d.id_documento][et]
            f["beto_leidas"] += por_doc_beto_leidas[d.id_documento]
            f["beto_aceptadas"] += por_doc_etapas[d.id_documento]["BETO"]
            f["total_entidades"] += sum(por_doc_etapas[d.id_documento].values())
            f["casos_revision"] += rev_por_doc.get(d.id_documento, 0)

        cols = [
            "id_lote", "tipo_fuente", "archivos", "lineas_stg", "tuplas_evaluadas",
            "pendientes_indice_beto", "resueltas_regla", "aciertos_cache_indice",
            "CI_EXACTA", "ENCABEZADO", "FUZZY", "REGEX", "BETO",
            "total_entidades", "beto_leidas", "beto_aceptadas", "casos_revision",
            "tiempo_ingesta_s", "tiempo_lectura_beto_s", "tiempo_prep_revision_s", "tiempo_ciclo_s",
        ]
        tot = {k: 0 for k in cols if k not in ("id_lote", "tipo_fuente", "tiempo_ingesta_s", "tiempo_lectura_beto_s", "tiempo_prep_revision_s", "tiempo_ciclo_s")}
        rows_out = []
        for fuente in sorted(por_fuente.keys()):
            d_f = por_fuente[fuente]
            assert sum(d_f[e] for e in _ETAPAS_CASCADA) == d_f["total_entidades"], f"Descuadre en {fuente}"
            row = {
                "id_lote": id_lote,
                "tipo_fuente": fuente,
                **d_f,
                "tiempo_ingesta_s": tiempos.get("INGESTA", 0.0),
                "tiempo_lectura_beto_s": tiempos.get("LECTURA_BETO", 0.0),
                "tiempo_prep_revision_s": tiempos.get("PREPARACION_REVISION", 0.0),
                "tiempo_ciclo_s": tiempo_ciclo_s,
            }
            rows_out.append(row)
            for k in tot:
                tot[k] += d_f[k]

        rows_out.append({
            "id_lote": id_lote,
            "tipo_fuente": "TOTAL",
            **tot,
            "tiempo_ingesta_s": tiempos.get("INGESTA", 0.0),
            "tiempo_lectura_beto_s": tiempos.get("LECTURA_BETO", 0.0),
            "tiempo_prep_revision_s": tiempos.get("PREPARACION_REVISION", 0.0),
            "tiempo_ciclo_s": tiempo_ciclo_s,
        })

        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows_out)
        print(f"Escrito {out_path} ({len(rows_out)} filas). TOTAL={tot}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
