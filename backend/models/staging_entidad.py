"""
backend/models/staging_entidad.py
---------------------------------
Modelo ORM para la tabla de staging de entidades NLP no resueltas.
Almacena entidades con FK Estado C que requieren revisión humana.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Numeric,
    Boolean, DateTime, ForeignKey
)
from sqlalchemy.sql import func
from core.database import Base


class StagingEntidadNoResuelta(Base):
    __tablename__ = "stg_entidad_no_resuelta"

    id_staging = Column(Integer, primary_key=True, index=True)
    id_documento = Column(
        Integer,
        ForeignKey("dim_origen_documental.id_documento", ondelete="CASCADE"),
        nullable=True,
    )
    tipo_entidad = Column(String(30), nullable=False)
    texto_original = Column(Text, nullable=False)
    ci_temporal = Column(String(30), nullable=True)
    mejor_candidato = Column(Text, nullable=True)
    score_fuzzy = Column(Numeric(5, 2), nullable=True)
    fk_estado = Column(String(1), default="C")
    nivel_confianza = Column(Numeric(5, 4), nullable=True)
    resuelto = Column(Boolean, default=False)
    resuelto_por = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resuelto_en = Column(DateTime, nullable=True)
    id_dimension_resuelta = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
