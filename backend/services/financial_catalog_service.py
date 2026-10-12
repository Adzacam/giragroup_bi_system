"""
backend/services/financial_catalog_service.py
---------------------------------------------
Servicio de homologación y resolución de conceptos financieros contra los catálogos
maestros (cat_concepto_financiero y cat_historico_equivalencia) de giragroup_catalog_db.

Aplica política estricta anti-contaminación del DW:
- Si score >= 90%: homologa automáticamente al concepto canónico correspondiente.
- Si score < 90%: marca requiere_revision = True y NO inventa registros en catálogo ni DW.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from models.catalogos import CatConceptoFinanciero, CatHistoricoEquivalencia
from core.database import get_catalog_db, CatalogSessionLocal


def _fuzzy_match(query: str, choices: List[str]):
    """Calcula la mejor coincidencia usando RapidFuzz con fallback a difflib."""
    if not query or not choices:
        return None, 0.0

    try:
        from rapidfuzz import fuzz, process
        res = process.extractOne(query, choices, scorer=fuzz.token_sort_ratio)
        if res:
            return res[0], round(float(res[1]), 2)
    except Exception:
        pass

    from difflib import SequenceMatcher
    q_low = query.strip().lower()
    best_cand = None
    best_ratio = 0.0
    for c in choices:
        ratio = SequenceMatcher(None, q_low, str(c).strip().lower()).ratio() * 100.0
        if ratio > best_ratio:
            best_ratio = ratio
            best_cand = c
    return best_cand, round(best_ratio, 2)


class FinancialCatalogService:

    @staticmethod
    def homologar_concepto(
        termino_crudo: str,
        db_catalog: Optional[Session] = None,
        umbral_confianza: float = 90.0
    ) -> Dict[str, Any]:
        """
        Homologa un término financiero crudo contra los conceptos canónicos y equivalencias históricas.
        
        Retorna:
            {
                "homologado": bool,
                "codigo_canonico": Optional[str],
                "nombre_canonico": Optional[str],
                "tipo_movimiento": Optional[str],
                "categoria_contable": Optional[str],
                "confianza": float,
                "termino_evaluado": str,
                "termino_coincidencia": Optional[str],
                "es_equivalencia_historica": bool,
                "requiere_revision": bool,
                "motivo": Optional[str]
            }
        """
        if not termino_crudo or not str(termino_crudo).strip():
            return {
                "homologado": False,
                "codigo_canonico": None,
                "nombre_canonico": None,
                "tipo_movimiento": None,
                "categoria_contable": None,
                "confianza": 0.0,
                "termino_evaluado": "",
                "termino_coincidencia": None,
                "es_equivalencia_historica": False,
                "requiere_revision": True,
                "motivo": "Término vacío o no proporcionado"
            }

        termino_clean = str(termino_crudo).strip()
        termino_norm = termino_clean.upper()

        own_session = False
        if db_catalog is None:
            db_catalog = CatalogSessionLocal()
            own_session = True

        try:
            # 1. Búsqueda exacta en conceptos canónicos
            concepto_exacto = db_catalog.query(CatConceptoFinanciero).filter(
                (CatConceptoFinanciero.nombre_canonico.ilike(termino_clean)) |
                (CatConceptoFinanciero.codigo_canonico.ilike(termino_clean))
            ).first()

            if concepto_exacto:
                return {
                    "homologado": True,
                    "codigo_canonico": concepto_exacto.codigo_canonico,
                    "nombre_canonico": concepto_exacto.nombre_canonico,
                    "tipo_movimiento": concepto_exacto.tipo_movimiento,
                    "categoria_contable": concepto_exacto.categoria_contable,
                    "confianza": 100.0,
                    "termino_evaluado": termino_clean,
                    "termino_coincidencia": concepto_exacto.nombre_canonico,
                    "es_equivalencia_historica": False,
                    "requiere_revision": False,
                    "motivo": "Coincidencia exacta con catálogo canónico"
                }

            # 2. Búsqueda exacta en equivalencias históricas
            eq_exacta = db_catalog.query(CatHistoricoEquivalencia).filter(
                CatHistoricoEquivalencia.termino_origen.ilike(termino_clean)
            ).first()

            if eq_exacta and eq_exacta.concepto:
                conf = float(eq_exacta.confianza_mapeo) * 100.0 if eq_exacta.confianza_mapeo else 98.0
                return {
                    "homologado": True,
                    "codigo_canonico": eq_exacta.concepto.codigo_canonico,
                    "nombre_canonico": eq_exacta.concepto.nombre_canonico,
                    "tipo_movimiento": eq_exacta.concepto.tipo_movimiento,
                    "categoria_contable": eq_exacta.concepto.categoria_contable,
                    "confianza": round(conf, 2),
                    "termino_evaluado": termino_clean,
                    "termino_coincidencia": eq_exacta.termino_origen,
                    "es_equivalencia_historica": True,
                    "requiere_revision": False,
                    "motivo": f"Equivalencia histórica validada ({eq_exacta.periodo_historico} - {eq_exacta.fuente_referencia})"
                }

            # 3. Búsqueda difusa (Fuzzy Token Sort) contra todo el universo de términos
            conceptos_todos = db_catalog.query(CatConceptoFinanciero).all()
            equivalencias_todas = db_catalog.query(CatHistoricoEquivalencia).all()

            # Mapeo de términos a su concepto destino
            termino_map = {}
            for c in conceptos_todos:
                termino_map[c.nombre_canonico] = (c, False, 100.0)
                termino_map[c.codigo_canonico] = (c, False, 100.0)

            for eq in equivalencias_todas:
                if eq.concepto:
                    termino_map[eq.termino_origen] = (
                        eq.concepto,
                        True,
                        float(eq.confianza_mapeo) * 100.0 if eq.confianza_mapeo else 95.0
                    )

            candidatos = list(termino_map.keys())
            mejor_cand, score = _fuzzy_match(termino_clean, candidatos)

            if mejor_cand and score >= umbral_confianza:
                concepto_dest, es_eq, conf_base = termino_map[mejor_cand]
                confianza_ponderada = round((score * (conf_base / 100.0)), 2)

                return {
                    "homologado": True,
                    "codigo_canonico": concepto_dest.codigo_canonico,
                    "nombre_canonico": concepto_dest.nombre_canonico,
                    "tipo_movimiento": concepto_dest.tipo_movimiento,
                    "categoria_contable": concepto_dest.categoria_contable,
                    "confianza": confianza_ponderada,
                    "termino_evaluado": termino_clean,
                    "termino_coincidencia": mejor_cand,
                    "es_equivalencia_historica": es_eq,
                    "requiere_revision": False,
                    "motivo": f"Coincidencia difusa alta ({score}% con '{mejor_cand}')"
                }

            # Si score < umbral_confianza: POLÍTICA ANTI-CONTAMINACIÓN
            sugerencia = mejor_cand if (mejor_cand and score >= 60.0) else None
            return {
                "homologado": False,
                "codigo_canonico": None,
                "nombre_canonico": None,
                "tipo_movimiento": None,
                "categoria_contable": None,
                "confianza": score,
                "termino_evaluado": termino_clean,
                "termino_coincidencia": sugerencia,
                "es_equivalencia_historica": False,
                "requiere_revision": True,
                "motivo": f"Concepto no homologado: confianza ({score}%) inferior al umbral de seguridad ({umbral_confianza}%)"
            }

        finally:
            if own_session:
                db_catalog.close()

    @staticmethod
    def listar_conceptos(
        db_catalog: Session,
        tipo_movimiento: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retorna lista de conceptos canónicos financieros con sus variantes históricas."""
        query = db_catalog.query(CatConceptoFinanciero)
        if tipo_movimiento:
            query = query.filter(CatConceptoFinanciero.tipo_movimiento.ilike(tipo_movimiento))
        
        conceptos = query.order_by(CatConceptoFinanciero.id_concepto).all()
        resultado = []
        for c in conceptos:
            eqs = [
                {
                    "id_equivalencia": eq.id_equivalencia,
                    "termino_origen": eq.termino_origen,
                    "periodo_historico": eq.periodo_historico,
                    "confianza_mapeo": float(eq.confianza_mapeo) if eq.confianza_mapeo else 1.0,
                    "fuente_referencia": eq.fuente_referencia
                }
                for eq in c.equivalencias
            ]
            resultado.append({
                "id_concepto": c.id_concepto,
                "codigo_canonico": c.codigo_canonico,
                "nombre_canonico": c.nombre_canonico,
                "tipo_movimiento": c.tipo_movimiento,
                "categoria_contable": c.categoria_contable,
                "descripcion": c.descripcion,
                "equivalencias_historicas": eqs
            })
        return resultado
