# Plan maestro: 4 chats (sistema ↔ documento)

Ubicación en el repo: `docs/cierres/plan_maestro.md`. Lo leen las skills `/gira-planificar`, `/gira-desarrollar` y `/gira-figuras`.

**Reglas madre**
1. El sistema respeta lo que el documento ya declara (invariantes, sección 3). Si una mejora necesita cambiarlo, el chat 2 se detiene y lo reporta.
2. Las cifras nuevas entran al documento **una sola vez**, después de congelar `docs/fuente_verdad_tesis.md`.
3. Ningún chat inventa datos. Una cifra sin archivo de evidencia en `docs/mediciones/` no existe.

---

## 1. Roles

| Chat | Modo | Hace | No hace | Recibe | Entrega |
|---|---|---|---|---|---|
| **1. Planificación** (Claude Code, `/gira-planificar`) | Solo lectura | Lee repo, md de cierre y documento; divide en fases; asigna agentes por dificultad; redacta prompts | Editar archivos, ejecutar comandos que escriben, decidir cifras | `CIERRE_<fase>.md`, `FIGURAS_<fase>.md` | `PLAN_<fase>.md` con el prompt para el chat 2 o el 4 |
| **2. Desarrollo** (Claude Code local, `/gira-desarrollar`) | Escritura en tu equipo | Implementa **solo** lo del `PLAN_<fase>.md`; prueba; mide sobre la copia aislada; al terminar: commit y reconstrucción | Tocar el docx; cambiar invariantes; improvisar tareas | `PLAN_<fase>.md` | Código, commit y `CIERRE_<fase>.md` |
| **3. Documento ↔ sistema** (claude.ai, Proyecto) | Lectura de docx y repo | Contrasta y redacta Lugar / Buscar / Reemplazar | Ejecutar o modificar el sistema; poner cifras no congeladas | `fuente_verdad_tesis.md` CONGELADO + `FIGURAS_*.md` | `.md` de correcciones por capítulo |
| **4. Figuras y comandos** (Claude Code, `/gira-figuras`) | Ejecuta scripts de salida | Gráficos, capturas, tablas exportadas y comandos de consulta | Cambiar lógica; calcular cifras que no estén en una medición | JSON o CSV de `docs/mediciones/` + `PLAN_FIG` del chat 1 | PNG o CSV + `FIGURAS_<fase>.md` |

**Flujo**
```
Chat 1 ──PLAN_<fase>.md──► Chat 2 ──CIERRE_<fase>.md──► Chat 1
Chat 1 ──PLAN_FIG.md──► Chat 4 ──FIGURAS_<fase>.md──► Chat 1
Chat 1 ──«F3 congelado»──► Chat 3 ──correcciones .md──► tú aplicas en el docx
```

Todos los md de traspaso van en `docs/cierres/`. Así el chat 1 los lee del repo y no hace falta pegarlos.

---

## 2. Asignación de agentes (chat 1)

| Dificultad | Ejemplos | Agente | Paralelizable |
|---|---|---|---|
| Alta | Medición A/B, fine-tuning, cambios de cascada o esquema, cifra final de tiempo, decisiones metodológicas | `dev-alta` (Opus) | No: una tarea alta va en un solo agente |
| Media | Funcionalidad con pruebas, KPI faltantes, KLM, análisis de desacuerdos | `dev-media` (Sonnet) | Sí, si no tocan los mismos archivos |
| Baja | Consultas SQL, conteos, purga de caché, merge, rebuild, inventarios | `dev-baja` (Haiku) | Sí |

---

## 3. Invariantes que el sistema debe respetar

