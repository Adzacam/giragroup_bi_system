# PLAN F2R — 15 de noviembre de 2026
Objetivo de la fase: cerrar los huecos de F2 antes del congelamiento. B-9 incompleto, KLM sin explicar, P-5 con definiciones mezcladas, KPI-15 en NULL sin diagnóstico, código que falla sin la migración y tiempos inestables.
Entrada: CIERRE_F2.md (commit `5994e88`); rama base = `beto-integracion` `5994e88`.

## Revisión de CIERRE_F2 por el chat 1 (huecos detectados)
| # | Hallazgo | Evidencia |
|---|---|---|
| H-1 | **B-9 (a) no cambia nada en el flujo medido.** `log_inconsistencias` sigue con 10 filas (`CI_NOMBRE_VARIANTE` 1 y `CONFLICTO_FUENTES` 9). Las 5.040 filas `RUIDO/DESCARTADO` de `stg_entidad_no_resuelta` ya existían antes de B-9 (5.076 en D3B). El registro por línea se añadió en `backend/routers/pipeline.py`, que no es el flujo DataOps que se mide. Los subtotales se guardan solo en la metadata del bloque, no en la BD. El criterio «Δ = 0 por regla entre memoria y BD» no se demostró con una corrida | `f2_b9_resultado.json`, `f2_b9_inventario_descartes.json` |
| H-2 | **Sin la migración, la carga se rompe.** `confirm-dw-insert` falla con `UndefinedColumn id_homonimo`, por eso no se reconstruyeron pipeline ni api. Además, el número `015` choca con `migrations_opcionales/015_cache_beto_entidades.sql`, que en F1 se cita como «migración 015» | CIERRE_F2 §Smoke test |
| H-3 | **El KLM no cuadra con D3B y no se explicó.** Da 815,5 / 295,5 s frente a 736,6 / 216,6 s, con la misma bandeja 680/19. La diferencia es +78,9 s con y sin W, lo que apunta a un cambio en la regla de mapeo o en los casos manuales, no en W | `f2_b6_klm.json`, `f1_d3b_klm.json` |
| H-4 | **Tiempos inestables.** La máquina dio 877 / 873 / 1.203 s (media 984,6 ± 189,5 s, por encima de 900 s). En la misma configuración, F1-V había dado 640 s. Sin protocolo controlado, B-7 no es defendible | `f2_b6_klm.json`, `f1_validacion_resumen.json` |
| H-5 | **P-5 mezcla definiciones.** F0 comparó 12.907.977,61 frente a 12.747.275,66 Bs; F2 compara la OLS sobre PROGRAMAS (11,85 M) y aparte el KPI-03, que suma PROGRAMAS + TECHOS_CERRADOS (12,84 M). No consta que se usara el mismo SQL de F0 (`33d6443b…`) ni la causa de la diferencia | `f2_b5_2025.json`, `f0_b5_2025.json` |
| H-6 | **KPI-15 en NULL**, porque las 725 filas tienen `estado_cartera = 'Vigente'`. Sin comprobar contra la fuente (BD Cobranzas) no se sabe si es la realidad o un error de mapeo | `f2_b2_kpi.json` |
| H-7 | **Árbol sucio.** `PLAN_F2.md` está sin commit. Hay trabajo de frontend V2 sin commit (`PLAN_FRONT_V2` / `CIERRE_FRONT_V2`, `frontend/src/v2/`, `App.jsx`, `Navbar.jsx`) que no pertenece a esta línea de trabajo | `git status` |

Lo que está bien y no se toca: P-1 (812 / 0 / 11 / 7, 70 %), P-3 (control v1 con Δ = 0; v2 en modo C estricto 0,9805 y relajado 0,9942), P-4, B-8 (puntos con Δ = 0), F2-0 (680/19, KPI-18 = 36, conteos iguales a D3B).

