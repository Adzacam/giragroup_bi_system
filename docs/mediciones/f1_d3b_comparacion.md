# F1D3B — Comparación lado a lado: `beto-v1` vs `beto-v2`

## 1. Tabla única de comparación (D-A y D-C)

| Bloque | Métrica | `beto-v1` | `beto-v2` | Δ (`v2 - v1`) | Fuente |
|---|---|---|---|---|---|
| D-A (Calidad sin pipeline) | gold_510 Modo A (strict) F1 [P / R | TP/FP/FN] | 1.0000 [P=1.0000, R=1.0000 | 510/0/0] | 1.0000 [P=1.0000, R=1.0000 | 510/0/0] | 0 | `f1_d3b_calidad_v1_gold.json / f1_d3b_calidad_v2_gold.json (f1_d3b_calidad.json)` |
| D-A (Calidad sin pipeline) | gold_510 Modo A (relaxed) F1 [P / R | TP/FP/FN] | 1.0000 [P=1.0000, R=1.0000 | 510/0/0] | 1.0000 [P=1.0000, R=1.0000 | 510/0/0] | 0 | `f1_d3b_calidad_v1_gold.json / f1_d3b_calidad_v2_gold.json (f1_d3b_calidad.json)` |
| D-A (Calidad sin pipeline) | gold_510 Modo B (strict) F1 [P / R | TP/FP/FN] | 1.0000 [P=1.0000, R=1.0000 | 510/0/0] | 1.0000 [P=1.0000, R=1.0000 | 510/0/0] | 0 | `f1_d3b_calidad_v1_gold.json / f1_d3b_calidad_v2_gold.json (f1_d3b_calidad.json)` |
| D-A (Calidad sin pipeline) | gold_510 Modo B (relaxed) F1 [P / R | TP/FP/FN] | 1.0000 [P=1.0000, R=1.0000 | 510/0/0] | 1.0000 [P=1.0000, R=1.0000 | 510/0/0] | 0 | `f1_d3b_calidad_v1_gold.json / f1_d3b_calidad_v2_gold.json (f1_d3b_calidad.json)` |
| D-A (Calidad sin pipeline) | gold_510 Modo C (strict) F1 [P / R | TP/FP/FN] | 0.9757 [P=0.9691, R=0.9824 | 501/16/9] | 0.9796 [P=0.9729, R=0.9863 | 503/14/7] | +0.0039 | `f1_d3b_calidad_v1_gold.json / f1_d3b_calidad_v2_gold.json (f1_d3b_calidad.json)` |
| D-A (Calidad sin pipeline) | gold_510 Modo C (relaxed) F1 [P / R | TP/FP/FN] | 0.9912 [P=0.9864, R=0.9961 | 508/7/2] | 0.9942 [P=0.9884, R=1.0000 | 510/6/0] | +0.003 | `f1_d3b_calidad_v1_gold.json / f1_d3b_calidad_v2_gold.json (f1_d3b_calidad.json)` |
| D-A (Calidad sin pipeline) | layouts_5 Modo A (strict) F1 [P / R | TP/FP/FN] | 0.2619 [P=0.9167, R=0.1528 | 11/1/61] | 0.2619 [P=0.9167, R=0.1528 | 11/1/61] | 0 | `f1_d3b_calidad_v1_layouts.json / f1_d3b_calidad_v2_layouts.json (f1_d3b_calidad.json)` |
| D-A (Calidad sin pipeline) | layouts_5 Modo A (relaxed) F1 [P / R | TP/FP/FN] | 0.2857 [P=1.0000, R=0.1667 | 12/0/60] | 0.2857 [P=1.0000, R=0.1667 | 12/0/60] | 0 | `f1_d3b_calidad_v1_layouts.json / f1_d3b_calidad_v2_layouts.json (f1_d3b_calidad.json)` |
| D-A (Calidad sin pipeline) | layouts_5 Modo B (strict) F1 [P / R | TP/FP/FN] | 0.3158 [P=0.3000, R=0.3333 | 24/56/48] | 0.4026 [P=0.3780, R=0.4306 | 31/51/41] | +0.0868 | `f1_d3b_calidad_v1_layouts.json / f1_d3b_calidad_v2_layouts.json (f1_d3b_calidad.json)` |
| D-A (Calidad sin pipeline) | layouts_5 Modo B (relaxed) F1 [P / R | TP/FP/FN] | 0.7164 [P=0.7742, R=0.6667 | 48/14/24] | 0.7376 [P=0.7536, R=0.7222 | 52/17/20] | +0.0212 | `f1_d3b_calidad_v1_layouts.json / f1_d3b_calidad_v2_layouts.json (f1_d3b_calidad.json)` |
| D-A (Calidad sin pipeline) | layouts_5 Modo C (strict) F1 [P / R | TP/FP/FN] | 0.2468 [P=0.2317, R=0.2639 | 19/63/53] | 0.3312 [P=0.3059, R=0.3611 | 26/59/46] | +0.0845 | `f1_d3b_calidad_v1_layouts.json / f1_d3b_calidad_v2_layouts.json (f1_d3b_calidad.json)` |
| D-A (Calidad sin pipeline) | layouts_5 Modo C (relaxed) F1 [P / R | TP/FP/FN] | 0.6923 [P=0.7759, R=0.6250 | 45/13/27] | 0.7206 [P=0.7656, R=0.6806 | 49/15/23] | +0.0283 | `f1_d3b_calidad_v1_layouts.json / f1_d3b_calidad_v2_layouts.json (f1_d3b_calidad.json)` |
| D-C (Pipeline operativo) | Lineas leidas por BETO | 12992 | 12992 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas carga_fila_origen | 15978 | 15978 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas dim_docente | 673 | 673 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas dim_estudiante | 14939 | 14978 | +39 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas dim_modulo | 3796 | 3796 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas dim_tiempo | 2230 | 2230 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas fact_costo_programa | 1320 | 1371 | +51 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas fact_evaluacion_docente | 75126 | 75073 | -53 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas fact_marketing | 299 | 299 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas fact_rendimiento_academico | 1393 | 1392 | -1 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas fact_rentabilidad | 95 | 91 | -4 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas fact_situacion_financiera | 725 | 725 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas fact_techo_convenio | 1 | 1 | 0 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas log_inconsistencias | 11 | 10 | -1 | `f1_d3b_operativo.json` |
| D-C (Tablas DW y staging) | Filas stg_entidad_no_resuelta | 5099 | 5076 | -23 | `f1_d3b_operativo.json` |
| D-C (Bandeja) | Bandeja: casos totales | 182 | 680 | +498 | `f1_d3b_operativo.json` |
| D-C (Bandeja) | Bandeja: grupos totales | 12 | 19 | +7 | `f1_d3b_operativo.json` |
| D-C (Bandeja) | Bandeja: grupos manuales | 7 | 14 | +7 | `f1_d3b_operativo.json` |
| D-C (Bandeja) | Bandeja: casos manuales | 59 | 47 | -12 | `f1_d3b_operativo.json` |
| D-C (KPIs) | KPI-10 | None | None | igual | `f1_d3b_operativo.json` |
| D-C (KPIs) | KPI-11 | None | None | igual | `f1_d3b_operativo.json` |
| D-C (KPIs) | KPI-18 | 59.0 | 36.0 | -23.0 | `f1_d3b_operativo.json` |
| D-C (Tiempos) | Tiempo maquina cache vacia (media +/- DE, s, n=3) | 848.09 +/- 71.61 | 864.28 +/- 80.28 | +16.19 | `f1_d3b_operativo.json` |
| D-C (Tiempos) | Tiempo pared cache vacia (media +/- DE, s, n=3) | 853.36 +/- 70.77 | 869.27 +/- 80.42 | +15.92 | `f1_d3b_operativo.json` |
| D-C (Tiempos) | Tiempo maquina cache llena (media +/- DE, s, n=3) | 267.98 +/- 18.86 | 281.56 +/- 6.90 | +13.58 | `f1_d3b_operativo.json` |
| D-C (Tiempos) | Tiempo pared cache llena (media +/- DE, s, n=3) | 272.95 +/- 18.50 | 286.66 +/- 6.90 | +13.71 | `f1_d3b_operativo.json` |
| D-C (KLM y Total) | klm_estimado_d3b con espera W=10s (s) | 903.3 | 736.6 | -166.7 | `f1_d3b_klm.json` |
| D-C (KLM y Total) | klm_estimado_d3b sin espera W=0s (s) | 263.3 | 216.6 | -46.7 | `f1_d3b_klm.json` |
| D-C (KLM y Total) | Tiempo total (maquina vacia + KLM W=10s) (s) | 1751.4 | 1600.9 | -150.5 | `f1_d3b_klm.json` |
| D-C (KLM y Total) | Tiempo total (maquina vacia + KLM W=0s) (s) | 1111.4 | 1080.9 | -30.5 | `f1_d3b_klm.json` |

