# PLAN ACEPTACION_FLUJO (AF) — Prueba de aceptación del pipeline, BETO y la revisión humana — 2026-11-22

**Objetivo (1 línea):** demostrar con mediciones, después de la recarga, que el pipeline lee bien las fuentes, que BETO actúa solo donde debe y acierta, y que a la revisión humana llegan los casos correctos y en forma coherente. Hasta que todas las compuertas estén en verde, **no se afirma** que el flujo es correcto.

**Entrada:**
- `CIERRE_DATAOPS_FLUJO.md` (`3e88499` y correcciones hasta `f2c6bcf`): **no verificado por este chat**; lo verificó otra sesión sobre el lote 46, que ya no existe.
- `PLAN_CATALOGO.md` sin ejecutar.
- DF-L10 sin ejecutar.
- FU-L0b (tres vías) **sin evidencia**: no hay archivo `fu_l0b_*` en `docs/mediciones/`.
- DW viva vaciada a propósito el 2026-11-22.

**Qué se prueba y qué no:**
- Se prueba la **calidad del flujo** sobre los 10 libros de `uploads/data` recargados y sobre fixtures sintéticas.
- No se prueban cifras de la tesis: si alguna cambia, sigue el camino de recongelado de siempre.

---

## Precondiciones (sin ellas no se empieza)
| # | Precondición | Evidencia |
|---|---|---|
| P1 | CAT-L1 y CAT-L2 ejecutados: el pipeline ya no crea `MOD-GEN` y el catálogo empieza limpio | `CIERRE_CAT_L1.md`, `CIERRE_CAT_L2.md` |
| P2 | Recarga completa de los 10 libros por el **flujo normal del sistema** (① → ② → preparación automática → ③), no por script de recarga directa | `af_p2_recarga.json`: lotes, documentos, sha256 de cada libro iguales a `CONTRATO_FUENTES.md` |
| P3 | DF-L10 ejecutado: lote congelado v2 sin hoja oculta | `df_lote_1387_v2.json` + huella |
| P5 | `PLAN_BETO_ACTIVO.md` aplicado hasta BA-L3 y BA-L6: configuración a3, ruteo < 0,85 → revisión y validación de relaciones. La recarga P2 se hace **con esa configuración** | `CIERRE_BA_L3.md`, `CIERRE_BA_L6.md`, `ba_l2_decision_flags.json` |
| P4 | Ninguna resolución humana hecha todavía en la bandeja recargada (las compuertas G3 y G4 miden lo que el sistema decidió solo) | `SELECT` sobre `stg_entidad_no_resuelta`: 0 filas `RESUELTO_HUMANO` |

---

## Compuertas

