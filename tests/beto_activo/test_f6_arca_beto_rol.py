"""Pruebas unitarias F6-3a (cruce ARCA MODULOS->ACTAS), F6-3b (rol BETO) y F6-3c (selección de celdas + caché)."""
import hashlib
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
for p in (str(RAIZ), str(RAIZ / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from pipeline import config as cfg
from pipeline.semantic.indice_confianza import MAX_CELDAS_TEXTO, MAX_LENGTH_TOKENS, texto_para_indice
from services import beto_integracion as bi
from services import confianza_service as cs
from services.extraccion_por_encabezado import indexar_modulos_arca, registros_academicos


# ── F6-3a: Cruce MODULOS -> ACTAS DE NOTAS en ARCA ────────────────────────────

def test_f6_3a_cruce_modulos_resuelve_fecha_y_docente():
    filas_modulos = [
        {
            "POS - MODULO": "POS-5010",
            "NRO MODULO": "1",
            "DOCENTE": "Dr. Roberto Silva",
            "NOMBRE DEL PROGRAMA": "Fundamentos de Finanzas",
            "FECHA INICIO": "2025-02-01",
            "FECHA FIN": "2025-03-15",
        },
    ]
    idx = indexar_modulos_arca(filas_modulos)
    fila_acta = {
        "CI": "8899001",
        "NOMBRE COMPLETO": "Carla Morales Vega",
        "POS - ACTAS": "POS-5010",
        "MODULO 1": "85",
        "ESTADO ACADEMICO": "Aprobado",
        "ESTADO TUTORIA": "Aprobado",
        "ESTADO ARCA": "Titulado",
    }
    regs = registros_academicos(fila_acta, indice_modulos=idx)
    assert len(regs) == 1
    assert regs[0]["fecha"] == date(2025, 3, 15)
    assert regs[0]["docente"]["valor_extraido"] == "Dr. Roberto Silva"
    assert regs[0]["requiere_revision"] is False


def test_f6_3a_d_f6_1_fecha_respaldo_solo_estados_cerrados_validos():
    # Estado válido cerrado (Titulado / Aprobado) sin fecha tras cruce -> fecha de respaldo trazable + requiere_revision=False
    fila_cerrada = {
        "CI": "8899002",
        "NOMBRE COMPLETO": "Luis Paredes Rojas",
        "POS - ACTAS": "POS-9999",
        "MODULO 1": "88",
        "ESTADO ACADEMICO": "Aprobado",
        "ESTADO TUTORIA": "Aprobado",
        "ESTADO ARCA": "Titulado",
    }
    regs = registros_academicos(fila_cerrada, indice_modulos={}, fecha_respaldo_archivo=date(2025, 12, 31))
    assert len(regs) == 1
    assert regs[0]["fecha"] == date(2025, 12, 31)
    assert regs[0]["requiere_revision"] is False
    assert any(a[0] == "FECHA_RESPALDO_ARCA" for a in regs[0]["avisos_acta"])

    # Estado abierto (En curso) sin fecha -> NO aplica respaldo, permanece en revisión
    fila_abierta = {
        "CI": "8899003",
        "NOMBRE COMPLETO": "Maria Gomez Diaz",
        "POS - ACTAS": "POS-9999",
        "MODULO 1": "80",
        "ESTADO ACADEMICO": "En curso",
        "ESTADO TUTORIA": "En curso",
        "ESTADO ARCA": "No Titulado",
    }
    regs_ab = registros_academicos(fila_abierta, indice_modulos={}, fecha_respaldo_archivo=date(2025, 12, 31))
    assert regs_ab[0]["fecha"] is None
    assert regs_ab[0]["requiere_revision"] is True

    # Nota anómala (fuera de 0-100) -> 100% permanece en revisión aunque estado sea cerrado
    fila_anomala = {
        "CI": "8899004",
        "NOMBRE COMPLETO": "Pedro Castro Luna",
        "POS - ACTAS": "POS-9999",
        "MODULO 1": "85",
        "MODULO 2": "7777777",
        "ESTADO ACADEMICO": "Aprobado",
        "ESTADO TUTORIA": "Aprobado",
        "ESTADO ARCA": "Titulado",
    }
    regs_an = registros_academicos(fila_anomala, indice_modulos={}, fecha_respaldo_archivo=date(2025, 12, 31))
    assert all(r["requiere_revision"] is True for r in regs_an)


# ── F6-3b: Reorientación flags y sugerencias BETO ─────────────────────────────

def test_f6_3b_flags_corte_y_acuerdo_solo_fuzzy(monkeypatch):
    monkeypatch.delenv("BETO_RESCATE_ACADEMICO", raising=False)
    monkeypatch.delenv("BETO_ACUERDO_SOLO_FUZZY", raising=False)
    assert cfg.BETO_FLAGS_POR_DEFECTO["BETO_RESCATE_ACADEMICO"] is True
    assert bi.activo("BETO_RESCATE_ACADEMICO") is True
    assert cfg.BETO_SUGERENCIA_CORTE_SIMILITUD == 80.0
    assert cfg.MOTIVOS_SUGERENCIA_HITL == frozenset({
        "ENTIDAD_NUEVA", "HOMONIMIA", "POS_NO_EN_DIM_MODULO", "BAJA_CONFIANZA_IA"
    })

    # ENCABEZADO limpio nunca es vetado por BETO_ACUERDO_QC (solo FUZZY)
    ent_enc = {"label": "ESTUDIANTE", "token": "Ana Perez", "matchedCanonical": "Ana Perez", "fuente_resolucion": "ENCABEZADO"}
    ent_fuz = {"label": "ESTUDIANTE", "token": "Ana Perez", "matchedCanonical": "Ana Perez", "fuente_resolucion": "FUZZY"}
    assert bi.persona_resuelta_por_reglas(ent_enc, solo_fuzzy=True) is False
    assert bi.persona_resuelta_por_reglas(ent_fuz, solo_fuzzy=True) is True

    # Verificar en refinar_lineas que ENCABEZADO produce 0 desacuerdos
    monkeypatch.setenv("BETO_ACUERDO_QC", "1")
    monkeypatch.setenv("BETO_CASCADA_FINAL", "0")
    monkeypatch.setenv("BETO_RESCATE_ACADEMICO", "0")
    cont = bi.Contadores()
    cliente = bi.ClienteBeto(cache=bi.CacheMemoria(), post=lambda lote: [[] for _ in lote], contadores=cont)
    res = bi.refinar_lineas(
        ["NOMBRE: Ana Perez | CI: 1234567"],
        lambda _l, **_kw: ([dict(ent_enc)], 0.95, False),
        tipo_fuente="ACTA",
        cliente=cliente,
        contadores=cont,
    )
    assert res[0].acuerdo is None
    assert cont.desacuerdos == 0


# ── F6-3c: Selección inteligente de celdas y caché sobre texto filtrado ───────

def test_f6_3c_prioriza_celdas_textuales_en_posicion_mayor_a_8_y_hash_filtrado(monkeypatch):
    assert MAX_LENGTH_TOKENS == 128
    assert MAX_CELDAS_TEXTO == 8
    linea = " | ".join([
        "N°: 1",
        "ID: 4001",
        "GESTION: 2025",
        "MES: 03",
        "CUOTA: 1",
        "MONTO: 1500.00",
        "SALDO: 500.00",
        "NOTA: 88",
        "HORAS: 40",
        "ESTUDIANTE: Maria Fernanda Rojas Quinteros",
        "PROGRAMA: Diplomado en Inteligencia de Negocios",
        "DOCENTE: Ing. Jorge Luis Morales",
    ])
    filtrado = texto_para_indice(linea)
    assert "ESTUDIANTE: Maria Fernanda Rojas Quinteros" in filtrado
    assert "PROGRAMA: Diplomado en Inteligencia de Negocios" in filtrado
    assert "DOCENTE: Ing. Jorge Luis Morales" in filtrado
    assert "N°: 1" not in filtrado
    assert "MONTO: 1500.00" not in filtrado
    assert len(filtrado.split(" | ")) <= MAX_CELDAS_TEXTO

    # Verificar que cache_indice_beto hashea el texto YA filtrado y usa versión MODELO actualizada
    assert cs.MODELO != "beto-v2"
    hashes_leidos = []

    def fake_leer(hashes):
        hashes_leidos.extend(hashes)
        return {hashlib.sha256(filtrado.encode("utf-8")).hexdigest(): 0.91}

    monkeypatch.setattr(cs, "_leer_cache", fake_leer)
    out = cs.obtener_indices([linea])
    assert out == [0.91]
    assert hashes_leidos == [hashlib.sha256(filtrado.encode("utf-8")).hexdigest()]
