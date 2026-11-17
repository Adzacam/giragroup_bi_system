# PLAN F3U-B — 2026-11-17
Objetivo de la fase: terminar lo que F3U dejó sin hacer (la carga completa de los 10 libros, el cuadre por hoja y el resumen), esta vez sin perder resultados, y rehacer el diseño de PLANIFICACION con las decisiones de Lean. En esta fase **no se cambia código**: la implementación va en PLAN_F3V.
Entrada: CIERRE previo leído = `CIERRE_F3U.md` (cierre parcial); rama base = `beto-integracion` `1db9e56`. Evidencias de partida: `f3u_planificacion_inventario.json`, `f3u_planificacion_diseno.md` (todavía sin commit), `f3s_cobertura_por_archivo.json`.

## Qué falló en F3U y cómo se evita
- **Se perdió el clon tmpfs `f3u_completo` antes de guardar los resultados.** Hay dos causas posibles, y el plan cubre ambas:
  - a) `aislada_tmpfs.sh up` ejecuta `docker rm -f beto_pg_tmpfs`. Si otro chat o una segunda corrida ejecuta `up`, el contenedor se borra.
  - b) El tmpfs tiene un tope de `size=3g`. En el recorte, Evaluación Docente ya genera 71.458 hechos; con el libro completo puede pasar de 3 GB y PostgreSQL se cae.
- **Cómo se evita:**
  - Se usa un contenedor propio (`beto_pg_f3ub`, puerto 55633) que ningún otro proceso usa.
  - El tmpfs es más grande, si la RAM alcanza.
  - El uso del disco se vigila durante la carga.
  - El avance se guarda **documento por documento** en `docs/mediciones/`.
  - Al terminar, se hace un `pg_dump` del clon a `output/f3ub/` (no versionado).
- **El undécimo archivo:** en `uploads/data/` hay 11 archivos, y `PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S) 1.xlsx` (05-nov, sha `05afce82…f2da`) **no es parte del lote congelado**. Se excluye con una lista explícita de los 10 archivos, y se comprueba que el sha conjunto da `aafde8ad…db60`.

## Decisiones de Lean (17-nov, por escrito en el chat 1)
1. **PLANIFICACION va con la opción B.** Se agregan `fact_planificacion_programa`, la vista `bi.vw_planificacion_ejecucion_mensual` y el KPI-23 (programas iniciados frente a planificados). El invariante pasa de «50 tablas / 9 hechos / 22 KPI» a **51 / 10 / 23**. Esto se implementa en F3V, y chat 3 lo pasa al documento solo con las cifras congeladas.
2. **Las metas de «Informe Gestión» se cargan.** Son valores escritos a mano, no fórmulas:
   - la meta mensual de programas regulares para 2025 y 2026 (por ejemplo, enero de 2025 = 827.437);
   - el ingreso proyectado de Techos (89.000 al mes en 2026, de febrero a noviembre);
   - el OKR «RC1.1.1 Abrir 12 programas» (12 por mes).
   
   Antes de cargarlas, hay que compararlas con las metas de `EJECUTADO VS META.xlsx` para no tener dos metas el mismo mes.
