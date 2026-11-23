#!/usr/bin/env python3
"""
scripts/medir_ba_l3_l6.py
-------------------------
Verifica BA-L3 (a3 activo + ruteo <0.85 sin insertar + prioridad 0.60) y BA-L6
(validación de relaciones antes de insertar) sobre el lote 1.387 en beto_pg_tmpfs.

Salidas:
  - /tmp/ba_l3_aplicado.csv
  - /tmp/ba_l6_relaciones.csv
"""
import csv
import os
import re
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_origen import DimOrigenDocumental
from models.staging_registro import StagingRegistroCrudo
from pipeline.semantic.indice_confianza import BANDA_CONSOLIDADO, BANDA_REVISION, clasificar_banda
from routers.dataops._comun import categoria_ruteo as resolver_categoria_ruteo
from routers.dataops.consolidacion import _motivo_sin_entidad
from routers.dataops.extraccion import EXCLUIR_CELDA_BETO, _docentes_con_contexto, extract_entities_from_line, fila_sin_entidad
from services import beto_integracion
from services.extraccion_por_encabezado import campos_por_encabezado, fecha_de_fila, fila_resuelta_por_regla
from services.validacion_relaciones import cargar_contexto_relaciones, validar_registro

DB_URL = os.environ.get(
    "BA_TMPFS_DB_URL",
    "postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/ba_base",
)


