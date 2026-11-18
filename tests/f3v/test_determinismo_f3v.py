"""V-1: Pruebas de determinismo en resolucion de dim_modulo, dim_docente, dim_estudiante y fact_marketing."""
import hashlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from core.database import Base  # noqa: E402
import models  # noqa: F401, E402
from models.dim_docente import DimDocente  # noqa: E402
from models.dim_estudiante import DimEstudiante  # noqa: E402
from models.dim_modulo import DimModulo  # noqa: E402
from models.dim_origen import DimOrigenDocumental  # noqa: E402
from models.dim_tiempo import DimTiempo  # noqa: E402
from models.fact_marketing import FactMarketing  # noqa: E402
from services.dw_loader import DWLoaderService, _fuzzy_best_match  # noqa: E402


def _make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _attach(dbapi_conn, _rec):
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS public")

    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_fuzzy_best_match_desempata_por_menor_id_sin_importar_orden():
    id_map = {"Diplomado Finanzas Corporativas": 25, "Diplomado Finanzas Corporativa": 12}
    cands_a = ["Diplomado Finanzas Corporativas", "Diplomado Finanzas Corporativa"]
    cands_b = list(reversed(cands_a))
    # Ambos empatan o casi empatan; si hay empate exacto en score, gana id_modulo=12 siempre
    m1, s1 = _fuzzy_best_match("Diplomado Finanzas Corporativ", cands_a, id_map=id_map)
    m2, s2 = _fuzzy_best_match("Diplomado Finanzas Corporativ", cands_b, id_map=id_map)
    assert (m1, s1) == (m2, s2)

    # Empate exacto garantizado (mismo conjunto de tokens)
    id_map_tie = {"Gestion Proyectos Alpha": 50, "Alpha Proyectos Gestion": 7}
    t1, st1 = _fuzzy_best_match("Gestion Proyectos Alpha", ["Gestion Proyectos Alpha", "Alpha Proyectos Gestion"], id_map=id_map_tie)
    t2, st2 = _fuzzy_best_match("Gestion Proyectos Alpha", ["Alpha Proyectos Gestion", "Gestion Proyectos Alpha"], id_map=id_map_tie)
    assert t1 == "Alpha Proyectos Gestion"
    assert t2 == "Alpha Proyectos Gestion"
    assert st1 == st2 == 100.0


def test_resolver_modulo_determinista_con_precarga_en_distinto_orden():
    def _cargar_clon(orden_inverso: bool):
        db = _make_session()
        db.add(DimTiempo(id_tiempo=1, gestion=2026, mes=3))
        db.add(DimOrigenDocumental(id_documento=1, nombre_archivo="mkt.xlsx", tipo_fuente="MARKETING"))
        modulos = [
            DimModulo(id_modulo=10, pos_code="POS-5001", nombre_modulo="Diplomado en Gestion Publica"),
            DimModulo(id_modulo=20, pos_code="POS-5001", nombre_modulo="Diplomado en Gestion Publica"),
            DimModulo(id_modulo=30, pos_code="MOD-GEN", nombre_modulo="Curso de Excel Avanzado I"),
            DimModulo(id_modulo=40, pos_code="MOD-GEN", nombre_modulo="I Avanzado Excel de Curso"),
        ]
        if orden_inverso:
            modulos = list(reversed(modulos))
        for m in modulos:
            db.add(m)
        db.commit()

        loader = DWLoaderService(db)
        # 1) Por pos_code duplicado -> siempre menor id_modulo (10)
        id_pos = loader.resolver_o_crear_modulo("Diplomado en Gestion Publica", pos_code="POS-5001")
        # 2) Por nombre exacto duplicado -> siempre menor id_modulo (10)
        id_nom = loader.resolver_o_crear_modulo("Diplomado en Gestion Publica", pos_code=None)
        # 3) Por fuzzy >= 80% con empate de token_sort_ratio -> siempre menor id_modulo (30)
        id_fuzz = loader.resolver_o_crear_modulo("Curso de Excel Avanzado I!", pos_code=None)
        return id_pos, id_nom, id_fuzz

    res_directo = _cargar_clon(False)
    res_inverso = _cargar_clon(True)
    assert res_directo == (10, 10, 30)
    assert res_inverso == res_directo


def test_fact_marketing_md5_identico_con_dim_modulo_en_distinto_orden():
    def _correr_lote_mkt(orden_inverso: bool):
        db = _make_session()
        db.add(DimTiempo(id_tiempo=202603, gestion=2026, mes=3))
        db.add(DimOrigenDocumental(id_documento=1, nombre_archivo="mkt.xlsx", tipo_fuente="MARKETING"))
        pre = [
            DimModulo(id_modulo=5, pos_code="POS-9001", nombre_modulo="Maestria Gerencia Empresarial"),
            DimModulo(id_modulo=15, pos_code="MOD-GEN", nombre_modulo="Empresarial Gerencia Maestria"),
            DimModulo(id_modulo=25, pos_code="POS-9002", nombre_modulo="Diplomado Tributacion"),
        ]
        if orden_inverso:
            pre = list(reversed(pre))
        for m in pre:
            db.add(m)
        db.commit()

        loader = DWLoaderService(db)
        filas = [
            ("k1", "Maestria Gerencia Empresarial", None, 3),
            ("k2", "Maestria Gerencia Empresarial!", None, 2),
            ("k3", "Diplomado Tributacion", "POS-9002", 4),
            ("k4", "Programa Nuevo", "POS-9003", 5),
        ]
        for clave, nom, pos, ins in filas:
            loader.cargar_registro({
                "doc_id": 1,
                "categoria": "marketing",
                "clave_origen": clave,
                "clave_contenido": clave,
                "resoluciones": {
                    "modulo": nom,
                    "pos_code": pos,
                    "fecha": "2026-03-01",
                    "inscritos": ins,
                    "leads": ins * 2,
                    "reservas": 1,
                },
                "calidad": {"requiere_revision": False},
            })
        db.commit()
        rows = (
            db.query(FactMarketing.id_modulo, FactMarketing.id_tiempo, FactMarketing.leads, FactMarketing.reservas, FactMarketing.inscritos)
            .order_by(FactMarketing.id_modulo, FactMarketing.id_tiempo)
            .all()
        )
        payload = "|".join(f"{r[0]}:{r[1]}:{r[2]}:{r[3]}:{r[4]}" for r in rows)
        return hashlib.md5(payload.encode()).hexdigest(), sum(r[4] for r in rows)

    md5_a, ins_a = _correr_lote_mkt(False)
    md5_b, ins_b = _correr_lote_mkt(True)
    assert md5_a == md5_b
    assert ins_a == ins_b == 14


def test_resolver_docente_y_estudiante_deterministas():
    db = _make_session()
    db.add(DimDocente(id_docente=8, nombre_completo="Carlos Mendoza"))
    db.add(DimDocente(id_docente=3, nombre_completo="Carlos Mendoza"))
    db.add(DimEstudiante(id_estudiante=22, ci="777888", ci_numero="777888", nombre_completo="Ana Torres", deprecado=False))
    db.add(DimEstudiante(id_estudiante=9, ci="777888", ci_numero="777888", nombre_completo="Ana Torres", deprecado=False))
    db.commit()

    loader = DWLoaderService(db)
    assert loader.resolver_o_crear_docente("Dr. Carlos Mendoza") == 3
    assert loader.resolver_o_crear_estudiante("777888", "Ana Torres") == (9, "A")
