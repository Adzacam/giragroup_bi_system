# Cierre de Fase F1V — Aplicación de Decisiones D1/D2/D3, Puertas y Validación F1-V

**Fecha:** 2026-11-15  
**Rama:** `beto-integracion` (base: `b559292`)  
**Estado:** Completo para F1 / F1-V. Quedan como pendientes de fases posteriores o decisión de Lean: revisión humana A-3/A-4 (limitación diferida; no se simularon etiquetas humanas), rotación de credenciales B-10 residual y pruebas de rendimiento RNF-03 (B-7 en F3).

---

## 1. Decisiones de Lean aplicadas y fe de erratas (`F1-E`)

- **D1 / A-5 ([f1_decision_flags.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_decision_flags.json)):** Los 4 flags reales quedan en `False`: `BETO_CASCADA_FINAL`, `BETO_ACUERDO_QC`, `BETO_SUGERENCIA_HITL`, `BETO_VENTANA`. Se agregó la sección `Erratas (2026-11-15)` en [CIERRE_F1.md](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/cierres/CIERRE_F1.md) corrigiendo los nombres inexistentes en §3 sin reescribir el resto.
- **D2 / A-9 ([f1_decision_cache.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_decision_cache.json)):** `public.cache_beto_entidades` es caché operativa fuera de las 50 tablas DW; la migración `015` sale de la inicialización y se crea al vuelo (`DDL_CACHE`) solo si se enciende la opción 1 o 2.
- **D3 ([f1_decision_modelo.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_decision_modelo.json)):** Promoción de `output/f1/reproduccion_1/modelo` a `pipeline/semantic/beto_local` condicionada a superar `F1-L` y `F1-C`.
- **Revisión humana A-3 / A-4:** Diferida como limitación explícita; no se generaron ni simularon etiquetas humanas.

---

## 2. Puertas y cambios ejecutados

### `F1-L` — Puerta de fuga para D3 ([f1_fuga_evaluacion.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_fuga_evaluacion.json))
- Script: [f1_fuga_evaluacion.py](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/scripts/f1_fuga_evaluacion.py).
- `train_vs_gold_510`, `train_vs_layouts_5`, `dev_vs_gold_510`, `dev_vs_layouts_5`: **`0` oraciones normalizadas solapadas** y **`0` personas normalizadas compartidas** en los 4 cruces.
- **Veredicto:** `pasa`.

### `F1-D2` — Migración 015 fuera de la inicialización
- Movida `015_cache_beto_entidades.sql` a [backend/scripts/migrations_opcionales/015_cache_beto_entidades.sql](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/scripts/migrations_opcionales/015_cache_beto_entidades.sql) con [README.md](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/scripts/migrations_opcionales/README.md) y retirada de [aislada_tmpfs.sh](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/scripts/aislada_tmpfs.sh).
- Inventario DW nuevo (`dw_vacio + run_migrations.py`, [f1_d2_inventario_dw_nuevo.csv](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_d2_inventario_dw_nuevo.csv)): **`48` `public.BASE TABLE` + `2` `bi.BASE TABLE` + `9` `bi.VIEW`** (sin `cache_beto_entidades`).
- Creación al vuelo verificada en `tmpfs` con `BETO_CASCADA_FINAL=1`: `True`.
- Lectura en DW viva ([f1_d2_dw_viva.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_d2_dw_viva.json)): `public.cache_beto_entidades` **`existe: false`**, `filas: 0`.

### `F1-C` — Invalidación de caché por identidad del modelo ([f1_cache_identidad_modelo.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_cache_identidad_modelo.json))
- `cache_indice_beto` PK: `(hash_texto, modelo)`; `cache_beto_entidades` PK: `(hash_texto, configuracion)` (`f"{MODELO}|ner|..."`).
- Demostrado aislamiento entre `beto-v1` y `beto-v2` en `tmpfs` (`hit_a: true`, `hit_b: false` en ambas tablas).
- En DW viva (`giragroup_db`), `cache_indice_beto` tiene `90.212` filas bajo `modelo = 'beto-v1'`; se fijó `BETO_MODELO_VERSION=beto-v2` en [docker-compose.yml](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docker-compose.yml) y [confianza_service.py](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/backend/services/confianza_service.py) para invalidar por versión sin tocar la DW viva.
- **Veredicto:** `pasa`.

### `F1-P2` — Promoción del checkpoint ([f1_promocion_modelo.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_promocion_modelo.json))
- Modelo anterior respaldado en `output/f1/beto_local_respaldo/`.
- Candidato `output/f1/reproduccion_1/modelo/` copiado a `pipeline/semantic/beto_local/` con hashes idénticos a [f1_modelo_manifest.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_modelo_manifest.json) (`7` archivos; `.gitignore:75` mantiene los pesos fuera de Git; actualizado [beto_manifiesto.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/evidencias/beto_manifiesto.json)).
- Reconstruidos `pipeline` y `api`; `/health` operativo en ambos (`BETO_MODELO_VERSION=beto-v2`).
- Reevaluación post-promoción en `output/f1/eval_post_promocion`: **`Δ F1 = 0.0`** en `gold_510`, `layouts_5` y `test.conll` (estricto y relajado) respecto a `f1_evaluacion_despues/metricas.json`. Nota: en `test.conll` el F1 estricto es `0.7668 < 0.85`; RNF-04 se sostiene sobre `gold_510` (`0.9805` estricto / `0.9932` relajado).

---

## 3. Validación final `F1-V` ([f1_validacion_resumen.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_validacion_resumen.json))

