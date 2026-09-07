"""
pipeline/analytics/audit_logger.py
-----------------------------------
Módulo de Registro y Trazabilidad de Inconsistencias (GIRA-43).
Estructura, clasifica por severidad y persiste todas las anomalías detectadas
en el pipeline de ingesta, normalización y procesamiento semántico en
`output/inconsistencias_sprint3.jsonl` y/o base de datos.

Esquema canónico:
{
    "timestamp": ISO-8601,
    "archivo": str,
    "hoja": str,
    "bloque_id": int/str,
    "fila": int,
    "tipo_inconsistencia": str,
    "campo_afectado": str,
    "valor_recibido": any,
    "severidad": "WARNING" | "ERROR" | "CRITICAL",
    "accion_tomada": str,
    "metadata": dict
}
"""

import json
import threading
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from pipeline.config import INCONSISTENCIAS_LOG_PATH
from pipeline.normalization.quality_rules import ResultadoCalidad, SeveridadRegla


class SeveridadInconsistencia(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class EventoInconsistencia:
    """
    Representa un evento atómico de inconsistencia detectado en cualquier fase del pipeline.
    """
    tipo_inconsistencia: str
    campo_afectado: str
    valor_recibido: Any
    severidad: str = SeveridadInconsistencia.WARNING.value
    accion_tomada: str = "MARCADO_PARA_REVISION"
    archivo: str = "DESCONOCIDO"
    hoja: str = "DESCONOCIDA"
    bloque_id: Union[int, str] = 0
    fila: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.severidad, Enum):
            self.severidad = self.severidad.value
        else:
            self.severidad = str(self.severidad).strip().upper()

    def to_dict(self) -> Dict[str, Any]:
        """Serializa al esquema formal de auditoría de GiraGroup."""
        return {
            "timestamp": self.timestamp,
            "archivo": self.archivo,
            "hoja": self.hoja,
            "bloque_id": self.bloque_id,
            "fila": self.fila,
            "tipo_inconsistencia": self.tipo_inconsistencia,
            "campo_afectado": self.campo_afectado,
            "valor_recibido": self.valor_recibido,
            "severidad": self.severidad,
            "accion_tomada": self.accion_tomada,
            "metadata": self.metadata,
        }


