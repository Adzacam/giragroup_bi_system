from sqlalchemy import Column, Integer, Numeric, ForeignKey
from core.database import Base


class FactRentabilidad(Base):
    __tablename__ = "fact_rentabilidad"

    id_hecho_rent = Column(Integer, primary_key=True, index=True)
    id_modulo = Column(Integer, ForeignKey("dim_modulo.id_modulo", ondelete="CASCADE"))
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo", ondelete="CASCADE"))
    id_categoria = Column(Integer, ForeignKey("dim_categoria_financiera.id_categoria", ondelete="CASCADE"))
    monto_ejecutado = Column(Numeric(14, 2))
    monto_meta = Column(Numeric(14, 2))
