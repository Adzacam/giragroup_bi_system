# CIERRE F1D3B — 15 de noviembre de 2026

Comparación lado a lado de **`beto-v1`** (`output/f1/beto_local_respaldo/`, sha256 `5966dde3fa4adccacb8ed74c62c991a6bf140c2b4d67598a05a1c35e67ec9543`) frente a **`beto-v2`** (`pipeline/semantic/beto_local/`, sha256 `9ff7fb9d914aca9eaa0618d9603d869a30808d9218369aef7b12dd92362b5f92`) en calidad sin pipeline (**D-A**), validez del reentrenamiento (**D-B**), efecto operativo en pipeline completo + KLM (**D-C**) y tabla unificada (**D-T**), sobre la rama `beto-integracion` (base `ce8ff46`).

**Integridad de defaults y entorno:**
- No se modificó ningún default: `BETO_MODELO_VERSION=beto-v2`, `docker-compose.yml`, `confianza_service.py`, `pipeline/semantic/beto_local/` (sha256 verificado antes y después: `9ff7fb9d914aca9eaa0618d9603d869a30808d9218369aef7b12dd92362b5f92`), `data/`, ni la DW viva (`giragroup_db` `:5434`).
- Lote congelado verificado antes y después de D-C: `aafde8adc246af13c4eeb9ffbf766eda4348cfb6e855860d0bf00bcd24cbdb60` (`docs/mediciones/f0_lote_manifest.json`).
- No se ejecutaron `D3-bis` ni `B-10`. Ningún veredicto ni estimación de esta fase se presenta como etiqueta humana.

---

## 1. Tabla única de comparación (D-T: `beto-v1` vs `beto-v2` vs `Δ`)

