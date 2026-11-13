"""Catálogo curricular: búsqueda por nombre/código/programa, filtro por gestión y paginación en el servidor."""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from models.dim_modulo import DimModulo
from models.dim_tiempo import DimTiempo
from models.fact_marketing import FactMarketing
from services.catalog_service import CatalogService


@pytest.fixture
def servicio():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def adjuntar_public(conn, _):
        cur = conn.cursor()
        cur.execute("ATTACH DATABASE ':memory:' AS public")
        cur.close()

    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    db.add_all([
        DimTiempo(id_tiempo=202401, gestion=2024, semestre=1, mes=1, periodo_mes="2024-01"),
        DimTiempo(id_tiempo=202501, gestion=2025, semestre=1, mes=1, periodo_mes="2025-01"),
    ])
    for i in range(1, 13):
        db.add(DimModulo(id_modulo=i, nombre_modulo=f"Módulo {i:02d}", nombre_institucion="GiraGroup",
                         programa="Maestría en Finanzas" if i <= 8 else "Diplomado en Datos",
                         pos_code=f"POS-{i:02d}" if i % 2 else None))
    db.flush()
    # módulos 1-3 con actividad en 2024; módulo 9 en 2025
    for modulo, tiempo in ((1, 202401), (2, 202401), (3, 202401), (9, 202501)):
        db.add(FactMarketing(id_modulo=modulo, id_tiempo=tiempo, inscritos=10))
    db.commit()
    yield CatalogService(db)
    db.close()


def test_pagina_en_el_servidor_con_total_real(servicio):
    r = servicio.listar_modulos(pagina=1, por_pagina=5)
    assert r["total"] == 12 and len(r["data"]) == 5
    ultima = servicio.listar_modulos(pagina=3, por_pagina=5)
    assert len(ultima["data"]) == 2


def test_busca_por_programa_ademas_de_nombre_y_codigo(servicio):
    assert servicio.listar_modulos(busqueda="diplomado", pagina=1, por_pagina=50)["total"] == 4
    assert servicio.listar_modulos(busqueda="pos-03", pagina=1, por_pagina=50)["total"] == 1


def test_filtra_por_gestion_con_actividad(servicio):
    assert servicio.listar_modulos(gestion=2024, pagina=1, por_pagina=50)["total"] == 3
    assert servicio.listar_modulos(gestion=2025, pagina=1, por_pagina=50)["total"] == 1
    assert servicio.listar_modulos(gestion=2023, pagina=1, por_pagina=50)["total"] == 0


def test_resumen_y_gestiones_disponibles(servicio):
    r = servicio.listar_modulos(pagina=1, por_pagina=5)
    assert r["resumen"] == {"instituciones": 1, "con_codigo_pos": 6}
    assert r["gestiones"] == [2024, 2025]


def test_sin_paginar_conserva_el_comportamiento_anterior(servicio):
    r = servicio.listar_modulos(busqueda="módulo 1")
    assert "resumen" not in r and r["total"] == len(r["data"]) == 3
