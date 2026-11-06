from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_docente import DimDocente
from models.dim_tiempo import DimTiempo
from models.dim_origen import DimOrigenDocumental
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from pipeline.config import NOTA_APROBACION



def _formatear_periodo(tiempo: Optional[DimTiempo], doc_periodo: Optional[str] = None) -> str:
    if doc_periodo and str(doc_periodo).strip():
        return str(doc_periodo).strip()
    if not tiempo:
        return "Multi-Semestre"
    gestion = tiempo.gestion or 2026
    sem = tiempo.semestre
    if not sem and tiempo.mes:
        sem = 1 if int(tiempo.mes) <= 6 else 2
    sem_roman = "II" if sem == 2 else "I"
    return f"{gestion}-{sem_roman}"


def _codigo_corto_programa(programa: str, pos_code: Optional[str] = None, idx: int = 1) -> str:
    if pos_code and pos_code.strip() and pos_code.strip().upper() != "MOD-GEN":
        return pos_code.strip().upper()
    p_upper = (programa or "").strip().upper()
    if "MAESTR" in p_upper:
        return f"MSC-{100 + idx}"
    if "DIPLOMADO" in p_upper:
        return f"DIP-{200 + idx}"
    if "ESPECIALIDAD" in p_upper or "EXPERTO" in p_upper:
        return f"EXP-{300 + idx}"
    words = [w for w in p_upper.split() if len(w) >= 3 and w not in ("DEL", "LAS", "LOS", "CON", "PARA", "POR")]
    if len(words) >= 2:
        return f"{words[0][:3]}-{words[1][:3]}"
    if words:
        return f"{words[0][:4]}-0{idx}"
    return f"PRG-0{idx}"


def get_riesgo_cruzado(db: Session, limite_nota: float = 70.0, min_cuotas_mora: int = 2):
    """
    Cruza la constelación de hechos: Obtiene estudiantes que están 
    reprobando o al límite (<= 70) Y que además tienen 2 o más cuotas en mora.
    """
    # Una fila por estudiante: el join directo multiplicaba notas x filas de cobranza del mismo estudiante.
    notas = db.query(
        FactRendimientoAcademico.id_estudiante.label("id_est"),
        func.min(FactRendimientoAcademico.nota_final).label("nota_final"),
    ).filter(FactRendimientoAcademico.nota_final <= limite_nota).group_by(FactRendimientoAcademico.id_estudiante).subquery()
    deudas = db.query(
        FactSituacionFinanciera.id_estudiante.label("id_est"),
        func.sum(FactSituacionFinanciera.cuotas_impagas).label("cuotas_impagas"),
        func.sum(FactSituacionFinanciera.monto_deuda).label("monto_deuda"),
        func.min(FactSituacionFinanciera.estado_cartera).label("estado_cartera"),  # "Mora" < "Vigente"
    ).group_by(FactSituacionFinanciera.id_estudiante
    ).having(func.sum(FactSituacionFinanciera.cuotas_impagas) >= min_cuotas_mora).subquery()
    resultados = db.query(
        DimEstudiante.nombre_completo,
        DimEstudiante.codigo_estudiante,
        DimEstudiante.ci,
        notas.c.nota_final,
        deudas.c.cuotas_impagas,
        deudas.c.monto_deuda,
        deudas.c.estado_cartera,
    ).join(notas, notas.c.id_est == DimEstudiante.id_estudiante
    ).join(deudas, deudas.c.id_est == DimEstudiante.id_estudiante).all()
    # Más cuotas en mora primero; a igual mora, la nota más baja
    resultados = sorted(resultados, key=lambda r: (-(r.cuotas_impagas or 0), float(r.nota_final or 0)))

    alertas_cruzadas = []
    for row in resultados:
        alertas_cruzadas.append({
            "estudiante": row.nombre_completo,
            "codigo": row.codigo_estudiante or row.ci or "S/C",
            "rendimiento": {
                "nota_actual": float(row.nota_final),
                "estado_academico": "CRÍTICO"
            },
            "finanzas": {
                "cuotas_mora": int(row.cuotas_impagas or 0),
                "deuda_total": float(row.monto_deuda or 0.0),
                "estado_cartera": row.estado_cartera or "En Mora"
            },
            "nivel_riesgo_global": "ALTO - REQUIERE INTERVENCIÓN"
        })
        
    return alertas_cruzadas


