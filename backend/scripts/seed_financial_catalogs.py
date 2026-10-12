"""
backend/scripts/seed_financial_catalogs.py
-------------------------------------------
Crea las tablas 'cat_concepto_financiero' y 'cat_historico_equivalencia' en giragroup_catalog_db
y siembra conceptos canónicos y equivalencias históricas extraídos de los datasets reales:
- uploads/data/BD Cobranzas.xlsx
- uploads/data/BD Egresos.xlsx
- uploads/data/BD Techos.xlsx
- uploads/data/EJECUTADO VS META.xlsx
"""

import sys
import os

# Asegurar path al backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import catalog_engine, CatalogSessionLocal, CatalogBase
from models.catalogos import CatConceptoFinanciero, CatHistoricoEquivalencia

def seed_financial_catalogs():
    print("Creando tablas financieras en giragroup_catalog_db...")
    CatalogBase.metadata.create_all(bind=catalog_engine)

    session = CatalogSessionLocal()
    try:
        conceptos_data = [
            {
                "codigo_canonico": "FIN-CUOTA-01",
                "nombre_canonico": "CUOTA",
                "tipo_movimiento": "INGRESO",
                "categoria_contable": "COBRANZA",
                "descripcion": "Cuota periódica mensual de programas académicos o diplomados",
                "equivalencias": [
                    ("Mensualidad", "2024-2025", 0.98, "BD Cobranzas.xlsx"),
                    ("Colegiatura", "HISTORICO", 0.95, "BD Cobranzas.xlsx"),
                    ("Cuota Diplomado", "2024-2025", 0.99, "BD Cobranzas.xlsx"),
                    ("Cuota Curso", "2024-2025", 0.99, "BD Cobranzas.xlsx"),
                    ("Total de Cuotas", "2024-2025", 0.94, "BD Cobranzas.xlsx"),
                    ("Cantidad de Cuotas", "2024-2025", 0.93, "BD Cobranzas.xlsx"),
                    ("Cuota Mensual", "2024-2025", 0.99, "BD Cobranzas.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-MAT-01",
                "nombre_canonico": "MATRICULA",
                "tipo_movimiento": "INGRESO",
                "categoria_contable": "COBRANZA",
                "descripcion": "Derecho de inscripción o matrícula inicial",
                "equivalencias": [
                    ("Inscripción", "2024-2025", 0.98, "BD Cobranzas.xlsx"),
                    ("Inscripcion", "2024-2025", 0.98, "BD Cobranzas.xlsx"),
                    ("Pago Inicial", "HISTORICO", 0.95, "BD Cobranzas.xlsx"),
                    ("Reserva de Plaza", "HISTORICO", 0.92, "BD Cobranzas.xlsx"),
                    ("Matrícula Académica", "2024-2025", 0.99, "BD Cobranzas.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-CONTADO-01",
                "nombre_canonico": "CONTADO",
                "tipo_movimiento": "INGRESO",
                "categoria_contable": "COBRANZA",
                "descripcion": "Pago total al contado de inversión del programa",
                "equivalencias": [
                    ("Pago al Contado", "2024-2025", 0.99, "BD Cobranzas.xlsx"),
                    ("Pago Único", "HISTORICO", 0.95, "BD Cobranzas.xlsx"),
                    ("Cancelación Total", "HISTORICO", 0.94, "BD Cobranzas.xlsx"),
                    ("Liquidación Completa", "HISTORICO", 0.90, "BD Cobranzas.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-REINC-01",
                "nombre_canonico": "REINCORPORACION",
                "tipo_movimiento": "INGRESO",
                "categoria_contable": "COBRANZA",
                "descripcion": "Pago o cuota por reincorporación de alumno a programa",
                "equivalencias": [
                    ("Reincorporación", "2024-2025", 0.99, "BD Cobranzas.xlsx"),
                    ("Reincorporacion", "2024-2025", 0.99, "BD Cobranzas.xlsx"),
                    ("Reactivación Alumno", "HISTORICO", 0.92, "BD Cobranzas.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-DESC-01",
                "nombre_canonico": "DESCUENTO",
                "tipo_movimiento": "AJUSTE",
                "categoria_contable": "COBRANZA",
                "descripcion": "Descuento comercial, beca o beneficio sobre arancel",
                "equivalencias": [
                    ("Beca", "2024-2025", 0.95, "BD Cobranzas.xlsx"),
                    ("Beca Parcial", "HISTORICO", 0.92, "BD Cobranzas.xlsx"),
                    ("Descuento Comercial", "2024-2025", 0.99, "BD Cobranzas.xlsx"),
                    ("Promoción 2x1", "HISTORICO", 0.90, "BD Cobranzas.xlsx"),
                    ("Beneficio Institucional", "2024-2025", 0.91, "BD Cobranzas.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-MORA-01",
                "nombre_canonico": "MORA",
                "tipo_movimiento": "AJUSTE",
                "categoria_contable": "COBRANZA",
                "descripcion": "Recargo, penalización o cuotas en mora",
                "equivalencias": [
                    ("Recargo por Mora", "2024-2025", 0.98, "BD Cobranzas.xlsx"),
                    ("Interés por Mora", "HISTORICO", 0.96, "BD Cobranzas.xlsx"),
                    ("Días de Mora", "2024-2025", 0.95, "BD Cobranzas.xlsx"),
                    ("Total Cuotas en Mora", "2024-2025", 0.96, "BD Cobranzas.xlsx"),
                    ("Penalización Mora", "HISTORICO", 0.94, "BD Cobranzas.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-DEUDA-01",
                "nombre_canonico": "DEUDA_TOTAL",
                "tipo_movimiento": "SALDO",
                "categoria_contable": "COBRANZA",
                "descripcion": "Saldo deudor total pendiente por cobrar",
                "equivalencias": [
                    ("Saldo Pendiente", "2024-2025", 0.95, "BD Cobranzas.xlsx"),
                    ("Saldo Deudor", "HISTORICO", 0.95, "BD Cobranzas.xlsx"),
                    ("Monto a Cobrar Después de Descuento", "2024-2025", 0.92, "BD Cobranzas.xlsx"),
                    ("Días de Pago Pendiente", "2024-2025", 0.90, "BD Cobranzas.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-PAGADO-01",
                "nombre_canonico": "TOTAL_PAGADO",
                "tipo_movimiento": "INGRESO",
                "categoria_contable": "COBRANZA",
                "descripcion": "Monto acumulado pagado hasta la fecha",
                "equivalencias": [
                    ("Total Pagado Hasta la Fecha", "2024-2025", 0.99, "BD Cobranzas.xlsx"),
                    ("Cobrado Real", "2024-2025", 0.95, "BD Cobranzas.xlsx"),
                    ("Recaudación Efectiva", "HISTORICO", 0.92, "BD Cobranzas.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-EGR-REAL-01",
                "nombre_canonico": "EGRESO_REAL",
                "tipo_movimiento": "EGRESO",
                "categoria_contable": "OPERATIVO",
                "descripcion": "Gasto operativo o de ejecución real del programa",
                "equivalencias": [
                    ("Egreso Real", "2023-2025", 0.99, "BD Egresos.xlsx"),
                    ("Gasto Efectivo", "HISTORICO", 0.95, "BD Egresos.xlsx"),
                    ("Costo de Operación", "HISTORICO", 0.92, "BD Egresos.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-EGR-ANT-01",
                "nombre_canonico": "EGRESO_ANTERIOR",
                "tipo_movimiento": "EGRESO",
                "categoria_contable": "OPERATIVO",
                "descripcion": "Egreso o presupuesto histórico de gestiones previas",
                "equivalencias": [
                    ("Egreso Anterior", "2023-2025", 0.99, "BD Egresos.xlsx"),
                    ("Gasto Histórico", "HISTORICO", 0.94, "BD Egresos.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-HON-DOC-01",
                "nombre_canonico": "HONORARIO_DOCENTE",
                "tipo_movimiento": "EGRESO",
                "categoria_contable": "DOCENTE",
                "descripcion": "Pago de honorarios profesionales a docentes por módulo",
                "equivalencias": [
                    ("Pago Docente", "HISTORICO", 0.98, "BD Egresos.xlsx"),
                    ("Honorarios Docente", "2024-2025", 0.99, "BD Egresos.xlsx"),
                    ("Remuneración Módulo", "HISTORICO", 0.94, "BD Egresos.xlsx"),
                    ("Facilitador Módulo", "HISTORICO", 0.91, "BD Egresos.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-TECHO-01",
                "nombre_canonico": "TECHO_CONVENIO",
                "tipo_movimiento": "INGRESO",
                "categoria_contable": "CONVENIO",
                "descripcion": "Facturación por acuerdos institucionales cerrados (techos)",
                "equivalencias": [
                    ("Techo Cerrado", "2024-2025", 0.99, "BD Techos.xlsx"),
                    ("Facturación Convenio", "HISTORICO", 0.95, "BD Techos.xlsx"),
                    ("Convenio Institucional", "2024-2025", 0.96, "BD Techos.xlsx"),
                    ("Convenio SIB TARIJA", "2024-2025", 0.92, "BD Techos.xlsx"),
                    ("Convenio STOLZEL", "2024-2025", 0.92, "BD Techos.xlsx"),
                    ("Convenio CODESING", "2024-2025", 0.92, "BD Techos.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-META-PROG-01",
                "nombre_canonico": "META_PROGRAMAS",
                "tipo_movimiento": "AJUSTE",
                "categoria_contable": "METAS",
                "descripcion": "Meta institucional mensual asignada a programas y diplomados",
                "equivalencias": [
                    ("Meta por Categoría Programas", "2024-2025", 0.97, "EJECUTADO VS META.xlsx"),
                    ("Presupuesto Programas", "HISTORICO", 0.93, "EJECUTADO VS META.xlsx"),
                ]
            },
            {
                "codigo_canonico": "FIN-META-TECHO-01",
                "nombre_canonico": "META_TECHOS",
                "tipo_movimiento": "AJUSTE",
                "categoria_contable": "METAS",
                "descripcion": "Meta institucional asignada a contratos por techos cerrados",
                "equivalencias": [
                    ("Meta Techos Cerrados", "2024-2025", 0.98, "EJECUTADO VS META.xlsx"),
                    ("Presupuesto Techos", "HISTORICO", 0.94, "EJECUTADO VS META.xlsx"),
                ]
            }
        ]

        total_conceptos = 0
        total_equivalencias = 0

        for c_data in conceptos_data:
            existente = session.query(CatConceptoFinanciero).filter(
                CatConceptoFinanciero.codigo_canonico == c_data["codigo_canonico"]
            ).first()

            if not existente:
                concepto = CatConceptoFinanciero(
                    codigo_canonico=c_data["codigo_canonico"],
                    nombre_canonico=c_data["nombre_canonico"],
                    tipo_movimiento=c_data["tipo_movimiento"],
                    categoria_contable=c_data["categoria_contable"],
                    descripcion=c_data["descripcion"]
                )
                session.add(concepto)
                session.flush()
                total_conceptos += 1
            else:
                concepto = existente

            for term, per, conf, fuente in c_data["equivalencias"]:
                eq_existente = session.query(CatHistoricoEquivalencia).filter(
                    CatHistoricoEquivalencia.id_concepto == concepto.id_concepto,
                    CatHistoricoEquivalencia.termino_origen == term
                ).first()

                if not eq_existente:
                    eq = CatHistoricoEquivalencia(
                        id_concepto=concepto.id_concepto,
                        termino_origen=term,
                        periodo_historico=per,
                        confianza_mapeo=conf,
                        fuente_referencia=fuente
                    )
                    session.add(eq)
                    total_equivalencias += 1

        session.commit()
        print(f"Siembra completada con éxito:")
        print(f" - {total_conceptos} nuevos conceptos canónicos sembrados.")
        print(f" - {total_equivalencias} nuevas equivalencias históricas registradas.")

    except Exception as e:
        session.rollback()
        print(f"Error durante la siembra de catálogos financieros: {e}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    seed_financial_catalogs()