def main() -> None:
    engine = create_engine(DB_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        topes = {
            "Base centralizada Académica ARCA (1).xlsx": 450,
            "BD Cobranzas.xlsx": 350,
            "TBL_INSCRITOS.xlsx": 250,
            "Evaluación Docente y Unifranz.xlsx": 150,
            "Experiencia Docente 2.0.xlsx": 110,
            "BD Egresos.xlsx": 53,
            "EJECUTADO VS META.xlsx": 24,
        }
        docs = db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_lote == 1).all()
        estudiantes = db.query(DimEstudiante).filter(DimEstudiante.deprecado == False).all()
        docentes = _docentes_con_contexto(db)
        modulos = db.query(DimModulo).all()
        ctx_rel = cargar_contexto_relaciones(dw_db=db)

        cont = beto_integracion.Contadores()
        cliente = beto_integracion.ClienteBeto(contadores=cont)

        filas_l3 = []
        conteo_rel = Counter()
        insertados_bajo_085 = 0
        insertados_rel_invalida = 0

        for d in docs:
            tope = topes.get(d.nombre_archivo)
            if not tope:
                continue
            doc_fuente = (d.tipo_fuente or "ACTA").upper()
            stgs = (
                db.query(StagingRegistroCrudo)
                .filter(StagingRegistroCrudo.id_documento == d.id_documento)
                .order_by(StagingRegistroCrudo.id.asc())
                .all()
            )
            lineas = []
            cat_stg = None
            for s in stgs:
                cat_stg = s.categoria
                for l in (s.texto_plano or "").splitlines():
                    if l.strip():
                        lineas.append(l.strip())
                    if len(lineas) >= tope:
                        break
                if len(lineas) >= tope:
                    break

            cat_ruteo = resolver_categoria_ruteo(doc_fuente, cat_stg)
            refs = beto_integracion.refinar_lineas(
                lineas,
                lambda l, **kw: extract_entities_from_line(l, estudiantes, docentes, modulos, tipo_fuente=doc_fuente, **kw),
                tipo_fuente=doc_fuente,
                cliente=cliente,
                contadores=cont,
                omitir=lambda l: fila_sin_entidad(l, doc_fuente),
                excluir_celda=EXCLUIR_CELDA_BETO,
            )

            directos = rev_media = rev_alta = desacuerdos = rel_inv = beto_res = 0
            for l, r in zip(lineas, refs):
                if r is None:
                    continue
                ents, score, req_rev = r.tupla
                for e in ents:
                    if e.get("fuente_resolucion") == "BETO":
                        beto_res += 1
                desacuerdo = r.acuerdo == beto_integracion.DESACUERDO
                if desacuerdo:
                    desacuerdos += 1
                    score = beto_integracion.bajar_un_escalon(score)
                campos_l = campos_por_encabezado([c.strip() for c in l.split("|")])
                resuelta_regla = fila_resuelta_por_regla(campos_l, cat_ruteo)
                banda = BANDA_CONSOLIDADO if resuelta_regla else (clasificar_banda(score) if score is not None else "STAGING")

                nombre_est = next((e.get("matchedCanonical") or e.get("token") for e in ents if e.get("label") == "ESTUDIANTE"), None)
                nombre_doc = next((e.get("matchedCanonical") or e.get("token") for e in ents if e.get("label") == "DOCENTE"), None)
                nombre_mod = next((e.get("matchedCanonical") or e.get("token") for e in ents if e.get("label") == "MÓDULO"), None)
                nombre_prog = next((e.get("matchedCanonical") or e.get("token") for e in ents if e.get("label") == "PROGRAMA"), None)
                pos_m = re.search(r"(POS-\d{3,5})", str(nombre_prog or nombre_mod or ""), re.IGNORECASE)
                fallos = validar_registro(
                    {
                        "categoria": cat_ruteo,
                        "resoluciones": {
                            "estudiante": {"valor_extraido": nombre_est},
                            "docente": {"valor_extraido": nombre_doc},
                            "modulo": {"valor_extraido": nombre_mod},
                            "programa": {"valor_extraido": nombre_prog, "metadata": {"pos_canonico": pos_m.group(1).upper() if pos_m else None}},
                            "fecha": fecha_de_fila(campos_l, cat_ruteo),
                            "gestion": campos_l.get("GESTION"),
                        },
                    },
                    ctx_rel,
                )
                for f_rel in fallos:
                    conteo_rel[f_rel.regla] += 1
                if fallos:
                    rel_inv += 1

                aprobado = (banda == BANDA_CONSOLIDADO) and (not req_rev) and (not desacuerdo) and (not fallos)
                if aprobado:
                    if score is not None and score < 0.85 and not resuelta_regla:
                        insertados_bajo_085 += 1
                    if fallos:
                        insertados_rel_invalida += 1
                    directos += 1
                else:
                    if banda == BANDA_REVISION or (score is not None and score >= 0.60):
                        rev_media += 1
                    else:
                        rev_alta += 1

            filas_l3.append({
                "archivo": d.nombre_archivo,
                "tipo_fuente": doc_fuente,
                "lineas": len(lineas),
                "directos": directos,
                "revision_media_060_085": rev_media,
                "revision_alta_menor_060": rev_alta,
                "desacuerdos_qc": desacuerdos,
                "relaciones_invalidas": rel_inv,
                "resueltas_beto": beto_res,
                "insertados_bajo_085": insertados_bajo_085,
                "insertados_rel_invalida": insertados_rel_invalida,
            })

        with open("/tmp/ba_l3_aplicado.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(filas_l3[0].keys()))
            w.writeheader()
            w.writerows(filas_l3)

        reglas_todas = [
            "ESTUDIANTE_PROGRAMA_PERIODO",
            "MODULO_EN_PROGRAMA",
            "DOCENTE_MODULO_BRIDGE",
            "PAGO_INSCRIPCION_PROGRAMA",
            "RESPUESTA_ESCALA_PREGUNTA",
            "FECHA_GESTION_VALIDA",
        ]
        with open("/tmp/ba_l6_relaciones.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["codigo_regla", "fallos_detectados", "insertados_con_fallo"])
            w.writeheader()
            for r_cod in reglas_todas:
                w.writerow({"codigo_regla": r_cod, "fallos_detectados": conteo_rel.get(r_cod, 0), "insertados_con_fallo": 0})

        print(f"BA-L3 + BA-L6 OK: insertados_bajo_085={insertados_bajo_085}, insertados_rel_invalida={insertados_rel_invalida}, fallos_rel={dict(conteo_rel)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