## Tareas
| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| G-1 | Migración compatible y renumerada | dev-media | — | G-3, G-4, G-5 | (1) `015_b9_descartes_y_homonimos.sql` pasa a llamarse `016_b9_descartes_y_homonimos.sql`; si `run_migrations.py` registra nombres aplicados, se comprueba que `dw_vacio` y la DW viva no tienen la 015 B-9 registrada. (2) `dw_loader.py` y `pipeline.py` detectan una sola vez (`information_schema.columns`) si existen `id_homonimo` y `regla_origen`; si faltan, cargan sin esas columnas y avisan en el log. (3) Prueba de humo en tmpfs **sin** la migración: `confirm-dw-insert` da 200 y los conteos son iguales a D3B v2. **Con** la migración: los mismos resultados que en `dw_f2`. (4) Pruebas nuevas en `tests/f2/` para los dos casos | `f2r_g1_compatibilidad.json` |
| G-2 | B-9 completo en el flujo medido | dev-alta | G-1 | G-3, G-4, G-5 | (1) Tabla regla → dónde se descarta → dónde queda en la BD, para el flujo DataOps (`consolidacion.py`) **y** para `pipeline.py`. (2) Los subtotales descartados dejan una fila por línea en `log_inconsistencias` (`regla_origen = 'SUBTOTAL'`), no solo en la metadata. (3) Corrida en tmpfs con el lote: por regla, las filas en la BD = los descartes contados en memoria, Δ = 0, en los dos flujos. (4) Fuera de `log_inconsistencias`, todas las tablas tienen los mismos conteos que `f2_base.json`; bandeja 680/19 y los 22 KPI iguales a `f2_b2_kpi.json`. (5) Equivalencia con la limitación 12 de `fuente_verdad_tesis.md` (A-24: 509 descartes sin bitácora): cuántos quedan sin bitácora ahora, con el número | `f2r_g2_b9_completo.json`, `f2r_base.json` + `.huella.json` (nueva referencia) |
| G-3 | Conciliar KLM D3B frente a F2 | dev-media | — | G-1, G-4, G-5 | (1) Eventos de los dos archivos lado a lado, grupo por grupo (acción y casos). (2) La diferencia de +78,9 s atribuida a eventos o reglas concretos, con las cuentas cuadradas a 0,1 s. (3) Qué mapeo es el correcto según la pantalla real de la bandeja (`accion_grupo` del endpoint) y el KLM recalculado con ese mapeo sobre la bandeja de `f2r_base` | `f2r_g3_klm_conciliacion.json` |
| G-4 | Conciliar P-5 | dev-baja | — | G-1, G-3, G-5 | (1) `f0_b5_consultas.sql` sin cambios (sha256 `33d6443b…`) sobre `dw_f2` o `f2r_base`, con la misma serie de F0. (2) Tabla F0 (snapshot, v1) frente a F2 (lote, v2) en la misma definición: observado, ajustado y Δ %. (3) Causa de la diferencia (snapshot frente a lote, filas por año). (4) La relación entre la serie OLS y el KPI-03, con las dos definiciones escritas. (5) Etiqueta «solo descriptiva» | `f2r_g4_b5_conciliacion.json` |
| G-5 | Diagnóstico del KPI-15 | dev-media | — | G-1, G-3, G-4 | (1) Valores distintos de estado o mora en la fuente del lote (BD Cobranzas y relacionados), con sus conteos. (2) Mapeo fuente → `estado_cartera` en el código (archivo:línea). (3) Veredicto: «0 en mora es real» o «defecto de mapeo, con N filas afectadas». **Solo diagnóstico:** si es defecto, se propone el arreglo sin aplicarlo, porque cambia el DW (decisión 3) | `f2r_g5_kpi15.json` |
| G-6 | Protocolo de tiempos para B-7 | dev-alta | G-2 | — (solo) | (1) Desglose por etapa de las corridas de F1-V (640 s), D3B (864 s) y F2-6 (877 / 873 / 1.203 s), sacado de sus JSON y `.meta.json`: dónde se va la diferencia. (2) Causa del pico de 1.203 s (carga, CPU, contenedores en marcha, térmica), con datos de `docker stats`/meta, no supuestos. (3) Protocolo escrito para F3: contenedores permitidos, plan de energía, calentamiento, orden, criterio para descartar una corrida y cómo se reporta. (4) Una corrida de prueba con el protocolo, marcada **no final** | `f2r_g6_tiempos.json`, `f2r_g6_protocolo_b7.md` |
| G-7 | Limpieza y cierre | dev-baja | G-1…G-6 | — | (1) `PLAN_F2.md` y `PLAN_F2R.md` con commit en `beto-integracion`. (2) **Frontend V2 fuera de F3 (decisión de Lean):** se mueve a la rama `front-v2`, cortada desde el commit de F2R, con un commit que contiene solo `frontend/index.html`, `frontend/src/App.jsx`, `frontend/src/components/layout/Navbar.jsx`, `frontend/src/v2/`, `docs/cierres/PLAN_FRONT_V2.md`, `docs/cierres/CIERRE_FRONT_V2.md` y `docs/flujo_web_pestanas_y_tipografia.md`. Después se vuelve a `beto-integracion` y `git status` no muestra nada de eso. Sin push y sin rebuild del frontend. (3) Rebuild de pipeline y api (posible gracias a G-1), `/health` sano y 9 servicios en `docker compose ps`; la DW viva sin la migración, salvo un sí de Lean | `f2r_servicios.txt` |

