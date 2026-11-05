from sqlalchemy import Column, Date, Integer, Numeric, String, ForeignKey, UniqueConstraint
from core.database import Base


class BridgeModuloDocente(Base):
    """
    Qué docente dictó cada módulo (POS-XXXX-MNN), según hojas de asignación como MODULOS de ARCA.
    Un módulo puede tener más de un docente (titular, auxiliar): por eso es un puente y no una columna
    de dim_modulo. Permite atribuir notas y evaluaciones al docente aunque la fila no lo nombre.
    """
    __tablename__ = "bridge_modulo_docente"
    __table_args__ = (UniqueConstraint("id_modulo", "id_docente", name="uq_bridge_modulo_docente"),)

    id_asignacion = Column(Integer, primary_key=True, index=True)
    id_modulo = Column(Integer, ForeignKey("dim_modulo.id_modulo", ondelete="CASCADE"), nullable=False, index=True)
    id_docente = Column(Integer, ForeignKey("dim_docente.id_docente", ondelete="CASCADE"), nullable=False, index=True)
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="SET NULL"))
    tipo_docente = Column(String(30))
    grado_academico = Column(String(50))
    horas_modulo = Column(Numeric(6, 2))
    pago_docente = Column(Numeric(12, 2))
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
