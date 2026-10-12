"""
tests/sprint3/test_financial_and_quality_post_steps.py
------------------------------------------------------
Pruebas unitarias e integrales para:
1. Unificación de escala de notas (0-10 -> 0-100).
2. Extracción y validación de campos académicos:
   - nota_final
   - asistencia_pct (0-100)
   - incumplimiento_actividades_pct (alerta deserción > 30%)
3. Extracción y validación de campos financieros:
   - monto_deuda (>= 0)
   - cuotas_impagas (alerta riesgo >= 2)
   - estado_cartera ('Vigente', 'Mora', 'Previsionable')
4. Máquina de estados FK (A, B, C) con exportación de fk_estado.
5. Umbral de certeza Cap. 3 (0.60 para activación de requiere_revision).
6. Post-pasos de persistencia de telemetría y volcado de inconsistencias.
"""

import json
import pytest
from pathlib import Path
from pipeline.normalization.quality_rules import QualityEvaluator, SeveridadRegla
from pipeline.normalization.fk_resolver import FKResolver
from pipeline.semantic.ner_schema import EntidadExtraida, TipoEntidad, NivelConfianza, ResultadoInferenciaNER
from pipeline.ejecutar_sprint3 import OrquestadorSprint3
from pipeline.config import OUTPUT_DIR


class TestEscalaNotaYAcademicos:
    """Verifica la unificación de escala y reglas de calidad académica."""

    def setup_method(self):
        self.evaluador = QualityEvaluator()

    def test_unificacion_escala_nota_sobre_10(self):
        # Escala 0-10 -> se debe unificar a 0-100 multiplicando por 10
        es_val, mot, num = self.evaluador.validar_rango_nota("7.5")
        assert es_val is True
        assert mot is None
        assert num == 75.0

    def test_unificacion_escala_nota_sobre_100(self):
        # Escala 0-100 directa
        es_val, mot, num = self.evaluador.validar_rango_nota("85.0")
        assert es_val is True
        assert mot is None
        assert num == 85.0

    def test_nota_fuera_de_rango(self):
        es_val, mot, num = self.evaluador.validar_rango_nota("105")
        assert es_val is False
        assert "NOTA_FUERA_DE_RANGO" in mot

    def test_asistencia_valida_e_invalida(self):
        es_val, mot, num = self.evaluador.validar_asistencia("92.5%")
        assert es_val is True
        assert num == 92.5

        es_val_inv, mot_inv, _ = self.evaluador.validar_asistencia("110%")
        assert es_val_inv is False
        assert "ASISTENCIA_FUERA_DE_RANGO" in mot_inv

    def test_incumplimiento_umbral_desercion(self):
        # 25% no activa alerta de deserción (> 30%)
        es_val, mot, num, alerta = self.evaluador.validar_incumplimiento("25.0%")
        assert es_val is True
        assert alerta is False

        # 35% supera el 30% -> activa alerta deserción
        es_val2, mot2, num2, alerta2 = self.evaluador.validar_incumplimiento("35.0%")
        assert es_val2 is True
        assert alerta2 is True

        res = self.evaluador.evaluar_registro_academico({
            "nota": 70,
            "ci": "1234567",
            "incumplimiento_actividades_pct": 40.0
        })
        assert any("ALERTA_DESERCION_INCUMPLIMIENTO" in m for m in res.motivos)


class TestCamposFinancieros:
    """Verifica reglas para fact_situacion_financiera."""

    def setup_method(self):
        self.evaluador = QualityEvaluator()

    def test_monto_deuda_valido_y_negativo(self):
        es_val, mot, num = self.evaluador.validar_monto_deuda("1500.50 Bs")
        assert es_val is True
        assert num == 1500.50

        es_val_neg, mot_neg, _ = self.evaluador.validar_monto_deuda("-200")
        assert es_val_neg is False
        assert "MONTO_NEGATIVO" in mot_neg

    def test_cuotas_impagas_umbral_riesgo(self):
        # 1 cuota no activa riesgo
        es_val, mot, num, riesgo = self.evaluador.validar_cuotas_impagas("1")
        assert es_val is True
        assert riesgo is False

        # 3 cuotas activa umbral riesgo (>= 2)
        es_val2, mot2, num2, riesgo2 = self.evaluador.validar_cuotas_impagas("3")
        assert es_val2 is True
        assert riesgo2 is True

    def test_estado_cartera_apendice_e(self):
        # Valores canónicos: Vigente, Mora, Previsionable
        es_val, mot, val_norm = self.evaluador.validar_estado_cartera("vigente")
        assert es_val is True
        assert val_norm == "Vigente"

        es_val_mora, _, val_mora = self.evaluador.validar_estado_cartera("MORA")
        assert es_val_mora is True
        assert val_mora == "Mora"

        es_val_prev, _, val_prev = self.evaluador.validar_estado_cartera("previsionable")
        assert es_val_prev is True
        assert val_prev == "Previsionable"

        es_val_inv, mot_inv, _ = self.evaluador.validar_estado_cartera("desconocida")
        assert es_val_inv is False
        assert "ESTADO_CARTERA_INVALIDO" in mot_inv


