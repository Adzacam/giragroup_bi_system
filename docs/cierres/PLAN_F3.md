# PLAN F3 — 15 de noviembre de 2026
Objetivo de la fase: congelar el sistema. Con los cambios que Lean aprobó, hacer la medición final B-7, la suite final, los KPI finales y la huella del DW, y dejar `docs/fuente_verdad_tesis.md` marcado **CONGELADO**.
Entrada: CIERRE_F2R.md; rama base = `beto-integracion` `b7c5006`.

## Revisión de CIERRE_F2R (chat 1)
| # | Lo que dice el cierre | Verificación | Qué pasa a F3 |
|---|---|---|---|
| H-1 | B-9 completo, 6.226 filas en `log_inconsistencias`, Δ = 0 en el resto | Cuadra: 5.455 + 761 + 10 = 6.226 (`f2r_g2_b9_completo.json`) | Base de comparación: `f2r_base` |
| H-2 | Migración 016 y código tolerante | `backend/core/esquema_opcional.py` consulta `information_schema` una vez por engine (`lru_cache`) | — |
| H-3 | KLM cuadrado (736,6 / 216,6 s) | Δ = 0 frente a D3B con la fórmula canónica | El KLM final se calcula sobre la bandeja de F3 |
| **H-4** | «Resuelta» | **Incompleta.** La corrida de prueba con B-9 completo dio **1.313,0 s** solo de máquina (`f2r_g6_tiempos.json`), por encima de 900 s y también de 1.200 s (20 min). `consolidacion_s` pasó de 627,6 s (D3B) a 1.162,4 s. En `consolidacion.py::_registrar_descarte_ruido`, cada una de las 5.455 líneas hace `db.add(LogInconsistencia)` y después un `SELECT` sobre `stg_entidad_no_resuelta` que provoca autoflush. Esa corrida no registra los recursos del equipo | **F3-1** (aprobado por Lean: optimizar antes de B-7) |
| H-5 | P-5 conciliado | Sí, misma definición y mismo sql (33d6443b…) | Valores finales en F3-7 |
| H-6 | KPI-15: defecto de mapeo | Propuesta en `f2r_g5_kpi15.json` | **F3-2** (aprobado por Lean: corregir) |
| H-7 | Árbol limpio, `front-v2` aparte | La rama `front-v2` (`eae8fc8`) se cortó desde `5994e88` y no desde `b7c5006`. No afecta, porque solo contiene frontend. `CLAUDE.md`, `.claude/agents/` y `.claude/skills/` siguen sin versionar (las skills ya se perdieron una vez) | F3-0 |
| — | «819 passed, 70 %» | **No hay archivo en `docs/mediciones/`** (no existe `f2r_pruebas.txt`), así que esa cifra no cuenta | La suite final se corre en F3-6 |

## Decisiones de Lean (15-nov-2026, respondidas en el chat 1)
1. B-9 lento: **optimizar antes de B-7**, con las mismas filas y huella Δ = 0.
2. KPI-15: **corregir en F3**, antes de congelar.
3. Huella: **aplicar huella v2** (propuesta de Z-3).
4. DW viva: **aplicar la migración 016 al final de F3**, con `pg_dump` previo fuera de Git y sin recargar.
5. Sin cambio: `requiere_revision` entra en los KPI y se documenta (F2R, decisión 4 recomendada); B-10 residual (reescribir el historial o rotar la clave) **no se ejecuta**.

