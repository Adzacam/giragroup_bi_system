"""F5V V-4: formularios de identidad en TBL_INSCRITOS, rótulos de grupo y versión de torch."""
import json
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
from models.dim_origen import DimOrigenDocumental  # noqa: E402
from models.staging_entidad import StagingEntidadNoResuelta  # noqa: E402
from services import revision_consulta as rc  # noqa: E402
from services.revision_formularios import campos_para_caso  # noqa: E402

CONVENIO = {"institucion", "clave_convenio", "monto_convenio"}


def _nombres(cat, motivo):
    return {c["name"] for c in campos_para_caso(cat, motivo)}


def test_cedula_dudosa_marketing_pide_identidad():
    n = _nombres("marketing", "CI_DUDOSA")
    assert "ci_corregido" in n and "nombre_completo" in n
    assert not (n & CONVENIO)


def test_marketing_otros_motivos_conservan_convenio():
    assert CONVENIO <= _nombres("marketing", "REVISION_GENERAL")
    assert CONVENIO <= _nombres("marketing", None)


def test_identidad_marketing_valida_payload():
    from services.revision_formularios import validar_payload_correccion
    validar_payload_correccion("marketing", "CI_DUDOSA", {"ci_corregido": "1234567", "nombre_completo": "X", "justificacion": "ok"})


def _sesion():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _attach(c, _r):
        c.execute("ATTACH DATABASE ':memory:' AS public")

    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_rotulos_de_grupo_distinguibles_y_conteos_iguales():
    db = _sesion()
    d1 = DimOrigenDocumental(id_documento=1, tipo_fuente="MARKETING", nombre_archivo="TBL_INSCRITOS.xlsx")
    d2 = DimOrigenDocumental(id_documento=2, tipo_fuente="COBRANZA", nombre_archivo="BD_COBRANZAS.xlsx")
    db.add_all([d1, d2])
    for i, (doc, t) in enumerate([(1, "CI: abc"), (1, "CI: abd"), (2, "CI: xyz")]):
        db.add(StagingEntidadNoResuelta(id_documento=doc, tipo_entidad="ESTUDIANTE", texto_original=t,
                                        motivo="CI_DUDOSA", resuelto=False))
    db.commit()
    docs = [d1, d2]
    from services.bandeja_grupos import grupos_pendientes
    base = grupos_pendientes(db, [1, 2], limite=10**9)
    pub = rc.grupos_publicos(db, docs)
    assert pub["total_casos"] == base["total_casos"] == 3
    assert pub["total_grupos"] == base["total_grupos"]
    assert sorted(g["n"] for g in pub["grupos"]) == sorted(g["n"] for g in base["grupos"])
    titulos = [g["titulo"] for g in pub["grupos"]]
    assert len(set(titulos)) == len(titulos)
    assert any("TBL_INSCRITOS" in t for t in titulos) and any("BD_COBRANZAS" in t for t in titulos)
    assert all(t.startswith("Cédula dudosa") for t in titulos)


def test_version_torch_sale_del_json():
    from routers.dataops.maestros import _framework_texto
    v = json.load(open(os.path.join(ROOT, "docs", "mediciones", "f1_training_info.json"), encoding="utf-8"))["versions"]
    t = _framework_texto()
    assert v["torch"] in t and "2.2" not in t


def test_titulo_de_hechos_incluye_archivo_y_estados():
    class D:  # documento mínimo
        nombre_archivo = "Base ARCA.xlsx"
    g = {"motivo": "HECHO_EN_REVISION", "valor": "academico|doc7|falta:nota|Aprobado|Aprobado|Titulado|estado:OK"}
    archivo, area = rc._origen_grupo(None, g, {7: D()})
    t = rc._titulo_grupo("Hecho", archivo, area)
    assert archivo == "Base ARCA" and "faltan nota" in t and "Aprobado / Aprobado / Titulado" in t