class TestFKEstadoResolver:
    """Verifica la emisión explícita del estado FK ('A', 'B', 'C')."""

    def setup_method(self):
        self.resolver = FKResolver()

    def test_fk_estado_a_ci_directo(self):
        res = self.resolver.resolver_estudiante(nombre="Juan Perez", ci_candidato="4859201")
        assert res["fk_estado"] == "A"
        assert res["ci"] == "4859201"
        assert res["es_sintetico"] is False

    def test_fk_estado_c_sintetico(self):
        res = self.resolver.resolver_estudiante(nombre="Persona Totalmente Inexistente 999", ci_candidato=None)
        assert res["fk_estado"] == "C"
        assert res["ci"].startswith("TEMP-CI-")
        assert res["es_sintetico"] is True


class TestUmbralCorte085:
    """Verifica que el corte de revisión estricto para BETO se ubica en 0.85."""

    def setup_method(self):
        self.evaluador = QualityEvaluator()

    def test_score_alto_no_activa_flag_por_beto(self):
        # 0.88 está en nivel ALTA (>= 0.85) -> aceptación directa, no activa flag
        ent = EntidadExtraida(
            tipo=TipoEntidad.DOCENTE,
            valor="Lic. Mario Ruiz",
            start_char=0,
            end_char=14,
            score=0.88
        )
        ner = ResultadoInferenciaNER(texto="Lic. Mario Ruiz", entidades=[ent])
        res = self.evaluador.evaluar_registro_academico({
            "nota": 80,
            "ci": "6543210"
        }, inferencia_ner=ner)
        assert not any("BETO_CONF" in m for m in res.motivos)

    def test_score_medio_activa_flag_beto_media(self):
        # 0.72 está en nivel MEDIA ([0.60, 0.85)) -> activa requiere_revision con BETO_CONF_MEDIA
        ent = EntidadExtraida(
            tipo=TipoEntidad.DOCENTE,
            valor="Lic. Mario Ruiz",
            start_char=0,
            end_char=14,
            score=0.72
        )
        ner = ResultadoInferenciaNER(texto="Lic. Mario Ruiz", entidades=[ent])
        res = self.evaluador.evaluar_registro_academico({
            "nota": 80,
            "ci": "6543210"
        }, inferencia_ner=ner)
        assert res.requiere_revision is True
        assert any("BETO_CONF_MEDIA" in m for m in res.motivos)

    def test_score_bajo_activa_flag_beto_baja(self):
        # 0.55 es BAJA (< 0.60) -> activa requiere_revision con BETO_CONF_BAJA y severidad ERROR
        ent = EntidadExtraida(
            tipo=TipoEntidad.DOCENTE,
            valor="Lic. Mario Ruiz",
            start_char=0,
            end_char=14,
            score=0.55
        )
        ner = ResultadoInferenciaNER(texto="Lic. Mario Ruiz", entidades=[ent])
        res = self.evaluador.evaluar_registro_academico({
            "nota": 80,
            "ci": "6543210"
        }, inferencia_ner=ner)
        assert res.requiere_revision is True
        assert any("BETO_CONF_BAJA" in m for m in res.motivos)
        assert res.severidad_maxima == SeveridadRegla.ERROR


class TestPostPasosSprint3:
    """Verifica la ejecución síncrona de los dos post-pasos institucionales."""

    def test_persistir_telemetria_y_volcar_inconsistencias(self, tmp_path):
        orquestador = OrquestadorSprint3(cpu_only=True)
        registros_mock = [
            {
                "doc_id": 1,
                "archivo": "Prueba_Academica.xlsx",
                "categoria": "academico",
                "resoluciones": {
                    "nota_final": 88.0,
                    "asistencia_pct": 95.0,
                    "incumplimiento_actividades_pct": 5.0,
                    "monto_deuda": None,
                    "cuotas_impagas": None,
                    "estado_cartera": None,
                    "nivel_confianza_ia": 0.92,
                    "fk_estado": "A"
                },
                "calidad": {
                    "requiere_revision": False,
                    "motivos": []
                }
            },
            {
                "doc_id": 2,
                "archivo": "Prueba_Financiera.xlsx",
                "categoria": "financiero",
                "resoluciones": {
                    "nota_final": None,
                    "asistencia_pct": None,
                    "incumplimiento_actividades_pct": None,
                    "monto_deuda": 2500.0,
                    "cuotas_impagas": 3,
                    "estado_cartera": "Mora",
                    "nivel_confianza_ia": 0.52,
                    "fk_estado": "B"
                },
                "calidad": {
                    "requiere_revision": True,
                    "motivos": ["ALERTA_RIESGO_CUOTAS_IMPAGAS", "BETO_CONF_BAJA"]
                }
            }
        ]

        # Post-paso 1: Persistir telemetría y hechos
        res_tel = orquestador.persistir_telemetria(registros_mock)
        assert res_tel["persistidos_archivo"] == 2
        assert Path(res_tel["ruta_archivo"]).exists()

        # Post-paso 2: Volcar inconsistencias
        res_inc = orquestador.volcar_inconsistencias(registros_mock)
        assert res_inc["total_inconsistencias"] == 1
        assert Path(res_inc["ruta_log"]).exists()
