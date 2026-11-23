# PLAN BETO_ACTIVO (BA) — Que BETO participe de verdad en lo que revisa el pipeline — 2026-11-23

**Objetivo (1 línea):** que BETO lea y resuelva los residuales de la cascada y ayude en la revisión humana, y que la web muestre con cifras reales qué hizo, en vez de «Leído por BETO: 0».

**Entrada:**
- Observación de Lean en la pantalla ②: «Total entidades evaluadas: 268.091 · Leído por BETO: 0 · Aceptado por BETO: 0».
- Código y mediciones en la rama `beto-integracion`.

---

## PARTE 1 — Por qué hoy BETO da 0 (evidencia)

| # | Hallazgo | Evidencia |
|---|---|---|
| H1 | **Los 4 interruptores de BETO están apagados.** `BETO_CASCADA_FINAL`, `BETO_ACUERDO_QC`, `BETO_SUGERENCIA_HITL` y `BETO_VENTANA` = `False` por defecto, y ninguno se define en el entorno de la API | `pipeline/config.py:51-56`; `beto_integracion.py:48-54` («con los flags apagados nada de este módulo se ejecuta»); `docker compose exec api env` sin `BETO_CASCADA_*` |
| H2 | Es una **decisión registrada**: D1/A-5 del 2026-11-15, «propuesta conservadora» de F1V | `docs/mediciones/f1_decision_flags.json`; `PLAN_F1.md:24`; `fuente_verdad_tesis.md:10` |
| H3 | **Contradicción con la tesis.** La fuente de verdad declara los flags en `False` (línea 10), pero también **A-15: «Cascada: resolución por BETO 3.382 (29,26 %)»** en el lote 1.387. Esa cifra se midió con scripts de evaluación (`ablacion_beto.py`) que ejecutan BETO por su cuenta. **El sistema vivo nunca ejecuta esa etapa.** Además, el invariante de `CLAUDE.md` pone a BETO como último escalón de la cascada | `fuente_verdad_tesis.md:10` y `:51`; `CLAUDE.md` (Cascada) |
| H4 | Lo único que BETO hace hoy en el flujo es **calcular el índice de confianza**, y solo para las líneas que **las reglas no resolvieron** (`indices_cascada`). Si encabezado, aproximación y patrón resuelven casi todo, BETO casi no recibe líneas. Las bandas 0,85 / 0,60 que mandan a revisión dependen de ese índice | `confianza_service.py:140-155` |
| H5 | El contador «Leído por BETO» suma `beto_ents` guardadas en staging, que **solo existen con los flags 1 o 2 encendidos**. Con los flags apagados siempre da 0, aunque BETO haya calculado índices | `routers/dataops/lectura.py:84-101`; `BetoCascadaResumen.jsx:22` |
| H6 | La etapa «Patrón» (REGEX) resuelve el 16,8 % (44.954). Hay que comprobar si acepta como resueltas líneas que en realidad deberían pasar a BETO | captura de Lean |

**Conclusión:** BETO no se usa como etapa de la cascada ni en la bandeja por una decisión de configuración (D1/A-5), no por una falla de código. Y la pantalla no distingue «BETO calculó confianza» de «BETO resolvió entidades».

## PARTE 2 — Loops

