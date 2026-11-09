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
from sqlalchemy import bindparam, event, text
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from core.database import Base
from models.staging_registro import FlexibleJSONB


class StagingEntidadNoResuelta(Base):
    __tablename__ = "stg_entidad_no_resuelta"

    id_staging = Column(Integer, primary_key=True, index=True)
    id_documento = Column(
        Integer,
        ForeignKey("dim_origen_documental.id_documento", ondelete="CASCADE"),
        nullable=True,
    )
    tipo_entidad = Column(String(50), nullable=False)
    texto_original = Column(Text, nullable=False)
    ci_temporal = Column(String(150), nullable=True)
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

    # Columnas estructuradas HITL / DataOps
    motivo = Column(String(100), nullable=True)
    payload_json = Column(FlexibleJSONB, nullable=True)
    registro_origen_id = Column(
        Integer,
        ForeignKey("staging_registros_crudos.id", ondelete="CASCADE"),
        nullable=True,
    )
    estado_resolucion = Column(String(30), default="PENDIENTE")
    lock_usuario_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    lock_expira = Column(DateTime, nullable=True)
    version = Column(Integer, default=1)
    # Idempotencia: md5(hash del archivo | tipo | motivo | valor normalizado); índice único uq_stg_entidad_clave_origen
    clave_origen = Column(String(32), nullable=True)

    created_at = Column(DateTime, server_default=func.now())


def clave_staging(hash_doc, tipo, motivo, texto):
    """Clave de idempotencia de una entidad en cola: mismo archivo (por hash), tipo, motivo y valor normalizado."""
    import hashlib
    valor = " ".join((texto or "").split()).lower()
    return hashlib.md5("|".join([hash_doc or "", tipo or "", motivo or "", valor]).encode("utf-8")).hexdigest()


@event.listens_for(Session, "before_flush")
def _deduplicar_staging(session, flush_context, instances):
    """Reprocesar el mismo archivo no vuelve a encolar la misma entidad (una sola por clave_origen)."""
    nuevos = [o for o in session.new if isinstance(o, StagingEntidadNoResuelta)]
    if not nuevos:
        return
    con = session.connection()
    ids = {o.id_documento for o in nuevos if o.id_documento is not None}
    hashes = {}
    if ids:
        hashes = {r[0]: r[1] for r in con.execute(
            text("SELECT id_documento, hash_sha256 FROM dim_origen_documental WHERE id_documento IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": list(ids)})}
    vistas = set()
    for o in nuevos:
        h = hashes.get(o.id_documento) or (f"doc{o.id_documento}" if o.id_documento is not None else "")
        o.clave_origen = clave_staging(h, o.tipo_entidad, o.motivo, o.texto_original)
    claves = list({o.clave_origen for o in nuevos})
    existentes = {r[0] for r in con.execute(
        text("SELECT clave_origen FROM stg_entidad_no_resuelta WHERE clave_origen IN :c").bindparams(bindparam("c", expanding=True)), {"c": claves})}
    for o in nuevos:
        if o.clave_origen in existentes or o.clave_origen in vistas:
            session.expunge(o)
        else:
            vistas.add(o.clave_origen)
