# CIERRE ADW-L9 (PARCIAL) — 2026-11-21
Rama / commit: beto-integracion · commit `adw(L9): …`
Hecho:
- DW viva: las 12.326 aprobaciones históricas en bloque pasaron a `APROBACION_BLOQUE` (`adw_l8_reclasificar_bloque.sql`, autorizado por Lean; solo cambia el texto). Antes: 12.326 «Aprobación en bloque sin cambios»; después: 12.326 `APROBACION_BLOQUE`; las 10 revelaciones intactas.
- Remedición de los 23 KPI × 4 gestiones en la DW viva (solo SELECT): **92/92 iguales a L0** (`adw_l9_comparacion_l0.csv`). Las vistas y los datos no cambiaron todavía.
- `AVISO_CHAT3_ADW.md`: cifras que ya cambiaron (pronóstico DA8, calidad NLP) y las que cambiarán.
No hecho y por qué:
- **No se recongeló `docs/fuente_verdad_tesis.md`:** hacerlo ahora congelaría cifras que cambian con la recarga del plan FU (FU-L3 a FU-L9). Evita dos congelamientos. L9 de ADW se completa tras FU-L9: remedir, recongelar con nueva huella y avisar «ADW congelado».
- No se corrieron pytest ni vitest ni rebuild (no se tocó código en este paso); el último resultado de L5/DA8 sigue vigente.
- Sin capturas «después» (sesión del navegador caducada; 2FA de Lean).
Invariantes cambiados: no.
Riesgos abiertos: base de `bi.vw_riesgo_estudiante` (parte de estudiantes con registro académico; 2026 vacío) y Alertas Tempranas con SQL propio; aviso a chat 1 sobre premisas corregidas; el N de la serie predictiva (33 / 43 / 40).
