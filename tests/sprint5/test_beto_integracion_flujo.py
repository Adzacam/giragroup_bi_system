"""Conexión de las opciones 1 y 2 con la lectura (paso ③) y la consolidación (paso ④), con un servicio BETO simulado y bases aisladas."""
import io

import pandas as pd
import pytest

from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_origen import DimOrigenDocumental
from models.fact_rendimiento import FactRendimientoAcademico
from models.log_inconsistencia import LogInconsistencia
from models.lote import Lote
from routers import dataops
from services import beto_integracion as bi, cache_consultas, cache_lectura
from tests.dataops_parches import parchear

FLAGS = ("BETO_CASCADA_FINAL", "BETO_ACUERDO_QC", "BETO_SUGERENCIA_HITL", "BETO_RESCATE_ACADEMICO", "BETO_VENTANA")


def _ingestar(db, tmp_path, filas):
    from services import ingestion_service
    from services.ingestion_service import IngestionService
    lote = Lote(institucion='Prueba', periodo='2025')
    db.add(lote)
    db.flush()
    for nombre in ('ANA TORREZ SALINAS', 'LUIS PEREZ ROJAS'):
        db.add(DimEstudiante(nombre_completo=nombre, fk_estado='A'))
    for n in (1, 2):
        db.add(DimModulo(nombre_modulo=f'POS-9876 · Módulo {n}', pos_code=f'POS-9876-M0{n}', programa='Programa de prueba'))
    db.commit()
    buffer = io.BytesIO()
    pd.DataFrame(filas).to_excel(buffer, index=False)
    archivo = tmp_path / 'acta_prueba.xlsx'
    archivo.write_bytes(buffer.getvalue())
    IngestionService.procesar_archivo(db, str(archivo), archivo.name, id_lote=lote.id_lote, tipo_fuente='ACTA', institucion='Prueba',
                                      tipo_escala='CENTESIMAL_100')
    return lote, db.query(DimOrigenDocumental).filter_by(id_lote=lote.id_lote).all()


@pytest.fixture
def entorno(dw_sqlite, monkeypatch, tmp_path):
    from services import ingestion_service
    cache_consultas.invalidar()
    monkeypatch.setattr(cache_lectura, 'DIR', tmp_path)
    monkeypatch.setattr(ingestion_service, 'AsymmetricFlattener', None)
    parchear(monkeypatch, 'obtener_indices', lambda lineas, **kw: [.95] * len(lineas))
    for f in FLAGS:
        monkeypatch.delenv(f, raising=False)
    monkeypatch.setattr(bi, 'CacheEntidades', bi.CacheMemoria)
    yield dw_sqlite
    cache_consultas.invalidar()


def _servicio(monkeypatch, ve):
    """Simula POST /infer-batch: ve = nombres que BETO reconoce como estudiante; en el resto del texto ve «O»."""
    llamadas = []

    def post(lote):
        llamadas.append(list(lote))
        salida = []
        for texto in lote:
            ents = []
            for nombre in ve:
                i = texto.lower().find(nombre.lower())
                if i >= 0:
                    ents.append(bi.EntidadBeto('ESTUDIANTE', texto[i:i + len(nombre)], i, i + len(nombre), 0.97))
            salida.append(ents)
        return salida

    monkeypatch.setattr(bi, '_post_infer_batch', post)
    return llamadas


ACTA = [{'POS - ACTAS': 'POS-9876', 'NOMBRE COMPLETO': 'ANA TORREZ SALINAS', 'MES INICIO': 'Marzo', 'AÑO INICIO': 2025, 'MÓDULO 1': 90, 'MÓDULO 2': 80},
        {'POS - ACTAS': 'POS-9876', 'NOMBRE COMPLETO': 'LUIS PEREZ ROJAS', 'MES INICIO': 'Marzo', 'AÑO INICIO': 2025, 'MÓDULO 1': 60, 'MÓDULO 2': 70}]


def test_con_los_flags_apagados_no_hay_rastro_de_beto(entorno, monkeypatch, tmp_path):
    for f in FLAGS:
        monkeypatch.setenv(f, "0")
    llamadas = _servicio(monkeypatch, [])
    lote, docs = _ingestar(entorno, tmp_path, ACTA)
    lectura = dataops._evaluar_documentos_lote(entorno, docs)
    res = dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), entorno, None)
    assert 'beto' not in lectura and 'beto' not in res and llamadas == []
    assert lectura['autoCount'] == 2 and entorno.query(LogInconsistencia).filter_by(tipo_regla='DESACUERDO_REGLA_BETO').count() == 0


