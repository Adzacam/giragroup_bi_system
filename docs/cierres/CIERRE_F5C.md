# CIERRE F5C — 2026-11-19

Rama / commits: `beto-integracion` (`84cd352` código y pruebas + commit de cierre `docs(f5c,f5v)`). No se tocaron ni commitearon `backend/routers/powerbi.py`, `docs/cierres/PLAN_FRONT_V2.md`, `docs/cierres/CIERRE_FRONT_V2.md` ni `uploads/otras_versiones/`.

## Hecho
- **C-0 (Restauración del lote):** Se restauraron los 10 libros desde `output/backups/f0_lote/originales/` a `uploads/data/` (copia, SHA-256 `aafde8ad…db60` verificado). Evidencia: `docs/mediciones/f5c_lote_restaurado.json`.
- **C-1 (Diagnóstico por columna en los 10 libros):** Matriz hoja × entidad → columna de origen (lectura vs. carga) y conteo de casos afectados en la DW viva. Evidencia: `docs/mediciones/f5c_columnas_por_entidad.json`.
- **C-2 (Corrección por estructura, sin reglas por nombre de archivo):**
  - Programa por prioridad estructural (código `POS` / `NUMEROPROYECTO` / `N° POS`, luego nombre `NOMBRE DEL PROGRAMA` / `PROGRAMA`). `CARRERA`, `NIVEL ACADEMICO`, `UNIVERSIDAD/INSTITUTO` y `INSTITUCION DONDE TRABAJA` quedan como atributos del estudiante y nunca como programa ni módulo.
  - Docente excluye columnas de rol no docente (`ASESOR`, `COORDINADOR`, `RESPONSABLE`, `RAZON SOCIAL`…) tanto en regla como en entidad `PER` de BETO.
  - Módulo resuelto únicamente desde columnas de módulo/curso.
  - Pruebas: `tests/f5c/test_extraccion_por_estructura.py`.
- **C-3 (Índice recalculado y confianza transparente — DECISIÓN 1):**
  - Cada entidad reporta `confianza` medida por origen y `origen_confianza` ∈ {`BETO`, `REGLA_ENCABEZADO`, `REGEX`, `FUZZY`, `CI_EXACTA`}, sin constantes de confianza escritas en código ni atribuidas a BETO.
  - Informe A/B previo (`docs/mediciones/f5c_indice_ab.json`): `APROBADO_CONTINUAR` (KPI-11 = `97,76 % >= 85 %`; HITL `676 -> 700` = `1,04x`).
  - Pruebas: `tests/f5c/test_confianza_origen.py`, `docs/mediciones/f5c_confianza_origen.json`.
- **C-4 (Re-medición completa y SFV 0/0/0):**
  - `f3_base` (2 corridas, misma huella `8afad01159f63bfd84f75d9f5ba32736024a4902d894b23def555fe880745c94`): **168.013** hechos (`166.983` acad. + `1.030` fin.; bandeja **700** casos en **10** grupos, **67** manuales). Evidencia: `docs/mediciones/f5c_base.json`, `docs/mediciones/f5c_base.json.huella.json`.
  - B-7 (**n = 3** por condición, huella idéntica en las 6): caché vacía **1.430,98 ± 365,09 s** (`23,85 min`), caché llena **757,46 ± 15,39 s** (`12,62 min`). KLM (`W = 2,5 s` medido): **474,0 s** (sensibilidad `W=0/10`: `294,0 / 1.014,0 s`). Total RNF-03: caché llena + KLM = **1.231,46 s (`20,52 min`)**, caché vacía + KLM = **1.904,98 s (`31,75 min`)** — **declarado:** supera umbral 15/20 min (`cumple_rnf03_15min = false`, `cumple_aceptable_20min = false`). Evidencia: `docs/mediciones/f5c_b7_corridas.json`, `docs/mediciones/f5c_klm.json`.
  - Lote 1.387 (2 corridas idénticas): `97,76 %` directo (`1.356/1.387`), `31` HITL (`2,24 %`), KPI-10a = `0,9538`, KPI-10b = `0,8953`, KPI-11 = `97,76 %`. Evidencia: `docs/mediciones/f5c_lote_1387_r1.json`, `docs/mediciones/f5c_lote_1387_r2.json`.
  - `f5v_completo` (10 libros en clon): `fact_planificacion_programa = 1.663`, `dim_meta = 58`, `KPI-23` = `100,00 % / 99,77 % / 46,62 %`; `fact_rendimiento_academico = 25.108`, `fact_situacion_financiera = 10.736`, `fact_marketing = 8.922`. Evidencia: `docs/mediciones/f5v_completo.json`, `docs/mediciones/f5v_kpi23_serie.json`.
  - SFV actualizada y verificada: `scripts/verificar_sfv.py` → **181 entradas, 0 / 0 / 0** (`docs/mediciones/f5c_sfv_verificacion.txt`).