- **Ejecutor:** [f1_validar.py](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/scripts/f1_validar.py) sobre árbol aislado `/tmp/f1_validacion`, lote congelado `sha256: aafde8adc246af13c4eeb9ffbf766eda4348cfb6e855860d0bf00bcd24cbdb60` (verificado antes y después), 4 flags en `0`, `BETO_MODELO_VERSION=beto-v2`.
- **Caché vacía (`n=3`):** `tiempo_maquina_s` = `639.85 ± 26.253 s` (`[653.01, 656.92, 609.62]`), `pared_s` = `675.407 ± 29.054 s`, `cache_indice_beto` `0 → 12.559` filas.
- **Caché llena con modelo final `beto-v2` (`n=3`):** `tiempo_maquina_s` = `176.637 ± 1.531 s` (`[174.96, 176.99, 177.96]`), `pared_s` = `179.793 ± 1.566 s`, `cache_indice_beto` `12.559 → 12.559` filas. *(Tiempos de máquina; no certifican RNF-03).*
- **Consistencia interna:** `0` diferencias de tablas ni bandeja entre las 6 corridas.
- **Comparación vs `f1_off` (`beto-v1`):**
  - Diferencias esperadas por la promoción a `beto-v2` reportadas por tabla en `f1_validacion_resumen.json` (`dim_estudiante`: `14.939 → 14.978`, `fact_costo_programa`: `1.320 → 1.371`, `fact_evaluacion_docente`: `75.126` filas con distinto `md5`, `fact_situacion_financiera`: `725` filas con distinto `md5`, `log_inconsistencias`: `11 → 10`, `stg_entidad_no_resuelta`: `5.099 → 5.076`).
  - Bandeja: `182` casos / `12` grupos (`f1_off`) → `680` casos / `19` grupos (`f1_validacion`).
  - KPI: `KPI-10: null`, `KPI-11: null`, `KPI-18: 59.0 → 36.0` (NULL se mantiene NULL).

---

## 4. Verificación integral (`A-10`)

- **`pytest` ([f1_pruebas.txt](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_pruebas.txt)):** **`801 passed, 11 skipped, 7 xfailed`** en `200.38 s`, cobertura total `70%`.
  - Ajuste reportado: [test_purga_cache.py](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/tests/f1/test_purga_cache.py) ahora crea `cache_beto_entidades` antes del `INSERT` de prueba porque `dw_vacio` ya no incluye la migración `015` tras `F1-D2`.
- **Snapshot:** `f1_snapshot_despues.json` vs `f1_snapshot_antes.json` -> **`0` diferencias en `59` relaciones**.
- **Servicios ([f1_servicios.txt](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_servicios.txt)):** `9` servicios activos en `docker compose ps`; `/health` saludable en `api` y `pipeline`. `beto_pg_tmpfs` desmontado.

---

## 5. Pendientes para Lean (sin ejecutar)

1. Confirmar si en la DW viva (donde `cache_beto_entidades` hoy **no existe**) queda cerrada la observación D2 sin acciones adicionales.
2. Confirmar que el aislamiento por `BETO_MODELO_VERSION=beto-v2` en `cache_indice_beto` cubre el riesgo de las `90.212` filas `beto-v1` en la DW viva sin borrarlas.
3. **B-10 residual:** rotación de la contraseña de PostgreSQL y reescritura de historial Git si aplica.
4. **Revisión humana A-3 (90) y A-4 (7) — COMPLETADA (`rev_01`, 2026-11-15):**
   - **A-4 (`7/7`):** importado en [f0_top1_resumen.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f0_top1_resumen.json) (`exclude: 7`, `human_validation_pending: false`, `top1: N/D` en `a3` y `a123`).
   - **A-3 (`90/90`):** completado en [f0_desacuerdos_muestra.csv](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f0_desacuerdos_muestra.csv) (`desacuerdo real: 90/90`). Resumen conjunto en [f1_revision_humana_resumen.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_revision_humana_resumen.json).

## Erratas (2026-11-15, F1R2)

Esta sección corrige y completa lo anterior sin reescribirlo. Las cifras de §3 y §4 no cambian.

1. **§5, punto 4 (§5.4): evidencia de la revisión humana.** La evidencia de la revisión `rev_01` está en `docs/mediciones/f1_revision_humana/` (`resumen.json`, `a3_etiquetas_rev01.csv`, `a4_decisiones_rev01.csv`), no en los archivos `f0_*`. Los archivos de F0 siguen sellados: `f0_desacuerdos_muestra.csv` con sha256 `dda8815a…0da2` y `f0_top1_resumen.json` con sha256 `647e0fc5…80ae`. Lean declaró `rev_01` el 2026-11-15; la dictó al chat 2, que la registró en lote. Limitaciones:
   - (i) A-3 no fue ciega a la sugerencia técnica: `technical_label` estaba visible. El resultado 90/90 «desacuerdo real» (0/90 = 0 % falsos desacuerdos) puede tener sesgo de anclaje.
   - (ii) Las marcas de tiempo son de registro, no de revisión. No sirven para medir esfuerzo ni para el KLM (B-6).
   - (iii) Top-1 de A-4 = N/D: 7/7 casos con decisión `exclude` y 0 casos con candidato decidido.

2. **R-2 en una línea:** Bandeja 182→680 (+569 altas, −71 bajas, neto +498) atribuida en 640/640 casos a cambios de banda de beto-v2; veredicto técnico automático: mezcla (109 mejora / 531 regresión); KPI-18 59→36 = 59 − 53 + 30 — ver `docs/mediciones/f1_r2_diagnostico.json` y `f1_r2_bandeja_diff.csv`.

3. **Estado:** parcial hasta D3-bis (decisión pendiente de Lean: mantener beto-v2 o volver a beto-v1).
