# CIERRE F1Z — 15 de noviembre de 2026

Cierre completo de **F1** sobre la rama `beto-integracion` (base `4a28300`). Se declara **F1 completa** y lista para que **F2** arranque desde una base estable.

---

## 1. Z-1 — Decisión D3-bis y alcance de RNF-03 (`docs/mediciones/f1_decision_modelo.json`)

- **D3-bis (decidido por Lean):** `1. Mantiene beto-v2`.
  - Modelo vigente en `pipeline/semantic/beto_local/` sin cambios ni rebuild: `model.safetensors` sha256 `9ff7fb9d914aca9eaa0618d9603d869a30808d9218369aef7b12dd92362b5f92`.
  - Costo declarado: `+498 casos de bandeja, +509 en un grupo APROBAR de ARCA` (`docs/mediciones/f1_d3b_comparacion.md`, `f1_d3b_validez.json`, `f1_r2_diagnostico.json`).
- **Alcance de RNF-03 para F3 (decidido por Lean):** medir dos números:
  1. Solo tiempo de máquina del ciclo.
  2. Tiempo de máquina del ciclo más revisión humana (KLM).

---

## 2. Z-2 — Suite en verde en el entorno canónico (`docs/mediciones/f1z_pruebas.txt`, `f1z_fallos_d3b.json`)

- **Causa demostrada de los 6 fallos de `f1_d3b_pruebas.txt`:** los 6 fallos se debieron exclusivamente a haber apuntado `DATABASE_URL` a una base inexistente (`dw_base`) en lugar de `giragroup_db` (la base restaurada por `scripts/aislada_tmpfs.sh up`). No se modificó ningún test.
- **Ejecución canónica en `beto_pg_tmpfs` (`127.0.0.1:55632/giragroup_db` + plantilla `dw_vacio`):**
  - Resultado: **`805 passed, 0 failed, 11 skipped, 7 xfailed`** en `318.66s`.
  - Cobertura total: **`70%`** (`14555` sentencias, `4343` sin cubrir).
  - Contenedor `beto_pg_tmpfs` desmontado tras la corrida (`aislada_tmpfs.sh down`).

---

## 3. Z-3 — Diagnóstico de `md5` inestables entre sesiones (`docs/mediciones/f1z_md5_inestables.json`)

- **Tablas analizadas (sin modificar `scripts/huella_dw.py`):**
  - `stg_entidad_no_resuelta` (`v1`: `5099` filas, `03fd0a265e` vs `b2cdb582e7`; `v2`: `5076` filas, `c2b72bb03a` vs `fff3ce024b`).
  - `fact_situacion_financiera` (`v2`: `725` filas, `d2c1185b2f` vs `b6c34aad63`).
- **Diagnóstico:** en ambos casos, las 6 corridas dentro de una misma sesión (`F1-V` y `D3B`) produjeron `md5` 100% idénticos, con 0 cambios en código (`git diff = 0` desde `4b4a554`), mismos conteos, misma bandeja (`680/19`, `firma_sha256 = 22bd6464...`) y mismos KPIs. La variación entre sesiones proviene de columnas sensibles al orden de ejecución / sesión de contenedor (`registro_origen_id` autoincremental no excluido en `stg_entidad_no_resuelta`, precisión flotante en `score_fuzzy` / `nivel_confianza` / `nivel_confianza_ia` y orden de upsert dependiente de `PYTHONHASHSEED`).
- **Veredicto para F3:** **afecta** únicamente a la comparación estricta por `md5` de esas dos tablas entre sesiones distintas. Propuesta para F3 (sin aplicar): excluir `registro_origen_id`, redondear los flotantes de confianza/fuzzy a 4 decimales en `huella_dw.py` y fijar `PYTHONHASHSEED=0`.

---

## 4. Z-4 — Árbol limpio y lo que pasa a F2 / F3

- **Estado del repositorio:** `docs/` sin modificaciones pendientes (bitácora `f0_comandos_redactados.jsonl` incluida en el commit); `output/f1/` permanece fuera de Git; DW viva y defaults intactos.
- **Lo que pasa a F2:**
  - `B-1`, `B-2`, `B-6` (y `B-8` / `B-9` si Lean los aprueba).
  - Revisión humana diferida de `A-3` / `A-4` (cuando se incorporen etiquetas reales adicionales).
  - `B-10 residual` (sin cambios).
- **Lo que pasa a F3:**
  - `B-7` (RNF-03) midiendo ambos números aprobados por Lean: (1) solo máquina del ciclo y (2) máquina + revisión humana (KLM), bajo condiciones de máquina fijadas (carga registrada, sin contenedores pesados compitiendo, energía en alto rendimiento).
  - Decisión sobre la propuesta de `scripts/huella_dw.py` (`f1z_md5_inestables.json`) y `PYTHONHASHSEED=0` para la huella congelada de F3.
