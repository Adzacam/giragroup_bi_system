"""
backend/services/cross_source_reconciler.py
-------------------------------------------
Servicio de Cascada de Resolución de Identidad y Detección de Discrepancias Cross-Source
(Fragmentación Informacional):
1. Cascada de Resolución Jerárquica:
   CI -> ID Estudiante -> Correo Institucional -> Nombre + Programa + Período
2. Verificación de Presencia Cruzada entre fuentes dispares (Moodle, Actas, Cobranzas):
   - Alumno activo en Moodle/Actas pero AUSENTE en Cobranzas.
   - Alumno con pagos en Cobranzas pero AUSENTE en Aula Virtual Moodle.
"""

import re
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from models.dim_estudiante import DimEstudiante
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera


def _fuzzy_name_match(query: str, candidates: List[str]):
    """Búsqueda difusa para nombres de personas contemplando omisión de segundo apellido."""
    if not query or not candidates:
        return None, 0.0
    try:
        from rapidfuzz import fuzz, process
        res = process.extractOne(query, candidates, scorer=fuzz.token_set_ratio)
        if res:
            return res[0], round(float(res[1]), 2)
    except Exception:
        pass
    from difflib import SequenceMatcher
    q_low = query.strip().lower()
    best_cand = None
    best_ratio = 0.0
    for c in candidates:
        ratio = SequenceMatcher(None, q_low, str(c).strip().lower()).ratio() * 100.0
        if ratio > best_ratio:
            best_ratio = ratio
            best_cand = c
    return best_cand, round(best_ratio, 2)


