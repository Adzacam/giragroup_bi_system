from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.dim_estudiante import DimEstudiante
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera

def get_riesgo_cruzado(db: Session, limite_nota: float = 70.0, min_cuotas_mora: int = 2):
    """
    Cruza la constelación de hechos: Obtiene estudiantes que están 
    reprobando o al límite (<= 70) Y que además tienen 2 o más cuotas en mora.
    """
    # Consulta SQLAlchemy uniendo las dos tablas de hechos mediante la dimensión compartida
    resultados = db.query(
        DimEstudiante.nombre_completo,
        DimEstudiante.codigo_estudiante,
        FactRendimientoAcademico.nota_final,
        FactSituacionFinanciera.cuotas_impagas,
        FactSituacionFinanciera.monto_deuda,
        FactSituacionFinanciera.estado_cartera
    ).join(
        FactRendimientoAcademico, 
        DimEstudiante.id_estudiante == FactRendimientoAcademico.id_estudiante
    ).join(
        FactSituacionFinanciera, 
        DimEstudiante.id_estudiante == FactSituacionFinanciera.id_estudiante
    ).filter(
        FactRendimientoAcademico.nota_final <= limite_nota,
        FactSituacionFinanciera.cuotas_impagas >= min_cuotas_mora
    ).order_by(
        desc(FactSituacionFinanciera.cuotas_impagas),
        FactRendimientoAcademico.nota_final
    ).all()

    # Formatear la salida para FastAPI (Transformar las tuplas de SQLAlchemy a diccionarios)
    alertas_cruzadas = []
    for row in resultados:
        alertas_cruzadas.append({
            "estudiante": row.nombre_completo,
            "codigo": row.codigo_estudiante,
            "rendimiento": {
                "nota_actual": float(row.nota_final),
                "estado_academico": "CRÍTICO"
            },
            "finanzas": {
                "cuotas_mora": row.cuotas_impagas,
                "deuda_total": float(row.monto_deuda),
                "estado_cartera": row.estado_cartera
            },
            "nivel_riesgo_global": "ALTO - REQUIERE INTERVENCIÓN"
        })
        
    return alertas_cruzadas