"""
backend/services/financial_rules_engine.py
------------------------------------------
Motor de Reglas Determinísticas, Detección de Anomalías y Desacoplamiento Analítico:
1. Reglas Determinísticas de Negocio:
   - cuotas_impagas >= 2 o dias_mora >= 90 -> 'Riesgo Financiero / Mora Crítica'
   - cuotas_impagas == 1 y dias_mora > 15 -> 'Mora Preventiva'
   - saldo <= 0 -> 'Cartera Vigente / Al Día'
   - Cruce Académico-Financiero: cuotas_impagas >= 2 y nota <= 70 -> 'Riesgo Dual (Académico + Financiero)'
2. Detección de Anomalías Transversales:
   - Desproporción Meta vs. Ejecutado (> 200% o ejecutado negativo)
   - Sobrepago Atípico (pago > cuota * 3 sin cancelación total documentada)
   - Descuento excesivo (descuento > costo del programa)
   - Inconsistencia en cuotas (cuotas en mora > total cuotas contratadas)
3. Puente a Holt-Winters:
   - Provisión de series temporales de ejecutado histórico para proyección independiente.
"""

from typing import Dict, Any, List, Optional
from services.financial_validator_service import FinancialTransactionValidator


class FinancialRulesEngine:
    """Motor determinístico de reglas financieras y detector de anomalías de datos."""

    @classmethod
    def evaluar_riesgo_cartera(
        cls,
        cuotas_impagas: int = 0,
        dias_mora: int = 0,
        saldo: float = 0.0,
        total_cuotas: int = 1,
        nota_academica: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Evalúa el riesgo de cartera y genera alertas determinísticas.
        """
        reglas_activadas = []
        nivel_riesgo = "BAJO"
        requiere_gestion = False
        estado_cartera = "VIGENTE"

        # 1. Saldo en cero o negativo
        if saldo <= 0.0:
            estado_cartera = "AL_DIA"
            nivel_riesgo = "NINGUNO"
            reglas_activadas.append("Regla 1: Saldo cancelado en su totalidad (Cartera al día)")
            return {
                "estado_cartera": estado_cartera,
                "nivel_riesgo": nivel_riesgo,
                "requiere_gestion": False,
                "es_riesgo_critico": False,
                "es_riesgo_dual": False,
                "reglas_activadas": reglas_activadas,
                "diagnostico": "Estudiante al día con sus obligaciones financieras."
            }

        # 2. Mora Crítica (>= 2 cuotas impagas o >= 90 días de mora)
        if cuotas_impagas >= 2 or dias_mora >= 90:
            estado_cartera = "MORA_CRITICA"
            nivel_riesgo = "CRITICO"
            requiere_gestion = True
            reglas_activadas.append(
                f"Regla 2: Mora crítica detectada ({cuotas_impagas} cuotas impagas, {dias_mora} días de mora)"
            )

        # 3. Mora Preventiva / Alerta Temprana (1 cuota impaga y > 15 días de mora)
        elif cuotas_impagas == 1 and dias_mora > 15:
            estado_cartera = "MORA_PREVENTIVA"
            nivel_riesgo = "MEDIO"
            requiere_gestion = True
            reglas_activadas.append(
                f"Regla 3: Mora preventiva (1 cuota impaga con {dias_mora} días de retraso)"
            )

        # 4. En período de gracia (1 cuota pero <= 15 días)
        elif cuotas_impagas == 1 and dias_mora <= 15:
            estado_cartera = "PERIODO_GRACIA"
            nivel_riesgo = "BAJO"
            reglas_activadas.append("Regla 4: Cuota impaga dentro del período de tolerancia/gracia (<= 15 días)")

        # 5. Cruce Dual Académico-Financiero
        es_riesgo_dual = False
        if (nivel_riesgo in {"MEDIO", "CRITICO"}) and (nota_academica is not None and nota_academica <= 70.0):
            es_riesgo_dual = True
            nivel_riesgo = "EXTREMO_DUAL"
            reglas_activadas.append(
                f"Regla 5: Alerta combinada de retención — Rendimiento académico en riesgo ({nota_academica:.1f} pts) "
                f"con mora financiera activa ({cuotas_impagas} cuotas)"
            )

        diagnostico = (
            "Riesgo de cartera bajo control."
            if nivel_riesgo in {"NINGUNO", "BAJO"}
            else f"Caso prioritario para gestión de cobranza y retención ({nivel_riesgo})."
        )

        return {
            "estado_cartera": estado_cartera,
            "nivel_riesgo": nivel_riesgo,
            "requiere_gestion": requiere_gestion,
            "es_riesgo_critico": (nivel_riesgo in {"CRITICO", "EXTREMO_DUAL"}),
            "es_riesgo_dual": es_riesgo_dual,
            "reglas_activadas": reglas_activadas,
            "diagnostico": diagnostico
        }

    @classmethod
    def detectar_anomalias_financieras(
        cls,
        datos: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Inspecciona el registro en búsqueda de incongruencias o anomalías transversales:
        - Meta vs Ejecutado desproporcionado (> 200% o < 0)
        - Sobrepago atípico (pago > cuota * 3 sin ser contado)
        - Descuento mayor al costo del programa
        - Cuotas en mora mayores al total de cuotas contratadas
        """
        anomalias = []

        # 1. Anomalía de Escala Meta vs. Ejecutado
        meta_raw = datos.get("meta")
        ejecutado_raw = datos.get("ejecutado")
        if meta_raw is not None and ejecutado_raw is not None:
            m = FinancialTransactionValidator.sanitizar_importe(meta_raw)
            e = FinancialTransactionValidator.sanitizar_importe(ejecutado_raw)
            if m is not None and e is not None:
                if e < 0:
                    anomalias.append({
                        "tipo": "EJECUTADO_NEGATIVO",
                        "severidad": "CRITICAL",
                        "mensaje": f"El monto ejecutado ({e:.2f} Bs) no puede ser negativo.",
                        "campo": "ejecutado",
                        "valor_detectado": e
                    })
                elif m > 0 and (e / m) > 2.0:
                    pct = round((e / m) * 100, 1)
                    anomalias.append({
                        "tipo": "DESPROPORCION_META_EJECUTADO",
                        "severidad": "WARNING",
                        "mensaje": f"Ejecución desproporcionada ({pct}%): Ejecutado ({e:.2f} Bs) supera en más del 200% la meta ({m:.2f} Bs). Posible duplicidad o error de escala.",
                        "campo": "ejecutado",
                        "valor_detectado": e
                    })

        # 2. Anomalía de Sobrepago Atípico
        cuota_raw = datos.get("cuota")
        pago_raw = datos.get("pago") or datos.get("total_pagado")
        tipo_inscripcion = str(datos.get("tipo_inscripcion") or "").upper()
        if cuota_raw is not None and pago_raw is not None and "CONTADO" not in tipo_inscripcion:
            c = FinancialTransactionValidator.sanitizar_importe(cuota_raw)
            p = FinancialTransactionValidator.sanitizar_importe(pago_raw)
            if c is not None and p is not None and c > 0:
                if p > (c * 3.0):
                    anomalias.append({
                        "tipo": "SOBREPAGO_ATIPICO",
                        "severidad": "WARNING",
                        "mensaje": f"Sobrepago atípico detectado: Pago registrado ({p:.2f} Bs) es {p/c:.1f} veces superior a la cuota regular ({c:.2f} Bs). Verificar si corresponde a cancelación total o adelanto masivo.",
                        "campo": "pago",
                        "valor_detectado": p
                    })

        # 3. Anomalía de Descuento Excesivo
        costo_raw = datos.get("costo_programa")
        descuento_raw = datos.get("descuento")
        if costo_raw is not None and descuento_raw is not None:
            costo = FinancialTransactionValidator.sanitizar_importe(costo_raw)
            desc = FinancialTransactionValidator.sanitizar_importe(descuento_raw)
            if costo is not None and desc is not None:
                if desc > costo:
                    anomalias.append({
                        "tipo": "DESCUENTO_EXCESIVO",
                        "severidad": "CRITICAL",
                        "mensaje": f"El descuento otorgado ({desc:.2f} Bs) excede el costo total del programa ({costo:.2f} Bs).",
                        "campo": "descuento",
                        "valor_detectado": desc
                    })

        # 4. Anomalía de Cuotas en Mora Superiores al Total
        cuotas_mora = datos.get("cuotas_en_mora")
        total_cuotas = datos.get("total_cuotas")
        if cuotas_mora is not None and total_cuotas is not None:
            try:
                cm = int(cuotas_mora)
                tc = int(total_cuotas)
                if tc > 0 and cm > tc:
                    anomalias.append({
                        "tipo": "CUOTAS_MORA_SUPERIOR_TOTAL",
                        "severidad": "CRITICAL",
                        "mensaje": f"Inconsistencia en plan de pagos: Las cuotas en mora ({cm}) no pueden superar el total de cuotas del programa ({tc}).",
                        "campo": "cuotas_en_mora",
                        "valor_detectado": cm
                    })
            except (ValueError, TypeError):
                pass

        return anomalias

    @classmethod
    def preparar_serie_temporal_holtwinters(
        cls,
        registros_historicos: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Prepara y estructura la serie temporal para consumo del estimador estadístico Holt-Winters.
        Desacopla totalmente la extracción y limpieza de la fase de pronóstico.
        """
        serie_ordenada = sorted(
            registros_historicos,
            key=lambda x: str(x.get("periodo", ""))
        )
        periodos = [str(r.get("periodo", "")) for r in serie_ordenada if r.get("periodo")]
        valores = [
            float(FinancialTransactionValidator.sanitizar_importe(r.get("valor", 0.0)) or 0.0)
            for r in serie_ordenada if r.get("periodo")
        ]

        n_puntos = len(valores)
        es_apta_holtwinters = n_puntos >= 4  # Mínimo para estimación exponencial con tendencia

        return {
            "periodos": periodos,
            "valores": valores,
            "n_puntos": n_puntos,
            "es_apta_holtwinters": es_apta_holtwinters,
            "sugerencia_modelo": "ExponentialSmoothing(trend='add')" if es_apta_holtwinters else "Insuficientes datos (requiere >= 4 periodos)"
        }
