"""
Ronda 7, tarea 2: aplica las reglas nuevas al stock pendiente (staging y hechos en revisión) del DW indicado por DATABASE_URL.
  Staging  - CI_NOMBRE_DISCORDANTE: variante de nombre con CI exacta -> resuelto (CI_NOMBRE_VARIANTE en el log).
           - BAJA_CONFIANZA_IA: línea sin hecho posible -> descartada (LINEAS_NO_APLICABLES); línea que las reglas resuelven -> se carga.
           - HOMONIMIA: valor que no es una persona (dígitos / 'clave: valor') -> descartado.
  Hechos   - académicos/financieros en revisión que las reglas dan por buenos (estudiante, módulo, fecha, estado y combinación válidos,
             nota o acta sin notas con estado válido) -> requiere_revision = FALSE.
Uso: DATABASE_URL=... python scripts/stock_reglas_nuevas.py <salida.json>   (dentro de giragroup_api para acceder al catálogo de estados)
"""
import json, re, sys, time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from sqlalchemy import text
from core.database import SessionLocal
from models.fact_rendimiento import FactRendimientoAcademico
from models.log_inconsistencia import LogInconsistencia
from routers.pipeline import _campos_financieros_por_encabezado, _motivo_no_aplicable, _resolver_linea
from services.bandeja_grupos import motivo_estado
from services.dw_loader import DWLoaderService, _es_variante_de_nombre
from services.extraccion_por_encabezado import campos_por_encabezado, factores_escala_por_programa
from pipeline.normalization.person_resolver import es_correo

CATEGORIA = {"ACTA": "academico", "MOODLE": "academico", "COBRANZA": "financiero", "RENTABILIDAD": "rentabilidad", "EGRESOS": "rentabilidad",
             "ADMISION": "admision", "MARKETING": "marketing", "EVALUACION_DOCENTE": "evaluacion_docente", "TECHOS": "rentabilidad", "PLANIFICACION": "rentabilidad"}
db = SessionLocal()
t0 = time.perf_counter()


def estado():
    q = lambda s: db.execute(text(s)).scalar()
    por_motivo = {f"{r[0]}": r[1] for r in db.execute(text("SELECT motivo, count(*) FROM stg_entidad_no_resuelta WHERE NOT resuelto GROUP BY 1 ORDER BY 2 DESC"))}
    return {"staging_pendiente": q("SELECT count(*) FROM stg_entidad_no_resuelta WHERE NOT resuelto"), "staging_por_motivo": por_motivo,
            "hechos_aca_en_revision": q("SELECT count(*) FROM fact_rendimiento_academico WHERE requiere_revision"),
            "hechos_fin_en_revision": q("SELECT count(*) FROM fact_situacion_financiera WHERE requiere_revision"),
            "hechos_aca": q("SELECT count(*) FROM fact_rendimiento_academico"), "hechos_fin": q("SELECT count(*) FROM fact_situacion_financiera"),
            "estudiantes": q("SELECT count(*) FROM dim_estudiante")}


antes = estado()
res = {"antes": antes, "acciones": Counter()}
tipo_fuente = {r[0]: (r[1] or "ACTA").upper() for r in db.execute(text("SELECT id_documento, tipo_fuente FROM dim_origen_documental"))}
loader = DWLoaderService(db)

