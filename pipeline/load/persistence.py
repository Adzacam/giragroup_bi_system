"""
persistence.py — GIRA-12
Persistencia relacional y transaccional para materializar la información
procesada dentro del esquema constelación de PostgreSQL.
"""

import logging
from typing import Optional

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def poblar_dimensiones_cascada(df_crudo: pd.DataFrame, session: Session) -> dict:
    """
    Procesa las dimensiones maestras primero, recupera las claves subrogadas
    autogeneradas por la base de datos, y construye mapas de búsqueda en memoria.

    Args:
        df_crudo: DataFrame con datos crudos normalizados.
        session: Sesión SQLAlchemy activa.

    Returns:
        dict con lookup dicts: {
            "estudiantes": {codigo_o_nombre: id_estudiante, ...},
            "docentes": {nombre: id_docente, ...},
            "modulos": {nombre_modulo: id_modulo, ...},
            "tiempo": {(gestion, semestre): id_tiempo, ...},
        }
    """
    from backend.models import DimEstudiante, DimDocente, DimModulo, DimTiempo

    lookups = {
        "estudiantes": {},
        "docentes": {},
        "modulos": {},
        "tiempo": {},
    }

    # --- DIM_TIEMPO ---
    tiempos_existentes = session.query(DimTiempo).all()
    for t in tiempos_existentes:
        lookups["tiempo"][(t.gestion, t.semestre)] = t.id_tiempo

    # --- DIM_ESTUDIANTE ---
    estudiantes_existentes = session.query(DimEstudiante).all()
    for e in estudiantes_existentes:
        clave = e.codigo_estudiante or e.nombre_completo
        lookups["estudiantes"][clave] = e.id_estudiante

    # --- DIM_DOCENTE ---
    docentes_existentes = session.query(DimDocente).all()
    for d in docentes_existentes:
        lookups["docentes"][d.nombre_completo] = d.id_docente

    # --- DIM_MODULO ---
    modulos_existentes = session.query(DimModulo).all()
    for m in modulos_existentes:
        lookups["modulos"][m.nombre_modulo] = m.id_modulo

    logger.info(
        "Lookups cargados: %d estudiantes, %d docentes, %d módulos, %d tiempos",
        len(lookups["estudiantes"]),
        len(lookups["docentes"]),
        len(lookups["modulos"]),
        len(lookups["tiempo"]),
    )
    return lookups


def materializar_rendimiento(
    registros_calificados: list[dict],
    session: Session,
) -> dict:
    """
    Upsert masivo sobre fact_rendimiento_academico.
    Inyecta nivel_confianza_ia y requiere_revision en cada registro.

    Args:
        registros_calificados: Lista de dicts con campos del hecho + confianza.
        session: Sesión SQLAlchemy activa.

    Returns:
        dict con estadísticas: insertados, actualizados, errores.
    """
    from backend.models import FactRendimientoAcademico

    stats = {"insertados": 0, "actualizados": 0, "errores": 0}

    for registro in registros_calificados:
        try:
            stmt = pg_insert(FactRendimientoAcademico).values(
                id_estudiante=registro.get("id_estudiante"),
                id_docente=registro.get("id_docente"),
                id_modulo=registro.get("id_modulo"),
                id_tiempo=registro.get("id_tiempo"),
                id_documento=registro.get("id_documento"),
                id_usuario_carga=registro.get("id_usuario_carga"),
                nota_final=registro.get("nota_final"),
                asistencia_pct=registro.get("asistencia_pct"),
                incumplimiento_actividades_pct=registro.get("incumplimiento_actividades_pct", 0),
                nivel_confianza_ia=registro.get("nivel_confianza_ia"),
                requiere_revision=registro.get("requiere_revision", False),
                estado_academico=registro.get("estado_academico"),
            )

            # ON CONFLICT DO UPDATE (basado en constraint de unicidad)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_fact_rendimiento_estudiante_modulo",
                set_={
                    "nota_final": stmt.excluded.nota_final,
                    "asistencia_pct": stmt.excluded.asistencia_pct,
                    "incumplimiento_actividades_pct": stmt.excluded.incumplimiento_actividades_pct,
                    "nivel_confianza_ia": stmt.excluded.nivel_confianza_ia,
                    "requiere_revision": stmt.excluded.requiere_revision,
                    "estado_academico": stmt.excluded.estado_academico,
                },
            )
            session.execute(stmt)
            stats["insertados"] += 1
        except Exception as e:
            logger.error("Error al materializar rendimiento: %s", e)
            stats["errores"] += 1

    session.commit()
    logger.info("Rendimiento materializado: %s", stats)
    return stats


