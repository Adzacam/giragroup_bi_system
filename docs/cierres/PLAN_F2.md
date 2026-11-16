# PLAN F2 — 15 de noviembre de 2026 (v2: con B-8 y B-9 aprobados por Lean)
Objetivo de la fase: implementar B-8 y B-9 y responder P-1 a P-5 con cifras del sistema vigente (beto-v2, flags en 0, lote congelado), sin congelar todavía. El congelamiento es F3.
Entrada: CIERRE_F1Z.md (F1 completa); rama base = `beto-integracion` `4c8bd69`.

**Decisión de Lean (2026-11-15):** «Las B-8 y B-9». Las dos entran en F2.

**Por qué este orden:** B-9 cambia lo que se escribe en el DW (`log_inconsistencias` y el identificador de homónimos). Por eso va **primero**, y la base de medición `dw_f2` se construye **con B-9 ya aplicado**. Lo que se mida antes de B-9 no vale para P-2, P-5 ni B-6.

**Base de medición única de F2 (`dw_f2`):** una corrida del pipeline completo con beto-v2 y el código de B-9, sobre el lote `aafde8ad…db60` en tmpfs. Todas las consultas de F2 se hacen sobre ella, nunca sobre la DW viva.

**Nota:** B-3, B-4 y B-5 se midieron en F0 con beto-v1 y su corpus. Como D3-bis = v2, se repiten.

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| F2-9 | **B-9:** (a) todos los descartes por reglas de calidad quedan registrados en `log_inconsistencias`; (b) identificador estable para homónimos sin CI | dev-alta | — | F2-3, F2-4, F2-7, F2-8 | (1) Antes de codificar, inventario de los puntos de descarte en `pipeline/normalization/` (regla, archivo:línea, si hoy registra). (2) Cada descarte escribe una fila con `regla_origen`, archivo, fila de origen y valor; la suma de filas por regla = descartes contados en memoria en la misma corrida (Δ = 0). (3) El identificador de homónimos es determinista (mismo lote → mismo id en 2 corridas) y **no cambia el estado C**: no fusiona, no crea perfiles, no toca A/B, y BETO no lo asigna. (4) **Invariantes:** siguen 50 tablas + 9 vistas `bi` (solo columnas nuevas o filas en tablas existentes, con una migración numerada); cascada y umbrales sin cambios. Si hace falta una tabla nueva, se detiene y reporta. (5) Con flags en 0, todas las tablas salvo `log_inconsistencias` y las columnas nuevas tienen los mismos conteos que D3B v2, y la bandeja sigue en 680/19, salvo que la diferencia se explique caso por caso. (6) Pruebas nuevas en `tests/f2/` | `f2_b9_inventario_descartes.json`, `f2_b9_resultado.json` |
| F2-8 | **B-8:** intervalo de predicción formal de Holt-Winters | dev-media | — | F2-9, F2-3, F2-4 | (1) Modelo sin cambios: amortiguado, m = 12, hold-out de 6 meses (invariante). Las métricas del punto (MAE, MAPE o las que tenga hoy) dan Δ = 0. (2) Intervalo del 80 % y del 95 % con método explícito: simulación del modelo de espacio de estados de `statsmodels` (`simulate`, ≥ 1.000 repeticiones, semilla fija) o la fórmula analítica, dejando escrita la elegida. (3) Cobertura empírica en el hold-out: cuántos de los 6 meses caen dentro de cada intervalo. (4) Expuesto en `forecast_service` / `forecast_schemas` sin romper el contrato actual (campos nuevos opcionales). (5) Pruebas nuevas | `f2_b8_intervalos.json` |
| F2-7 | Fe de erratas de CIERRE_F1Z | dev-baja | — | todas | La sección «Erratas (F2)» corrige §4: A-3/A-4 están registrados como revisión declarada por Lean (`f1_revision_humana/`), con 3 limitaciones; solo el top-1 sigue en N/D | — |
| F2-3 | **B-3 / P-3:** gold_510 con v2 y el evaluador de F0 | dev-media | — | F2-9, F2-8, F2-4 | (1) Mismo evaluador que `f0_b3_ablacion.csv` (`evaluator_sha256 555c085d…`), semilla 42, v2: TP/FP/FN, P, R y F1, estrictos y relajados, modos A/B/C. (2) Control: el mismo evaluador con v1 reproduce `f0_b3_ablacion.csv` (Δ = 0). (3) Datos del Gráfico 3.1: soporte 510 por tipo y explicación del 503. (4) Se anota la diferencia con `seqeval` (D3B), sin mezclar cifras | `f2_b3_ablacion_v2.csv`, `f2_b3_ablacion_v2.json` |
| F2-4 | **B-4 / P-4:** corpus de v2 | dev-baja | — | todas | Solo archivos existentes: separación → aumento (`f1_d3b_validez.json`), personas train–dev v2 0/1, fuga en 4 niveles = 0, sha256 del corpus (`f1_corpus_auditoria.json`), anotación del gold_510 (`f0_b4_auditoria.json`), sin inventar procedencia | `f2_b4_corpus_v2.json` |
| F2-0 | Montar `dw_f2` con B-9 | dev-baja | F2-9 | F2-8 | (1) Lote verificado antes y después. (2) Comparación de huellas con D3B v2 (`85420985…e682`): solo difieren `log_inconsistencias` y las columnas de B-9, y la diferencia coincide con `f2_b9_resultado.json`. (3) Bandeja y KPI-18 iguales a D3B v2 (680/19, 36), o con la diferencia explicada por F2-9. (4) Una segunda corrida da la misma huella | `f2_base.json` + `.huella.json` |
| F2-1 | **B-1 / P-1:** pruebas por suite | dev-baja | F2-9, F2-8 | F2-2, F2-5 | (1) Tabla por carpeta de `tests/` (incluida `f2/`): passed, skipped, xfailed y failed; failed = 0. (2) Los 7 o más xfail con test, RF/RNF y motivo (`reason=`). (3) Los skip con su motivo. (4) Cobertura total ≥ 70 % y por módulo. Se marca provisional para F3 | `f2_b1_pruebas.json`, `f2_b1_pruebas.txt` |
| F2-2 | **B-2 / P-2:** KPI-12…15 y 17…20 | dev-media | F2-0 | F2-1, F2-5 | (1) Los 8 KPI para 2025 y para el total, según `bi.ref_kpi`; API `/api/v1/cmi/scorecard` = SQL (Δ = 0). (2) Por KPI: si los hechos con `requiere_revision = true` entran o no (SQL de la vista) y el valor sin esos hechos, como dato informativo. (3) NULL con su causa | `f2_b2_kpi.json`, `f2_b2_consultas.sql` |
| F2-5 | **B-5 / P-5:** OLS anual 2025 frente al KPI-03 | dev-baja | F2-0 | F2-2 | Mismo `f0_b5_consultas.sql` (`33d6443b…`) sobre `dw_f2`: observado, ajustado y Δ %; comparación con F0 (12.907.977,61 frente a 12.747.275,66 Bs, −1,24 %) y la causa de la diferencia; etiqueta «solo descriptiva» | `f2_b5_2025.json` |
| F2-6 | **B-6:** KLM sobre la bandeja actual | dev-media | F2-0, F2-1, F2-3 | — | (1) `medir_flujo_repetido.py` N = 3 sobre `dw_f2` (`FLUJO_CACHE_VACIA=1`) + `agregar_flujo_repetido.py`, sin cambiar los parámetros. (2) KLM con y sin W, media y DE, desglose por acción. (3) Coincide con `f1_d3b_klm.json` (736,6 / 216,6 s) o se explica la diferencia. (4) Tabla «documento 188/37, 490,5 s frente a actual». Provisional para F3 | `f2_b6_klm.json`, `f2_b6_flujo/` |

