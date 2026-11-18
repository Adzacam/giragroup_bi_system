from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from core.database import Base
from models.staging_registro import FlexibleJSONB


class FactPlanificacionPrograma(Base):
    __tablename__ = "fact_planificacion_programa"

    id_planificacion = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True)
    id_modulo = Column(Integer, ForeignKey("dim_modulo.id_modulo", ondelete="SET NULL"), nullable=True)
    id_tiempo_plan = Column(Integer, ForeignKey("dim_tiempo.id_tiempo", ondelete="SET NULL"), nullable=True)
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="CASCADE"), nullable=False, index=True)
    clave_fila_origen = Column(
        String(64),
        nullable=False,
        unique=True,
    )
    clave_contenido = Column(CHAR(64), nullable=False)
    hoja = Column(String(200), nullable=False)
    fila_excel = Column(Integer, nullable=False)
    pos_code_fuente = Column(String(80), nullable=True)
    nombre_programa = Column(Text, nullable=True)
    tipo_programa = Column(String(100), nullable=True)
    escuela = Column(String(120), nullable=True)
    origen_programa = Column(String(120), nullable=True)
    diseno_curricular = Column(String(160), nullable=True)
    fecha_notificacion = Column(Date, nullable=True)
    fecha_inicio_plan = Column(Date, nullable=True)
    fecha_fin_plan = Column(Date, nullable=True)
    duracion_meses = Column(Numeric(8, 2), nullable=True)
    estado_fuente = Column(String(120), nullable=True)
    notificado = Column(Boolean, nullable=True)
    costo_programa = Column(Numeric(14, 2), nullable=True)
    costo_descuento_20 = Column(Numeric(14, 2), nullable=True)
    tarifa_contado_100 = Column(Numeric(14, 2), nullable=True)
    tarifa_contado_80 = Column(Numeric(14, 2), nullable=True)
    punto_equilibrio = Column(Numeric(14, 2), nullable=True)
    leads_fuente = Column(Numeric(14, 2), nullable=True)
    reservas_fuente = Column(Numeric(14, 2), nullable=True)
    inscritos_fuente = Column(Numeric(14, 2), nullable=True)
    pauta_ejecutada = Column(Numeric(14, 2), nullable=True)
    pauta_asignada = Column(Numeric(14, 2), nullable=True)
    payload_fuente = Column(FlexibleJSONB, nullable=True)
    requiere_revision = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_fact_plan_pos_mes", "pos_code_fuente", "id_tiempo_plan"),
    )
