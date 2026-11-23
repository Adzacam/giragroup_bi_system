"""Pruebas de CAT-L3: resolución de institución canónica y sinónimo 'GiraGroup' -> 361."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ / "backend") not in sys.path:
    sys.path.insert(0, str(RAIZ / "backend"))

from core.database import Base
from models.catalogos import CatInstitucion
from models.dim_modulo import DimModulo
from services.dw_loader import DWLoaderService


@pytest.fixture
def dw_mem():
    engine = create_engine("sqlite:///:memory:").execution_options(schema_translate_map={"public": None})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(CatInstitucion(id_institucion=361, nombre_institucion="GiraGroup Posgrado", sigla="GG"))
    db.commit()
    try:
        yield db
    finally:
        db.close()


def test_giragroup_resuelve_a_canonica_361(dw_mem):
    loader = DWLoaderService(dw_mem)
    with patch.object(loader, "_buscar_sinonimo_institucion", side_effect=lambda c, **_: "GiraGroup Posgrado" if c == "giragroup" else None):
        id_mod = loader.resolver_o_crear_modulo(
            "Módulo 1: Gerencia", pos_code="POS-8888", doc_id=1, institucion="GiraGroup"
        )
    assert id_mod is not None
    mod = dw_mem.query(DimModulo).filter_by(id_modulo=id_mod).first()
    assert mod.id_institucion == 361