## Tareas
| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| F3-0 | Versionar las reglas de los chats | dev-baja | — | F3-1, F3-3 | (1) Búsqueda de secretos en `CLAUDE.md`, `.claude/agents/` y `.claude/skills/` (`password`, `postgres://`, `postgresql://`, `token`, `secret`, `api_key`, `:5434@`): **0 coincidencias con valores**. Si hay alguna, se detiene y se reporta. (2) Commit `chore(f3): versionar CLAUDE.md y skills/agents`. (3) `git status` sin `??` en esas rutas | `f3_0_secretos.txt` |
| F3-1 | B-9 sin coste de tiempo | dev-alta | — | F3-0, F3-3 | (1) `_registrar_descarte_ruido`, y el registro de `SUBTOTAL` si tiene el mismo patrón, dejan de hacer flush por línea: acumular y `add_all`/inserción en bloque al cierre de la hoja, comprobar «ya registrada» con un conjunto en memoria o un `no_autoflush`. **Misma semántica**: mismas filas, mismos campos y misma deduplicación. (2) Una corrida en tmpfs (`dw_vacio` + 016, caché vacía, `beto-v2`, 4 flags en False) contra `f2r_base`: **Δ = 0** en las filas y el md5 de todas las tablas (con la huella v2 si F3-3 ya terminó; si no, con la actual), `log_inconsistencias` por `tipo_regla`/`regla_origen` idéntico (5.455 / 761 / 10), bandeja 680/19 con firma `22bd6464…5875` y KPI-18 = 36. (3) `consolidacion_s` de esa corrida ≤ 750 s, con los recursos del equipo registrados; si no se llega, se reporta la cifra y el perfil (`cProfile` de la consolidación), sin medir B-7. (4) Prueba nueva en `tests/f2/` que compruebe que N descartes producen N filas y que reejecutar no duplica | `f3_1_b9_rendimiento.json` |
| F3-2 | KPI-15: mapeo de cartera | dev-media | F3-1 (mismo archivo `consolidacion.py`) | F3-3 | (1) Se leen `TIPO DE CARTERA`, `DIAS DE MORA` y `RANGO MORA` según la propuesta de `f2r_g5_kpi15.json`. Los valores de `estado_cartera` se toman **del dominio que ya existe** (CHECK, dimensión o los valores usados por `bi.vw_*` / la fórmula de KPI-15), sin crear valores nuevos. El dominio comprobado se escribe en el JSON. (2) Corrida en tmpfs frente a la salida de F3-1: solo cambian `fact_situacion_financiera.estado_cartera` y KPI-15. **Todas las demás tablas y KPI con Δ = 0.** (3) Conteo por `estado_cartera` cuadrado con la fuente: filas en mora e incobrables contra las 85 / 5 de `f2r_g5_kpi15.json`, explicando la diferencia de granularidad entre 272 filas de origen y 725 hechos. (4) KPI-15 no NULL, con el mismo valor en `/api/v1/cmi/scorecard` y en el SQL (Δ = 0). (5) Pruebas unitarias del mapeo (incobrable, mora por días, mora por rango, vigente, nulos) | `f3_2_kpi15.json` |
| F3-3 | Huella v2 | dev-media | — | F3-0, F3-1 | (1) Script nuevo `scripts/huella_dw_v2.py` (`huella_dw.py` no se toca): excluye `registro_origen_id`, redondea a 4 decimales `score_fuzzy`, `nivel_confianza` y `nivel_confianza_ia`, y anota `PYTHONHASHSEED=0` en el `.meta`. Columnas excluidas y redondeadas listadas en el propio JSON de salida. (2) Reproducibilidad: dos corridas del mismo código en **dos sesiones de contenedor distintas** (con reinicio de `pipeline` y `api` entre ellas) → **md5 idéntico en las 50 tablas**. (3) Las `.huella.json` anteriores no se modifican (`git diff` vacío en `docs/mediciones/*.huella.json`) | `f3_3_huella_v2.json` |
| F3-4 | Rebuild y base F3 | dev-baja | F3-1, F3-2, F3-3 | — | (1) Rebuild de `pipeline` y `api`, 9 servicios arriba, `/health` 200 en los dos. (2) Una corrida en tmpfs → `f3_base` con huella v2. (3) Diferencias frente a `f2r_base`: **solo** las que declara F3-2. (4) Inventario: 50 tablas + 9 vistas `bi`, 22 filas en `bi.ref_kpi`, 9 servicios | `f3_base.json`, `f3_base.json.huella.json`, `f3_4_inventario.json`, `f3_servicios.txt` |
| F3-5 | **B-7: medición final del ciclo (RNF-03)** | dev-alta | F3-4 | **ninguna** (corre sola) | (1) Protocolo `f2r_g6_protocolo_b7.md` completo: sin otros procesos pesados, alto rendimiento, `docker stats` y `psutil` cada 5 s, 30 s de reposo entre corridas. (2) Lote `aafde8ad…db60` verificado antes y después; `beto-v2` (sha `9ff7fb9d…5f92`); 4 flags en False. (3) **3 corridas con caché vacía y 3 con caché llena**, todas con huella v2 = `f3_base` (0 diferencias), misma bandeja y mismos KPI. (4) Por modo: media, DE muestral (n − 1), mínimo y máximo de `tiempo_maquina_s`, con desglose por etapa (carga, lectura BETO, consolidación). (5) Los dos números de RNF-03 que aprobó Lean: (a) solo máquina; (b) máquina (media con caché vacía) + KLM con W = 10 s y W = 0 s, usando `klm()` de `scripts/agregar_flujo_repetido.py` sobre la bandeja de `f3_base`. Veredicto frente a 900 s y 1.200 s para cada uno. (6) Una corrida descartada solo si cumple el criterio 5 del protocolo y queda escrita con sus recursos; como máximo 2 repeticiones, y si no, se detiene y se reporta | `f3_b7_corridas.json`, `f3_b7_corrida_<vacia\|llena>_r<i>.json` (+ `.huella.json`, `.recursos.json`), `f3_b7_klm.json`, `f3_b7_rnf03.json` |
| F3-6 | Suite final (B-1 sobre la suite final) | dev-baja | F3-5 (no corre durante B-7) | F3-7, F3-8 | (1) `pytest --cov` en tmpfs: **0 failed**, cobertura ≥ 70 %. (2) Totales por suite (carpeta), lista de xfail con su RF/RNF y motivo, y motivo de cada skipped, como en `f2_b1_pruebas.json` | `f3_pruebas.txt`, `f3_pruebas.json` |
| F3-7 | KPI y pronóstico finales | dev-media | F3-4 (puede ir después de F3-5) | F3-6, F3-8 | (1) Los 22 KPI sobre `f3_base` (2025, global y 2026 cuando aplique): scorecard frente a SQL con **Δ = 0** en todos los no nulos; nulos con su causa. (2) KPI con y sin `requiere_revision` (decisión 5), con los mismos campos que `f2_b2_kpi.json`. (3) Holt-Winters (m = 12, hold-out de 6) e intervalos 80/95 % de B-8: métricas puntuales con Δ = 0 frente a F2 (el pronóstico no depende de cartera). (4) OLS mensual N = 40 y OLS anual descriptiva con `f0_b5_consultas.sql` (33d6443b…) | `f3_kpi.json`, `f3_pronostico.json` |
| F3-8 | DW viva: migración 016 | dev-baja | F3-5 | F3-6, F3-7 | (1) `pg_dump -Fc` de `giragroup_db` (:5434) a `output/f3/` (fuera de Git), con su sha256 y tamaño. (2) Aplicar `016_b9_descartes_y_homonimos.sql` y registrarla en `schema_migrations`. (3) Antes y después: filas por tabla idénticas (no se recarga), columnas `regla_origen` e `id_homonimo` presentes y `/health` 200. (4) El snapshot `snapshot_dw_20261110_1201` no se toca (sha del dump sin cambios) | `f3_8_dw_viva.json` |
| F3-9 | `fuente_verdad_tesis.md` CONGELADO | dev-media | F3-5, F3-6, F3-7, F3-8 | — | (1) Encabezado nuevo: «**CONGELADO** — F3», fecha, commit, sha del lote `aafde8ad…`, sha del modelo `beto-v2`, sha de la huella v2 de `f3_base`, flags. El snapshot del 10-nov queda como referencia histórica. (2) En las secciones A–I, cada cifra que cambia lleva valor nuevo, valor anterior y archivo de `docs/mediciones/` (con la ruta JSON). Entran como mínimo las filas de la §7 del plan maestro (pruebas, cobertura, KLM, líneas y casos del ciclo, tiempo), P-1 a P-5, KPI-15, B-8, B-9 (limitaciones 12 y 13) y RNF-03 con los dos números. (3) `f3_sfv_trazabilidad.json`: una entrada por cifra nueva (ID, valor, archivo, ruta) y un script `scripts/verificar_sfv.py` que lee cada archivo y compara: **0 discrepancias, 0 cifras sin fuente**. (4) Formato boliviano (coma decimal, punto de miles). (5) Las cifras que no salen de una medición quedan **N/D** con el motivo | `f3_sfv_trazabilidad.json`, `f3_sfv_verificacion.txt` |