def materializar_finanzas(
    registros: list[dict],
    session: Session,
) -> dict:
    """
    Upsert masivo sobre fact_situacion_financiera y fact_cobranzas_proyectadas.

    Args:
        registros: Lista de dicts con campos del hecho financiero.
        session: Sesión SQLAlchemy activa.

    Returns:
        dict con estadísticas: insertados, errores.
    """
    from backend.models import FactSituacionFinanciera, FactCobranzasProyectadas

    stats = {"insertados": 0, "errores": 0}

    for registro in registros:
        try:
            tabla_destino = registro.get("_tabla_destino", "fact_situacion_financiera")

            if tabla_destino == "fact_cobranzas_proyectadas":
                stmt = pg_insert(FactCobranzasProyectadas).values(
                    id_estudiante=registro.get("id_estudiante"),
                    id_tiempo=registro.get("id_tiempo"),
                    monto_esperado=registro.get("monto_esperado"),
                    estado_pago=registro.get("estado_pago"),
                )
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_fact_cobranzas_proyectadas_estudiante_tiempo",
                    set_={
                        "monto_esperado": stmt.excluded.monto_esperado,
                        "estado_pago": stmt.excluded.estado_pago,
                    },
                )
            else:
                stmt = pg_insert(FactSituacionFinanciera).values(
                    id_estudiante=registro.get("id_estudiante"),
                    id_tiempo=registro.get("id_tiempo"),
                    monto_deuda=registro.get("monto_deuda"),
                    cuotas_impagas=registro.get("cuotas_impagas"),
                    estado_cartera=registro.get("estado_cartera"),
                    tipo_alerta=registro.get("tipo_alerta"),
                )
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_fact_situacion_financiera_estudiante_tiempo",
                    set_={
                        "monto_deuda": stmt.excluded.monto_deuda,
                        "cuotas_impagas": stmt.excluded.cuotas_impagas,
                        "estado_cartera": stmt.excluded.estado_cartera,
                        "tipo_alerta": stmt.excluded.tipo_alerta,
                    },
                )

            session.execute(stmt)
            stats["insertados"] += 1
        except Exception as e:
            logger.error("Error al materializar finanzas: %s", e)
            stats["errores"] += 1

    session.commit()
    logger.info("Finanzas materializadas: %s", stats)
    return stats


def duplicar_a_log_auditoria(
    registro: dict,
    session: Session,
) -> None:
    """
    Inserta un registro en log_auditoria_nlp cuando requiere_revision = True.
    Congela el estado del texto original frente a la predicción ambigua.

    Args:
        registro: Dict con texto_original, prediccion_beto, confianza_ia.
        session: Sesión SQLAlchemy activa.
    """
    from backend.models import LogAuditoriaNlp

    try:
        log_entry = LogAuditoriaNlp(
            texto_original=registro.get("texto_original", ""),
            prediccion_beto=registro.get("prediccion_beto", ""),
            confianza_ia=registro.get("nivel_confianza_ia"),
            correccion_humana="",  # Pendiente de auditoría humana
            usuario_auditor=registro.get("id_usuario_carga"),
        )
        session.add(log_entry)
        session.commit()
        logger.info("Registro de auditoría NLP creado para texto: %.50s...", registro.get("texto_original", ""))
    except Exception as e:
        session.rollback()
        logger.error("Error al duplicar a log_auditoria_nlp: %s", e)
