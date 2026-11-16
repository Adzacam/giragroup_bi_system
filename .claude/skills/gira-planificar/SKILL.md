---
name: gira-planificar
description: Chat de planificación de GiraGroup BI. Usar al iniciar o cerrar una fase, para leer CIERRE_*.md y escribir el PLAN de la siguiente fase con agentes por dificultad. Solo lectura.
---

# Planificación (chat 1)

**Modo solo lectura.** Trabaja en modo plan. No editas código, no ejecutas comandos que escriban, no decides cifras. El único archivo que produces es `docs/cierres/PLAN_<fase>.md`, y lo escribe el chat 2 si el modo plan no permite guardar: entrégalo completo en la respuesta.

## Al empezar
1. Lee `CLAUDE.md` (invariantes).
2. Lee `docs/cierres/` (todos los `CIERRE_*.md` y `FIGURAS_*.md`), `docs/fuente_verdad_tesis.md` y el plan maestro (`docs/cierres/plan_maestro.md`).
3. Identifica la fase siguiente y sus tareas pendientes.

## Qué contiene un PLAN_<fase>.md
```markdown
# PLAN <fase> — <fecha>
Objetivo de la fase (1 línea):
Entrada: CIERRE previo leído = <archivo>; rama base = <rama> <hash>

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|

Comandos exactos por tarea:
Riesgos y control:
DECISIONES PENDIENTES PARA LEAN (no se ejecutan hasta que responda):
Al cerrar: pytest + cobertura · rebuild de lo tocado · commit · CIERRE_<fase>.md

## PROMPT PARA CHAT 2
/gira-desarrollar
Ejecuta docs/cierres/PLAN_<fase>.md. ...
```

## Asignación de agentes
| Dificultad | Ejemplos | Agente |
|---|---|---|
| Alta | Medición A/B, fine-tuning, cambio de cascada o esquema, cifra final de tiempo | `dev-alta` (Opus). Una tarea en un solo agente, sin fragmentarla |
| Media | Funcionalidad con pruebas, KPI faltantes, KLM, análisis de desacuerdos | `dev-media` (Sonnet). En paralelo si no tocan los mismos archivos |
| Baja | Consultas SQL, conteos, purgas, merge, rebuild, inventarios | `dev-baja` (Haiku). En paralelo |

## Reglas
- Si una tarea exige cambiar un invariante, no la planifiques: ponla en DECISIONES PENDIENTES.
- Cada criterio de aceptación tiene número y archivo de evidencia.
- No mezcles fases: una fase cierra con su CIERRE antes de planificar la siguiente.
- Cuando la fase de congelamiento termine, el último paso es avisar «F3 congelado» para el chat 3.