| Loop | Tarea | Agente (modelo) | Depende de | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|
| BA-L0 | **Línea base con flags apagados** sobre un lote recargado: por etapa, cuántas líneas recibió BETO para el índice (`pendientes` de `indices_cascada`), aciertos de caché, entidades por etapa, casos a revisión y tiempo de ciclo | `dev-baja` (haiku) | recarga | Tabla por lote y fuente; la suma de etapas cuadra con el total de entidades | `ba_l0_linea_base.csv` |
| BA-L1 | **Medición A/B en la DW tmpfs** (nunca en la viva ni en el snapshot) de las combinaciones: a0 todo apagado · a1 `CASCADA_FINAL` · a2 a1 + `SUGERENCIA_HITL` · a3 a2 + `ACUERDO_QC` · a4 a3 + `VENTANA`. Tres corridas por combinación, con caché vacía y llena | `dev-alta` (rol) con `model: "sonnet"` | L0, DF-L10 | Por combinación: (a) entidades resueltas por BETO; (b) **0 sobrescrituras de A/B y 0 perfiles creados por BETO** (invariantes, test); (c) casos a revisión (cambio frente a a0); (d) F1 sobre el lote v2 (≥ 0,85, RNF-04); (e) desacuerdo regla–BETO (QC); (f) tiempo de ciclo frente a RNF-03 (< 15 min; aceptable < 20); media y DE de 3 corridas | `ba_l1_ab.csv`, `ba_l1_ab.json` |
| BA-L1b | Revisión de la etapa «Patrón» (H6): muestra de 100 líneas que resolvió REGEX, ¿cuántas eran correctas? | `dev-media` (sonnet) | L0 | Precisión de REGEX sobre la muestra. Si < 95 %, se propone ajustar la regla (sin cambiar umbrales) para que lo dudoso pase a BETO | `ba_l1b_regex.csv` |
| BA-L2 | **Decisión de Lean** (DB2) con la tabla de BA-L1 a la vista: qué combinación queda por defecto | Lean | L1 | Decisión escrita | `ba_l2_decision_flags.json` (reemplaza a `f1_decision_flags.json`) |
| BA-L3 | **Aplicar la decisión:** defaults a3 en `pipeline/config.py` y variables en `docker-compose.yml` (sin secretos); **ruteo nuevo: < 0,85, desacuerdo o relación inválida → bandeja sin insertar** (sin la carga con `requiere_revision`); prioridad en la bandeja según la banda 0,60; rebuild; recarga del lote y comprobación de que «Leído / Aceptado por BETO» > 0 y de que 0 filas con índice < 0,85 quedan insertadas | `dev-media` (sonnet) | L2 | Mismas cifras que BA-L1 para la combinación elegida (±1 %); invariantes en verde | `ba_l3_aplicado.csv` |
| BA-L4 | **Pantalla ② honesta:** tres cifras separadas, cada una con una frase: «BETO calculó la confianza de **N** líneas que las reglas no resolvieron», «BETO resolvió **M** entidades residuales», «BETO coincidió con las reglas en **K %**» (QC). Si un flag está apagado, el texto lo dice («Esta etapa está desactivada por configuración»), nunca un 0 sin explicación. En la bandeja ③, candidatos con «probabilidad BETO» cuando `SUGERENCIA_HITL` está activo | `dev-media` (sonnet) + `/frontend-design` | L3 | Las cifras de la pantalla son iguales a las de `ba_l3_aplicado.csv`; test de componente con flags on y off | `ba_l4_capturas/` |
| BA-L5 | **Coherencia con la tesis:** los scripts de medición (`ablacion_beto.py`, `beto_cifra_unica.py`, lote 1.387) usan **la misma configuración de flags** que el sistema vivo; A-15 y la línea 10 de la SFV quedan consistentes; recongelado + aviso al chat 3 (texto) y al chat 4 (Gráfico 4.2) | `dev-alta` (rol) con `model: "sonnet"` | L3, DF-L10 | Diferencia 0 entre la etapa BETO del sistema vivo y la del script sobre el mismo lote | `ba_l5_coherencia.json` |

| BA-L6 | **Validación de relaciones antes de insertar** (DB1-DB2, punto 2). Reglas configurables (en el catálogo, no en el código) sobre las entidades del NER y las dimensiones: (a) **estudiante ↔ programa o módulo**: el POS o módulo existe y la fecha de la fila cae dentro del período del programa; (b) **módulo ↔ programa**: el número de módulo existe para ese POS; (c) **docente ↔ módulo**: el docente está en `bridge_modulo_docente` para ese módulo o se marca `DOCENTE_SIN_VINCULAR`; (d) **pago ↔ inscripción**: la persona de una fila financiera está inscrita en ese programa; (e) **respuesta ↔ escala**: la puntuación cabe en la escala de la pregunta; (f) **fecha ↔ gestión**: la fecha cae en una gestión válida (no 0205, 2580 ni 3035). Lo que falle va a revisión como `RELACION_INCOHERENTE`, con la regla, el valor y la acción propia en el descriptor `acciones[]` («Vincular a…», «Corregir fecha», «Marcar sin dato») | `dev-media` (sonnet) | L3 | (1) test por regla con fixture sintética, correcto e incorrecto; (2) 0 inserciones con relación inválida en la recarga; (3) conteo por regla en `ba_l6_relaciones.csv`; (4) la cascada y sus umbrales no cambian (test) | `ba_l6_relaciones.csv` |

Orden: **L0 → (L1 ‖ L1b) → L2 (registrar la decisión) → L3 (aplicar a3 y el ruteo nuevo) → L6 → (L4 ‖ L5)**. Después, `PLAN_ACEPTACION_FLUJO.md` se mide con esta configuración: G3 y G4 incluyen los motivos nuevos `DESACUERDO_REGLA_BETO` y `RELACION_INCOHERENTE`. BA-L0 se hace con el **mismo lote** que AF-L0, y G2 de `PLAN_ACEPTACION_FLUJO.md` se mide con la combinación que se elija en BA-L2.

