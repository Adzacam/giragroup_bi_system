# PLAN F1R — 15 de noviembre de 2026
Objetivo: corregir la evidencia A-3/A-4 y explicar el salto de la bandeja (182→680) antes de dar F1 por cerrada.
Entrada: CIERRE_F1V.md; rama base = beto-integracion 3be4fbe.

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| R-1 | Restaurar la evidencia sellada de F0 | dev-baja | — | R-2 | `f0_desacuerdos_muestra.csv` y `f0_top1_resumen.json` byte a byte iguales a b559292 (sha256 registrado); `f0_top1_decisiones_humanas.csv` y `f1_revision_humana_resumen.json` movidos a `f1_revision_no_valida/` con un README de los 4 motivos; 0 cifras de A-3/A-4 presentadas como humanas | f1_r1_restauracion.json |
| R-2 | Diagnóstico de la bandeja 182→680 y de KPI-18 59→36 | dev-alta | — | R-1 | Desglose por grupo y tipo de caso (f1_off frente a f1_validacion); cada caso nuevo atribuido a un cambio de entidad de beto-v2 o a otra causa; muestra de 30 casos nuevos con veredicto técnico (marcado como automático); conclusión: mejora / regresión / mezcla, con conteos | f1_r2_bandeja_diff.csv, f1_r2_diagnostico.json |
| R-3 | Fe de erratas de CIERRE_F1V | dev-baja | R-1, R-2 | — | §5.4 dice «pendiente; la revisión rev_01 no es válida (ver f1_revision_no_valida/)»; el estado pasa a «parcial» hasta que Lean decida D3-bis | — |

Comandos:
- R-1: `git show b559292:docs/mediciones/f0_desacuerdos_muestra.csv > docs/mediciones/f0_desacuerdos_muestra.csv` (lo mismo para f0_top1_resumen.json), luego sha256 y comparación con el hash de f0_desacuerdos_resumen.json.
- R-2: lee solo las huellas y los .json de F1-V/f1_off que ya existen; si hace falta reejecutar, usa tmpfs con TMPFS_PORT verificado, sin tocar la DW viva ni el snapshot.

Riesgos y control:
- No volver a generar etiquetas «humanas» desde ningún agente; las de R-2 se llaman `veredicto_tecnico_automatico`.
- La DW viva ya corre con beto-v2: R-2 no la modifica; el respaldo de beto-v1 está en output/f1/beto_local_respaldo/.

DECISIONES PENDIENTES PARA LEAN:
1. D3-bis (tras R-2): mantener beto-v2 o revertir a beto-v1 (respaldo + BETO_MODELO_VERSION=beto-v1 + rebuild de pipeline/api).
2. A-3/A-4: hacerlos tú (paquete ciego, sin sugerencia) o dejarlos como limitación declarada en el documento.
3. B-10 residual (sin cambios).

Al cerrar: pytest + cobertura · sin rebuild salvo que se apruebe D3-bis · commit · CIERRE_F1R.md