| Bloque | Métrica | `beto-v1` | `beto-v2` | Δ (`v2 - v1`) | Fuente |
|---|---|---|---|---|---|
| D-A (Calidad sin pipeline) | `gold_510` Modo A (strict) F1 [P / R \| TP/FP/FN] | 1.0000 [P=1.0000, R=1.0000 \| 510/0/0] | 1.0000 [P=1.0000, R=1.0000 \| 510/0/0] | 0 | `f1_d3b_calidad_v1_gold.json` / `f1_d3b_calidad_v2_gold.json` (`f1_d3b_calidad.json`) |
| D-A (Calidad sin pipeline) | `gold_510` Modo A (relaxed) F1 [P / R \| TP/FP/FN] | 1.0000 [P=1.0000, R=1.0000 \| 510/0/0] | 1.0000 [P=1.0000, R=1.0000 \| 510/0/0] | 0 | `f1_d3b_calidad_v1_gold.json` / `f1_d3b_calidad_v2_gold.json` (`f1_d3b_calidad.json`) |
| D-A (Calidad sin pipeline) | `gold_510` Modo B (strict) F1 [P / R \| TP/FP/FN] | 1.0000 [P=1.0000, R=1.0000 \| 510/0/0] | 1.0000 [P=1.0000, R=1.0000 \| 510/0/0] | 0 | `f1_d3b_calidad_v1_gold.json` / `f1_d3b_calidad_v2_gold.json` (`f1_d3b_calidad.json`) |
| D-A (Calidad sin pipeline) | `gold_510` Modo B (relaxed) F1 [P / R \| TP/FP/FN] | 1.0000 [P=1.0000, R=1.0000 \| 510/0/0] | 1.0000 [P=1.0000, R=1.0000 \| 510/0/0] | 0 | `f1_d3b_calidad_v1_gold.json` / `f1_d3b_calidad_v2_gold.json` (`f1_d3b_calidad.json`) |
| D-A (Calidad sin pipeline) | `gold_510` Modo C (strict) F1 [P / R \| TP/FP/FN] | 0.9757 [P=0.9691, R=0.9824 \| 501/16/9] | 0.9796 [P=0.9729, R=0.9863 \| 503/14/7] | +0.0039 | `f1_d3b_calidad_v1_gold.json` / `f1_d3b_calidad_v2_gold.json` (`f1_d3b_calidad.json`) |
| D-A (Calidad sin pipeline) | `gold_510` Modo C (relaxed) F1 [P / R \| TP/FP/FN] | 0.9912 [P=0.9864, R=0.9961 \| 508/7/2] | 0.9942 [P=0.9884, R=1.0000 \| 510/6/0] | +0.003 | `f1_d3b_calidad_v1_gold.json` / `f1_d3b_calidad_v2_gold.json` (`f1_d3b_calidad.json`) |
| D-A (Calidad sin pipeline) | `layouts_5` Modo A (strict) F1 [P / R \| TP/FP/FN] | 0.2619 [P=0.9167, R=0.1528 \| 11/1/61] | 0.2619 [P=0.9167, R=0.1528 \| 11/1/61] | 0 | `f1_d3b_calidad_v1_layouts.json` / `f1_d3b_calidad_v2_layouts.json` (`f1_d3b_calidad.json`) |
| D-A (Calidad sin pipeline) | `layouts_5` Modo A (relaxed) F1 [P / R \| TP/FP/FN] | 0.2857 [P=1.0000, R=0.1667 \| 12/0/60] | 0.2857 [P=1.0000, R=0.1667 \| 12/0/60] | 0 | `f1_d3b_calidad_v1_layouts.json` / `f1_d3b_calidad_v2_layouts.json` (`f1_d3b_calidad.json`) |
| D-A (Calidad sin pipeline) | `layouts_5` Modo B (strict) F1 [P / R \| TP/FP/FN] | 0.3158 [P=0.3000, R=0.3333 \| 24/56/48] | 0.4026 [P=0.3780, R=0.4306 \| 31/51/41] | +0.0868 | `f1_d3b_calidad_v1_layouts.json` / `f1_d3b_calidad_v2_layouts.json` (`f1_d3b_calidad.json`) |
| D-A (Calidad sin pipeline) | `layouts_5` Modo B (relaxed) F1 [P / R \| TP/FP/FN] | 0.7164 [P=0.7742, R=0.6667 \| 48/14/24] | 0.7376 [P=0.7536, R=0.7222 \| 52/17/20] | +0.0212 | `f1_d3b_calidad_v1_layouts.json` / `f1_d3b_calidad_v2_layouts.json` (`f1_d3b_calidad.json`) |
| D-A (Calidad sin pipeline) | `layouts_5` Modo C (strict) F1 [P / R \| TP/FP/FN] | 0.2468 [P=0.2317, R=0.2639 \| 19/63/53] | 0.3312 [P=0.3059, R=0.3611 \| 26/59/46] | +0.0845 | `f1_d3b_calidad_v1_layouts.json` / `f1_d3b_calidad_v2_layouts.json` (`f1_d3b_calidad.json`) |
| D-A (Calidad sin pipeline) | `layouts_5` Modo C (relaxed) F1 [P / R \| TP/FP/FN] | 0.6923 [P=0.7759, R=0.6250 \| 45/13/27] | 0.7206 [P=0.7656, R=0.6806 \| 49/15/23] | +0.0283 | `f1_d3b_calidad_v1_layouts.json` / `f1_d3b_calidad_v2_layouts.json` (`f1_d3b_calidad.json`) |
| D-C (Pipeline operativo) | Líneas leídas por BETO | 12992 | 12992 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `carga_fila_origen` | 15978 | 15978 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `dim_docente` | 673 | 673 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `dim_estudiante` | 14939 | 14978 | +39 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `dim_modulo` | 3796 | 3796 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `dim_tiempo` | 2230 | 2230 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `fact_costo_programa` | 1320 | 1371 | +51 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `fact_evaluacion_docente` | 75126 | 75073 | -53 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `fact_marketing` | 299 | 299 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `fact_rendimiento_academico` | 1393 | 1392 | -1 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `fact_rentabilidad` | 95 | 91 | -4 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `fact_situacion_financiera` | 725 | 725 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `fact_techo_convenio` | 1 | 1 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `log_inconsistencias` | 11 | 10 | -1 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas `stg_entidad_no_resuelta` | 5099 | 5076 | -23 | `f1_d3b_operativo.json` |
| D-C (Bandeja) | Bandeja: casos totales | 182 | 680 | +498 | `f1_d3b_operativo.json` |
| D-C (Bandeja) | Bandeja: grupos totales | 12 | 19 | +7 | `f1_d3b_operativo.json` |
| D-C (Bandeja) | Bandeja: grupos manuales | 7 | 14 | +7 | `f1_d3b_operativo.json` |
| D-C (Bandeja) | Bandeja: casos manuales | 59 | 47 | -12 | `f1_d3b_operativo.json` |
| D-C (KPIs) | `KPI-10` | `None` | `None` | igual | `f1_d3b_operativo.json` |
| D-C (KPIs) | `KPI-11` | `None` | `None` | igual | `f1_d3b_operativo.json` |
| D-C (KPIs) | `KPI-18` | 59.0 | 36.0 | -23.0 | `f1_d3b_operativo.json` |
| D-C (Tiempos) | Tiempo máquina caché vacía (media ± DE, s, n=3) | 848.09 ± 71.61 | 864.28 ± 80.28 | +16.19 | `f1_d3b_operativo.json` |
| D-C (Tiempos) | Tiempo pared caché vacía (media ± DE, s, n=3) | 853.36 ± 70.77 | 869.27 ± 80.42 | +15.92 | `f1_d3b_operativo.json` |
| D-C (Tiempos) | Tiempo máquina caché llena (media ± DE, s, n=3) | 267.98 ± 18.86 | 281.56 ± 6.90 | +13.58 | `f1_d3b_operativo.json` |
| D-C (Tiempos) | Tiempo pared caché llena (media ± DE, s, n=3) | 272.95 ± 18.50 | 286.66 ± 6.90 | +13.71 | `f1_d3b_operativo.json` |
| D-C (KLM y Total) | `klm_estimado_d3b` con espera W=10s (s) | 903.3 | 736.6 | -166.7 | `f1_d3b_klm.json` |
| D-C (KLM y Total) | `klm_estimado_d3b` sin espera W=0s (s) | 263.3 | 216.6 | -46.7 | `f1_d3b_klm.json` |
| D-C (KLM y Total) | Tiempo total (máquina vacía + KLM W=10s) (s) | 1751.4 | 1600.9 | -150.5 | `f1_d3b_klm.json` |
| D-C (KLM y Total) | Tiempo total (máquina vacía + KLM W=0s) (s) | 1111.4 | 1080.9 | -30.5 | `f1_d3b_klm.json` |