## Riesgos y control
- **Tiempo de ciclo:** encender BETO en la cascada añade inferencia. Si una combinación pasa de 20 min (RNF-03), queda descartada salvo que Lean decida otra cosa.
- **Invariantes:** BETO sigue siendo el último escalón, solo para residuales; nunca sobrescribe A/B ni crea perfiles; 128 tokens (la ventana deslizante es opcional, a4).
- **Cifras congeladas:** activar BETO cambia A-12 a A-15, la distribución por bandas y probablemente KPI-10 y KPI-11 (confianza y automatización). Todo pasa por recongelado.
- **Estado operativo hoy (2026-11-23 00:4x):** en `giragroup_db` hay un `ALTER TABLE staging_registros_crudos …` **esperando un bloqueo desde hace más de 6 min**, detrás de una conexión de la API en «idle in transaction» desde hace más de 20 min. Mientras siga así, las consultas a `staging_registros_crudos` quedan en espera; una consulta de solo lectura mía también quedó en cola. Lo debe resolver quien esté recargando (reiniciar la API o cerrar esa transacción); este chat no lo toca.

## DECISIONES DE LEAN
- **DB1 + DB2 — RESUELTAS (Lean, 2026-11-23): el pipeline revisa todo con NER/PLN antes de insertar, y lo que quede por debajo del 85 % va a revisión.** Esto reemplaza a D1/A-5 (2026-11-15).

  1. **Combinación objetivo a3:** `BETO_CASCADA_FINAL` + `BETO_ACUERDO_QC` + `BETO_SUGERENCIA_HITL` encendidos (`BETO_VENTANA` sigue apagado salvo que BA-L1 muestre que hace falta).
     - **Cascada final:** BETO resuelve los residuales que las reglas no resolvieron.
     - **Acuerdo (control de calidad):** para **cada** fila que resolvieron las reglas, el NER de BETO comprueba que ve la misma entidad del mismo tipo; si no coincide, la fila no se inserta y va a revisión con el motivo `DESACUERDO_REGLA_BETO`.
     - **Sugerencias:** la bandeja muestra los candidatos con la probabilidad de BETO.
  2. **Relaciones antes de insertar (BA-L6):** además de las entidades, se valida que **las relaciones** entre ellas sean coherentes antes del `INSERT`. Lo que falle no se inserta y va a revisión con el motivo `RELACION_INCOHERENTE` y la regla que falló.
  3. **Ruteo nuevo:** un registro solo se inserta directo si cumple las tres condiciones: **índice ≥ 0,85**, BETO de acuerdo con las reglas y relaciones válidas. **Todo lo que esté por debajo de 0,85 va a la bandeja de revisión, sin insertarse.**
     - Hoy la banda 0,60–0,85 se insertaba marcada con `requiere_revision`; eso deja de pasar.
     - **Los umbrales 0,85 y 0,60 no cambian** (invariante). La banda 0,60 pasa a ser la **prioridad** dentro de la bandeja: de 0,60 a 0,85, prioridad media (con la sugerencia de BETO); menos de 0,60 o sin índice, prioridad alta.
     - El cierre debe declarar este cambio de semántica de la banda, que va al chat 3 (Cap. III, Sec. 3.4).
  4. **BA-L1 ya no elige la combinación: mide el impacto de a3 frente a a0.**
     - Mide tiempo de ciclo, F1, entidades resueltas por BETO, desacuerdos, relaciones incoherentes y **cuántos casos más llegan a la bandeja** (la carga de trabajo humana).
     - **Se detiene y vuelve a Lean** si a3 supera 20 min (RNF-03), si F1 < 0,85 (RNF-04) o si BETO sobrescribe A/B o crea un perfil (invariantes).
     - Si la bandeja crece más de 10 veces frente a a0, se informa antes de aplicar.
  5. **BA-L2 queda reducido a registrar la decisión** en `ba_l2_decision_flags.json`, con los resultados de BA-L1 adjuntos.

## PROMPT PARA CHAT 2
```
/gira-desarrollar
Ejecuta SOLO el loop BA-L<n> de docs/cierres/PLAN_BETO_ACTIVO.md.
- Agentes con model "sonnet" o "haiku", nunca Opus.
- La medición A/B se hace solo en la DW tmpfs, con pg_dump previo; ni la DW viva ni el snapshot.
- No cambies los defaults de los flags hasta que Lean responda DB2 por escrito.
- Cierra con CIERRE_BA_L<n>.md y commit ba(L<n>).
```
