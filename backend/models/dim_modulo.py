from sqlalchemy import Column, Integer, String, ForeignKey
from core.database import Base

class DimModulo(Base):
    __tablename__ = "dim_modulo"
    id_modulo = Column(Integer, primary_key=True, index=True)
    nombre_modulo = Column(String(200), nullable=False)
    id_institucion = Column(Integer, ForeignKey("dim_institucion.id_institucion"))
    programa = Column(String(200))