## Comandos exactos
- **F2-9:** `grep -rn` de los descartes en `pipeline/normalization/` (por ejemplo `person_resolver.py`: `es_etiqueta_likert`, `parece_nombre_propio`, `es_correo`, `PER_SIN_FORMA_NOMBRE`) → inventario → implementación → migración numerada en `backend/scripts/migrations/` (solo `ALTER TABLE … ADD COLUMN` si hace falta) → `pytest tests/f2 -q` sobre tmpfs.
- **F2-8:** modificar `backend/services/forecast_service.py` y `backend/schemas/forecast_schemas.py` → `pytest tests/sprint4/test_forecasting.py tests/f2 -q`.
- **F2-0:** `scripts/aislada_tmpfs.sh up` (TMPFS_PORT=55632) → `dw_f2` desde `dw_vacio` **con la migración de B-9 aplicada** → corrida v2 con caché vacía (ejecutor de D3B) → `huella_dw.py` → `comparar_huellas.py` contra `f1_d3b_corrida_v2_vacia_r1.json.huella.json`. Se deja montada hasta F2-6.
- **F2-1:** `pytest --cov --cov-report=term -rxs --junitxml=<scratchpad>/f2.xml` sobre tmpfs con `giragroup_db`; la URL solo en el entorno.
- **F2-2:** SQL de solo lectura sobre `dw_f2` y una api de prueba apuntada a `dw_f2`, nunca la api compartida.
- **F2-3:** el script y el evaluador de F0 (`f0_b3_procedencia.json`), primero con `--modelo output/f1/beto_local_respaldo` y después con `pipeline/semantic/beto_local`.
- **F2-5:** `psql -f docs/mediciones/f0_b5_consultas.sql` sobre `dw_f2`.
- **F2-6:** `FLUJO_CACHE_VACIA=1 python scripts/medir_flujo_repetido.py docs/mediciones/f2_b6_flujo 3` y `python scripts/agregar_flujo_repetido.py docs/mediciones/f2_b6_flujo docs/mediciones/f2_b6_klm.json`.