- **C-5 (Pruebas, despliegue y reproceso de `TBL_INSCRITOS` en la DW viva):**
  - `pytest` en worktree limpio (`84cd352`, `beto_pg_tmpfs/giragroup_dw`): **943 colectadas, 924 passed, 0 failed, 12 skipped, 7 xfailed**, cobertura **72,69 %** (`11.535 / 15.869`). Evidencia: `docs/mediciones/f5c_pruebas.json`.
  - Frontend: `vitest` **16/16 archivos (87/87 passed)**, `vite build` **2.035 módulos, 0 errores**.
  - Rebuild de `api` y `web` + reinicio de `giragroup_gateway`: `/health` **200**.
  - En la DW viva (`giragroup_db`), previo `pg_dump` (`backups/f5c_pre_reproceso_inscritos.dump`, 654 líneas `pg_restore --list`): borrado X-1 de `id_documento = 35` y recarga/consolidación de `TBL_INSCRITOS.xlsx` (lote `#36`). Verificadas **20 muestras**: `0` docentes de `ASESOR` y `20/20` programas correctos. Evidencia: `docs/mediciones/f5c_viva_inscritos.json`.

## Anexo de cambios para el chat 3 (antes F3V → después F5C)
- **Lote 1.387:** directo `1.360 (98,05 %)` → **1.356 (97,76 %)**; HITL `27 (1,95 %)` → **31 (2,24 %)** (`EJECUTADO VS META.xlsx`: `19/5` → `15/9`); KPI-11 `98,05 %` → **97,76 %**; excepciones interceptadas `550` → **554** (`PER_SIN_FORMA_NOMBRE` `21` → **25**); personas evaluadas `1.748` → **1.744**.
- **Ciclo `f3_base`:** `109.256` hechos (`11.307` reg.) → **168.013** hechos (`14.343` reg.); bandeja `676 / 17` → **700 / 10** (`67` manuales).
- **RNF-03 (n = 3):** caché vacía `424,29 ± 22,24 s` → **1.430,98 ± 365,09 s**; caché llena `36,53 ± 0,28 s` → **757,46 ± 15,39 s**; KLM (`W=2,5 s`) `320,6 s` → **474,0 s**; total llena+KLM `5,95 min` → **20,52 min**; vacía+KLM `12,41 min` → **31,75 min** (supera umbral 15/20 min).
- **`f5v_completo`:** `fact_rendimiento_academico` `25.191` → **25.108**, `fact_situacion_financiera` `10.719` → **10.736**, `fact_marketing` `10.510` → **8.922** (`fact_planificacion_programa = 1.663`, `dim_meta = 58` y `KPI-23` sin cambios).
- **Pruebas:** `875` colectadas / `856` passed / `72,42 %` → **943** colectadas / **924** passed / **72,69 %** cobertura; `vitest` `84/84` → **87/87**.