**Control de D-A (`f1_d3b_calidad.json`):**
- Mismo `scripts/ablacion_beto.py` (sha256 `114bcdf8090421ccf355c12b7818b19718227709da0abe060724a8aa04799554`), `--semilla 42`, `BETO_INT8=0`, `max_tokens=128`, `torch==2.13.0+cpu`, `transformers==5.14.1`.
- Soporte de `gold_510` (`7dce0bec4dd3a60b94a7e6e5a48df29a6844fc93d28375697aa04f1b9a3d51a5`): **510** entidades (`130 PER_ESTUDIANTE`, `180 PROGRAMA`, `150 MODULO`, `50 PER_DOCENTE`, todas visibles dentro de 128 tokens; según `f0_b3_conteos.json`, el 503 histórico provenía de una matriz 4×4 hardcodeada donde `PROGRAMA` sumaba 173).
- Control contra `docs/mediciones/f0_b3_ablacion.csv`: en Modos A y B (`gold_510`), Δ = 0 (`F1 = 1.0`). En Modo C (`gold_510`): en relajado `TP=508, FP=7, FN=2` (`ΔF1 = -0.00002` por redondeo a 4 decimales); en estricto `FP=16 vs 14` (`F1=0.975657 vs 0.977561`, `ΔF1 = -0.001904`) porque `f0_b3_ablacion.csv` fue generado con el evaluador auxiliar de F0 (`evaluator_sha256 555c085d...`, IOB2 estricto explícito), mientras que `scripts/ablacion_beto.py` usa `seqeval` en modo por defecto. Como `v1` y `v2` se midieron con el mismo `scripts/ablacion_beto.py`, la comparación `v1 vs v2` es homogénea.

---

## 2. Validez del reentrenamiento de `beto-v2` (D-B, `docs/mediciones/f1_d3b_validez.json`)

- **Orden aumento / separación (`scripts/preparar_corpus_robusto.py`):** `separa_antes_de_aumentar = True`. Primero particiona por claves de persona en `particionar_por_persona` (l.101-110, llamado en l.334) y luego ejecuta `generar_muestras` por separado sobre `est_tr/doc_tr` y `est_dv/doc_dv` (l.336-344).
- **Prueba empírica `train vs dev` (personas compartidas, spans / IOB2):**
  - `beto-v1`: **273** (spans) / **143** (IOB2) — generado antes de la corrección de partición por persona.
  - `beto-v2`: **0** (spans) / **1** (IOB2, debido a tokenización con punto en abreviaturas como `M . Sc .` al reconstruir desde IOB2).
- **Fuga de 4 niveles × 2 trains (`f1_d3b_validez.json`):**

| Cruce | a) Oración exacta | b) Texto normalizado | c) Variantes (plantilla / Jaccard≥0.8) | d) Personas compartidas |
|---|---:|---:|---:|---:|
| `v1_train_vs_gold_510` | 0 | 0 | 0 | 0 |
| `v1_train_vs_layouts_5` | 0 | 0 | 0 | 0 |
| `v2_train_vs_gold_510` | 0 | 0 | 0 | 0 |
| `v2_train_vs_layouts_5` | 0 | 0 | 0 | 0 |