## Comandos exactos
- **G-1:** `git mv backend/scripts/migrations/015_b9_descartes_y_homonimos.sql backend/scripts/migrations/016_b9_descartes_y_homonimos.sql`. Prueba de humo: `scripts/aislada_tmpfs.sh up` → base nueva desde `dw_vacio` sin la 016 → corrida → `confirm-dw-insert`; repetir con la 016.
- **G-2:** corrida del lote en tmpfs (ejecutor de D3B, v2, caché vacía) → `huella_dw.py` → `comparar_huellas.py` contra `f2_base.json.huella.json`; los conteos en memoria salen del log estructurado de la misma corrida.
- **G-3:** solo lectura de `f1_d3b_klm.json` y `f2_b6_klm.json` y `GET /api/v1/dataops/review-tray/grupos` sobre `f2r_base`.
- **G-4:** `psql -f docs/mediciones/f0_b5_consultas.sql` sobre `f2r_base` (o `dw_f2`), y comparar con `f0_b5_2025.json`.
- **G-5:** lectura de los archivos del lote (sin modificarlos) y `grep -rn estado_cartera backend pipeline`.
- **G-6:** sin pytest, sin inferencia en paralelo y sin el frontend dev server; `docker stats --no-stream` antes, durante y después.

## Riesgos y control
- **Nueva referencia:** G-2 genera `f2r_base`, que sustituye a `f2_base` como referencia para F3. Solo puede diferir en `log_inconsistencias`.
- **La DW viva no se toca:** ni migración ni carga. G-1 hace que el rebuild sea seguro sin la migración.
- **G-5 no corrige:** un cambio de mapeo altera hechos y KPI, y lo decide Lean.
- **G-6 no da la cifra final:** la cifra de RNF-03 es B-7 en F3, con el protocolo de G-6.
- **No mezclar con el frontend V2:** no se hace commit ni rebuild del frontend en esta fase.

## DECISIONES PENDIENTES PARA LEAN (no se ejecutan hasta que responda)
1. ~~Frontend V2~~ **Resuelta (2026-11-15):** «Dejarlo fuera de F3». Se mueve a la rama `front-v2` (G-7).
2. **Aplicar la migración 016 a la DW viva** (`giragroup_db`), con un `pg_dump` previo. Recomendado antes de F3, para que el sistema vivo sea igual al medido.
3. **KPI-15**, según G-5: si es un defecto de mapeo, ¿se corrige antes de F3? Cambia hechos y KPI.
4. **`requiere_revision` en los KPI:** F2-2 muestra un efecto pequeño (nota media 87,03 con revisión frente a 86,91 sin ella; 632 de 1.392 filas). Recomiendo mantenerlo como está y documentarlo.
5. **B-10 residual.**

## Al cerrar
pytest + cobertura (incluye `tests/f2/`) · rebuild de pipeline y api · commit `fix(f2r): B-9 completo, migración 016 compatible, conciliaciones KLM/P-5, KPI-15 y protocolo de tiempos` · `CIERRE_F2R.md`. Después viene F3 (congelamiento).

## PROMPT PARA CHAT 2
```
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F2R.md.
- Primera ola, en paralelo: G-1 (dev-media), G-3 (dev-media), G-4 (dev-baja) y G-5 (dev-media).
- Después: G-2 (dev-alta, tras G-1), G-6 (dev-alta, tras G-2 y sola: sin pytest, sin inferencia, sin frontend dev) y, al final, G-7.
- Solo se mide sobre tmpfs con el lote aafde8ad…db60 y beto-v2. No toques la DW viva ni le apliques la migración.
- G-5 solo diagnostica; G-6 no da la cifra final de RNF-03.
- Frontend V2 fuera de F3 (Lean: «Dejarlo fuera de F3»): en G-7, después del commit de F2R, muévelo a la rama
  front-v2 con su propio commit (solo los archivos listados en G-7), vuelve a beto-integracion y deja el árbol limpio.
  No hagas push ni reconstruyas el frontend.
Al terminar: pytest con cobertura, rebuild de pipeline y api, commit y docs/cierres/CIERRE_F2R.md
con la tabla H-1…H-7 marcada como resuelta o pendiente, cada fila con su archivo.
```