def evaluar_alertas_tempranas_deterministicas(
    db: Session,
    periodo: Optional[str] = None,
    programa: Optional[str] = None,
    modulo: Optional[str] = None,
    docente: Optional[str] = None,
    regla_filtro: Optional[str] = None,
    busqueda: Optional[str] = None,
    umbral_nota: float = 70.0,
    umbral_incumplimiento: float = 30.0,
    umbral_cuotas_mora: int = 2,
) -> Dict[str, Any]:
    """
    Evalúa estrictamente mediante reglas determinísticas IF/THEN (sin inferencia ML individual)
    el estado de la matrícula activa sobre fact_rendimiento_academico y fact_situacion_financiera.
    """
    # estudiantes_db se cargará selectivamente tras consultar los hechos para evitar full-scan en RAM
    modulos_db = {
        m.id_modulo: m
        for m in db.query(
            DimModulo.id_modulo,
            DimModulo.nombre_modulo,
            DimModulo.programa,
            DimModulo.pos_code,
        )
        .all()
    }
    docentes_db = {
        d.id_docente: d
        for d in db.query(
            DimDocente.id_docente,
            DimDocente.nombre_completo,
        )
        .all()
    }
    tiempos_db = {
        t.id_tiempo: t
        for t in db.query(
            DimTiempo.id_tiempo,
            DimTiempo.gestion,
            DimTiempo.semestre,
            DimTiempo.mes,
            DimTiempo.periodo_mes,
        )
        .all()
    }
    origenes_db = {
        o.id_documento: o
        for o in db.query(
            DimOrigenDocumental.id_documento,
            DimOrigenDocumental.periodo,
        )
        .all()
    }

    hechos_aca = (
        db.query(
            FactRendimientoAcademico.id_hecho_aca,
            FactRendimientoAcademico.id_estudiante,
            FactRendimientoAcademico.id_modulo,
            FactRendimientoAcademico.id_docente,
            FactRendimientoAcademico.id_tiempo,
            FactRendimientoAcademico.id_documento,
            FactRendimientoAcademico.nota_final,
            FactRendimientoAcademico.incumplimiento_actividades_pct,
            FactRendimientoAcademico.asistencia_pct,
            FactRendimientoAcademico.tipo_alerta,
        )
        .all()
    )
    hechos_fin = (
        db.query(
            FactSituacionFinanciera.id_hecho_fin,
            FactSituacionFinanciera.id_estudiante,
            FactSituacionFinanciera.id_modulo,
            FactSituacionFinanciera.id_tiempo,
            FactSituacionFinanciera.id_documento,
            FactSituacionFinanciera.cuotas_impagas,
            FactSituacionFinanciera.monto_deuda,
        )
        .all()
    )

    # Optimización R-06: Filtrar estudiantes en SQL por los IDs con hechos existentes en lugar de full-scan ciego
    ids_con_hechos = {h.id_estudiante for h in hechos_aca if h.id_estudiante} | {
        f.id_estudiante for f in hechos_fin if f.id_estudiante
    }
    estudiantes_db = {
        e.id_estudiante: e
        for e in db.query(
            DimEstudiante.id_estudiante,
            DimEstudiante.ci,
            DimEstudiante.ci_numero,
            DimEstudiante.codigo_estudiante,
            DimEstudiante.nombre_completo,
            DimEstudiante.programa_origen,
            DimEstudiante.deprecado,
        )
        .filter(
            DimEstudiante.deprecado == False,
            DimEstudiante.id_estudiante.in_(ids_con_hechos)
        )
        .all()
    } if ids_con_hechos else {}

    periodos_set = set()
    programas_set = set()
    modulos_set = set()
    docentes_set = set()

    f_periodo = (periodo or "").strip()
    if f_periodo.upper() in ("", "TODOS", "ALL"):
        f_periodo = ""
    f_programa = (programa or "").strip()
    if f_programa.upper() in ("", "TODOS", "ALL"):
        f_programa = ""
    f_modulo = (modulo or "").strip()
    if f_modulo.upper() in ("", "TODOS", "ALL"):
        f_modulo = ""
    f_docente = (docente or "").strip()
    if f_docente.upper() in ("", "TODOS", "ALL"):
        f_docente = ""
    f_regla = (regla_filtro or "").strip().upper()
    if f_regla in ("", "TODOS", "ALL"):
        f_regla = ""
    f_busqueda = (busqueda or "").strip().lower()

    perfiles: Dict[int, Dict[str, Any]] = {}

    def _asegurar_perfil(id_est: int) -> Optional[Dict[str, Any]]:
        est = estudiantes_db.get(id_est)
        if not est:
            return None
        if id_est not in perfiles:
            ci_limpio = (est.ci or est.ci_numero or est.codigo_estudiante or "S/C").strip()
            perfiles[id_est] = {
                "id_estudiante": id_est,
                "ci": ci_limpio,
                "codigo_estudiante": est.codigo_estudiante or ci_limpio,
                "nombre_completo": (est.nombre_completo or f"Estudiante #{id_est}").strip(),
                "programa_est": (est.programa_origen or "").strip(),
                "programas": [],
                "modulos": [],
                "docentes": [],
                "periodos": [],
                "pos_codes": [],
                "notas": [],
                "incumplimientos": [],
                "asistencias": [],
                "alerta_desercion_explicita": False,
                "cuotas_mora": 0,
                "deuda_mora_bs": 0.0,
            }
        return perfiles[id_est]

    # Procesar hechos académicos
    for h in hechos_aca:
        if not h.id_estudiante:
            continue
        est = estudiantes_db.get(h.id_estudiante)
        if not est:
            continue

        mod = modulos_db.get(h.id_modulo)
        doc = docentes_db.get(h.id_docente)
        t = tiempos_db.get(h.id_tiempo)
        orig = origenes_db.get(h.id_documento)

        per_str = _formatear_periodo(t, orig.periodo if orig else None)
        prog_str = (
            (mod.programa if mod and mod.programa else "")
            or (est.programa_origen or "")
            or (mod.nombre_modulo if mod and mod.nombre_modulo else "")
            or "Programa General"
        ).strip()
        mod_str = (mod.nombre_modulo if mod and mod.nombre_modulo else "Módulo General").strip()
        doc_str = (doc.nombre_completo if doc and doc.nombre_completo else "Sin Docente Asignado").strip()
        pos_code = (mod.pos_code if mod and mod.pos_code else None)

        periodos_set.add(per_str)
        if prog_str:
            programas_set.add(prog_str)
        if mod_str:
            modulos_set.add(mod_str)
        if doc_str and doc_str != "Sin Docente Asignado":
            docentes_set.add(doc_str)

        if f_periodo and per_str.lower() != f_periodo.lower() and (not t or str(t.periodo_mes or "").lower() != f_periodo.lower()):
            continue
        if f_programa and prog_str.lower() != f_programa.lower():
            continue
        if f_modulo and mod_str.lower() != f_modulo.lower():
            continue
        if f_docente and doc_str.lower() != f_docente.lower():
            continue

        p = _asegurar_perfil(h.id_estudiante)
        if not p:
            continue

        if prog_str and prog_str not in p["programas"]:
            p["programas"].append(prog_str)
        if mod_str and mod_str not in p["modulos"]:
            p["modulos"].append(mod_str)
        if doc_str and doc_str not in p["docentes"]:
            p["docentes"].append(doc_str)
        if per_str and per_str not in p["periodos"]:
            p["periodos"].append(per_str)
        if pos_code and pos_code not in p["pos_codes"]:
            p["pos_codes"].append(pos_code)

        if h.nota_final is not None:
            p["notas"].append(float(h.nota_final))

        inc_val = float(h.incumplimiento_actividades_pct or 0.0)
        if h.asistencia_pct is not None:
            asist_val = float(h.asistencia_pct)
            p["asistencias"].append(asist_val)
            inasist_val = max(0.0, 100.0 - asist_val)
            inc_val = max(inc_val, inasist_val)
        p["incumplimientos"].append(inc_val)

        if (h.tipo_alerta or "").upper() == "DESERCION":
            p["alerta_desercion_explicita"] = True

    # Procesar hechos financieros
    for f in hechos_fin:
        if not f.id_estudiante:
            continue
        est = estudiantes_db.get(f.id_estudiante)
        if not est:
            continue

        mod = modulos_db.get(f.id_modulo)
        t = tiempos_db.get(f.id_tiempo)
        orig = origenes_db.get(f.id_documento)

        per_str = _formatear_periodo(t, orig.periodo if orig else None)
        prog_str = (
            (mod.programa if mod and mod.programa else "")
            or (est.programa_origen or "")
            or (mod.nombre_modulo if mod and mod.nombre_modulo else "")
            or "Programa General"
        ).strip()
        mod_str = (mod.nombre_modulo if mod and mod.nombre_modulo else "Módulo General").strip()
        pos_code = (mod.pos_code if mod and mod.pos_code else None)

        periodos_set.add(per_str)
        if prog_str:
            programas_set.add(prog_str)
        if mod_str and mod_str != "Módulo General":
            modulos_set.add(mod_str)

        if f_periodo and per_str.lower() != f_periodo.lower() and (not t or str(t.periodo_mes or "").lower() != f_periodo.lower()):
            continue
        if f_programa and prog_str.lower() != f_programa.lower():
            continue
        if f_modulo and mod_str.lower() != f_modulo.lower():
            continue
        if f_docente and f.id_estudiante not in perfiles:
            continue

        p = _asegurar_perfil(f.id_estudiante)
        if not p:
            continue

        if prog_str and prog_str not in p["programas"]:
            p["programas"].append(prog_str)
        if mod_str and mod_str not in p["modulos"]:
            p["modulos"].append(mod_str)
        if per_str and per_str not in p["periodos"]:
            p["periodos"].append(per_str)
        if pos_code and pos_code not in p["pos_codes"]:
            p["pos_codes"].append(pos_code)

        cuotas = int(f.cuotas_impagas or 0)
        deuda = float(f.monto_deuda or 0.0)
        p["cuotas_mora"] += cuotas
        if cuotas > 0 or deuda > 0:
            p["deuda_mora_bs"] += deuda

    total_matricula_activa = len(perfiles) if perfiles else len(estudiantes_db)
    denom_matricula = max(1, total_matricula_activa)

    cnt_academico = 0
    cnt_desercion = 0
    cnt_financiero = 0
    cnt_critica = 0
    total_mora_bs = 0.0

    cnt_ad = 0
    cnt_df = 0
    cnt_af = 0
    cnt_adf = 0

    afectados_por_programa: Dict[str, Dict[str, Any]] = {}
    estudiantes_en_alerta: List[Dict[str, Any]] = []

    for id_est, p in perfiles.items():
        prom_notas = round(sum(p["notas"]) / len(p["notas"]), 1) if p["notas"] else None
        max_incumpl = round(max(p["incumplimientos"]), 1) if p["incumplimientos"] else 0.0
        min_asist = round(min(p["asistencias"]), 1) if p["asistencias"] else None
        cuotas_mora = int(p["cuotas_mora"])
        deuda_bs = round(float(p["deuda_mora_bs"]), 2)

        # Reglas determinísticas estrictas IF/THEN
        regla_aca = bool(prom_notas is not None and prom_notas <= umbral_nota)
        regla_des = bool(max_incumpl > umbral_incumplimiento or p["alerta_desercion_explicita"])
        regla_fin = bool(cuotas_mora >= umbral_cuotas_mora)

        cant_reglas = int(regla_aca) + int(regla_des) + int(regla_fin)

        if regla_aca:
            cnt_academico += 1
        if regla_des:
            cnt_desercion += 1
        if regla_fin:
            cnt_financiero += 1
            total_mora_bs += deuda_bs
        if cant_reglas >= 2:
            cnt_critica += 1

        if regla_aca and regla_des and regla_fin:
            cnt_adf += 1
        if regla_aca and regla_des:
            cnt_ad += 1
        if regla_des and regla_fin:
            cnt_df += 1
        if regla_aca and regla_fin:
            cnt_af += 1

        if cant_reglas == 0:
            continue

        tags_partes = []
        if regla_aca:
            tags_partes.append("A")
        if regla_des:
            tags_partes.append("D")
        if regla_fin:
            tags_partes.append("F")
        tag_str = "+".join(tags_partes)

        prog_principal = p["programas"][0] if p["programas"] else (p["programa_est"] or "Programa General")
        mod_principal = p["modulos"][0] if p["modulos"] else "Módulo General"
        doc_principal = p["docentes"][0] if p["docentes"] else "Sin Docente Asignado"
        per_principal = p["periodos"][0] if p["periodos"] else "Multi-Semestre"
        pos_principal = p["pos_codes"][0] if p["pos_codes"] else None

        if prog_principal not in afectados_por_programa:
            afectados_por_programa[prog_principal] = {
                "programa": prog_principal,
                "pos_code": pos_principal,
                "total_afectados": 0,
            }
        afectados_por_programa[prog_principal]["total_afectados"] += 1

        prioridad = "CRITICA" if cant_reglas >= 2 else ("ALTA" if (regla_aca or regla_des) else "MEDIA")

        item_nominal = {
            "id_estudiante": id_est,
            "ci": p["ci"],
            "codigo_estudiante": p["codigo_estudiante"],
            "nombre_completo": p["nombre_completo"],
            "programa": prog_principal,
            "modulo": mod_principal,
            "docente": doc_principal,
            "periodo": per_principal,
            "promedio_notas": prom_notas,
            "incumplimiento_pct": max_incumpl,
            "asistencia_pct": min_asist,
            "cuotas_mora": cuotas_mora,
            "deuda_mora_bs": deuda_bs,
            "regla_academico": regla_aca,
            "regla_desercion": regla_des,
            "regla_financiero": regla_fin,
            "tag": tag_str,
            "cantidad_reglas": cant_reglas,
            "prioridad": prioridad,
        }

        pasa_regla = True
        if f_regla == "ACADEMICO":
            pasa_regla = regla_aca
        elif f_regla == "DESERCION":
            pasa_regla = regla_des
        elif f_regla == "FINANCIERO":
            pasa_regla = regla_fin
        elif f_regla == "CRITICA":
            pasa_regla = cant_reglas >= 2
        elif f_regla == "A+D":
            pasa_regla = regla_aca and regla_des
        elif f_regla == "D+F":
            pasa_regla = regla_des and regla_fin
        elif f_regla == "A+F":
            pasa_regla = regla_aca and regla_fin
        elif f_regla == "A+D+F":
            pasa_regla = regla_aca and regla_des and regla_fin

        if not pasa_regla:
            continue

        if f_busqueda:
            texto_busqueda = f"{item_nominal['nombre_completo']} {item_nominal['ci']} {item_nominal['programa']} {item_nominal['modulo']}".lower()
            if f_busqueda not in texto_busqueda:
                continue

        estudiantes_en_alerta.append(item_nominal)

    estudiantes_en_alerta.sort(
        key=lambda x: (
            -x["cantidad_reglas"],
            -x["cuotas_mora"],
            x["promedio_notas"] if x["promedio_notas"] is not None else 999.0,
        )
    )

    top_progs_sorted = sorted(
        afectados_por_programa.values(),
        key=lambda item: item["total_afectados"],
        reverse=True,
    )[:5]
    top_programas = [
        {
            "programa": tp["programa"],
            "codigo_programa": _codigo_corto_programa(tp["programa"], tp.get("pos_code"), idx + 1),
            "total_afectados": tp["total_afectados"],
        }
        for idx, tp in enumerate(top_progs_sorted)
    ]

    pct_aca = round((cnt_academico / denom_matricula) * 100.0, 1)
    pct_des = round((cnt_desercion / denom_matricula) * 100.0, 1)

    tarjetas = {
        "riesgo_academico": {
            "codigo": "ACADEMICO",
            "titulo": "RIESGO ACADÉM.",
            "regla_texto": f"Regla: Promedio <= {int(umbral_nota)}",
            "severidad": "ROJO",
            "total_alumnos": cnt_academico,
            "porcentaje_matricula": pct_aca,
            "monto_mora_bs": None,
            "subtitulo_secundario": f"{pct_aca}% de matrícula",
        },
        "riesgo_desercion": {
            "codigo": "DESERCION",
            "titulo": "RIESGO DESERC.",
            "regla_texto": f"Regla: Incumpl. > {int(umbral_incumplimiento)}%",
            "severidad": "ROJO",
            "total_alumnos": cnt_desercion,
            "porcentaje_matricula": pct_des,
            "monto_mora_bs": None,
            "subtitulo_secundario": f"{pct_des}% de matrícula",
        },
        "riesgo_financiero": {
            "codigo": "FINANCIERO",
            "titulo": "RIESGO FINANC.",
            "regla_texto": f"Regla: Mora >= {umbral_cuotas_mora} Cuot.",
            "severidad": "AMBAR",
            "total_alumnos": cnt_financiero,
            "porcentaje_matricula": round((cnt_financiero / denom_matricula) * 100.0, 1),
            "monto_mora_bs": round(total_mora_bs, 2),
            "subtitulo_secundario": f"{total_mora_bs:,.0f} Bs en mora",
        },
        "alerta_critica": {
            "codigo": "CRITICA",
            "titulo": "ALERTA CRÍTICA",
            "regla_texto": "(2 o + Reglas)",
            "severidad": "CRITICO",
            "total_alumnos": cnt_critica,
            "porcentaje_matricula": round((cnt_critica / denom_matricula) * 100.0, 1),
            "monto_mora_bs": None,
            "subtitulo_secundario": "Prioridad Alta",
        },
    }

    matriz_interseccion = [
        {"codigo": "A+D", "etiqueta": "Académico + Deserción (A+D)", "total_alumnos": cnt_ad},
        {"codigo": "D+F", "etiqueta": "Deserción + Financiero (D+F)", "total_alumnos": cnt_df},
        {"codigo": "A+F", "etiqueta": "Académico + Financiero (A+F)", "total_alumnos": cnt_af},
        {"codigo": "A+D+F", "etiqueta": "Triple Alerta (A+D+F)", "total_alumnos": cnt_adf},
    ]

    return {
        "status": "success",
        "motor_reglas": "DETERMINISTICO_IF_THEN_ESTRICTO",
        "total_matricula_activa": total_matricula_activa,
        "tarjetas": tarjetas,
        "matriz_interseccion": matriz_interseccion,
        "top_programas": top_programas,
        "filtros_disponibles": {
            "periodos": sorted(list(periodos_set), reverse=True),
            "programas": sorted(list(programas_set)),
            "modulos": sorted(list(modulos_set)),
            "docentes": sorted(list(docentes_set)),
        },
        "total_estudiantes_filtrados": len(estudiantes_en_alerta),
        "estudiantes": estudiantes_en_alerta,
    }


