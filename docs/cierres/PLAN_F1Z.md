# PLAN F1Z — 15 de noviembre de 2026
Objetivo de la fase: cerrar F1 por completo. Registrar D3-bis, dejar la suite en verde, explicar los md5 que cambian entre sesiones y dejar el árbol limpio, para que F2 arranque desde una base estable.
Entrada: CIERRE_F1D3B.md; rama base = `beto-integracion` `4a28300`.

## Recomendación del chat 1 para D3-bis: **mantener beto-v2**
Todas las cifras salen de `f1_d3b_comparacion.md` y `f1_d3b_validez.json`.
| Criterio | v1 | v2 | Lectura |
|---|---|---|---|
| Validez del corpus: personas compartidas entre train y dev (spans) | **273** | **0** | El Dev F1 de v1 (0,9989) está inflado por fuga train→dev; v1 no es defendible en el capítulo III |
| Fuga contra gold_510 / layouts_5 (4 niveles) | 0 | 0 | Empate |
| gold_510, modo C, estricto (F1) | 0,9757 | 0,9796 | v2 ≥ v1; los dos cumplen RNF-04 (≥ 0,85) |
| layouts_5, modo B/C, estricto (F1) | 0,3158 / 0,2468 | 0,4026 / 0,3312 | v2 mejor (+0,08) |
| KPI-18 (entidades no resueltas en espera; menos es mejor) | 59 | 36 | v2 mejor |
| Casos manuales de la bandeja | 59 | 47 | v2 pide menos trabajo uno a uno |
| KLM estimado, W = 10 s / W = 0 s | 903,3 / 263,3 s | 736,6 / 216,6 s | v2 −167 s / −47 s |
| Bandeja total (casos / grupos) | 182 / 12 | 680 / 19 | El aumento se concentra en un solo grupo APROBAR de ARCA (+509), que se resuelve con una acción por bloque |
| Tiempo de máquina con caché vacía (media ± DE) | 848 ± 72 s | 864 ± 80 s | Diferencia de +16 s, dentro de la DE: no distingue entre versiones |

**Costo de v2 que hay que declarar:** 498 casos más en la bandeja. R-2 los atribuye en su mayoría a revisiones innecesarias, porque las reglas ya los confirman. Es ruido, aunque casi no cuesta tiempo humano, ya que se aprueban en bloque.

## Tareas
| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| Z-1 | Registrar D3-bis | dev-baja | **Respuesta de Lean** | Z-2, Z-3 | `f1_decision_modelo.json` añade `d3_bis` con: `decision` (el texto de Lean), `fecha`, `fuentes: [f1_d3b_comparacion.md, f1_d3b_validez.json, f1_r2_diagnostico.json]` y `costo_declarado: "+498 casos de bandeja, +509 en un grupo APROBAR de ARCA"`. Si la decisión es v2: sha256 del modelo vigente = `9ff7fb9d…5f92` y sin rebuild. Si es v1: aplicar el procedimiento del respaldo y comprobar `/health` en pipeline y api | `f1_decision_modelo.json` |
| Z-2 | Suite en verde en el entorno canónico | dev-media | — | Z-1, Z-3 | (1) Para cada uno de los 6 fallos de `f1_d3b_pruebas.txt`, causa demostrada: nombre de base `dw_base` en lugar de `giragroup_db` u otra. (2) pytest con cobertura sobre tmpfs con la base `giragroup_db` (como en F1R2): **0 failed**; passed ≥ 805, cobertura ≥ 70 %. (3) Si algún fallo no es del entorno, se detiene y se reporta, sin tocar el test | `f1z_pruebas.txt`, `f1z_fallos_d3b.json` |
| Z-3 | md5 inestables entre sesiones | dev-media | — | Z-1, Z-2 | Para `stg_entidad_no_resuelta` (v1: igual número de filas y distinto md5 frente a f1_off) y `fact_situacion_financiera` (v2: igual número de filas y distinto md5 frente a F1-V): (1) columnas que difieren, sacadas comparando el contenido de las dos huellas o de una reejecución en tmpfs; (2) causa (orden, id autoincremental, timestamp, otra); (3) veredicto «afecta / no afecta a la huella congelada de F3» y, si afecta, la propuesta de qué columnas excluir de `huella_dw.py`, **sin aplicarla** (queda como decisión para F3) | `f1z_md5_inestables.json` |
| Z-4 | Árbol limpio y cierre de F1 | dev-baja | Z-1, Z-2, Z-3 | — | `git status` sin cambios en `docs/` (incluido `f0_comandos_redactados.jsonl`, que se commitea como bitácora); `output/f1/` sigue fuera de Git; `CIERRE_F1Z.md` declara F1 **completa** y lista lo que pasa a F2/F3 | — |