# ---- staging -------------------------------------------------------------------------------------------------------------
filas = db.execute(text("SELECT id_staging, id_documento, motivo, texto_original, ci_temporal, mejor_candidato FROM stg_entidad_no_resuelta WHERE NOT resuelto ORDER BY id_staging")).all()
resolver, logs = [], Counter()
for id_stg, doc, motivo, texto, ci, mejor in filas:
    nuevo = None
    if motivo == "CI_NOMBRE_DISCORDANTE":
        m = re.search(r"Nombre: (.*?) \(Discordante con: (.*)\)\s*$", texto or "", re.S)
        if m and _es_variante_de_nombre(m.group(2), m.group(1)):
            nuevo = ("RESUELTO_VARIANTE", "CI_NOMBRE_VARIANTE")
            if re.match(r"^\s*estudiante\s+ci\b", m.group(2), re.I) and ci:
                db.execute(text("UPDATE dim_estudiante SET nombre_completo = :n WHERE (ci_numero = :c OR ci = :c) AND nombre_completo ~* '^\\s*estudiante\\s+ci\\y'"), {"n": m.group(1).strip(), "c": ci})
    elif motivo == "HOMONIMIA":
        t = (texto or "").strip()
        if re.search(r"\d", t) or re.match(r"^[^:]{1,40}:\s", t) or es_correo(t):
            nuevo = ("DESCARTADO_REGLA", "NO_ES_PERSONA")
    elif motivo == "BAJA_CONFIANZA_IA":
        celdas = [c.strip() for c in (texto or "").split("|")]
        if _motivo_no_aplicable(celdas):
            nuevo = ("DESCARTADO_REGLA", "LINEAS_NO_APLICABLES")
        else:
            cat = CATEGORIA.get(tipo_fuente.get(doc, "ACTA"), "academico")
            campos_fin = _campos_financieros_por_encabezado(celdas) if cat == "financiero" else None
            campos = campos_por_encabezado(celdas)
            try:
                lista, ents, por_reglas = _resolver_linea(cat, celdas, campos, campos_fin, factores_escala_por_programa([campos]) if cat == "academico" else None)
            except Exception:
                por_reglas = False
            if por_reglas:
                ok = False
                try:
                    for r in lista:
                        rev = r.pop("_revision_fila", False)
                        out = loader.cargar_registro({"doc_id": doc, "categoria": cat, "entidades_ner": ents, "resoluciones": r, "calidad": {"requiere_revision": rev},
                                                      "clave_origen": None}, id_usuario=None)
                        ok = ok or out.get("status") == "loaded"
                    db.flush()
                except Exception:
                    db.rollback()
                    ok = False
                if ok:
                    nuevo = ("RESUELTO_REGLAS", "LINEA_CARGADA_POR_REGLAS")
    if nuevo:
        resolver.append((id_stg, nuevo[0]))
        logs[(doc, nuevo[1])] += 1
        res["acciones"][f"{motivo} -> {nuevo[1]}"] += 1
for i in range(0, len(resolver), 5000):
    parte = resolver[i:i + 5000]
    db.execute(text("UPDATE stg_entidad_no_resuelta SET resuelto = TRUE, estado_resolucion = v.e, resuelto_en = now() FROM (SELECT unnest(CAST(:ids AS int[])) AS i, unnest(CAST(:es AS text[])) AS e) v WHERE id_staging = v.i"),
               {"ids": [p[0] for p in parte], "es": [p[1] for p in parte]})
for (doc, tipo), n in logs.items():  # un registro agregado por documento y regla (no uno por caso)
    db.add(LogInconsistencia(id_documento=doc, campo_afectado="stock_staging", valor_recibido=str(n), tipo_regla=tipo, severidad="BAJA",
                             estado_resolucion="REGISTRADO", descripcion=f"{n} casos de staging resueltos por las reglas nuevas ({tipo})"))
db.commit()

# ---- hechos académicos en revisión ---------------------------------------------------------------------------------------
liberar = []
for h in db.query(FactRendimientoAcademico).filter(FactRendimientoAcademico.requiere_revision == True).all():  # noqa: E712
    estados_ok = motivo_estado(h.estado_academico, h.estado_tutoria, h.estado_arca) == "OK"
    sin_nota_ok = h.nota_final is not None or (h.estado_academico or h.estado_arca)  # acta sin notas con estado válido
    if h.id_estudiante and h.id_modulo and h.id_tiempo and estados_ok and sin_nota_ok:
        liberar.append(h.id_hecho_aca)
    else:
        res["acciones"]["hecho_aca_se_queda: " + ("combinacion/estado" if not estados_ok else "falta estudiante, modulo o fecha")] += 1
for i in range(0, len(liberar), 5000):
    db.execute(text("UPDATE fact_rendimiento_academico SET requiere_revision = FALSE WHERE id_hecho_aca = ANY(:i)"), {"i": liberar[i:i + 5000]})
res["acciones"]["hecho_aca_liberado_por_reglas"] = len(liberar)
if liberar:
    db.add(LogInconsistencia(id_documento=None, campo_afectado="requiere_revision", valor_recibido=str(len(liberar)), tipo_regla="HECHOS_LIBERADOS_POR_REGLAS", severidad="BAJA",
                             estado_resolucion="REGISTRADO", descripcion=f"{len(liberar)} hechos académicos en revisión liberados: estudiante, módulo, fecha, estado y combinación válidos"))
# financieros: estudiante, fecha y monto presentes
r_fin = db.execute(text("UPDATE fact_situacion_financiera SET requiere_revision = FALSE WHERE requiere_revision AND id_estudiante IS NOT NULL AND id_tiempo IS NOT NULL AND (monto_deuda IS NOT NULL OR monto_pagado IS NOT NULL)"))
res["acciones"]["hecho_fin_liberado_por_reglas"] = r_fin.rowcount
db.commit()
res["despues"] = estado()
res["acciones"] = dict(res["acciones"])
res["segundos"] = round(time.perf_counter() - t0, 1)
Path(sys.argv[1]).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