def obtener_ficha_cruzada_estudiante(db: Session, id_estudiante: int) -> Optional[Dict[str, Any]]:
    """
    Construye la Ficha Cruzada Académico-Financiera del Estudiante unificando
    fact_rendimiento_academico, fact_situacion_financiera y la trazabilidad de
    dim_origen_documental (hash SHA-256).
    """
    est = db.query(DimEstudiante).filter(DimEstudiante.id_estudiante == id_estudiante).first()
    if not est:
        return None

    hechos_aca = (
        db.query(FactRendimientoAcademico)
        .filter(FactRendimientoAcademico.id_estudiante == id_estudiante)
        .order_by(desc(FactRendimientoAcademico.id_hecho_aca))
        .all()
    )
    hechos_fin = (
        db.query(FactSituacionFinanciera)
        .filter(FactSituacionFinanciera.id_estudiante == id_estudiante)
        .order_by(desc(FactSituacionFinanciera.id_hecho_fin))
        .all()
    )

    # Carga dirigida únicamente de las dimensiones asociadas al estudiante (sin .all() global)
    modulo_ids = {h.id_modulo for h in hechos_aca if h.id_modulo} | {h.id_modulo for h in hechos_fin if h.id_modulo}
    docente_ids = {h.id_docente for h in hechos_aca if h.id_docente}
    tiempo_ids = {h.id_tiempo for h in hechos_aca if h.id_tiempo} | {h.id_tiempo for h in hechos_fin if h.id_tiempo}
    doc_ids = {h.id_documento for h in hechos_aca if h.id_documento} | {h.id_documento for h in hechos_fin if h.id_documento}

    modulos_db = {m.id_modulo: m for m in db.query(DimModulo).filter(DimModulo.id_modulo.in_(modulo_ids)).all()} if modulo_ids else {}
    docentes_db = {d.id_docente: d for d in db.query(DimDocente).filter(DimDocente.id_docente.in_(docente_ids)).all()} if docente_ids else {}
    tiempos_db = {t.id_tiempo: t for t in db.query(DimTiempo).filter(DimTiempo.id_tiempo.in_(tiempo_ids)).all()} if tiempo_ids else {}
    origenes_db = {o.id_documento: o for o in db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_documento.in_(doc_ids)).all()} if doc_ids else {}

    historial_aca = []
    notas_vals = []
    incumpl_vals = []

    for h in hechos_aca:
        mod = modulos_db.get(h.id_modulo)
        doc = docentes_db.get(h.id_docente)
        t = tiempos_db.get(h.id_tiempo)
        orig = origenes_db.get(h.id_documento)

        nota_f = float(h.nota_final or 0.0)
        notas_vals.append(nota_f)
        asist_f = float(h.asistencia_pct) if h.asistencia_pct is not None else None
        inc_f = float(h.incumplimiento_actividades_pct or 0.0)
        if asist_f is not None:
            inc_f = max(inc_f, max(0.0, 100.0 - asist_f))
        incumpl_vals.append(inc_f)

        reglas_fila = []
        if nota_f <= 70.0:
            reglas_fila.append("IF nota_final <= 70 -> RIESGO_ACADEMICO")
        if inc_f > 30.0:
            reglas_fila.append("IF incumplimiento > 30% -> RIESGO_DESERCION")

        historial_aca.append({
            "id_hecho_aca": h.id_hecho_aca,
            "modulo": (mod.nombre_modulo if mod and mod.nombre_modulo else "Módulo General"),
            "programa": (
                (mod.programa if mod and mod.programa else "")
                or (est.programa_origen or "")
                or (mod.nombre_modulo if mod and mod.nombre_modulo else "Programa General")
            ),
            "docente": (doc.nombre_completo if doc and doc.nombre_completo else "Sin Docente Asignado"),
            "periodo": _formatear_periodo(t, orig.periodo if orig else None),
            "nota_final": round(nota_f, 1),
            "asistencia_pct": round(asist_f, 1) if asist_f is not None else None,
            "incumplimiento_pct": round(inc_f, 1),
            "estado_academico": h.estado_academico or ("Reprobado" if nota_f < NOTA_APROBACION else "Aprobado"),
            "regla_disparada": " | ".join(reglas_fila) if reglas_fila else "SIN_ALERTA",
            "origen_archivo": orig.nombre_archivo if orig else None,
            "hash_sha256": orig.hash_sha256 if orig else None,
        })

    historial_fin = []
    total_cuotas_mora = 0
    total_deuda_bs = 0.0
    total_pagado_bs = 0.0

    for f in hechos_fin:
        mod = modulos_db.get(f.id_modulo)
        t = tiempos_db.get(f.id_tiempo)
        orig = origenes_db.get(f.id_documento)

        cuotas = int(f.cuotas_impagas or 0)
        deuda = float(f.monto_deuda or 0.0)
        pagado = float(f.monto_pagado or 0.0)
        total_cuotas_mora += cuotas
        total_deuda_bs += deuda
        total_pagado_bs += pagado

        historial_fin.append({
            "id_hecho_fin": f.id_hecho_fin,
            "concepto": f.concepto or "Cuota de Colegiatura",
            "modulo": (mod.nombre_modulo if mod and mod.nombre_modulo else None),
            "periodo": _formatear_periodo(t, orig.periodo if orig else None),
            "monto_pagado": round(pagado, 2),
            "monto_deuda": round(deuda, 2),
            "cuotas_impagas": cuotas,
            "estado_cartera": f.estado_cartera or ("En Mora" if cuotas >= 2 else "Vigente"),
            "fecha_registro": f.fecha_registro.isoformat() if f.fecha_registro else None,
            "origen_archivo": orig.nombre_archivo if orig else None,
            "hash_sha256": orig.hash_sha256 if orig else None,
        })

    prom_notas = round(sum(notas_vals) / len(notas_vals), 1) if notas_vals else None
    max_inc = round(max(incumpl_vals), 1) if incumpl_vals else 0.0

    regla_aca = bool(prom_notas is not None and prom_notas <= 70.0)
    regla_des = bool(max_inc > 30.0)
    regla_fin = bool(total_cuotas_mora >= 2)

    tags = []
    if regla_aca:
        tags.append("A")
    if regla_des:
        tags.append("D")
    if regla_fin:
        tags.append("F")

    ci_limpio = (est.ci or est.ci_numero or est.codigo_estudiante or "S/C").strip()

    return {
        "status": "success",
        "id_estudiante": est.id_estudiante,
        "nombre_completo": est.nombre_completo,
        "ci": ci_limpio,
        "codigo_estudiante": est.codigo_estudiante or ci_limpio,
        "programa_origen": est.programa_origen or (historial_aca[0]["programa"] if historial_aca else "Programa General"),
        "ciudad": est.ciudad or "Bolivia",
        "resumen_reglas": {
            "promedio_notas": prom_notas,
            "incumplimiento_max_pct": max_inc,
            "cuotas_mora_total": total_cuotas_mora,
            "deuda_total_bs": round(total_deuda_bs, 2),
            "pagado_total_bs": round(total_pagado_bs, 2),
            "regla_academico": regla_aca,
            "regla_desercion": regla_des,
            "regla_financiero": regla_fin,
            "tag": "+".join(tags) if tags else "NORMAL",
            "alerta_critica": (int(regla_aca) + int(regla_des) + int(regla_fin)) >= 2,
        },
        "historial_academico": historial_aca,
        "historial_financiero": historial_fin,
    }