## Comandos exactos
- **tmpfs:** `TMPFS_PORT=55632 scripts/aislada_tmpfs.sh up` al empezar cada tarea con corridas y `down` al terminarla. La URL de conexión se pasa solo por el entorno (`TEST_DATABASE_URL` / `DATABASE_URL`), nunca en archivos.
- **Corridas:** el mismo ejecutor de F2R (`f2r_base`), sobre `dw_vacio` + migración 016, con `BETO_MODELO_VERSION=beto-v2` y los 4 flags en False. Huella con `PYTHONHASHSEED=0 python scripts/huella_dw_v2.py …` (desde F3-3; antes, `scripts/huella_dw.py`). Comparación con `scripts/comparar_huellas.py`.
- **F3-1:** `python -m cProfile -o output/f3/consolidacion.prof …` solo si no se alcanza el criterio (3).
- **F3-5:** antes, `docker stats --no-stream` y la lista de procesos guardados en `f3_b7_corridas.json`. Durante B-7 no se ejecuta pytest, vite, entrenamiento ni otra sesión del chat 2.
- **F3-6:** `pytest --cov --cov-report=term > docs/mediciones/f3_pruebas.txt` con la base tmpfs `giragroup_db`.
- **F3-8:** `docker exec giragroup_db pg_dump -Fc -U "$POSTGRES_USER" giragroup_db > output/f3/giragroup_db_pre016.dump`, con el usuario tomado del entorno. Después `psql … -f backend/scripts/migrations/016_b9_descartes_y_homonimos.sql`.