## Riesgos y control
- **B-9 y los invariantes:** no se crean tablas ni se tocan la cascada, los umbrales ni los estados A/B/C. El identificador de homónimos es un dato, no una fusión. Cualquier choque con un invariante detiene F2-9 y pasa a decisión de Lean.
- **B-9 cambia la huella de referencia:** la huella de `dw_f2` es la nueva referencia de F2 y la base para F3. La propuesta de Z-3 (excluir `registro_origen_id`, redondear flotantes, `PYTHONHASHSEED=0`) **no** se aplica aquí; sigue siendo de F3.
- **B-8 sin cambiar el modelo:** si las métricas del punto cambian, se detiene.
- **No congelar:** las cifras son «F2, provisional»; nada entra en `fuente_verdad_tesis.md`.
- **Tiempos (F2-6):** se miden solos, sin pytest ni inferencia BETO en paralelo y con la carga registrada.
- **No tocar la DW viva:** sigue con el código anterior a B-9 hasta el rebuild del cierre.

## DECISIONES PENDIENTES PARA LEAN (no se ejecutan hasta que responda)
1. **Tratamiento de `requiere_revision` en los KPI**, según lo que muestre F2-2: mantenerlo y documentarlo, o excluir esos hechos (cambio en las vistas `bi`, en una fase propia).
2. **Aplicar la migración de B-9 a la DW viva:** el cierre reconstruye pipeline y api, pero aplicar la migración a `giragroup_db` (:5434) espera tu sí explícito.
3. **B-10 residual** (sin cambios).

## Al cerrar
pytest + cobertura · rebuild de `pipeline` y `api` (cambia el código con B-8 y B-9) **solo si** el código nuevo funciona contra una base sin la migración de B-9 (prueba de humo en tmpfs sin la migración: `/health` sano y una carga sin errores); si no funciona, el rebuild espera la decisión 2 y se deja escrito en el CIERRE · `docker compose ps` con 9 servicios · `aislada_tmpfs.sh down` · commit `feat(f2): B-8 intervalos HW, B-9 bitácora de descartes y homónimos; respuestas P-1 a P-5` · `CIERRE_F2.md`, con «Respuestas P-1 a P-5», cada una con su cifra y su archivo.

## PROMPT PARA CHAT 2
```
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F2.md (v2). Lean aprobó B-8 y B-9.
- Primera ola en paralelo: F2-9 (dev-alta), F2-8 (dev-media), F2-3 (dev-media), F2-4 (dev-baja) y F2-7 (dev-baja).
- Después: F2-0 (tras F2-9), F2-1 (tras F2-9 y F2-8), F2-2 y F2-5 (tras F2-0) y, al final, F2-6, solo.
- B-9: sin tablas nuevas, sin tocar la cascada, los umbrales ni los estados A/B/C; si choca con un invariante, detente y repórtalo.
- B-8: el modelo HW no cambia (amortiguado, m=12, hold-out 6); las métricas del punto con Δ=0.
- Toda la medición va sobre dw_f2 (tmpfs, lote aafde8ad…db60, beto-v2 + B-9). Nunca la DW viva.
- No apliques la migración de B-9 a giragroup_db (:5434): es una decisión pendiente de Lean.
- Cifras «F2, provisional»; nada entra en fuente_verdad_tesis.md.
Al terminar: pytest con cobertura, rebuild de pipeline y api solo si el código nuevo funciona sin la migración
(si no, no reconstruyas y déjalo escrito), commit y docs/cierres/CIERRE_F2.md
con las respuestas P-1 a P-5, cada una con su archivo de evidencia.
```
