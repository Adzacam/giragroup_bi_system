"""
audit_logger.py — GIRA-43 (Sprint 2)
Registro estructurado de auditoría para el pipeline de ingestión.

Registra:
- Columnas no reconocidas en el diccionario canónico
- Hojas descartadas con causa explícita
- Registros marcados con sin_llave_valida
- Duplicados detectados

Emite el informe como JSON en logs/ingestion_audit.json.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Ruta por defecto del log de auditoría
_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
_AUDIT_PATH = _LOGS_DIR / "ingestion_audit.json"


class AuditLogger:
    """
    Acumulador de eventos de auditoría durante la ingestión de un archivo.
    Al finalizar, exporta un informe JSON estructurado.
    """

    def __init__(self, nombre_archivo: str = ""):
        self._nombre_archivo = nombre_archivo
        self._timestamp = datetime.now(timezone.utc).isoformat()

        self._hojas_descartadas: list[dict] = []
        self._columnas_no_mapeadas: list[dict] = []
        self._registros_sin_llave: list[dict] = []
        self._registros_duplicados: list[dict] = []
        self._errores: list[dict] = []
        self._advertencias: list[str] = []

    @property
    def nombre_archivo(self) -> str:
        return self._nombre_archivo

    @property
    def total_eventos(self) -> int:
        return (
            len(self._hojas_descartadas)
            + len(self._columnas_no_mapeadas)
            + len(self._registros_sin_llave)
            + len(self._registros_duplicados)
            + len(self._errores)
        )

    # ── Registrar eventos ─────────────────────────────────────────────

    def registrar_hoja_descartada(
        self, nombre_hoja: str, razon: str, detalle: str = ""
    ) -> None:
        """Registra una hoja descartada con su razón."""
        self._hojas_descartadas.append({
            "hoja": nombre_hoja,
            "razon": razon,
            "detalle": detalle,
        })
        logger.info(
            "[Auditoría] Hoja descartada: '%s' — %s",
            nombre_hoja, razon,
        )

    def registrar_columnas_no_mapeadas(
        self, columnas: list[dict], nombre_hoja: str = ""
    ) -> None:
        """Registra columnas que no pudieron mapearse al diccionario canónico."""
        for col_info in columnas:
            entrada = {
                "hoja": nombre_hoja,
                "columna": col_info.get("columna", "?"),
                "mejor_candidato": col_info.get("mejor_candidato"),
                "mejor_score": col_info.get("mejor_score", 0),
            }
            self._columnas_no_mapeadas.append(entrada)

        if columnas:
            logger.info(
                "[Auditoría] %d columnas no mapeadas en hoja '%s'.",
                len(columnas), nombre_hoja,
            )

    def registrar_sin_llave_valida(
        self, id_documento: str, pos: str, hoja: str = ""
    ) -> None:
        """Registra un documento con POS no válido."""
        self._registros_sin_llave.append({
            "id_documento": id_documento,
            "pos_reportado": pos,
            "hoja": hoja,
        })

    def registrar_duplicados(self, duplicados: list[dict]) -> None:
        """Registra los registros eliminados por deduplicación."""
        for dup in duplicados:
            self._registros_duplicados.append({
                "llaves": {k: str(v) for k, v in dup.items()
                           if k in ("pos", "identificador_persona", "fecha_evento")},
            })

        if duplicados:
            logger.info(
                "[Auditoría] %d registros duplicados eliminados.",
                len(duplicados),
            )

    def registrar_error(self, mensaje: str, detalle: str = "") -> None:
        """Registra un error general del pipeline."""
        self._errores.append({
            "mensaje": mensaje,
            "detalle": detalle,
        })
        logger.error("[Auditoría] Error: %s — %s", mensaje, detalle)

    def registrar_advertencia(self, mensaje: str) -> None:
        """Registra una advertencia informativa."""
        self._advertencias.append(mensaje)

    # ── Exportar informe ──────────────────────────────────────────────

    def exportar_reporte(self, ruta: Optional[str] = None) -> dict:
        """
        Genera el informe de auditoría como dict y opcionalmente
        lo guarda en disco como JSON.

        Args:
            ruta: Ruta del archivo JSON. Si None, usa la ruta por defecto.

        Returns:
            Dict con el informe completo.
        """
        reporte = {
            "archivo": self._nombre_archivo,
            "timestamp": self._timestamp,
            "resumen": {
                "hojas_descartadas": len(self._hojas_descartadas),
                "columnas_no_mapeadas": len(self._columnas_no_mapeadas),
                "registros_sin_llave_valida": len(self._registros_sin_llave),
                "registros_duplicados": len(self._registros_duplicados),
                "errores": len(self._errores),
            },
            "hojas_descartadas": self._hojas_descartadas,
            "columnas_no_mapeadas": self._columnas_no_mapeadas,
            "registros_sin_llave_valida": self._registros_sin_llave,
            "registros_duplicados": self._registros_duplicados,
            "errores": self._errores,
            "advertencias": self._advertencias,
        }

        # Guardar a disco
        ruta_out = Path(ruta) if ruta else _AUDIT_PATH
        ruta_out.parent.mkdir(parents=True, exist_ok=True)

        # Cargar reporte existente si existe (acumular por archivo)
        reportes_existentes = []
        if ruta_out.exists():
            try:
                with open(ruta_out, "r", encoding="utf-8") as f:
                    contenido = json.load(f)
                    if isinstance(contenido, list):
                        reportes_existentes = contenido
                    else:
                        reportes_existentes = [contenido]
            except (json.JSONDecodeError, Exception):
                reportes_existentes = []

        reportes_existentes.append(reporte)

        with open(ruta_out, "w", encoding="utf-8") as f:
            json.dump(reportes_existentes, f, ensure_ascii=False, indent=2)

        logger.info(
            "[Auditoría] Reporte guardado en %s (%d eventos totales).",
            ruta_out, self.total_eventos,
        )

        return reporte

    def limpiar(self) -> None:
        """Resetea todos los acumuladores."""
        self._hojas_descartadas.clear()
        self._columnas_no_mapeadas.clear()
        self._registros_sin_llave.clear()
        self._registros_duplicados.clear()
        self._errores.clear()
        self._advertencias.clear()