| Área | Valor declarado en el documento |
|---|---|
| Cascada | CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO. BETO va al final, solo para residuales; nunca sobrescribe A/B ni crea perfiles |
| Umbrales | 0,92 personas · 90 % homónimos · 85 % CI variante y docentes · 80 % módulos · bandas 0,85 / 0,60 |
| Estados de identidad | A (CI exacta) / B (rescate difuso o TEMP) / C (homonimia o docente provisional) |
| Catálogo | Solo entidades institucionales, **sin docentes ni estudiantes** |
| BETO | `dccuchile/bert-base-spanish-wwm-cased`, IOB2, 128 tokens (ventana deslizante permitida; **no 512**) |
| DW | 50 tablas + 9 vistas `bi`; 9 hechos, 7 dimensiones, 1 puente; esquema constelación; idempotencia por `carga_fila_origen` |
| CMI | 22 KPI en `bi.ref_kpi`; `/api/v1/cmi/scorecard` |
| Pronóstico | Holt-Winters amortiguado (m = 12, hold-out de 6 meses); OLS mensual N = 40; OLS anual solo descriptiva |
| Requisitos | 11 RF, 7 RNF, 12 HU, 6 sprints; RNF-03 < 15 min (aceptable < 20 min); RNF-04 F1 ≥ 0,85 |
| Infraestructura | 9 servicios en docker-compose, sin licencias comerciales |
| Datos | Snapshot `snapshot_dw_20261110_1201` en solo lectura; las mediciones van en la copia tmpfs; **un único lote congelado** para la medición final |

---

## 4. Pendientes A y B (entrada del chat 1)

### Parte A: integración de BETO (rama `beto-integracion`)

**Estado:** opciones 1–3 y ventana implementadas tras flags apagados; DW idéntico a la base con flags apagados; 699 pruebas (681 passed / 11 skipped / 7 xfailed / 0 failed); cobertura 70,15 %. La medición no se ejecutó.

| ID | Tarea | Chat | Dificultad | Criterio de salida |
|---|---|---|---|---|
| A-1 | A/B por flag (a0, a1, a2, a3, a12, a123), 3 corridas, con caché vacía y llena (§7 de `docs/beto_integracion_implementacion.md`) | 2 | Alta | Tabla de ablación: hechos, staging, bandeja, KPI-10/11/18, tiempos (media y DE) |
| A-2 | Opción 2 con `BETO_VENTANA=1` (sin ventana, 145 de 150 son «no evaluables») | 2 | Alta | Tasa de acuerdo con «no evaluables» < 20 % |
| A-3 | Revisar desacuerdos por archivo (falsos por nombres cortados: «ED» + «GAR») | 2 | Media | Muestra revisada y % de falsos desacuerdos |
| A-4 | Opción 3: % de veces en que el primer candidato coincide con la decisión del revisor | 2 | Media | Tasa de acierto top-1 |
| A-6 | Efecto de la opción 2 en KPI-10/11, bandeja y 97,55 / 2,45 % | 2 | Media | Antes / después por KPI |
| A-5 | **Decidir qué flags quedan encendidos.** Criterio: aporte medido y tiempo < 15 min (aceptable < 20) | Tú + 1 | — | Decisión escrita en `PLAN_F1.md` |
| A-7 | Purga de `cache_beto_entidades`, que guarda nombres de personas | 2 | Baja | Purga + prueba |
| A-8 | Rama `beto-entrenamiento`: estado e integración | 2 | Alta | F1 gold_510 y layouts_5 antes / después |
| A-9 | Decidir si `cache_beto_entidades` cuenta en las 50 tablas (se recomienda excluirla como caché) | Tú + 1 | — | Decisión escrita |
| A-10 | Merge, commit y reconstrucción (pipeline, API, frontend) | 2 | Baja | `docker compose ps` sano |

### Parte B: lo que pide la revisión y solo puede salir del sistema

| ID | Tarea | Chat | Dificultad | Fila del md de correcciones |
|---|---|---|---|---|
| B-1 | Pruebas por suite, lista de xfail con su RF/RNF y motivo de las omitidas (**sobre la suite final**) | 2 | Baja | P-1 → Tabla 3.29, III-11 |
| B-2 | KPI-12 a 15 y 17 a 20 (2025 y global); si los hechos con `requiere_revision` entran en los KPI | 2 | Media | P-2 → Tabla 4.6, IV-5/6/12/18 |
| B-3 | Gráfico 3.1 (503 frente a 510); TP, FP y FN estrictos y relajados por modo | 2 | Media | P-3 |
| B-4 | Orden aumento / separación train-dev, fuga entre conjuntos, anotación del gold_510 | 2 | Media | P-4 |
| B-5 | Valor 2025 de la OLS anual frente al ejecutado del KPI-03 | 2 | Baja | P-5 → Tabla 4.7 |
| B-6 | KLM recalculado sobre la bandeja actual (el documento usa 188 casos / 37 grupos; el lote actual da 182 / 12) | 2 | Media | Tabla 4.8, IV-9 |
| B-7 | Medición final del ciclo con los flags elegidos: caché vacía y llena, 3 corridas, media y DE | 2 | Alta | PD-01 / RNF-03 |
| B-8 | (Opcional) Intervalo de predicción formal de Holt-Winters | 2 | Media | IV-13, IV-17 |
| B-9 | (Opcional) Registrar todos los descartes en `log_inconsistencias`; identificador para homónimos sin CI | 2 | Media | Limitaciones 12 y 13 |
| B-10 | Retirar del repositorio la contraseña de PostgreSQL expuesta | 2 | Baja | — |

