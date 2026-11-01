"""
pipeline/jobs/scheduler.py
--------------------------
Punto de entrada para ejecución programada o bajo demanda (one-shot jobs / cron)
dentro del contenedor 'pipeline' de GiraGroup BI.

Permite disparar de forma independiente:
- Ingesta y PLN completo Sprint 3: python -m pipeline.jobs.scheduler --task full
- Post-paso de telemetría y persistencia de hechos: python -m pipeline.jobs.scheduler --task telemetria
- Post-paso de volcado y auditoría de inconsistencias: python -m pipeline.jobs.scheduler --task auditoria
"""

import argparse
import json
import sys
from pathlib import Path

PROYECTO_RAIZ = Path(__file__).resolve().parent.parent.parent
if str(PROYECTO_RAIZ) not in sys.path:
    sys.path.insert(0, str(PROYECTO_RAIZ))

from pipeline.config import OUTPUT_DIR, SPRINT2_DOCS_PATH
from pipeline.ejecutar_sprint3 import OrquestadorSprint3


def ejecutar_job_telemetria():
    """Ejecuta el job one-shot de telemetría leyendo las entidades procesadas más recientes."""
    ruta_proc = OUTPUT_DIR / "sprint3_entidades_procesadas.jsonl"
    if not ruta_proc.exists():
        print(f"[Job Telemetria] Archivo {ruta_proc} no encontrado. Ejecute primero el pipeline.")
        return 0

    registros = []
    with open(ruta_proc, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    registros.append(json.loads(line))
                except Exception:
                    pass

    orquestador = OrquestadorSprint3(cpu_only=True)
    res = orquestador.persistir_telemetria(registros)
    print(f"[Job Telemetria] Finalizado con éxito: {res}")
    return res.get("persistidos_archivo", 0)


def ejecutar_job_auditoria():
    """Ejecuta el job one-shot de auditoría e inconsistencias."""
    ruta_proc = OUTPUT_DIR / "sprint3_entidades_procesadas.jsonl"
    if not ruta_proc.exists():
        print(f"[Job Auditoria] Archivo {ruta_proc} no encontrado. Ejecute primero el pipeline.")
        return 0

    registros = []
    with open(ruta_proc, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    registros.append(json.loads(line))
                except Exception:
                    pass

    orquestador = OrquestadorSprint3(cpu_only=True)
    res = orquestador.volcar_inconsistencias(registros)
    print(f"[Job Auditoria] Finalizado con éxito: {res}")
    return res.get("total_inconsistencias", 0)


def main():
    parser = argparse.ArgumentParser(description="Scheduler de Jobs One-Shot Sprint 3")
    parser.add_argument(
        "--task",
        choices=["full", "telemetria", "auditoria"],
        default="full",
        help="Tipo de tarea a ejecutar (default: full)"
    )
    parser.add_argument("--cpu-only", action="store_true", help="Forzar modo CPU")
    parser.add_argument("--limite-docs", type=int, default=None, help="Límite de documentos para prueba")
    args = parser.parse_args()

    if args.task == "telemetria":
        ejecutar_job_telemetria()
    elif args.task == "auditoria":
        ejecutar_job_auditoria()
    else:
        orquestador = OrquestadorSprint3(cpu_only=args.cpu_only)
        orquestador.ejecutar(
            ruta_entrada=SPRINT2_DOCS_PATH,
            ruta_salida=OUTPUT_DIR / "sprint3_entidades_procesadas.jsonl",
            limite_docs=args.limite_docs
        )


if __name__ == "__main__":
    main()