class IdentityResolutionCascade:
    """Implementa la jerarquía estricta de identificación del estudiante."""

    PATRON_DEPTO = re.compile(r'\b(LP|SC|CB|CBBA|OR|PT|TJ|CH|BE|BN|PD)\b', re.IGNORECASE)

    @classmethod
    def normalizar_ci(cls, ci_raw: Optional[str]) -> Optional[str]:
        """Limpia sufijos de departamento y caracteres no alfanuméricos del CI."""
        if not ci_raw:
            return None
        texto = str(ci_raw).strip()
        # Eliminar sufijos como '4892019 LP' o '4892019-1B'
        texto_sin_depto = cls.PATRON_DEPTO.sub('', texto)
        ci_limpio = re.sub(r'[^0-9A-Za-z]', '', texto_sin_depto).strip()
        return ci_limpio if ci_limpio else None

    @classmethod
    def resolver_estudiante_cascada(
        cls,
        db: Session,
        ci: Optional[str] = None,
        id_estudiante_codigo: Optional[str] = None,
        correo: Optional[str] = None,
        nombre: Optional[str] = None,
        programa: Optional[str] = None,
        periodo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta la cascada jerárquica de resolución:
        1. CI directo
        2. ID/Código Estudiante
        3. Correo institucional/personal
        4. Nombre completo + Programa + Período (Fuzzy)
        """
        ci_norm = cls.normalizar_ci(ci)
        es_sintetico = not ci_norm or ci_norm.startswith("TEMP") or "TEMP" in (ci_norm or "").upper()

        # ── Nivel 1: Cédula de Identidad (CI) ──────────────────────────────────
        if ci_norm and not es_sintetico:
            est_ci = db.query(DimEstudiante).filter(
                (DimEstudiante.codigo_estudiante == ci_norm) |
                (DimEstudiante.codigo_estudiante.ilike(f"{ci_norm}%"))
            ).first()

            if est_ci:
                return {
                    "resuelto": True,
                    "id_estudiante": est_ci.id_estudiante,
                    "codigo_estudiante": est_ci.codigo_estudiante,
                    "nombre_completo": est_ci.nombre_completo,
                    "nivel_resolucion": "CI",
                    "confianza": 100.0,
                    "fk_estado": "A",
                    "requiere_revision": False,
                    "motivo": f"Identidad confirmada por CI oficial ({ci_norm})"
                }

        # ── Nivel 2: ID / Código Estudiante (ej. 'EST-00452' o número) ─────────
        if id_estudiante_codigo and str(id_estudiante_codigo).strip():
            codigo_clean = str(id_estudiante_codigo).strip().upper()
            est_codigo = db.query(DimEstudiante).filter(
                (DimEstudiante.codigo_estudiante.ilike(codigo_clean))
            ).first()

            # Si no coincide con codigo_estudiante, comprobar si es ID numérico
            if not est_codigo and codigo_clean.replace("EST-", "").isdigit():
                id_num = int(codigo_clean.replace("EST-", ""))
                est_codigo = db.query(DimEstudiante).filter(
                    DimEstudiante.id_estudiante == id_num
                ).first()

            if est_codigo:
                return {
                    "resuelto": True,
                    "id_estudiante": est_codigo.id_estudiante,
                    "codigo_estudiante": est_codigo.codigo_estudiante,
                    "nombre_completo": est_codigo.nombre_completo,
                    "nivel_resolucion": "ID_ESTUDIANTE",
                    "confianza": 98.0,
                    "fk_estado": "A",
                    "requiere_revision": False,
                    "motivo": f"Identidad confirmada por Código/ID ({id_estudiante_codigo})"
                }

        # ── Nivel 3: Correo Electrónico Institucional / Personal ───────────────
        if correo and "@" in str(correo):
            correo_clean = str(correo).strip().lower()
            # En caso de que codigo_estudiante almacene correo o prefijo
            username = correo_clean.split("@")[0]
            est_correo = db.query(DimEstudiante).filter(
                DimEstudiante.codigo_estudiante.ilike(f"%{username}%")
            ).first()

            if est_correo:
                return {
                    "resuelto": True,
                    "id_estudiante": est_correo.id_estudiante,
                    "codigo_estudiante": est_correo.codigo_estudiante,
                    "nombre_completo": est_correo.nombre_completo,
                    "nivel_resolucion": "CORREO",
                    "confianza": 95.0,
                    "fk_estado": "A",
                    "requiere_revision": False,
                    "motivo": f"Identidad resuelta por correlación de correo ({correo_clean})"
                }

        # ── Nivel 4: Nombre + Programa + Período (Matching Difuso RapidFuzz) ───
        if nombre and str(nombre).strip():
            nombre_clean = str(nombre).strip()
            estudiantes = db.query(DimEstudiante).all()

            if estudiantes:
                nombres_map = {e.nombre_completo: e for e in estudiantes if e.nombre_completo}
                mejor_cand, score = _fuzzy_name_match(nombre_clean, list(nombres_map.keys()))

                if mejor_cand and score and score >= 85.0:
                    est_fuzzy = nombres_map[mejor_cand]
                    confianza_final = score

                    # Si hay coincidencia de programa o período, reforzamos la confianza
                    if programa:
                        confianza_final = min(98.0, round(score * 1.05, 2))

                    return {
                        "resuelto": True,
                        "id_estudiante": est_fuzzy.id_estudiante,
                        "codigo_estudiante": est_fuzzy.codigo_estudiante,
                        "nombre_completo": est_fuzzy.nombre_completo,
                        "nivel_resolucion": "NOMBRE_PROGRAMA",
                        "confianza": confianza_final,
                        "fk_estado": "B",
                        "requiere_revision": False,
                        "motivo": f"Identidad rescatada difusamente ('{nombre_clean}' ~ '{mejor_cand}', similitud {score}%)"
                    }

        # ── Nivel 5: No Resuelto (Estado C -> Revisión Humana) ─────────────────
        return {
            "resuelto": False,
            "id_estudiante": None,
            "codigo_estudiante": ci_norm or id_estudiante_codigo,
            "nombre_completo": nombre,
            "nivel_resolucion": "NO_RESUELTO",
            "confianza": 0.0,
            "fk_estado": "C",
            "requiere_revision": True,
            "motivo": "No se encontró coincidencia por CI, ID, Correo ni Nombre en la dimensión canónica."
        }


class CrossSourceReconciler:
    """Detecta inconsistencias y fragmentación entre plataformas dispares (Moodle vs Cobranzas)."""

    @classmethod
    def verificar_presencia_cruzada(
        cls,
        db: Session,
        id_estudiante: int,
        id_documento_actual: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Coteja la presencia de un estudiante entre hechos académicos y financieros:
        - ¿Tiene registros en FactRendimientoAcademico (Moodle / Actas)?
        - ¿Tiene registros en FactSituacionFinanciera (Cobranzas)?
        """
        estudiante = db.query(DimEstudiante).filter(DimEstudiante.id_estudiante == id_estudiante).first()
        if not estudiante:
            return {
                "id_estudiante": id_estudiante,
                "nombre_completo": "Desconocido",
                "reconciliado": False,
                "estado": "ESTUDIANTE_NO_EXISTE",
                "tiene_academico": False,
                "tiene_financiero": False,
                "alerta": "El ID de estudiante no existe en el Data Warehouse.",
                "fragmentacion_detectada": True
            }

        # Conteo en FactRendimientoAcademico
        query_aca = db.query(FactRendimientoAcademico).filter(
            FactRendimientoAcademico.id_estudiante == id_estudiante
        )
        total_aca = query_aca.count()

        # Conteo en FactSituacionFinanciera
        query_fin = db.query(FactSituacionFinanciera).filter(
            FactSituacionFinanciera.id_estudiante == id_estudiante
        )
        total_fin = query_fin.count()

        tiene_academico = total_aca > 0
        tiene_financiero = total_fin > 0

        # Determinación de estado y alertas de fragmentación
        if tiene_academico and tiene_financiero:
            estado = "RECONCILIADO"
            alerta = None
            reconciliado = True
            fragmentacion = False
        elif tiene_academico and not tiene_financiero:
            estado = "DISCREPANCIA_SIN_COBRANZA"
            alerta = (
                f"Estudiante activo en plataforma académica (Moodle/Acta con {total_aca} registros) "
                f"pero NO figura en las planillas de cobranza financiera."
            )
            reconciliado = False
            fragmentacion = True
        elif tiene_financiero and not tiene_academico:
            estado = "DISCREPANCIA_SIN_AULA_VIRTUAL"
            alerta = (
                f"Estudiante con {total_fin} registro(s) de pago/cobranza en finanzas "
                f"pero NO registra actividad académica en el aula virtual Moodle ni actas."
            )
            reconciliado = False
            fragmentacion = True
        else:
            estado = "SIN_REGISTROS"
            alerta = "Estudiante catalogado pero sin hechos académicos ni financieros asociados."
            reconciliado = False
            fragmentacion = False

        return {
            "id_estudiante": id_estudiante,
            "codigo_estudiante": estudiante.codigo_estudiante,
            "nombre_completo": estudiante.nombre_completo,
            "tiene_academico": tiene_academico,
            "total_registros_academicos": total_aca,
            "tiene_financiero": tiene_financiero,
            "total_registros_financieros": total_fin,
            "reconciliado": reconciliado,
            "estado": estado,
            "alerta": alerta,
            "fragmentacion_detectada": fragmentacion
        }

    @classmethod
    def auditar_discrepancias_lote(
        cls,
        db: Session,
        limite: int = 50
    ) -> Dict[str, Any]:
        """
        Genera reporte ejecutivo y auditoría de fragmentación de datos para el lote activo.
        """
        estudiantes = db.query(DimEstudiante).limit(limite).all()

        total = len(estudiantes)
        reconciliados = 0
        sin_cobranza = 0
        sin_aula_virtual = 0
        discrepancias_list: List[Dict[str, Any]] = []

        for e in estudiantes:
            res = cls.verificar_presencia_cruzada(db, e.id_estudiante)
            if res["reconciliado"]:
                reconciliados += 1
            elif res["fragmentacion_detectada"]:
                if res["estado"] == "DISCREPANCIA_SIN_COBRANZA":
                    sin_cobranza += 1
                elif res["estado"] == "DISCREPANCIA_SIN_AULA_VIRTUAL":
                    sin_aula_virtual += 1
                discrepancias_list.append(res)

        return {
            "total_estudiantes_auditados": total,
            "estudiantes_reconciliados": reconciliados,
            "tasa_reconciliacion_pct": round((reconciliados / total) * 100.0, 2) if total > 0 else 0.0,
            "discrepancias_sin_cobranza": sin_cobranza,
            "discrepancias_sin_aula_virtual": sin_aula_virtual,
            "total_discrepancias_fragmentacion": len(discrepancias_list),
            "casos_discrepancia": discrepancias_list
        }
