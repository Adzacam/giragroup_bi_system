# PLAN F1R2 — 15 de noviembre de 2026
Objetivo de la fase: volver a registrar la revisión `rev_01` como revisión humana de Lean (declarada, con sus limitaciones) sin tocar la evidencia sellada de F0, y cerrar lo que quedó pendiente de F1R (R-2, R-3).
Entrada: CIERRE_F1V.md + PLAN_F1R.md (R-1 ejecutada: `f1_r1_restauracion.json`; R-2 y R-3 sin ejecutar); rama base = `beto-integracion` `3be4fbe` + cambios sin commit de R-1.

**Decisión de Lean (2026-11-15, en el chat 1):** «revisé yo y le di todo para que lo ponga el chat; lo único que fallaría son los tiempos». Lean declara `rev_01` como revisión propia, dictada al chat 2 y registrada por él en lote. Así se explica el motivo 3 del README (2 marcas de tiempo): son marcas de **registro**, no de **revisión**. Esta decisión deja sin efecto la clasificación «no válida» de R-1, pero R-1 sigue en pie en lo demás: los artefactos de F0 se quedan sellados y la revisión vive en archivos propios de F1.

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| R-4 | Reinstalar `rev_01` como revisión humana declarada, en archivos de F1 | dev-baja | — | R-2 | (a) `f0_desacuerdos_muestra.csv` y `f0_top1_resumen.json` con sha256 `dda8815a…0da2` y `647e0fc5…80ae` (iguales a `b559292`, sin cambios); (b) `f1_revision_humana/a3_etiquetas_rev01.csv` = 90 filas (`case_id, technical_label, human_label, reviewer_id`) sacadas de `3be4fbe:docs/mediciones/f0_desacuerdos_muestra.csv`, con 90/90 `case_id` presentes en la muestra sellada; (c) `f1_revision_humana/a4_decisiones_rev01.csv` = las 7 filas de `f1_revision_no_valida/f0_top1_decisiones_humanas.csv` (sha256 `5ee7b13a…faf`, sin cambios); (d) `f1_revision_humana/resumen.json` con las cifras recalculadas desde esos CSV: A-3 `desacuerdo real 90/90` → falsos desacuerdos `0/90 = 0 %`; A-4 `exclude 7/7` → top-1 `N/D` (0 casos con candidato decidido); (e) campos de procedencia: `declarado_por: "Lean"`, `fecha_declaracion: 2026-11-15`, `modo_registro: "dictado por el revisor, registrado en lote por el chat 2"`, `marcas_tiempo: "de registro, no de revisión"`, `a3_ciego_a_sugerencia_tecnica: false` (la columna `technical_label` estaba visible), `a4_paquete_ciego: true` (`blind_package_sha256 099d8f49…101`); (f) `f1_revision_no_valida/` eliminado o renombrado a `f1_revision_humana/historial_r1/` con su README marcado «superado por la declaración de Lean del 2026-11-15» | `f1_revision_humana/` (3 archivos + README) |
| R-2 | Diagnóstico de la bandeja 182→680 y de KPI-18 59→36 (igual que en PLAN_F1R) | dev-alta | — | R-4 | Desglose por grupo y tipo de caso (`f1_off` frente a `f1_validacion`); cada caso nuevo atribuido a un cambio de entidad de beto-v2 o a otra causa (suma = 498); muestra de 30 casos nuevos con `veredicto_tecnico_automatico`; conclusión «mejora / regresión / mezcla» con conteos; KPI-18 explicado por las filas que cambian | `f1_r2_bandeja_diff.csv`, `f1_r2_diagnostico.json` |
| R-3 | Fe de erratas de CIERRE_F1V | dev-baja | R-4, R-2 | — | Sección «Erratas (2026-11-15, F1R2)» al final, sin reescribir lo anterior: §5.4 apunta a `f1_revision_humana/` (no a los archivos de F0) y nombra las 3 limitaciones (A-3 no ciego a la sugerencia, marcas de tiempo de registro, top-1 N/D); resume R-2 en 1 línea con su archivo; estado «parcial hasta D3-bis» | — |