| # | Qué se afirma | Cómo se mide | Criterio de aprobación | Salida en docs/mediciones/ |
|---|---|---|---|---|
| **G1** | **El pipeline lee lo que hay en los archivos** | **Tres vías por hoja y campo:** (a) perfil crudo (`perfil_fuentes.py`), (b) salida del **lector del sistema** en seco (`preview-workbook` y extracción sin cargar), (c) DW tras P2. Con los scripts `fu_l*_comparar_fuente_vs_dw.py` como base | **Conservación de filas** en cada hoja «usar»: `leídas = cargadas + en revisión + descartadas con motivo`, con diferencia **0**. Agregados clave iguales a la fuente: pagos por año, inscritos por año, estados académicos, respuestas válidas de encuestas, metas por mes. Toda diferencia debe estar explicada en el CSV | `af_g1_tres_vias.csv`, `af_g1_balance_filas.csv` |
| **G2** | **La cascada y BETO hacen lo que deben** | Conteo por etapa (CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO) por lote; tests de invariantes; F1 sobre el lote v2 | (a) BETO solo recibe residuales: 0 entidades resueltas por BETO que ya tenían A/B; (b) BETO no crea perfiles (test); (c) **F1 ≥ 0,85** (RNF-04) sobre el lote v2, 2 corridas con diferencia 0; (d) por entidad se guarda qué etapa la resolvió y con qué evidencia (muestreo de 50: 100 % con etapa y evidencia) | `af_g2_cascada.csv`, `af_g2_f1.json` |
| **G3** | **A la revisión llega lo que debe llegar** (enrutamiento) | **Muestra estratificada etiquetada a ciegas por Lean** (ver abajo): para cada fila, Lean dice adónde **debía** ir sin ver la decisión del sistema. Matriz de confusión sistema frente a Lean | (según DA-A1) **Exactitud ≥ 95 %**; **falsos negativos** (aceptadas directo que debían revisarse) **≤ 2 %**, con límite superior del IC 95 % (Wilson) ≤ 5 %; **falsos positivos** (enviadas a revisión que eran directas) **≤ 20 %**; motivo correcto en ≥ 90 % de las que sí debían ir a revisión | `af_g3_matriz.csv`, `af_g3_metricas.json` (solo agregados, sin PII) |
| **G4** | **Lo que llega a revisión es coherente** | Chequeo automático sobre **todos** los casos pendientes y avisos | (a) 0 casos con payload vacío; (b) 0 casos con confianza 0 en `BAJA_CONFIANZA_IA` (deben ser `SIN_LECTURA`); (c) 100 % con motivo de catálogo, evidencia (documento, hoja, fila, columna) y `acciones[]` propias de su motivo y rol; (d) campos precargados en el 100 % de los casos donde la fuente trae el valor; (e) 0 casos duplicados por `clave_origen`; (f) los avisos pendientes de `log_inconsistencias` aparecen en `/review-tray/avisos`; (g) el número de casos es igual en ②, ③, el historial y la notificación de la tarea | `af_g4_coherencia.csv` |
| **G5** | **Las acciones hacen lo que dicen** | Por cada motivo presente, resolver **1 caso** con cada acción de su descriptor en la DW tmpfs; comprobar el efecto en la DW y en la auditoría; deshacer o reabrir | 100 % de las acciones: efecto esperado (hecho creado o vinculado, perfil C creado, sinónimo guardado, descarte con motivo), fila de auditoría con valor anterior y nuevo, y deshacer o reabrir que deja la DW como estaba. `APROBACION_BLOQUE` no cuenta como `correccion_humana` | `af_g5_acciones.csv` |
| **G6** | **El flujo es idempotente y no escribe al mirar** | (a) Reprocesar el mismo lote; (b) borrar un documento y volver a subirlo; (c) abrir ①, ② y ③ | (a) 0 hechos y 0 casos nuevos; (b) mismos conteos que antes (la clase de error de «inscritos ×2» no vuelve); (c) 0 filas nuevas en `dataops_tarea` al hacer GET | `af_g6_idempotencia.csv` |
| **G7** | **No depende de los 10 archivos** | Fixtures sintéticas (renombradas, columnas en otro orden, sinónimos de cabecera, hoja sin cabecera, texto libre largo, hojas ocultas) + un test que busca nombres de libro u hoja en `backend/` y `pipeline/` | Resultados en la DW **idénticos** a los de los originales; texto libre: 0 hechos inventados y casos a revisión con motivo; el grep da 0 coincidencias | `af_g7_agnostico.txt` |
| **G8** | **El catálogo queda limpio tras la recarga** | CAT-L6 | 0 `MOD-GEN`; 0 módulos o instituciones de clase inválida; instituciones de convenio cargadas | `cat_l6_post_recarga.csv` |
| **G9** | **Se ve en pantalla** | Playwright con sesión real, en 1440, 768 y 375 px, claro y oscuro, sobre un lote recargado | 0 errores de consola; las cifras de ①, ② y ③ coinciden con G4 (g); un caso de cada motivo muestra sus acciones propias; los datos personales se ven enmascarados; la franja de capacidades está presente y sin números de tarea | `af_g9_capturas/`, `af_g9_consola.txt` |

