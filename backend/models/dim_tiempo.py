from sqlalchemy import Column, Integer, String
from core.database import Base

class DimTiempo(Base):
    __tablename__ = "dim_tiempo"
    id_tiempo = Column(Integer, primary_key=True, index=True)
    gestion = Column(Integer, nullable=False)
    semestre = Column(Integer)
    mes = Column(String(20))