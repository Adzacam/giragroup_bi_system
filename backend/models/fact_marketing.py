from sqlalchemy import Column, Integer, Numeric, ForeignKey
from core.database import Base


class FactMarketing(Base):
    __tablename__ = "fact_marketing"

    id_hecho_mkt = Column(Integer, primary_key=True, index=True)
    id_modulo = Column(Integer, ForeignKey("dim_modulo.id_modulo", ondelete="CASCADE"))
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo", ondelete="CASCADE"))
    leads = Column(Integer, default=0)
    reservas = Column(Integer, default=0)
    inscritos = Column(Integer, default=0)
    # Pareja informada por la misma fuente de captación. NULL significa no comprobada.
    # No incluye inscripciones sueltas ni reconstruye cifras históricas.
    leads_captacion = Column(Integer, nullable=True)
    inscritos_captacion = Column(Integer, nullable=True)
    costo_programa = Column(Numeric(12, 2))
