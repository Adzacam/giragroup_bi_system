from sqlalchemy import Column, Integer, String, ForeignKey
from core.database import Base


class DimCategoriaFinanciera(Base):
    __tablename__ = "dim_categoria_financiera"

    id_categoria = Column(Integer, primary_key=True, index=True)
    nombre_categoria = Column(String(200), nullable=False)
    tipo = Column(String(50))  # 'INGRESO', 'EGRESO', 'RENTABILIDAD', 'EBITDA'
    id_cat_categoria_fin = Column(Integer, ForeignKey("cat_categoria_financiera.id_categoria_fin", ondelete="SET NULL"), nullable=True)
