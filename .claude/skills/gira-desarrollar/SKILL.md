---
name: gira-desarrollar
description: Chat de desarrollo de GiraGroup BI en el equipo local. Usar solo para ejecutar un docs/cierres/PLAN_<fase>.md; prueba, reconstruye, hace commit y escribe CIERRE_<fase>.md.
---

# Desarrollo (chat 2)

Solo ejecutas lo que trae `docs/cierres/PLAN_<fase>.md`. **Nada fuera del plan.** Si falta el PLAN, pídelo y no empieces.

## Al empezar
1. Lee `CLAUDE.md` (invariantes) y el `PLAN_<fase>.md` indicado.
2. Si el plan tiene DECISIONES PENDIENTES sin respuesta de Lean, ejecuta solo las tareas que no dependen de ellas.
3. Delega cada tarea al agente que indica el plan (`dev-alta`, `dev-media`, `dev-baja`). Las marcadas como paralelas se lanzan juntas.

## Reglas
- Si una tarea exige cambiar un invariante (cascada, umbrales 0,92/90/85/80, bandas 0,85/0,60, catálogo sin docentes ni estudiantes, 128 tokens, 50 tablas, 22 KPI), **detente y repórtalo**.
- Las mediciones se hacen solo en la copia tmpfs. Nunca en la DW viva ni en el snapshot.
- Toda cifra va con su JSON o CSV en `docs/mediciones/`.
- No tocas el documento de tesis.

## Cierre de la fase (en este orden)
1. `python -m pytest tests --cov=backend --cov=pipeline`
2. Si tocaste backend o pipeline: `docker compose up -d --build api pipeline`. Si tocaste frontend: `docker compose up -d --build frontend`.
3. `docker compose ps` y una prueba manual del endpoint afectado.
4. `git add -A && git commit -m "<fase>: <resumen>"`. Merge solo si el plan lo indica.
5. Escribe `docs/cierres/CIERRE_<fase>.md`:

```markdown
# CIERRE <fase> — <fecha>
Rama / commit: <rama> <hash>
Hecho (máx. 10 líneas):
No hecho y por qué:
Invariantes cambiados: no | sí → cuál y por qué
Pruebas: colectadas / passed / failed / skipped / xfailed · cobertura % (sentencias)
Servicios reconstruidos + estado de docker compose ps:
Cambios de esquema o API:
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
Impacto en el documento (sección o tabla):
Riesgos abiertos:
Pendiente para el chat 4:
```

6. Responde solo: «CIERRE_<fase>.md listo; pásalo al chat 1».
