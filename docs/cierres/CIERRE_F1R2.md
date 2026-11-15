# Cierre de Fase F1R2 — Revisión `rev_01` declarada, diagnóstico de bandeja (`R-2`) y erratas (`R-3`)

**Fecha:** 2026-11-15  
**Rama:** `beto-integracion` (base: `3be4fbe` + restauración `R-1`)  
**Estado:** Completo para `PLAN_F1R2.md` (cierre parcial de F1 hasta la decisión **D3-bis** de Lean; sin rebuild por no tocar código ni modelo).

---

## 1. `R-4` — Reinstalación de `rev_01` como revisión humana declarada (criterios `a`–`f`)

- **(a) Artefactos de F0 intactos:** Verificados antes y después contra [f1_r1_restauracion.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_r1_restauracion.json) (`b559292`):
  - [f0_desacuerdos_muestra.csv](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f0_desacuerdos_muestra.csv): `sha256 dda8815a965dbc2f52b80f715c173968f66a81c19aefb32f78fb510c344a0da2` (sin cambios).
  - [f0_top1_resumen.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f0_top1_resumen.json): `sha256 647e0fc5481415985708038cff7cb7c76992e5de2ce0fa9f6125e6e0da6a80ae` (sin cambios).
- **(b) A-3 en F1:** [a3_etiquetas_rev01.csv](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_revision_humana/a3_etiquetas_rev01.csv) (`sha256 4a970be2315c793d1564e36b6b4935331699f022867e1b387d1714c032d365db`): `90` filas (`case_id, technical_label, human_label, reviewer_id`), `90/90` `case_id` presentes en la muestra sellada de F0.
- **(c) A-4 en F1:** [a4_decisiones_rev01.csv](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_revision_humana/a4_decisiones_rev01.csv) (`sha256 5ee7b13a1a889ac9ac464b7c862186464f4d36814152beb48fcad46a35414faf`): `7` filas idénticas al paquete de decisiones `rev_01`.
- **(d) Cifras recalculadas ([resumen.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_revision_humana/resumen.json)):**
  - **A-3:** `desacuerdo real` `90/90` → falsos desacuerdos `0/90 = 0.0 %` (con nota obligatoria de sesgo de anclaje por visibilidad de `technical_label`).
  - **A-4:** `exclude` `7/7`, `0` casos con `candidate_id` → `top1 = N/D`.
- **(e) Procedencia y limitaciones declaradas:** `declarado_por: "Lean"`, `fecha_declaracion: "2026-11-15"`, `modo_registro: "dictado por el revisor, registrado en lote por el chat 2"`, `marcas_tiempo: "de registro, no de revisión"`, `a3_ciego_a_sugerencia_tecnica: false`, `a4_paquete_ciego: true` (`blind_package_sha256: 099d8f4974d3d411b065f2e14a58f43ded16adf1a958f8597abcaa6f0ebc6101`).
- **(f) Historial R-1:** `f1_revision_no_valida/` archivado en `docs/mediciones/f1_revision_humana/historial_r1/` con su `README.md` marcado como superado por la declaración de Lean del `2026-11-15`.

---

## 2. `R-2` — Diagnóstico de bandeja `182 → 680` y `KPI-18` `59 → 36`

- **Evidencia:** [f1_r2_diagnostico.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_r2_diagnostico.json) y [f1_r2_bandeja_diff.csv](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_r2_bandeja_diff.csv).
- **Reejecución aislada en `tmpfs`:** `run_r2r_v1` (`beto-v1`, bandeja idéntica a `f1_off`: `182` casos / `12` grupos) y `run_r2r_v2` (`beto-v2`, bandeja idéntica a `f1_validacion_llena_r1`: `680` casos / `19` grupos). Sin tocar la DW viva ni el snapshot; lote `aafde8ad…db60` idéntico antes y después.
- **Desglose y atribución:** `182 → 680` (`+569` altas, `−71` bajas, neto `+498`); `640/640` casos cambiados atribuidos a cambios de banda por entidades de `beto-v2`.
- **Veredicto técnico automático (`veredicto_tecnico_automatico`, no es etiqueta humana):** **mezcla** — `109` casos de mejora (`39` altas donde falla la regla + `70` bajas donde las reglas corroboran) y `531` de regresión (`530` altas que las reglas corroboran + `1` baja con defecto de regla). En la muestra de `30` casos nuevos: `27` `revision_innecesaria_reglas_corroboran` y `3` `revision_justificada_regla_falla`.
- **`KPI-18` (`59 → 36`):** `59 − 53` bajas de `stg_entidad_no_resuelta` (`51` en `BD Egresos.xlsx`, `1` en `ARCA`, `1` en `EVALUACION_DOCENTE`) `+ 30` altas (`18` en `EVALUACION_DOCENTE`, `8` en `ARCA`, `4` en `EJECUTADO VS META.xlsx`) `= 36` (`cuadra: true`).

---

## 3. `R-3` y verificación (`pytest`)

- **`R-3`:** Añadida la sección `Erratas (2026-11-15, F1R2)` al final de [CIERRE_F1V.md](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/cierres/CIERRE_F1V.md).
- **`pytest` ([f1_r2_pruebas.txt](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_r2_pruebas.txt)):** **`805 passed, 11 skipped, 7 xfailed`** en `240.80 s`, cobertura total `70 %` sobre `beto_pg_tmpfs` (`127.0.0.1:55632/giragroup_db` y `catalogo_copia`). `beto_pg_tmpfs` desmontado al cerrar; sin rebuild por no modificar código ni modelo.

---

## 4. Decisiones pendientes para Lean (sin ejecutar)

1. **D3-bis (tras `R-2`):** mantener `beto-v2` o revertir a `beto-v1` (respaldo en `output/f1/beto_local_respaldo/` + `BETO_MODELO_VERSION=beto-v1` + rebuild de `pipeline` y `api`).
2. **B-10 residual:** rotación de la contraseña de PostgreSQL y reescritura del historial Git si aplica.