## 2. Validez del reentrenamiento (D-B, fuente: `f1_d3b_validez.json`)

- **Orden aumento / separación:** `separa_antes_de_aumentar = True` (`scripts/preparar_corpus_robusto.py` l.101-110 y l.334-344).
- **Personas compartidas train vs dev (spans / IOB2):** `beto-v1` = 273 / 143; `beto-v2` = 0 / 1.

| Cruce | a) Oración exacta | b) Texto normalizado | c) Variantes (plantilla / Jaccard≥0.8) | d) Personas compartidas |
|---|---:|---:|---:|---:|
| `v1_train_vs_gold_510` | 0 | 0 | 0 | 0 |
| `v1_train_vs_layouts_5` | 0 | 0 | 0 | 0 |
| `v2_train_vs_gold_510` | 0 | 0 | 0 | 0 |
| `v2_train_vs_layouts_5` | 0 | 0 | 0 | 0 |

## 3. Huellas del DW (`v1` vs `v2`)

- **`beto-v1` (`f1_d3b_corrida_v1_vacia_r1.json.huella.json`):** sha256 `9cfbffebb790d9b4653558a94ee2293bf5b1294458f1f9e8cc91110d65a3032f`
- **`beto-v2` (`f1_d3b_corrida_v2_vacia_r1.json.huella.json`):** sha256 `85420985c49895fa96b91feb7fd391ac6db8a59b0a2f2a61213bf405c76ee682`

