from sqlalchemy import Column, Integer, String
from api.database import Base
from .dim_financiero import DimFinanciero

class DimInstitucion(Base):
    __tablename__ = "dim_institucion"

    id_institucion = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)