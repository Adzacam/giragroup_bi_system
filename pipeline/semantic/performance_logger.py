"""
pipeline/semantic/performance_logger.py
----------------------------------------
Módulo de telemetría y persistencia de rendimiento para el motor NER (GIRA-12).
Registra latencia (ms/oración), throughput (tokens/segundo), dispositivo (cpu/cuda),
conteo de entidades y distribución de niveles de confianza probabilísticos.
Persiste eventos estructurados en output/telemetria_ner.jsonl.
"""

import json
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from pipeline.config import OUTPUT_DIR
from pipeline.semantic.ner_schema import ResultadoInferenciaNER, NivelConfianza


RUTA_TELEMETRIA_DEFAULT = OUTPUT_DIR / "telemetria_ner.jsonl"


@dataclass
class MetricasTelemetria:
    id_ejecucion: str
    timestamp_iso: str
    total_oraciones: int
    total_tokens_estimados: int
    total_entidades: int
    tiempo_total_ms: float
    latencia_ms_por_oracion: float
    tokens_por_segundo: float
    dispositivo: str
    modelo: str
    entidades_por_tipo: Dict[str, int] = field(default_factory=dict)
    entidades_por_nivel: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceLogger:
    """
    Monitor y recolector de telemetría de rendimiento para el motor de inferencia BETO.
    """

    def __init__(self, ruta_archivo: Optional[Path] = None):
        self.ruta_archivo = ruta_archivo or RUTA_TELEMETRIA_DEFAULT
        self.ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
        self._historial_memoria: List[MetricasTelemetria] = []

    def registrar_lote(
        self,
        resultados: List[ResultadoInferenciaNER],
        tiempo_total_ms: Optional[float] = None,
        metadata_adicional: Optional[Dict[str, Any]] = None
    ) -> MetricasTelemetria:
        """
        Calcula y persiste las métricas agregadas de un lote de inferencias NER.
        """
        if not resultados:
            metricas_vacias = MetricasTelemetria(
                id_ejecucion=str(uuid.uuid4()),
                timestamp_iso=datetime.now(timezone.utc).isoformat(),
                total_oraciones=0,
                total_tokens_estimados=0,
                total_entidades=0,
                tiempo_total_ms=0.0,
                latencia_ms_por_oracion=0.0,
                tokens_por_segundo=0.0,
                dispositivo="none",
                modelo="none",
                metadata=metadata_adicional or {}
            )
            return metricas_vacias

        t_acumulado = sum(r.tiempo_inferencia_ms for r in resultados)
        t_efectivo = tiempo_total_ms if tiempo_total_ms is not None else t_acumulado
        t_efectivo = max(0.001, t_efectivo)

        total_oraciones = len(resultados)
        total_tokens = sum(len(r.texto.split()) for r in resultados)
        total_entidades = sum(len(r.entidades) for r in resultados)

        conteo_tipos: Dict[str, int] = {}
        conteo_niveles: Dict[str, int] = {"ALTA": 0, "MEDIA": 0, "BAJA": 0}

        for r in resultados:
            for ent in r.entidades:
                conteo_tipos[ent.tipo] = conteo_tipos.get(ent.tipo, 0) + 1
                conteo_niveles[ent.nivel_confianza.value] = (
                    conteo_niveles.get(ent.nivel_confianza.value, 0) + 1
                )

        tokens_sec = (total_tokens / (t_efectivo / 1000.0)) if t_efectivo > 0 else 0.0
        latencia_prom = t_efectivo / total_oraciones if total_oraciones > 0 else 0.0

        dispositivo = resultados[0].dispositivo if resultados else "cpu"
        modelo = resultados[0].modelo if resultados else "dccuchile/bert-base-spanish-wwm-cased"

        metricas = MetricasTelemetria(
            id_ejecucion=str(uuid.uuid4()),
            timestamp_iso=datetime.now(timezone.utc).isoformat(),
            total_oraciones=total_oraciones,
            total_tokens_estimados=total_tokens,
            total_entidades=total_entidades,
            tiempo_total_ms=round(t_efectivo, 2),
            latencia_ms_por_oracion=round(latencia_prom, 2),
            tokens_por_segundo=round(tokens_sec, 2),
            dispositivo=dispositivo,
            modelo=modelo,
            entidades_por_tipo=conteo_tipos,
            entidades_por_nivel=conteo_niveles,
            metadata=metadata_adicional or {}
        )

        # Persistencia atómica en JSONL
        self._persistir_en_disco(metricas)
        self._historial_memoria.append(metricas)

        return metricas

    def _persistir_en_disco(self, metricas: MetricasTelemetria) -> None:
        """Escribe una línea en el archivo de log de telemetría."""
        linea = json.dumps(metricas.to_dict(), ensure_ascii=False) + "\n"
        with open(self.ruta_archivo, "a", encoding="utf-8") as f:
            f.write(linea)

    def obtener_resumen(self) -> Dict[str, Any]:
        """Genera un resumen acumulado de rendimiento de todas las ejecuciones registradas."""
        if not self._historial_memoria:
            return {"ejecuciones_totales": 0}

        total_ejecs = len(self._historial_memoria)
        total_oraciones = sum(m.total_oraciones for m in self._historial_memoria)
        total_tokens = sum(m.total_tokens_estimados for m in self._historial_memoria)
        total_entidades = sum(m.total_entidades for m in self._historial_memoria)
        tiempo_global_ms = sum(m.tiempo_total_ms for m in self._historial_memoria)

        lat_promedio = (
            sum(m.latencia_ms_por_oracion for m in self._historial_memoria) / total_ejecs
            if total_ejecs > 0 else 0.0
        )

        return {
            "total_ejecuciones": total_ejecs,
            "total_oraciones_procesadas": total_oraciones,
            "total_tokens_procesados": total_tokens,
            "total_entidades_extraidas": total_entidades,
            "tiempo_acumulado_ms": round(tiempo_global_ms, 2),
            "latencia_promedio_ms": round(lat_promedio, 2),
            "ultimo_dispositivo": self._historial_memoria[-1].dispositivo,
            "ultimo_modelo": self._historial_memoria[-1].modelo,
        }