3. **«Inicio Confirmado» cuenta como iniciado,** igual que «En curso» y «Finalizo». El 71,56 % de U-4 queda anulado: usaba solo los estados de `Programas Notificados`.
4. **P/EJECUTADO** (análisis del chat 1, lo confirma B-4):
   - Es lo **gastado en publicidad digital** del programa, y `P/ASIGNADO` es lo asignado para esa publicidad. Lo que indica:
     - está junto a `LEADS` y a las columnas `ADs` y `Días Activos`;
     - va de 61 a 392, mientras que lo que se cobra por un programa va de 5.000 a 135.000;
     - la mediana de P/EJECUTADO / P/ASIGNADO es 0,80;
     - la correlación con los interesados (leads) es 0,36, con los días de campaña 0,41 y con los inscritos 0,15.
   - Hay solo 48 filas, de julio, agosto y octubre de 2025.
   - Se guarda en el hecho nuevo como `pauta_ejecutada` y `pauta_asignada`. **No lleva KPI y no se suma a los ingresos.**

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| B-0 | **Preparar el entorno aislado.** RAM libre del host (`docker info`, memoria de WSL). Contenedor `beto_pg_f3ub` en 127.0.0.1:55633 con los mismos pasos que `aislada_tmpfs.sh up` y luego `vacio`, pero con `--tmpfs ...size=8g` si hay ≥ 12 GB libres (si no, `size=6g` y avisar). Aplicar la migración `016_b9_descartes_y_homonimos.sql` a `dw_vacio` **del contenedor nuevo** (no a la DW viva). Luego `clon f3u_completo` | dev-baja | — | B-4 | 1) Comando exacto de `docker run` en el JSON (sin contraseñas); 2) `dw_vacio` con 0 filas en hechos, staging, logs, `lote`, `dim_origen_documental` y `carga_fila_origen` (consulta de S-1); 3) la migración 016 aplicada en `f3u_completo` (comprobar las columnas o tablas que crea); 4) sha del lote calculado con la **lista explícita de los 10 archivos** = `aafde8ad…db60`, y el archivo `... 1.xlsx` en una lista `excluidos`; 5) conteo de `lote` y `dim_origen_documental` de la DW viva (:5434) antes de empezar | `f3ub_preparacion.json` |
| B-1 | **Carga de los 10 libros completos** en `f3u_completo`, uno por uno, con el código de `1db9e56` y BETO en False. Nunca por el gateway: se usa un proceso con `DATABASE_URL` hacia 127.0.0.1:55633/f3u_completo, igual que en T-1. **Después de cada documento**, se agrega una línea a `f3ub_avance.jsonl` con el archivo, `id_documento`, estado, segundos, conteo por tabla de hechos y staging, logs, `carga_fila_origen` y `df -h` del tmpfs. Cada 10 min, `df -h`: si pasa del 85 %, se detiene y se avisa | dev-baja | B-0 | B-4 | 1) 10/10 líneas en `f3ub_avance.jsonl` con estado final de consolidación (no solo HTTP 200); 2) conteo final por tabla; 3) sha del lote, del modelo (`9ff7fb9d…5f92`) y del snapshot (`14D45F5A…E2EB`) iguales antes y después; 4) `lote` y `dim_origen_documental` de la DW viva sin cambios; 5) `pg_dump -Fc` de `f3u_completo` en `output/f3ub/f3u_completo.dump`, con su sha en el JSON | `f3ub_avance.jsonl`, `f3ub_completo.json` |
| B-2 | **Cuadre por archivo y por hoja** con `scripts/f3s_cobertura_por_archivo.py`, sin cambiarle la lógica; solo se le pasa la base `f3u_completo` y la carpeta de origen con los 10 archivos. Para cada hoja: filas de origen, categoría, cargadas por tabla, staging, log, ruido por motivo, `sin_explicar`, fechas mínima y máxima por hecho | dev-baja | B-1 | B-4 | 1) 10 archivos y 100 % de las hojas; 2) `origen = cargadas + staging + log + ruido + sin_explicar` en cada fila; 3) cada `sin_explicar > 0` con 10 ejemplos y la regla (archivo:línea), marcado como `regla_correcta`, `defecto` (D-U#) o `requiere_revision`; 4) se corre dos veces con el mismo md5; 5) los defectos ya conocidos (D-A2, D-A4, D-A4b, D-A5, D-A8a, D-A9, D-T1) se enlazan, sin crear un D-U# duplicado | `f3ub_cobertura_por_hoja.json`, `.csv`, `f3ub_defectos.md` |
| B-3 | **Diseño B definitivo** (solo documento). Reescribe `f3u_planificacion_diseno.md` como `f3ub_planificacion_diseno.md` con las decisiones 1 a 4. Incluye: a) DDL propuesto en texto de `fact_planificacion_programa` (columnas, tipos, `id_modulo` nullable, `id_tiempo_plan`, FK, UNIQUE por clave de fila origen), como migración `017_…` y `V016__…`; b) dónde van las metas de Informe Gestión (tabla existente, primero `dim_meta`, o el hecho nuevo), con su clave mes + tipo y la conciliación de B-4; c) fórmula del KPI-23 con «Inicio Confirmado» como iniciado, cómo se trata el estado vacío y la meta OKR de 12 por mes, más su fila en `bi.ref_kpi` (meta y bandas 0,85 / 0,60); d) columnas de `bi.vw_planificacion_ejecucion_mensual`; e) archivos que F3V va a tocar (extractor, loader, consolidación, kpi_service, router, frontend del CMI) y pruebas nuevas; f) secciones de la SFV y del documento que cambian (51 / 10 / 23, RF o HU afectadas) | dev-media | B-4 | B-1, B-2 | 1) Cada hoja `dato_fuente` con su destino y su mapeo columna → columna; 2) `P/EJECUTADO` y `P/ASIGNADO` → `pauta_ejecutada` y `pauta_asignada`, sin KPI; 3) KPI-23 con fórmula SQL **escrita, no calculada** (la cifra sale en F3V); 4) lista cerrada de invariantes que cambian; 5) estimación de filas de B-4 | `f3ub_planificacion_diseno.md` |
| B-4 | **Adenda del inventario** (lectura con openpyxl, sin pasar por el sistema): a) «Informe Gestión»: cada celda escrita a mano (no fórmula) con hoja, celda, rótulo de fila y columna, año, mes y valor; las metas de 2025 y 2026, Techos 89.000 y el OKR 12; b) **comparación mes a mes** de esas metas con `EJECUTADO VS META.xlsx` (META POR CATEGORIA y META AAAA, por categoría), con la diferencia absoluta y relativa; c) confirmar el análisis de P/EJECUTADO con las 48 filas (rango, mediana, cociente con P/ASIGNADO, correlaciones); d) recontar los estados de las 18 hojas mensuales y de `Programas Notificados`, con «Inicio Confirmado» por separado; e) «Dashboard Programas»: comprobar que es una tabla dinámica (pivot cache) y no un dato fuente | dev-baja | — | B-0, B-1, B-2 | 1) Lista completa de celdas escritas a mano de Informe Gestión, con su conteo; 2) tabla de conciliación con una fila por mes, de 2025 a 2026; 3) estadísticas de P/EJECUTADO que repiten o corrigen las del chat 1; 4) conteo de estados por hoja | `f3ub_planificacion_adenda.json` |
| B-5 | **Resumen para Lean**: tabla de 10 archivos (cuadre del libro completo), defectos D-U# con su impacto (KPI, sección de la SFV, figura), el diseño B de B-3 y la conciliación de metas de B-4 | dev-baja | B-2, B-3 | — | 1) 10 filas sin `sin_explicar` sin clasificar; 2) cada defecto enlaza a su evidencia; 3) **0 cambios** en `backend/`, `pipeline/`, `frontend/`, `db/`, `scripts/` (`git diff --stat` igual que al empezar) | `f3ub_resumen.md` |

