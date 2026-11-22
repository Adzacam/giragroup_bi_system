from sqlalchemy import Column, Integer, Numeric, ForeignKey, String
from sqlalchemy.orm import deferred
from core.database import Base


class FactRentabilidad(Base):
    __tablename__ = "fact_rentabilidad"

    id_hecho_rent = Column(Integer, primary_key=True, index=True)
    id_modulo = Column(Integer, ForeignKey("dim_modulo.id_modulo", ondelete="CASCADE"))
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo", ondelete="CASCADE"))
    id_categoria = Column(Integer, ForeignKey("dim_categoria_financiera.id_categoria", ondelete="CASCADE"))
    monto_ejecutado = Column(Numeric(14, 2))
    monto_meta = Column(Numeric(14, 2))
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="SET NULL"))  # fuente de la cifra vigente
    # FU-L6 (migración 026, DA4): MENSUAL (meta de ese mes) o ANUAL (una sola celda de la gestión: no es la meta de ningún mes).
    # NULL: anterior a la 026 o fuente sin perfil; las vistas lo leen como MENSUAL. deferred: la DW puede no tener la migración.
    granularidad_meta = deferred(Column(String(10), nullable=True))