## Riesgos y control
- **RNF-03 puede no cumplirse.** Si con F3-1 la media de máquina con caché vacía supera 900 s, se reporta tal cual, sin más optimizaciones dentro de B-7. Con KLM y W = 10 s, la suma probablemente pasa de 1.200 s (D3B: 864 + 736,6). Ese resultado se reporta, no se esconde.
- **F3-2 cambia hechos.** Por eso va antes de `f3_base` y de B-7, y su Δ se limita a una columna y un KPI. Si toca algo más, se detiene.
- **Un único lote congelado y un único estado del código para B-7.** Cualquier cambio de código después de F3-4 invalida `f3_base` y B-7.
- **Una sola sesión del chat 2.** En F2R hubo dos sesiones sobre el mismo checkout y la misma tmpfs. En F3 solo corre una.
- **DW viva:** solo la toca F3-8, con el dump antes. El snapshot es de solo lectura.
- No se toca el docx; nada de credenciales en archivos versionados (F3-0 lo comprueba).

## DECISIONES PENDIENTES PARA LEAN
Ninguna bloquea F3 (las 4 están respondidas arriba). Quedan abiertas, sin ejecutar: B-10 residual (rotar la clave de PostgreSQL o reescribir el historial) y el merge de `beto-integracion` a `main` después del congelamiento.

## Al cerrar
pytest + cobertura (F3-6) · rebuild de `pipeline` y `api` (F3-4; el frontend no se reconstruye) · commit `F3: congelamiento` · `CIERRE_F3.md` con la tabla de tareas, los dos números de RNF-03 y el sha de la huella congelada. **Después, el chat 1 revisa el CIERRE_F3 y avisa «F3 congelado» al chat 3.** El chat 2 no lo anuncia.

## PROMPT PARA CHAT 2
```
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F3.md (congelamiento). Decisiones de Lean del 15-nov-2026, ya tomadas:
optimizar B-9 antes de B-7; corregir KPI-15; huella v2; migración 016 en la DW viva al final con pg_dump previo.
- Orden: F3-0 (dev-baja), F3-1 (dev-alta) y F3-3 (dev-media) en paralelo → F3-2 (dev-media, después de F3-1:
  mismo archivo) → F3-4 (dev-baja) → F3-5 B-7 (dev-alta, SOLO, nada más corriendo en la máquina) →
  F3-6 (dev-baja), F3-7 (dev-media) y F3-8 (dev-baja) en paralelo → F3-9 (dev-media).
- F3-1 no cambia la semántica: Δ = 0 contra f2r_base en todas las tablas. Si consolidacion_s > 750 s, detente y reporta.
- F3-2: solo cambian estado_cartera y KPI-15; valores del dominio que ya existe.
- F3-3: script nuevo huella_dw_v2.py; no modifiques huella_dw.py ni las .huella.json anteriores.
- B-7 con el protocolo f2r_g6_protocolo_b7.md, 3 vacías + 3 llenas, recursos registrados, y los dos números de RNF-03.
- Ningún cambio de código después de F3-4. Ninguna cifra en fuente_verdad_tesis.md sin archivo en docs/mediciones/.
- No toques el docx ni el snapshot. No ejecutes B-10. Sin push. Una sola sesión.
Al terminar: commit "F3: congelamiento" y docs/cierres/CIERRE_F3.md. No anuncies «F3 congelado»: lo hace el chat 1.
```