| **G10** | **Aporte de BETO, PLN y NER** frente a usar solo reglas | **Comparación pareada** sobre la **misma muestra etiquetada**: cada fila se evalúa con la configuración **a3** (BETO activo, `PLAN_BETO_ACTIVO.md`) y con **a0** (solo reglas), recalculada en la DW tmpfs sobre el mismo lote. Como las etiquetas de Lean no dependen de lo que decide el sistema, se usan para las dos | **(a)** falsos negativos, falsos positivos y exactitud de a3 frente a a0, con **prueba de McNemar** sobre las filas en las que las dos configuraciones deciden distinto; **(b)** precisión del control de acuerdo: de los casos `DESACUERDO_REGLA_BETO` etiquetados, % que de verdad debían revisarse; **(c)** rescates de BETO: de las entidades que resolvió la cascada final, % correctas; **(d)** F1 del NER por tipo de entidad sobre el lote v2 (de G2); **(e)** PLN: de las filas de texto heterogéneo (DF-L11), % en que las entidades extraídas son correctas (muestra de 20); **(f)** costo: tiempo de ciclo y casos en la bandeja de a3 frente a a0. **Criterio:** G10 **no exige mejorar**, exige **medir y declarar**. Da verde si las 6 métricas están calculadas con su IC y si **a3 no tiene más falsos negativos que a0** (BETO no puede empeorar la calidad de los datos). Para cada métrica, el cierre dice «aporte significativo» (McNemar p < 0,05 o IC que no cruza 0) o «sin diferencia significativa». No se infla | `af_g10_aporte.json`, `af_g10_tabla_cap4.csv` |

### Muestra etiquetada de G3 y G10 (lo más importante)
- **Diseño:** estratificada por **destino del sistema** (directo / revisión / descartado) × **tipo de fuente** (acta, cobranza, marketing, evaluación docente, planificación, rentabilidad o egresos, techos), con semilla fija. **250 filas: 120 directo · 70 revisión · 30 descartado · 30 discordantes** (DA-A2 ajustado por G10), con exactitud reponderada por el peso real de cada destino.
- **Discordantes (G10):** filas en las que a0 y a3 deciden distinto. Son las que muestran el aporte de BETO.
- **Mínimos para G10 dentro de la muestra:** al menos 20 filas «revisión» con motivo `DESACUERDO_REGLA_BETO` y al menos 20 filas «directo» resueltas por la cascada final de BETO. Si el lote no tiene tantas, se toman todas y el cierre lo declara.
- **Límite de falsos negativos con 120 «directo»:** con 0 / 1 / 2 errores = 3,1 / **4,6** / 5,9 %. Sigue pasando el umbral de ≤ 5 % con hasta 1 error.
- **A ciegas:** la planilla de etiquetado **no muestra** la decisión del sistema ni su confianza. Por fila muestra el texto de origen, la hoja y la columna, y los candidatos del padrón **solo si Lean los pide**.
- **Opciones de Lean:** «directo», «revisión» (con el motivo de una lista) o «descartar».
- **Privacidad:** la planilla con datos reales vive **fuera del repositorio** (`output/aceptacion/af_g3_etiquetado.csv`, en una carpeta ignorada por git). En `docs/mediciones/` solo entran la matriz y las métricas agregadas.
- **Tiempo estimado:** unas 2 horas (unos 30 s por fila).
- **Cómo se lee:**
  - un **falso negativo** es el error grave: entra a la DW un dato que debía revisarse;
  - un **falso positivo** cuesta tiempo humano, pero no ensucia datos.

  Por eso los umbrales son distintos.

---

## Loops

