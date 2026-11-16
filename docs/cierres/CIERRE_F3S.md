# CIERRE F3S — 2026-11-16
Rama / commit: `beto-integracion`. Código: `4b8dedc` (D-A4, D-A8a, dw_vacio) y `7fab72a` (dos pruebas). Documentación: `0e2d93c`.

**No se anuncia «F3 congelado»: eso lo hace el chat 1 tras revisar este cierre.**

## Hecho
- **S-1 (D-A9):** `scripts/aislada_tmpfs.sh` vacía también `carga_fila_origen`, `fact_costo_programa`, `fact_techo_convenio` y `cache_indice_beto`; el nombre del contenedor se parametriza con `TMPFS_NAME`. `dw_vacio` queda con 0 filas en hechos, staging, logs, `carga_fila_origen` y `dim_origen_documental`; conserva las dimensiones del snapshot (p. ej. `dim_estudiante` = 14.078), catálogos y `bi.ref_*`. Evidencia: `f3s_dw_vacio.json`.
- **S-2 (D-A4):** `consolidacion.py` respeta `staging.categoria = 'evaluacion_docente'` en libros con documento ACTA. `Experiencia Docente 2.0.xlsx` aporta 29.866 hechos (1.137 filas, 0 sin explicar). Evidencia: `f3s_d_a4.json`; prueba `tests/f3s/test_d_a4_evaluacion_en_libro_acta.py`.
- **S-3 (D-A8a):** una fila que una regla ya resolvió no va a BETO; la cascada y los umbrales no cambian. `fact_rentabilidad` = 95 y 0 filas `EJECUTADO VS META` como ESTUDIANTE. Evidencia: `f3s_d_a8a.json`; prueba `tests/f3s/test_d_a8a_metas_no_van_a_beto.py`.
- **S-4 (D-A8b, sin cambios de código):** meta de diciembre de 2024 de TECHOS/CERRADOS = 10.719.694 Bs y 0 metas en otros meses de 2024; KPI-02 = 6,25 % y KPI-03 = 102,26 % con Δ = 0; snapshot sha `14d45f5a…e2eb` igual. Evidencia: `f3s_d_a8b.json`, `f3s_d_a8b.sql`.
- **S-5 (Newman):** la colección ya coincidía con las rutas vigentes (0 cambios). 11 peticiones, 24 aserciones, 0 fallidas. Evidencia: `f3s_newman.json` (resumen), `f3s_newman_diff.txt`, `f3s_newman_probe_live.txt`.
- **S-6 (pytest en worktree limpio, `7fab72a`):** 845 colectadas / 826 passed / 0 failed / 12 skipped / 7 xfailed; cobertura 71,03 %. Evidencia: `f3s_pruebas.json`, `f3s_cobertura_archivos.csv`.
- **S-7 (remedición):** ver «Cifras nuevas». **S-8:** SFV actualizada, `verificar_sfv.py` 0 / 0 / 0 (`f3s_sfv_verificacion.txt`).

## No hecho y por qué
- **Rebuild de `api` y `pipeline` (`docker compose up -d --build api pipeline`): pendiente.** `docker-compose.yml` exige `POSTGRES_PASSWORD` desde el entorno privado de Lean y no está disponible en esta sesión; no se extrajo de los contenedores. Los contenedores en marcha (`giragroup_api`, `giragroup_pipeline`) siguen con la imagen anterior. Prueba manual del endpoint afectado: no hecha por lo mismo.
- **Newman contra la DW viva:** no se ejecutó (las peticiones de login mutan `users`); se corrió contra una API de prueba sobre copia tmpfs.
- **Frontend V2:** no se tocó. Está en la rama local `front-v2` (`eae8fc8`, sin push).

## Invariantes cambiados: no
Cascada CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO, umbrales (0,92 / 90 / 85 / 80; bandas 0,85 / 0,60), 22 KPI, 128 tokens y estados A/B/C sin cambios.

## Pruebas
845 colectadas / 826 passed / 0 failed / 12 skipped / 7 xfailed · cobertura 71,03 % (10.434 de 14.690 sentencias).
Historial: la primera corrida sobre `4b8dedc` dio 819 passed y 7 failed. Ninguno fue regresión: 5 por `DATABASE_URL` del `.env` apuntando al host docker (series sin datos), 1 prueba que dependía de un archivo residual y 1 de codificación; las dos pruebas se corrigieron en `7fab72a`. La corrida sobre `7fab72a` sin las entradas de `uploads/data` dio 2 failed (archivo ausente). Con las 10 entradas de `uploads/data` (no versionadas, sha256 en `f3s_pruebas.json`): 0 failed. Diagnóstico: `f3s_pruebas_fallos_diag.json`.
**La suite depende de esos 10 archivos no versionados y de una BD tmpfs poblada con el snapshot.** Lean decide si se versionan o si esas pruebas se marcan como dependientes de datos locales.