## Comandos exactos por tarea
- **R-4**
  - `git show 3be4fbe:docs/mediciones/f0_desacuerdos_muestra.csv` → extraer con Python (`csv`) las columnas `case_id, technical_label, human_label, reviewer_id` a `docs/mediciones/f1_revision_humana/a3_etiquetas_rev01.csv`. No incluir `review_timestamp` como dato de revisión; si se incluye, nombrarla `registro_timestamp`.
  - `git mv`/`mv docs/mediciones/f1_revision_no_valida/f0_top1_decisiones_humanas.csv docs/mediciones/f1_revision_humana/a4_decisiones_rev01.csv` (contenido idéntico).
  - `sha256sum` de los 2 archivos de F0 y de los 2 nuevos CSV → `resumen.json`.
  - Cruce: los 90 `case_id` contra `docs/mediciones/f0_desacuerdos_muestra.csv` sellado; los 7 contra `f0_top1_paquete_sellado.json`.
- **R-2:** solo con las huellas y los JSON ya existentes (`f1_validacion_*.json`, `*.huella.json`, salidas de `f1_off`). Si hace falta reejecutar: `scripts/aislada_tmpfs.sh` con `TMPFS_PORT` verificado, sin tocar la DW viva ni el snapshot.
- **R-3:** solo edición de `docs/cierres/CIERRE_F1V.md`.

## Riesgos y control
- **No reescribir F0.** Ningún archivo `f0_*` cambia en esta fase; el criterio (a) lo comprueba con el hash.
- **No ampliar la declaración.** Lean declara `rev_01` (90 + 7). Ningún agente genera, completa ni corrige etiquetas humanas; las de R-2 se llaman `veredicto_tecnico_automatico`.
- **Sesgo de anclaje en A-3.** 90/90 coincide con la sugerencia técnica, que estaba visible. Se registra como limitación; la cifra `0 % falsos desacuerdos` va siempre con esa nota.
- **«Los tiempos».** Las marcas de tiempo de `rev_01` no sirven para medir el esfuerzo de revisión ni para el KLM (B-6). Los tiempos de ciclo de F1-V siguen sin certificar RNF-03; eso es B-7 en F3.
- La DW viva corre con beto-v2; R-2 no la modifica. El respaldo de beto-v1 está en `output/f1/beto_local_respaldo/`.

## DECISIONES PENDIENTES PARA LEAN (no se ejecutan hasta que responda)
1. **D3-bis (tras R-2):** mantener beto-v2 o volver a beto-v1 (respaldo + `BETO_MODELO_VERSION=beto-v1` + rebuild de pipeline y api).
2. **B-10 residual:** rotación de la contraseña de PostgreSQL y reescritura del historial Git si aplica.

## Al cerrar
pytest + cobertura · sin rebuild (no se toca código ni modelo) · commit `chore(f1r2): revisión rev_01 declarada por Lean, diagnóstico de bandeja y erratas` · `CIERRE_F1R2.md`

## PROMPT PARA CHAT 2
```
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F1R2.md (reemplaza las tareas pendientes de PLAN_F1R.md; R-1 ya está hecha).
- R-4 (dev-baja) y R-2 (dev-alta) en paralelo; R-3 (dev-baja) al final.
- Lean declaró que rev_01 es su revisión, dictada al chat y registrada en lote. Regístrala en
  docs/mediciones/f1_revision_humana/ con los campos de procedencia del plan. No modifiques ningún
  archivo f0_*: verifica sus sha256 contra f1_r1_restauracion.json antes y después.
- No generes ni completes etiquetas humanas. Las de R-2 son veredicto_tecnico_automatico.
- R-2 no toca la DW viva ni el snapshot; si reejecutas, usa tmpfs.
- No ejecutes D3-bis ni B-10.
Al terminar: pytest + cobertura, commit y docs/cierres/CIERRE_F1R2.md con los criterios (a)–(f) de R-4,
el desglose de R-2 y las decisiones pendientes D3-bis y B-10.
```