| Loop | Tarea | Agente (modelo) | Depende de | Paralelo con | Salida |
|---|---|---|---|---|---|
| AF-L0 | Verificar P1–P4 y congelar la línea base de la recarga | `dev-baja` (haiku) | CAT-L2, recarga, DF-L10 | — | `af_p*.json` |
| AF-L1 | G1 tres vías + balance de filas | `dev-media` (sonnet) | L0 | L2, L4, L6, L7 | `af_g1_*` |
| AF-L2 | G2 cascada, invariantes y F1 | `dev-media` (sonnet) | L0 | L1 | `af_g2_*` |
| AF-L3 | Generar la muestra de G3 y G10 (250 = 120 / 70 / 30 / 30 discordantes), la submuestra común de 50, las 2 planillas sin la decisión visible y `GUIA_ETIQUETADO_AF.md` | `dev-baja` (haiku) | L0 | L1, L2 | `output/aceptacion/af_g3_etiquetado_lean.csv`, `…_auditor.csv` |
| AF-L3b | **Etiquetado por Lean (250) y por el auditor (submuestra de 50)**, por separado y a ciegas, con `GUIA_ETIQUETADO_AF.md` | Lean + auditor | L3 | — | 2 planillas completas |
| AF-L3c | κ de Cohen, consenso de desacuerdos, matriz y métricas de G3 con IC de Wilson y exactitud reponderada | `dev-baja` (haiku) | L3b | — | `af_g3_*`, `af_g3_kappa.json` |
| AF-L4 | G4 coherencia de todos los casos | `dev-media` (sonnet) | L0 | L1, L2 | `af_g4_coherencia.csv` |
| AF-L5 | G5 acciones, en la DW tmpfs | `dev-media` (sonnet) | L4 | L6 | `af_g5_acciones.csv` |
| AF-L6 | G6 idempotencia y «ver no escribe», en tmpfs | `dev-media` (sonnet) | L0 | L5 | `af_g6_idempotencia.csv` |
| AF-L7 | G7 agnosticidad | `dev-baja` (haiku) | — | todos | `af_g7_agnostico.txt` |
| AF-L8 | G8 (CAT-L6) y G9 en el navegador | `dev-baja` (haiku) | L4 | L5–L7 | `af_g9_*` |
| AF-L10 | G10: recalcular el mismo lote con a0 en la DW tmpfs, identificar las filas discordantes para AF-L3, y después de etiquetar: McNemar, precisión del control de acuerdo, rescates, F1 por tipo, PLN en texto heterogéneo y costo | `dev-media` (sonnet) | L0 (a0 antes de L3); L3c (métricas) | L4–L8 | `af_g10_aporte.json`, `af_g10_tabla_cap4.csv` |
| AF-L9 | **Veredicto** | `dev-media` (sonnet) | L1–L8 | — | `CIERRE_ACEPTACION_FLUJO.md` |

**Veredicto (AF-L9):**
- `CIERRE_ACEPTACION_FLUJO.md` trae una tabla G1–G10 con estado (verde / rojo), cifra medida, umbral y archivo de evidencia.
- **El aporte de BETO, PLN y NER** se escribe solo con G10 en verde, usando las frases que fija G10 («aporte significativo» o «sin diferencia significativa») y su tabla `af_g10_tabla_cap4.csv`, que pasa al chat 3 después del recongelado.
- **Solo con G1–G9 en verde** se puede escribir «el pipeline y BETO hacen el flujo correcto y a la revisión humana llegan datos coherentes», citando la tabla.
- Con alguna en rojo, el cierre lista las fallas como tickets para un plan de corrección, y la afirmación **no** se hace.

## Comandos
```powershell
.venv\Scripts\python scripts\auditoria_fuentes\perfil_fuentes.py
```
```powershell
.venv\Scripts\python -m pytest tests -q -k "invariante or cascada or beto or agnostic"
```
```powershell
node e2e/dataops_flujo.mjs
```

## Riesgos y control
- **Sesgo del etiquetado:** si Lean ve la decisión del sistema, G3 no vale. La planilla no la muestra y el orden de las filas es aleatorio.
- **Medir sobre una bandeja ya tocada:** P4 exige 0 resoluciones humanas antes de G3 y G4. G5 resuelve casos solo en tmpfs.
- **PII:** la planilla con datos reales queda fuera del repositorio y no se envía a ningún servicio externo. Las evidencias versionadas son agregadas.
- **Recarga por script:** si P2 se hace con `fu_l9_recarga_completa.py` en vez del flujo de la web, G1 a G4 no prueban el flujo real. P2 exige el flujo normal.
- **Cifras:** si la recarga cambia KPI congelados, sigue el camino de recongelado con aviso al chat 3.

## DECISIONES PENDIENTES PARA LEAN
- **DA-A1 — RESUELTA (Lean, 2026-11-22): se aceptan los umbrales de G3.**
  - **Exactitud ≥ 95 %**.
  - **Falsos negativos ≤ 2 %**, con el límite superior del IC 95 % (Wilson) **≤ 5 %**.
  - **Falsos positivos ≤ 20 %**.
  - **Motivo correcto ≥ 90 %** en las filas que debían ir a revisión.
  - Los cuatro se aplican sobre la muestra total. Los falsos negativos por tipo de fuente se **informan** en `af_g3_metricas.json`, pero no son umbral: con unas 12 filas por estrato, un solo error ya da un 8 %.
  - Quedan fijos antes del etiquetado. No se ajustan después de ver los resultados.