## Servicios reconstruidos + estado
Ninguno reconstruido (ver «No hecho»). `docker ps`: 9 contenedores `giragroup_*` arriba (db y catalog_db healthy); ningún contenedor `beto_pg_*` sigue activo. Comando para Lean, con `POSTGRES_PASSWORD` en su entorno:
`docker compose up -d --build api pipeline`

## Cambios de esquema o API
Ninguno. Solo `scripts/aislada_tmpfs.sh`, `consolidacion.py`, `confianza_service.py`, `extraccion_por_encabezado.py` y `.gitignore` (`output/f3s/`).

## Cifras nuevas (cifra | valor | archivo en docs/mediciones/)
| Cifra | Valor | Archivo |
|---|---|---|
| Huella v2 de f3_base | `c8e10263…0153`; coincide en las 2 corridas de f3_base y en las 3 de B-7 con caché vacía (normalizando `schema_migrations.applied_at`) | `f3s_base.json.huella.json` |
| fact_evaluacion_docente | 104.939 (doc 7 = 29.866) | `f3s_base.json`, `f3s_d_a4.json` |
| fact_rentabilidad | 95 | `f3s_d_a8a.json` |
| stg_entidad_no_resuelta / B-9 | 3.935 / 5.090 | `f3s_extraccion_f3base.json` |
| Bandeja | 676 casos, 17 grupos (12 manuales, 43 casos) | `f3s_extraccion_f3base.json` |
| KPI-18 | 32 | `f3s_extraccion_f3base.json` |
| Cuadre KPI-15 | 500 / 7 / 218, 69,93 % | `f3s_kpi15_cuadre.json` |
| Cobertura por archivo | 0 sin explicar | `f3s_cobertura_por_archivo.json` |
| B-7 caché vacía (1 corrida limpia) | 616,61 s (10,28 min) | `f3s_b7_corridas.json` |
| B-7 caché llena (1 corrida limpia) | 177,20 s | `f3s_b7_corridas.json` |
| W medido (p95 de review-tray/grupos) | 0,034 s | `f3s_locust.json` |
| KLM (W medido / 0 / 10) | 202,3 / 200,6 / 680,6 s | `f3s_klm.json` |
| Vacía + KLM (W medido / 0 / 10) | 818,91 s (13,65 min) / 817,21 s / 1.297,21 s (21,6 min) | `f3s_klm.json`, `f3s_b7_corridas.json` |
| Llena + KLM (W medido / 0 / 10) | 379,50 / 377,80 / 857,80 s | `f3s_klm.json` |
| Lote 1.387 (2 corridas idénticas) | 98,05 % directo, 27 HITL | `f3s_lote_1387.json`, `f3s_lote_1387_r2.json` |
| Locust | 1.252 peticiones, 0 fallos, 42,9 RPS | `f3s_locust.json` |
| Newman | 11 peticiones, 24 aserciones, 0 fallidas | `f3s_newman.json` |
| pytest | 845 / 826 / 0 / 12 / 7; 71,03 % | `f3s_pruebas.json` |

**Cambios frente a F3R** (41 en `f3s_cambios_vs_f3r.json`, solo para este cierre): evaluación docente 75.073 → 104.939; rentabilidad 91 → 95; staging 5.076 → 3.935; B-9 6.226 → 5.090; `carga_fila_origen` 15.978 → 782 (D-A9); bandeja 680/19 → 676/17; KPI-18 36 → 32; W medido 0,089 → 0,034 s; B-7 caché vacía 850,18 → 616,61 s. `fact_costo_programa` tiene md5 distinto con el mismo conteo: ahora sus 1.371 filas tienen `requiere_revision = False` por D-A8a (`consolidacion.py:257`); se infiere del código y de 5 corridas idénticas, porque la base anterior no se conservó.