## Comandos exactos
- **Z-2:** `scripts/aislada_tmpfs.sh up` (TMPFS_PORT 55632) → `TEST_DATABASE_URL` apuntando a `127.0.0.1:55632/giragroup_db` (desde el entorno, nunca escrita en un archivo) → `pytest --cov --cov-report=term > docs/mediciones/f1z_pruebas.txt` → `scripts/aislada_tmpfs.sh down`.
- **Z-3:** `scripts/comparar_huellas.py` sobre `f1_off.json.huella.json` contra `f1_d3b_corrida_v1_vacia_r1.json.huella.json`, y sobre `f1_validacion_vacia_r1.json.huella.json` contra `f1_d3b_corrida_v2_vacia_r1.json.huella.json`. Si las huellas no guardan filas, reejecutar una corrida por versión en tmpfs y comparar las tablas columna a columna con `EXCEPT`.

## Riesgos y control (se pasan a F3)
- **Tiempos (RNF-03), el riesgo principal.** En la misma configuración v2, F1-V midió 640 ± 26 s y D3B 864 ± 80 s: la máquina cambia unos 225 s entre sesiones. 864 s ya está cerca del límite de 900 s (15 min). Si el tiempo total suma el KLM (W = 10 s), da unos 1.601 s (≈ 26,7 min), por encima de 20 min. **B-7 en F3 tiene que fijar las condiciones de la máquina** (sin otros contenedores pesados, energía en alto rendimiento, carga registrada) **y Lean tiene que definir qué mide RNF-03** (ver la decisión 2).
- La DW viva sigue con beto-v2; esta fase solo la toca si Lean elige v1.

## DECISIONES PENDIENTES PARA LEAN (no se ejecutan hasta que responda)
1. **D3-bis:** mantener v2 (recomendado) o volver a v1.
2. **Alcance de RNF-03** (para F3): solo el tiempo de máquina del ciclo, o máquina + revisión humana (KLM). Con las cifras de hoy, solo la máquina pasa (< 15 min) y máquina + KLM no pasa (> 20 min).
3. **B-10 residual** (sin cambios).

## Al cerrar
pytest + cobertura (Z-2) · rebuild solo si D3-bis = v1 · commit `chore(f1z): cierre de F1 (D3-bis, suite verde, md5 inestables)` · `CIERRE_F1Z.md`. Después se planifica F2 (B-1, B-2, B-6; B-8 y B-9 si los apruebas).

## PROMPT PARA CHAT 2
```
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F1Z.md.
- Decisión de Lean para D3-bis: «<PEGAR AQUÍ LA RESPUESTA DE LEAN>». Z-1 registra ese texto literal.
- Z-1 (dev-baja), Z-2 (dev-media) y Z-3 (dev-media) en paralelo; Z-4 (dev-baja) al final.
- Z-2: no modifiques tests; si un fallo no es del entorno, detente y repórtalo.
- Z-3: solo diagnóstico; no cambies scripts/huella_dw.py.
- Sin rebuild salvo que D3-bis = v1. No ejecutes B-10.
Al terminar: commit y docs/cierres/CIERRE_F1Z.md con F1 marcada como completa y los pendientes que pasan a F2/F3.
```