---

## 5. Fases

| Fase | Flujo | Contenido | Sale con |
|---|---|---|---|
| F0 | 1 → 2 | A-1, A-2, A-3, A-4, A-6 (solo medición, copia aislada, sin cambiar defaults). En paralelo: B-3, B-4, B-5, B-10 (no dependen de los flags) | `CIERRE_F0.md` + JSON de ablación |
| F1 | 1 → tú → 2 | A-5 y A-9 (decisiones); A-7, A-8, A-10 | Defaults fijados, merge, rebuild |
| F2 | 1 → 2 | B-1, B-2, B-6 (B-8 y B-9 si los apruebas) | `CIERRE_F2.md` con respuestas P-1 a P-5 |
| F3 | 1 → 2 | B-7 + pytest con cobertura + KPI + huella del DW → `fuente_verdad_tesis.md` **CONGELADO** | Commit `F3: congelamiento` |
| F4 | 1 → 4 | Figuras: Gráficos 3.1, 3.3, 4.4, 4.5 y 4.6, Figura 3.40, capturas reales pendientes | `FIGURAS_F4.md` |
| F5 | 1 → 3 | Cap. III, IV y V con las cifras congeladas | Correcciones `.md` |

**Antes de F0:** congelar un único lote de 10 archivos (bytes fijos). El estado actual de `uploads/data` da 12.992 líneas y 182 casos; las mediciones previas usaban 15.926 y 194.

**En paralelo, sin depender del sistema:** aplicas en el docx la sección 4 de `pendientes_datos_reales_y_sistema.md` y reúnes tus datos (D-1 Likert, D-2, D-3, D-5, D-6).

---

## 6. Prompt de arranque del chat 1

```
/gira-planificar
Fase F0. Lee docs/cierres/plan_maestro.md (secciones 3, 4 y 5) y docs/beto_integracion_implementacion.md.
Escribe PLAN_F0.md con:
 1. Paso previo: congelar el lote de 10 archivos (bytes fijos) y registrar su huella.
 2. Tareas A-1, A-2, A-3, A-4, A-6 ordenadas, con criterio de aceptación medible.
 3. En paralelo: B-3, B-4, B-5, B-10.
 4. Agente por tarea (dev-alta / dev-media / dev-baja) y qué va en paralelo.
 5. Comandos exactos (§7 del md de implementación) y archivos de salida en docs/mediciones/.
 6. Riesgos de la §8 que afectan la medición y cómo controlarlos (lote, caché, servicio compartido :8006).
 7. Al final, el bloque PROMPT PARA CHAT 2.
No propongas cambiar invariantes; si algo los exige, ponlo como DECISIÓN PENDIENTE para Lean.
```

Las reglas del chat 2, del chat 4 y la plantilla de `CIERRE_<fase>.md` están en sus skills (`.claude/skills/`).

---

## 7. Cifras ya desactualizadas en el documento (no tocar hasta F3)

| Cifra en el docx | Valor actual del sistema | Entra en |
|---|---|---|
| 652 / 634 pruebas | 699 / 681 | F3 |
| Cobertura 68,4 % | 70,15 % (10.210 / 14.555) | F3 |
| KLM 490,5 s (188 casos / 37 grupos) | Lote actual: 182 casos / 12 grupos (recalcular, B-6) | F2–F3 |
| Ciclo 15.926 líneas / 194 casos | 12.992 líneas / 182 casos (otro estado de `uploads/data`) | F3 |
| Tiempo 9,2 min | Pendiente de B-7 | F3 |