def test_acuerdo_qc_en_lectura_y_consolidacion(entorno, monkeypatch, tmp_path):
    monkeypatch.setenv('BETO_ACUERDO_QC', '1')
    llamadas = _servicio(monkeypatch, ['ANA TORREZ SALINAS'])     # de LUIS PEREZ ROJAS, BETO no ve persona
    lote, docs = _ingestar(entorno, tmp_path, ACTA)
    lectura = dataops._evaluar_documentos_lote(entorno, docs)
    assert lectura['beto']['desacuerdos'] == 1 and lectura['beto']['acuerdos'] == 1 and lectura['beto']['tasa_acuerdo'] == 0.5
    assert lectura['beto']['desacuerdos_por_archivo_y_tipo'] == {'acta_prueba.xlsx | ACTA': 1}
    por_estudiante = {d['estudiante']: d for d in lectura['detalles']}
    assert por_estudiante['ANA TORREZ SALINAS']['estado'] == 'AUTOMATICO'
    luis = por_estudiante['LUIS PEREZ ROJAS']
    assert luis['estado'] == 'REVISION' and luis['motivo'] == 'DESACUERDO_REGLA_BETO' and luis['indice_registro'] == 84
    assert (lectura['autoCount'], lectura['auditCount']) == (1, 1)

    res = dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), entorno, None)
    # BA-L3: con el ruteo nuevo, DESACUERDO_REGLA_BETO va a bandeja sin insertar el hecho (inserted_revision == 0)
    assert res['beto']['desacuerdos'] == 1 and res['inserted_revision'] == 0 and res['sent_hitl'] >= 1
    hechos = {h.id_estudiante: h for h in entorno.query(FactRendimientoAcademico).all()}
    luis_id = entorno.query(DimEstudiante).filter_by(nombre_completo='LUIS PEREZ ROJAS').one().id_estudiante
    ana_id = entorno.query(DimEstudiante).filter_by(nombre_completo='ANA TORREZ SALINAS').one().id_estudiante
    assert luis_id not in hechos
    assert hechos[ana_id].requiere_revision is False and float(hechos[ana_id].nivel_confianza_ia) == pytest.approx(0.95)
    log = entorno.query(LogInconsistencia).filter_by(tipo_regla='DESACUERDO_REGLA_BETO').all()
    assert len(log) == 1 and log[0].valor_recibido == 'LUIS PEREZ ROJAS' and log[0].estado_resolucion == 'PENDIENTE'
    assert len(llamadas) >= 1


def test_servicio_caido_con_el_flag_encendido_deja_el_resultado_de_siempre(entorno, monkeypatch, tmp_path):
    monkeypatch.setenv('BETO_ACUERDO_QC', '1')
    monkeypatch.setenv('BETO_CASCADA_FINAL', '1')

    def caido(lote):
        raise RuntimeError('sin servicio')

    monkeypatch.setattr(bi, '_post_infer_batch', caido)
    lote, docs = _ingestar(entorno, tmp_path, ACTA)
    lectura = dataops._evaluar_documentos_lote(entorno, docs)
    assert lectura['autoCount'] == 2 and lectura['beto']['desacuerdos'] == 0
    res = dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), entorno, None)
    assert res['inserted_revision'] == 0 and entorno.query(FactRendimientoAcademico).count() == 4


def test_cascada_final_rescata_a_un_residual_en_la_lectura_y_la_consolidacion(entorno, monkeypatch, tmp_path):
    """El nombre está en una columna que las reglas no leen como estudiante; BETO lo propone y el catálogo lo resuelve (A/B → BETO)."""
    monkeypatch.setenv('BETO_CASCADA_FINAL', '1')
    llamadas = _servicio(monkeypatch, ['luis perez rojas'])
    # La fila de prueba no tiene encabezado de estudiante: se desactiva el filtro de ruido para ejercitar la conexión
    parchear(monkeypatch, 'fila_sin_entidad', lambda linea, doc_fuente: False)
    parchear(monkeypatch, 'motivo_fila_sin_entidad', lambda campos, categoria: None)
    filas = [{'POS - ACTAS': 'POS-9876', 'DETALLE': 'luis perez rojas 7', 'MES INICIO': 'Marzo', 'AÑO INICIO': 2025, 'MÓDULO 1': 60, 'MÓDULO 2': 70}]
    lote, docs = _ingestar(entorno, tmp_path, filas)
    lectura = dataops._evaluar_documentos_lote(entorno, docs)
    assert lectura['beto']['residuales_enviadas'] == 1 and lectura['beto']['resueltas_por_beto'] == 1 and lectura['beto']['a_hitl'] == 0
    estudiante = next(e for e in lectura['detalles'][0]['lectura']['entidades'] if e['label'] == 'ESTUDIANTE')
    assert estudiante['fuente_resolucion'] == 'BETO' and estudiante['matchedCanonical'] == 'LUIS PEREZ ROJAS'
    res = dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), entorno, None)
    assert res['beto']['resueltas_por_beto'] == 1 and res['beto']['a_hitl'] == 0 and len(llamadas) >= 1
    assert entorno.query(DimEstudiante).count() == 2                  # BETO no creó ningún perfil nuevo
