from sqlalchemy import Column, Integer, String
from core.database import Base


class DimModulo(Base):
    __tablename__ = "dim_modulo"
    id_modulo = Column(Integer, primary_key=True, index=True)
    nombre_modulo = Column(String(200), nullable=False)
    nombre_institucion = Column(String(200), nullable=False, server_default="GiraGroup")
    programa = Column(String(200))
    pos_code = Column(String(50))