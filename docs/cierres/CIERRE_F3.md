# Cierre F3 (Congelamiento)

Rama: `beto-integracion` (sobre `155192b`).
Lote congelado: `aafde8adc246af13c4eeb9ffbf766eda4348cfb6e855860d0bf00bcd24cbdb60` (`10` archivos).
Modelo BETO: `beto-v2` (`9ff7fb9d914aca9eaa0618d9603d869a30808d9218369aef7b12dd92362b5f92`), 4 flags en `False`.
Huella v2 congelada (`f3_base.json.huella.json`, SHA-256): **`b5f1d7b145ceeef8ca85c1f85fd9121eb20d506fcad618a13d66fd944eaaf24f`**.

---

## Tabla de tareas F3-0…F3-9

| ID | Tarea | Estado | Resultado clave | Evidencia |
|---|---|---|---|---|
| F3-0 | Versionar reglas de los chats | **Completa** | `0` coincidencias de secretos; commit `155192b` (`CLAUDE.md`, `.claude/agents/`, `.claude/skills/`) | [f3_0_secretos.txt](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_0_secretos.txt) |
| F3-1 | B-9 sin coste de tiempo | **Completa** | `consolidacion_s` bajó de `1.162,43 s` a `734,57 s` (`<= 750 s`) con acumulación en bloque; `Δ = 0` frente a `f2r_base` (`6.226` filas en `log_inconsistencias`) | [f3_1_b9_rendimiento.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_1_b9_rendimiento.json) |
| F3-2 | KPI-15: mapeo de cartera | **Completa** | `fact_situacion_financiera`: `500` `Mora`, `7` `Previsionable`, `218` `Vigente` (`725` hechos); `KPI-15` 2025 = `73,44 %` (API == SQL, `Δ = 0`) | [f3_2_kpi15.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_2_kpi15.json) |
| F3-3 | Huella v2 | **Completa** | `scripts/huella_dw_v2.py` sobre las `50` tablas (`PYTHONHASHSEED=0`); `49/49` tablas idénticas entre dos sesiones con reinicio (solo difiere `fact_situacion_financiera` por F3-2) | [f3_3_huella_v2.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_3_huella_v2.json) |
| F3-4 | Rebuild y base F3 | **Completa** | `pipeline` y `api` reconstruidos; `9` servicios activos (`/health` `200` en ambos); `50` tablas + `9` vistas `bi` + `22` KPI; bandeja `680/19`, `KPI-18 = 36` | [f3_base.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_base.json), [f3_4_inventario.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_4_inventario.json), [f3_servicios.txt](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_servicios.txt) |
| F3-5 | **B-7: medición final RNF-03** | **Completa** | `3` vacías (`800,21 / 847,91 / 902,42 s`, media `850,18 s`, DE `51,14 s`) + `3` llenas (`257,90 / 258,02 / 252,52 s`, media `256,15 s`, DE `3,14 s`) | [f3_b7_corridas.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_b7_corridas.json), [f3_b7_klm.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_b7_klm.json), [f3_b7_rnf03.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_b7_rnf03.json) |
| F3-6 | Suite final (`pytest --cov`) | **Completa** | **`824 passed, 0 failed, 11 skipped, 7 xfailed`** (`325,68 s`), cobertura total **`70 %`** (`14.672` sentencias) | [f3_pruebas.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_pruebas.json), [f3_pruebas.txt](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_pruebas.txt) |
| F3-7 | KPI y pronóstico finales | **Completa** | 22 KPIs API == SQL (`Δ = 0`) + sensibilidad `requiere_revision`; HW (`META_MENSUAL_PROGRAMAS`, RMSE `241.708,20`) + intervalos B-8 + OLS | [f3_kpi.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_kpi.json), [f3_pronostico.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_pronostico.json) |
| F3-8 | DW viva: migración `016` | **Completa** | Dump previo `output/f3/giragroup_db_pre016.dump` (`31.627.540` bytes, SHA-256 `0763d1db...`); `016` aplicada y registrada; filas intactas; `/health` `200`; snapshot intacto | [f3_8_dw_viva.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_8_dw_viva.json) |
| F3-9 | `fuente_verdad_tesis.md` | **Completa** | Actualizada con estado **CONGELADO — F3**, trazabilidad JSON y `scripts/verificar_sfv.py` (`0` discrepancias) | [fuente_verdad_tesis.md](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/fuente_verdad_tesis.md), [f3_sfv_trazabilidad.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_sfv_trazabilidad.json), [f3_sfv_verificacion.txt](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f3_sfv_verificacion.txt) |

---

## Los dos números de RNF-03 (B-7, F3)
1. **Solo máquina (caché vacía, media `N=3`):** **`850,18 s`** (`14,17 min`) → **cumple** $\le 900\text{ s}$ (`15 min`) y $\le 1.200\text{ s}$. Con caché llena: **`256,15 s`** (`4,27 min`).
2. **Máquina (media caché vacía) + revisión humana KLM (`680` casos / `19` grupos):**
   - Con espera $W = 10\text{ s}$ (`736,6 s` KLM): **`1.586,78 s`** (`26,45 min`) → **no** cumple $\le 900\text{ s}$ ni $\le 1.200\text{ s}$.
   - Sin espera $W = 0\text{ s}$ (`216,6 s` KLM): **`1.066,78 s`** (`17,78 min`) → **no** cumple $\le 900\text{ s}$, **sí** cumple $\le 1.200\text{ s}$ (`20 min`).