---

## 3. Huellas del DW y consistencia operativa (D-C y D-T)

- **Consistencia interna (6 corridas por versión en `tmpfs`):**
  - `beto-v1`: las 6 corridas (3 vacías + 3 llenas) son **idénticas entre sí** (`huella_sha256 = 9cfbffebb790d9b4653558a94ee2293bf5b1294458f1f9e8cc91110d65a3032f`). Frente a `f1_off.json.huella.json`, `bandeja` y `kpis` son idénticos; difiere únicamente el `md5` de `stg_entidad_no_resuelta` (mismas 5099 filas).
  - `beto-v2`: las 6 corridas (3 vacías + 3 llenas) son **idénticas entre sí** (`huella_sha256 = 85420985c49895fa96b91feb7fd391ac6db8a59b0a2f2a61213bf405c76ee682`). Frente a `f1_validacion_vacia_r1.json.huella.json`, `bandeja` (`680/19`, `firma_sha256 = 22bd64640929883070af7854b5cad000a907d6aea00f906b7e77fd220e635875`) y `kpis` son idénticos; difiere el `md5` de `fact_situacion_financiera` (mismas 725 filas) y `stg_entidad_no_resuelta` (mismas 5076 filas).
- **Tablas que difieren entre `beto-v1` y `beto-v2` (8 tablas):**
  `dim_estudiante` (`14939 → 14978`, `+39`), `fact_costo_programa` (`1320 → 1371`, `+51`), `fact_evaluacion_docente` (`75126 → 75073`, `-53`), `fact_rendimiento_academico` (`1393 → 1392`, `-1`), `fact_rentabilidad` (`95 → 91`, `-4`), `fact_situacion_financiera` (`725 → 725`, `0`, distinto `md5`), `log_inconsistencias` (`11 → 10`, `-1`), `stg_entidad_no_resuelta` (`5099 → 5076`, `-23`).
- **Explicación de `182/12 → 680/19` (`docs/mediciones/f1_r2_bandeja_diff.csv`):**
  - Cuadre: `182 + 569 altas − 71 bajas = 680` (`+498` neto).
  - **Altas (`569`):** `HECHO_EN_REVISION = 539`, `BAJA_CONFIANZA_IA = 30`. Concentradas en `Base centralizada Académica ARCA (1).xlsx` (`543`), `_BBDD_ ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx` (`18`), `BD Cobranzas.xlsx` (`4`), `EJECUTADO VS META.xlsx` (`4`). Por grupo: `grupo-eeb97aecd3` (`APROBAR`, `+509`), `grupo-3d630e02eb` (`APROBAR`, `+15`), `grupo-fce10f6266` (`MANUAL`, `+11`), `grupo-a370459559` (`MANUAL`, `+10`), `grupo-3a4ebffc23` (`MANUAL`, `+8`), `grupo-89de0bd808` (`APROBAR`, `+4`), más 7 grupos `MANUAL` de 1 a 3 casos (`12` en total).
  - **Bajas (`71`):** `BAJA_CONFIANZA_IA = 53`, `HECHO_EN_REVISION = 18`. Concentradas en `BD Egresos.xlsx` (`51`), `Base centralizada Académica ARCA (1).xlsx` (`18`), `BD Cobranzas.xlsx` (`1`), `_BBDD_ ANTIGUO...` (`1`).

---

## 4. Pruebas (`pytest --cov`)

- Archivo: `docs/mediciones/f1_d3b_pruebas.txt` (ejecutado contra `127.0.0.1:55632/dw_base` en `beto_pg_tmpfs`, posteriormente desmontado con `aislada_tmpfs.sh down`).
- Resultado: **`799 passed, 6 failed, 11 skipped, 7 xfailed`** · Cobertura total: **`70%`** (`14555` sentencias, `4382` sin cubrir).
- Los 6 fallos corresponden exclusivamente al entorno `tmpfs` (sin modificar código ni tests): `test_database_url_segura_y_configurada` (espera literal `giragroup_db` en `SQLALCHEMY_DATABASE_URL`), 4 tests de `tests/sprint4/test_forecasting.py` y `test_loop4_validacion_estricta_contratos`.

---

## 5. Decisiones pendientes para Lean (no ejecutadas)

1. **D3-bis:** con `docs/mediciones/f1_d3b_comparacion.md` en la mano, decidir si se mantiene `beto-v2` o se vuelve a `beto-v1` (respaldo + `BETO_MODELO_VERSION=beto-v1` + rebuild de pipeline y api).
2. **B-10 residual** (sin cambios).