## Comandos exactos por tarea
- B-0: `TMPFS_NAME=beto_pg_f3ub TMPFS_PORT=55633 sh scripts/aislada_tmpfs.sh up` **no sirve como está**, porque fija `size=3g`. Se copian sus pasos a mano, con el mismo `docker run` pero `size=8g` (o 6g), y luego los de `vacio` con `PSQL="docker exec beto_pg_f3ub psql …"`. **No se modifica `aislada_tmpfs.sh`.** Todos los comandos ejecutados quedan en `f3ub_preparacion.json`.
- Durante B-1, **nadie corre `up` ni `down`** de ningún contenedor tmpfs. Al terminar B-2 (y no antes), se borra el contenedor con `docker rm -f beto_pg_f3ub`.
- B-1 con `run_in_background`. Si el equipo puede suspenderse, se pide mantenerlo despierto antes de empezar.
- Consultas: solo `SELECT`, con `PYTHONIOENCODING=utf-8`. La DW viva (`giragroup_db` :5434) solo se lee para los conteos de control.
- B-4: `openpyxl.load_workbook(..., data_only=False)` para distinguir los valores escritos de las fórmulas, y `data_only=True` para los valores calculados.

## Riesgos y control
- **La carga completa no reemplaza ninguna cifra congelada.** RNF-03, la huella y los KPI siguen saliendo de f3_base y del snapshot. Esta fase no toca `docs/fuente_verdad_tesis.md`.
- **Si la carga pasa de 3 h o se cae:** se conserva `f3ub_avance.jsonl` con lo que alcanzó a cargar, se avisa a Lean y no se reintenta en un bucle.
- **Haiku:** si una causa no queda clara, se marca `requiere_revision`. El cierre no da por cumplido ningún criterio que no tenga su archivo.
- **Cambios locales de Lean** (`backend/routers/powerbi.py`, `frontend/`, PLAN_FRONT_V2.md, CIERRE_FRONT_V2.md): no se tocan ni se agregan.