### Tablas que difieren entre `beto-v1` y `beto-v2`

| Tabla | Filas `v1` | Filas `v2` | Δ filas | MD5 `v1` | MD5 `v2` |
|---|---:|---:|---:|---|---|
| `dim_estudiante` | 14939 | 14978 | 39 | `a94e0313e916cf881d60e8d694439f16` | `da1dfde796b270d12ee5c55b7114e22b` |
| `fact_costo_programa` | 1320 | 1371 | 51 | `6f9b389b4a8eb3ac8555042606c98841` | `e3d740db0c2c43f2bd6d0f7f701655fc` |
| `fact_evaluacion_docente` | 75126 | 75073 | -53 | `73c5fce5c67ecda90fa5a2433fd3717a` | `55d21657b8d73e4aea453c46fcab8087` |
| `fact_rendimiento_academico` | 1393 | 1392 | -1 | `0f1bbdf972f3e3cc3bcad6ad6f5ee7dd` | `f74c105130d4186c12eab6c547616a15` |
| `fact_rentabilidad` | 95 | 91 | -4 | `b4cac1dfd6b04910c261497a4bde4a47` | `4fdd8c66a5b7e540821ecc6851a76c4e` |
| `fact_situacion_financiera` | 725 | 725 | 0 | `43a8d3e0df7a582ac05ebf9ee558c83a` | `b6c34aad63570d51a97125ba66b0838c` |
| `log_inconsistencias` | 11 | 10 | -1 | `e039adbdf1751b318c10ef87d5e76f87` | `5a4ae59ffab8b9244a8c384f7d45b3de` |
| `stg_entidad_no_resuelta` | 5099 | 5076 | -23 | `b2cdb582e73015c7a0985c219612db71` | `fff3ce024b55bde8eb96e0d6f008e431` |