class AuditLogger:
    """
    Logger centralizado y thread-safe para trazabilidad de inconsistencias (GIRA-43).
    Escribe eventos en formato JSONL y mantiene métricas agregadas en memoria.
    """

    def __init__(self, ruta_log: Optional[Path] = None):
        self.ruta_log = ruta_log or INCONSISTENCIAS_LOG_PATH
        self._lock = threading.Lock()
        self._eventos_memoria: List[EventoInconsistencia] = []

        # Asegurar directorio de logs
        self.ruta_log.parent.mkdir(parents=True, exist_ok=True)

    def registrar_inconsistencia(
        self,
        tipo_inconsistencia: str,
        campo_afectado: str,
        valor_recibido: Any,
        severidad: Union[SeveridadInconsistencia, str] = SeveridadInconsistencia.WARNING,
        accion_tomada: str = "MARCADO_PARA_REVISION",
        archivo: str = "DESCONOCIDO",
        hoja: str = "DESCONOCIDA",
        bloque_id: Union[int, str] = 0,
        fila: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        persistir_inmediato: bool = True
    ) -> EventoInconsistencia:
        """
        Registra una inconsistencia atómica y opcionalmente la persiste en el JSONL.
        """
        sev_str = severidad.value if isinstance(severidad, Enum) else str(severidad).strip().upper()

        evento = EventoInconsistencia(
            tipo_inconsistencia=tipo_inconsistencia,
            campo_afectado=campo_afectado,
            valor_recibido=valor_recibido,
            severidad=sev_str,
            accion_tomada=accion_tomada,
            archivo=archivo,
            hoja=hoja,
            bloque_id=bloque_id,
            fila=fila,
            metadata=metadata or {},
        )

        with self._lock:
            self._eventos_memoria.append(evento)
            if persistir_inmediato:
                self._escribir_linea_jsonl(evento)

        return evento

    def registrar_desde_evaluacion_calidad(
        self,
        resultado_calidad: ResultadoCalidad,
        archivo: str = "DESCONOCIDO",
        hoja: str = "DESCONOCIDA",
        bloque_id: Union[int, str] = 0,
        fila: int = 0,
        accion_tomada: str = "MARCADO_PARA_REVISION",
        persistir_inmediato: bool = True
    ) -> List[EventoInconsistencia]:
        """
        Transforma los hallazgos de un ResultadoCalidad (GIRA-27) en eventos de auditoría (GIRA-43).
        """
        if not resultado_calidad.requiere_revision:
            return []

        eventos_creados = []

        # Si hay detalles de reglas específicos
        if resultado_calidad.detalles_reglas:
            for regla in resultado_calidad.detalles_reglas:
                ev = self.registrar_inconsistencia(
                    tipo_inconsistencia=regla.get("motivo", "REGLA_CALIDAD_FALLIDA"),
                    campo_afectado=regla.get("campo") or "registro",
                    valor_recibido=regla.get("valor"),
                    severidad=regla.get("severidad", SeveridadInconsistencia.WARNING.value),
                    accion_tomada=accion_tomada,
                    archivo=archivo,
                    hoja=hoja,
                    bloque_id=bloque_id,
                    fila=fila,
                    metadata={"valores_auditados": resultado_calidad.valores_auditados},
                    persistir_inmediato=persistir_inmediato
                )
                eventos_creados.append(ev)
        else:
            # Fallback a los motivos textuales
            for motivo in resultado_calidad.motivos:
                ev = self.registrar_inconsistencia(
                    tipo_inconsistencia=motivo,
                    campo_afectado="general",
                    valor_recibido=resultado_calidad.valores_auditados,
                    severidad=resultado_calidad.severidad_maxima.value,
                    accion_tomada=accion_tomada,
                    archivo=archivo,
                    hoja=hoja,
                    bloque_id=bloque_id,
                    fila=fila,
                    metadata={},
                    persistir_inmediato=persistir_inmediato
                )
                eventos_creados.append(ev)

        return eventos_creados

    def _escribir_linea_jsonl(self, evento: EventoInconsistencia) -> None:
        """Escribe un evento en una sola línea del archivo JSONL."""
        linea = json.dumps(evento.to_dict(), ensure_ascii=False)
        with open(self.ruta_log, "a", encoding="utf-8") as f:
            f.write(linea + "\n")

    def vaciar_a_jsonl(self) -> int:
        """Escribe todos los eventos almacenados en memoria que no hayan sido persistidos."""
        with self._lock:
            with open(self.ruta_log, "w", encoding="utf-8") as f:
                for ev in self._eventos_memoria:
                    f.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")
            return len(self._eventos_memoria)

    def leer_inconsistencias(self) -> List[Dict[str, Any]]:
        """Lee y deserializa todas las inconsistencias desde el archivo JSONL."""
        if not self.ruta_log.exists():
            return []

        registros = []
        with open(self.ruta_log, "r", encoding="utf-8") as f:
            for linea in f:
                txt = linea.strip()
                if txt:
                    try:
                        registros.append(json.loads(txt))
                    except json.JSONDecodeError:
                        continue
        return registros

    def obtener_resumen_metricas(self) -> Dict[str, Any]:
        """Calcula estadísticas agregadas sobre las inconsistencias registradas en memoria."""
        with self._lock:
            total = len(self._eventos_memoria)
            por_severidad: Dict[str, int] = {}
            por_tipo: Dict[str, int] = {}
            por_archivo: Dict[str, int] = {}

            for ev in self._eventos_memoria:
                por_severidad[ev.severidad] = por_severidad.get(ev.severidad, 0) + 1
                por_tipo[ev.tipo_inconsistencia] = por_tipo.get(ev.tipo_inconsistencia, 0) + 1
                por_archivo[ev.archivo] = por_archivo.get(ev.archivo, 0) + 1

            return {
                "total_inconsistencias": total,
                "por_severidad": por_severidad,
                "top_tipos": sorted(por_tipo.items(), key=lambda x: x[1], reverse=True)[:5],
                "top_archivos": sorted(por_archivo.items(), key=lambda x: x[1], reverse=True)[:5],
            }

    def limpiar_log(self) -> None:
        """Borra el archivo de logs y resetea la memoria interna."""
        with self._lock:
            self._eventos_memoria.clear()
            if self.ruta_log.exists():
                self.ruta_log.unlink()