- **DA-A2 — RESUELTA (Lean, 2026-11-22): unas 250 filas, con más peso en «directo».**
  - **Por qué no un reparto parejo:** los falsos negativos solo existen entre las filas que el sistema aceptó directo. Con un reparto parejo (unas 84 de 250), el límite superior de Wilson con **1** error es **6,4 %** (> 5 %): la compuerta fallaría por tamaño de muestra, no por calidad.
  - **Reparto fijado:**
    - ~~140 / 80 / 30~~ → **ajustado por G10 (2026-11-23), mismas 250 filas:**
    - **120 filas «directo»**: límite superior con 0 / 1 / 2 errores = 3,1 / **4,6** / 5,9 %. Pasa con hasta 1 error;
    - **70 filas «revisión»**: para falsos positivos y motivo correcto;
    - **30 filas «descartado»**;
    - **30 filas discordantes** entre a0 y a3 (G10).
    - Dentro de cada destino, el reparto entre tipos de fuente es proporcional al volumen, con un mínimo de 5 filas por tipo presente.
  - **Cómo se calcula:** la exactitud global se calcula **reponderando** cada destino por su peso real en el lote (pesos inversos a la probabilidad de selección), para que el sobremuestreo no infle ni hunda la cifra.
  - **Tasas:** falsos negativos = filas «directo» que Lean marcó «revisión» o «descartar» / filas «directo» de la muestra. Falsos positivos = filas «revisión» que Lean marcó «directo» / filas «revisión» de la muestra.
  - Tiempo: unas 2 horas.
- **DA-A3 — RESUELTA (Lean, 2026-11-22): Lean y el auditor de calidad.**
  - **Lean** etiqueta las 250 filas. **El auditor** etiqueta una submuestra común de **50** (28 directo · 16 revisión · 6 descartado, con la misma proporción), **por separado y a ciegas**: no ve la decisión del sistema ni las etiquetas de Lean. Cada uno trabaja en su propia planilla en `output/aceptacion/`.
  - **Tiene que ser otra persona.** Si la cuenta de auditor la usa Lean, el acuerdo no mide nada y el cierre lo declara.
  - **Guía de etiquetado:** antes de empezar, AF-L3 escribe `docs/fuentes/GUIA_ETIQUETADO_AF.md` con qué es «directo», qué es «revisión» (con la lista de motivos) y qué es «descartar», con 1 ejemplo enmascarado de cada uno. Los dos usan la misma guía.
  - **Acuerdo:** κ de Cohen sobre las 50 filas (tres clases).
    - **κ ≥ 0,61** (acuerdo sustancial): la guía es clara y valen las etiquetas de Lean.
    - **κ < 0,61:** las filas en desacuerdo se discuten, se ajusta la guía, se registra el cambio y se vuelve a etiquetar la submuestra **una sola vez**. Si sigue por debajo, G3 queda **en rojo** por ambigüedad del criterio, no del sistema.
  - **Verdad de referencia** para G3: las etiquetas de Lean, con los desacuerdos de la submuestra resueltos por consenso y documentados.
  - **Salida:** `af_g3_kappa.json` (κ, IC, matriz de acuerdo, n desacuerdos y su resolución), sin PII.
  - **Tiempo:** Lean unas 2 horas; el auditor unos 30 minutos.

## PROMPT PARA CHAT 2 (uno por loop)
```
/gira-desarrollar
Ejecuta SOLO el loop AF-L<n> de docs/cierres/PLAN_ACEPTACION_FLUJO.md.
- Agentes con model "sonnet" o "haiku", nunca Opus.
- No empieces si faltan las precondiciones P1–P4.
- La planilla de G3 va fuera del repositorio (output/aceptacion/), sin la decisión del sistema visible.
- G5 y G6 solo en la DW tmpfs, con pg_dump previo.
- Cierra con CIERRE_AF_L<n>.md y commit af(L<n>).
```