## RNF-03 (declaración)
Con **1 corrida por condición** (sin dispersión): caché vacía 10,28 min y vacía + KLM con W medido 13,65 min, ambas < 15 min. Con W = 10 s (sensibilidad) 21,6 min. El protocolo `f2r_g6_protocolo_b7.md` pide 3 corridas; Lean decidió una sola.
**Serie descartada:** una primera serie de 3 corridas con caché vacía (1.224,91 / 1.158,82 / 1.203,28 s; mediana 20,05 min) se midió con un juego en ejecución (~4,5 de 24 núcleos) y actividad ajena; queda marcada como DESCARTADA en `f3s_b7_corridas.json` y no se cita en la SFV. La máquina limpia midió casi la mitad.

## Impacto en el documento (sección o tabla)
SFV `docs/fuente_verdad_tesis.md`: encabezado (huella y commit), metodología (frase de `dw_vacio`), Sección A.3/B.2 (conteos), RNF-03/B-7, Locust, Newman, pytest, Sección H (D-A9, D-A4 y D-A8a corregidos; D-A8b fuera; D-A4b, D-A5 y D-A2 siguen como limitaciones), nota de KPI-02 2024, mapa J. Tabla 3.32 (Locust/Newman) y las tablas de tiempos del docx deben tomar las cifras `f3s_*`. Las cifras de KLM de F2 (815,5 / 295,5 s) no deben usarse (ver `f2r_g3_klm_conciliacion.json`).

## Riesgos abiertos
1. **Rebuild pendiente** de `api` y `pipeline` (ver arriba): el sistema en marcha no tiene aún D-A4 y D-A8a.
2. **KPI-15 sin reconciliar.** El cuadre actual del sistema (500 Mora / 7 / 218) no coincide con el diagnóstico `f2r_g5_kpi15.json` (725 filas «Vigente» y TIPO DE CARTERA ignorado; 65 filas en mora o incobrables en la fuente). El diagnóstico cubre solo la hoja principal de 272 filas y no mide las 446 de «Copia de COBRANZAS». La SFV deja el cuadre tal como lo calcula el sistema y no añade limitación. Decisión pendiente (decisión 3 de F2R).
3. **n = 1** en B-7; plan de energía «Equilibrado» (no se cambió); Discord y Brave abiertos durante las corridas (CPU ajena media 8,1 %, pico 28,6 %); Defender activo tras Locust.
4. **«5 de 5» huellas:** las 5 corridas incluyen 3 de la serie contaminada, que comparten sha; se citan solo por la huella. Sin ellas, 2 de 2 en f3_base más la corrida limpia.
5. **Tmpfs poblada con el snapshot sin migración 014:** el snapshot no tiene `fact_marketing.inscritos_captacion`; conviene regenerarlo.
6. **Recomendación pendiente para Lean:** `dim_*` de datos (p. ej. `dim_estudiante` 14.078, `dim_modulo` 3.585) se conservan en `dw_vacio` por decisión documentada en la SFV.
7. **`f3s_newman.json`:** el JSON completo (37 MB, sha256 `090f5e4b…0feb43`) está en `output/f3s/` (ignorado por git).

## Para que Lean decida o limpie antes de F3
- **Frontend V2:** vive en la rama local `front-v2` (`eae8fc8`, desde `5994e88`, sin push).
- **Cambios locales de Lean sin commit:** `backend/routers/powerbi.py` y cambios en `frontend/` (más `PLAN_FRONT_V2.md` y `CIERRE_FRONT_V2.md` sin versionar); no se agregaron a ningún commit. Antes de F3 hay que moverlos a una rama o a un stash para dejar el árbol limpio.
- **Sin versionar y ajenos a F3S:** `docs/evidencias/matriz_confusion_ner.json`, `docs/evidencias/graficos_v2/grafico_3_1…png` y `grafico_3_3…png` (aparecieron durante una corrida sin que S-7 los creara), `output/f3/`, `output/f3r/`.
- **Scripts nuevos de S-7** versionados con este cierre: `scripts/f3s_*.py` (el script A-1 de cobertura por archivo no estaba en el repo; se escribió `f3s_cobertura_por_archivo.py` con las mismas reglas por línea).
- **Decisiones previas aún abiertas:** aplicar la migración 016 a la DW viva (con `pg_dump` previo); B-10 residual; merge de `beto-integracion` a `main`.

## Pendiente para el chat 4
Figuras y tablas a partir de `f3s_*`: tiempos de B-7 (vacía/llena/KLM), Locust, Newman, cobertura por archivo y los cambios de hechos (evaluación docente y rentabilidad).
