"""F3T T-1 (D-T1): filas de convenio resueltas por regla en libro MARKETING no van a BETO ni a staging."""
import pandas as pd

from models.dim_origen import DimOrigenDocumental
from models.fact_techo_convenio import FactTechoConvenio
from models.lote import Lote
from models.staging_entidad import StagingEntidadNoResuelta
from models.staging_registro import StagingRegistroCrudo
from routers import dataops
from services import cache_consultas
from services.extraccion_por_encabezado import campos_por_encabezado, fila_resuelta_por_regla
from tests.dataops_parches import parchear

# Filas reales 11, 13 y 14 del documento 20 (uploads/data/BD Techos.xlsx)
FILAS_REALES_DOC20 = [
    {
        "N°": 11,
        "Gestión Techo": 2023,
        "Coord.": "Sharon",
        "Fecha Inicio": "2023-09-25 00:00:00",
        "Fecha Conclusión": "2024-01-19 00:00:00",
        "Escuela techo": "TECNOLOGÍA",
        "Insitución": "CODESING",
        "POS": 5165,
        "EXP": "POS-5165",
        "Programa": "POS-5165 DIPLOMADO EN GESTIÓN DE CALIDAD PARA LABORATORIOS DE ENSAYO Y CALIBRACIÓN EN BASE A LA NB-ISO/IEC 17025:2018 V.3",
        "Estado de Pago": 5200.0,
        "N° Inscr.": 13,
        "Tipo de certificado": "Físico",
        "Estado entrega de certificados": "Entregado",
        "id_institucion": "CODESING5165",
    },
    {
        "N°": 13,
        "Gestión Techo": 2024,
        "Coord.": "Sharon",
        "Fecha Inicio": "2023-05-15 00:00:00",
        "Fecha Conclusión": "2023-06-27 00:00:00",
        "Escuela techo": "NEGOCIOS",
        "Insitución": "ICALP",
        "POS": 4943,
        "EXP": "POS-4943",
        "Programa": "DIPLOMADO EN DERECHO ADMINISTRATIVO Y CONTRATACIONES ESTATALES v. 5 - NAL",
        "Estado de Pago": 23942.4,
        "N° Inscr.": 43,
        "Tipo de certificado": "Físico",
        "Estado entrega de certificados": "Entregado",
        "id_institucion": "ICALP4943",
    },
    {
        "N°": 14,
        "Gestión Techo": 2024,
        "Coord.": "Sharon",
        "Fecha Inicio": "2023-05-18 00:00:00",
        "Fecha Conclusión": "2023-08-15 00:00:00",
        "Escuela techo": "CIENCIAS SOCIALES",
        "Insitución": "ICALP",
        "POS": 4944,
        "EXP": "POS-4944",
        "Programa": "DIPLOMADO EN EDUCACIÓN SUPERIOR v. 2 - NAL",
        "Estado de Pago": 25612.8,
        "N° Inscr.": 46,
        "Tipo de certificado": "Físico",
        "Estado entrega de certificados": "Entregado",
        "id_institucion": "ICALP4944",
    },
]


def test_regla_convenio_resuelve_en_marketing_y_admision():
    for fila in FILAS_REALES_DOC20:
        campos = campos_por_encabezado([f"{k}: {v}" for k, v in fila.items()])
        assert fila_resuelta_por_regla(campos, "marketing")
        assert fila_resuelta_por_regla(campos, "admision")
        assert fila_resuelta_por_regla(campos, "rentabilidad")
        assert not fila_resuelta_por_regla(campos, "academico")


def test_convenios_en_marketing_no_van_a_revision_estudiante(dw_sqlite, monkeypatch, tmp_path):
    from services import cache_lectura, ingestion_service
    from services.ingestion_service import IngestionService

    db = dw_sqlite
    cache_consultas.invalidar()
    monkeypatch.setattr(cache_lectura, "DIR", tmp_path)
    monkeypatch.setattr(ingestion_service, "AsymmetricFlattener", None)
    enviadas = []

    def beto_bajo(lineas, **kw):
        enviadas.extend(lineas)
        return [0.577] * len(lineas)

    parchear(monkeypatch, "obtener_indices", beto_bajo)
    monkeypatch.setattr("services.confianza_service.indices_en_cache", lambda lineas: [None] * len(lineas))

    lote = Lote(institucion="Prueba", periodo="2024")
    db.add(lote)
    db.flush()

    archivo = tmp_path / "BD Techos.xlsx"
    with pd.ExcelWriter(archivo) as w:
        pd.DataFrame(FILAS_REALES_DOC20).to_excel(w, sheet_name="BD Techos", index=False)

    IngestionService.procesar_archivo(
        db,
        str(archivo),
        archivo.name,
        id_lote=lote.id_lote,
        tipo_fuente="MARKETING",
        institucion="Prueba",
        tipo_escala="CENTESIMAL_100",
    )
    doc = db.query(DimOrigenDocumental).filter_by(id_lote=lote.id_lote).one()
    doc.tipo_fuente = "MARKETING"
    db.commit()
    assert db.query(StagingRegistroCrudo).filter_by(id_documento=doc.id_documento).count() >= 1

    dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), db, None)

    assert not enviadas, f"BETO recibió filas de convenio ya resueltas por regla: {enviadas}"
    assert db.query(StagingEntidadNoResuelta).filter_by(tipo_entidad="ESTUDIANTE").count() == 0
    assert db.query(FactTechoConvenio).count() == 3
    cache_consultas.invalidar()