## DECISIONES PENDIENTES PARA LEAN (al terminar B-5; con ellas se escribe PLAN_F3V)
1. Por cada defecto D-U#: ¿se corrige en F3V o queda como limitación?
2. Si B-4 muestra que las metas de Informe Gestión y las de EJECUTADO VS META no coinciden en algún mes, ¿cuál manda para el KPI-02/03/13/14? Recomendación previa: EJECUTADO VS META sigue mandando en esos KPI, y las de Informe Gestión se usan para la vista de planificación.
3. Meta del KPI-23: ¿el OKR de 12 aperturas por mes o un porcentaje de iniciados sobre planificados?
4. Siguen pendientes de F3U para la remedición final de F3V: el encabezado de la SFV (commit y huella), B-7 con n = 3 en «Alto rendimiento» y citar solo las corridas limpias.

## Al cerrar
Sin pytest (no hay cambios de código) · sin rebuild · un commit con rutas explícitas: `docs/mediciones/f3u_planificacion_inventario.json`, `docs/mediciones/f3u_planificacion_diseno.md`, `docs/mediciones/f3ub_*`, `docs/cierres/PLAN_F3U.md`, `docs/cierres/CIERRE_F3U.md`, `docs/cierres/PLAN_F3U_B.md`, `docs/cierres/CIERRE_F3U_B.md`. Mensaje: `docs(f3u-b): cobertura con libros completos y diseño B de PLANIFICACION`. **No se anuncia «F3 congelado».**

## PROMPT PARA CHAT 2
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F3U_B.md (base `beto-integracion` 1db9e56). Este chat corre en Haiku 5.5; B-3 va con dev-media.
Es una fase **sin cambios de código**. En F3U se perdió el clon tmpfs antes de guardar los resultados; por eso esta vez:
- usa un contenedor propio `beto_pg_f3ub` (puerto 55633, tmpfs de 8 GB si la RAM alcanza);
- guarda el avance documento por documento en `docs/mediciones/f3ub_avance.jsonl`;
- haz un dump del clon al terminar;
- no corras `up` ni `down` de ningún tmpfs mientras carga.

Carga solo los 10 archivos del lote, con una lista explícita: el archivo `... (INICIOS Y OKR`S) 1.xlsx` queda fuera. El sha tiene que dar `aafde8ad…db60`.
Orden: B-0 y B-4 en paralelo → B-1 (en segundo plano) → B-2; B-3 (dev-media) después de B-4 → B-5.
Las decisiones de Lean ya están en el plan: opción B, cargar las metas de Informe Gestión, «Inicio Confirmado» = iniciado y P/EJECUTADO = pauta, sin KPI.
No modifiques backend/, pipeline/, frontend/, db/, scripts/ ni docs/fuente_verdad_tesis.md. Si una causa no queda clara, márcala `requiere_revision`.
No des por cumplido ningún criterio sin su archivo en docs/mediciones/. Commit solo con las rutas de «Al cerrar». Después espera mis decisiones.
