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

## Asignación de agentes por fase y rol

### 1. Fase de Planificación y Arquitectura
- **Arquitecto principal (`dev-alta` — Modelos Insignia: Claude Opus 5.5 medio / Gemini 4 Argon medio o Neon / GPT-6.2 Astra medio)**:
  - Diseñar la estructura de la base de datos, definir la arquitectura del sistema, evaluar tecnologías o crear la hoja de ruta completa del proyecto.
  - Tareas de dificultad alta: medición A/B, fine-tuning, cambios de cascada o esquema, cifra final de tiempo. Una tarea completa por agente, sin fragmentarla.
- **Desglose de tareas (`dev-media` — Modelos Intermedios-Altos: Claude Sonnet 5.5 medio / Gemini 4 Neon o Hydrogen medio / GPT-6.2 Sol medio)**:
  - Dividir el plan general en tickets pequeños, redactar los pasos de implementación y crear listas de verificación técnicas.

### 2. Fase de Programación (Escritura y Depuración)
- **Desarrollador principal (`dev-media` — Modelos Intermedios-Altos: Claude Sonnet 5.5 / Gemini 4 Neon o Hydrogen / GPT-6.2 Sol medio)**:
  - Escribir funciones complejas, conectar APIs, refactorizar módulos completos y resolver errores (bugs) difíciles con potencia de razonamiento sin volverse lentos ni costosos. Funcionalidad con pruebas, KPI faltantes, KLM, análisis de desacuerdos. En paralelo si no tocan los mismos archivos.
- **Asistente rápido en el editor (`dev-baja` — Modelos Equilibrados: Haiku 5.5 bajo / Gemini 3.8 medio / GPT-6.1 Terra)**:
  - Autocompletar código en tiempo real, escribir pruebas unitarias (unit tests), generar documentación técnica, hacer consultas rápidas de sintaxis o correr comandos con resultados. Consultas SQL, conteos, purgas, merge, rebuild, inventarios. En paralelo.

## Reglas
- Si una tarea exige cambiar un invariante, no la planifiques: ponla en DECISIONES PENDIENTES.
- Cada criterio de aceptación tiene número y archivo de evidencia.
- No mezcles fases: una fase cierra con su CIERRE antes de planificar la siguiente.
- Cuando la fase de congelamiento termine, el último paso es avisar «F3 congelado» para el chat 3.
