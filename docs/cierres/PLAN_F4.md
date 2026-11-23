# PLAN F4 — 2026-11-18
Objetivo de la fase: que cada figura, tabla y captura de la tesis salga de `docs/mediciones/` o de la aplicación real con el estado congelado de F3, y entregar `FIGURAS_F4.md` al chat 3.
Entrada: CIERRE previo leído = `CIERRE_F3V.md` (**F3 congelado**, SFV con 181 cifras, 0/0/0); entrega previa del chat 4 = `FIGURAS_F3V.md` (16 archivos en `docs/figuras/f3/`); rama base = `beto-integracion` `e9267cd`.

## Revisión de FIGURAS_F3V (chat 1)
1. **Tres «capturas» no son capturas.** `figura_3_40_captura_pytest_856.png`, `figura_3_50_captura_cobertura_72_42.png` y `figura_3_44_captura_docker_ps_9_servicios.png` están dibujadas con matplotlib, como texto sobre un fondo de terminal (`scripts/generar_figuras_f3_congelado.py:1032-1046`). La regla del chat 4 dice que una captura es real, de la aplicación o de la terminal en ejecución, nunca texto fijo. Se rehacen (F4-1).
2. **El Gráfico 3.5 (OLS de matrícula, N = 33, pendiente +3,6541, R² 0,1921, p 0,0107) no tiene fila en la SFV.** Cita «SFV Tabla J.1 (E-14)», pero la SFV no tiene E-14 y el invariante declara OLS mensual N = 40. Esa cifra no existe hasta que tenga una medición trazada (F4-2).
3. **Los Gráficos 4.5 y 4.6** (línea base manual frente a sistema, −97,9 %; Likert antes/después 1,89 → …) toman datos de `f3r_evidencias_sueltas.json`. Hay que confirmar que cada valor esté en la SFV con su ruta (F4-2).
4. **Faltan figuras de lo nuevo de F3V:** la serie de KPI-23, las capturas reales del flujo DataOps de 3 pasos (V1/V2, claro y oscuro, pendiente desde F3W), el scorecard CMI con 23 KPI y los tiempos de RNF-03 con n = 3 (F4-3 y F4-4).

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida |
|---|---|---|---|---|---|---|
| F4-0 | **Comprobación de valores.** Para cada una de las 16 figuras actuales: cada número que aparece en la figura, en el pie o en `FIGURAS_F3V.md` existe en la SFV y en su JSON, con la misma ruta (script que lee el JSON y compara) | dev-baja | — | F4-1, F4-2 | 1) tabla figura × número → ruta de la SFV → igual sí/no; 2) 0 números sin fuente (si falta alguno, la figura se marca `retirar` o `corregir`) | `docs/mediciones/f4_figuras_vs_sfv.json` |
| F4-1 | **Capturas reales de terminal.** Volver a correr `pytest` (con cobertura) en el worktree limpio del commit congelado y `docker compose ps`, y capturar la terminal real: la ventana del terminal con el prompt, la fecha y el commit visibles. Reemplazar las tres figuras dibujadas. Si la suite da otra cifra que 856/0/72,42 %, **no se cambia la SFV**: se detiene y se avisa | dev-baja | — | F4-0 | 1) 3 PNG de capturas reales a 300 ppp (con la resolución original si la pantalla no llega); 2) el texto visible coincide con `f3v_pruebas.json` (875/856/0/12/7; 72,42 %) y con 9 contenedores `Up`; 3) se elimina el código de `generar_figuras_f3_congelado.py` que las dibujaba | `docs/figuras/f4/figura_3_40_*.png`, `figura_3_44_*`, `figura_3_50_*` |
| F4-2 | **Cifras sin trazar.** (a) Gráfico 3.5: buscar la medición de la OLS de matrícula (N = 33). Si existe un archivo en `docs/mediciones/` con esos valores, se pide al chat 2 que la agregue a la SFV. Si no existe, la figura se **retira**. Además, confirmar qué es «OLS mensual N = 40» del invariante (`META_MENSUAL_PROGRAMAS`) y graficar esa, si está en la SFV. (b) Gráficos 4.5 y 4.6: cada valor con su fila de la SFV, o la figura se retira | dev-media | F4-0 | F4-1 | 1) veredicto por figura: `trazada` / `retirar`; 2) ninguna figura queda en la entrega con una cifra fuera de la SFV | `docs/mediciones/f4_cifras_sin_trazar.json` |
| F4-3 | **Figuras nuevas de F3V, desde JSON:** (a) serie de KPI-23 por gestión con las bandas 85/60 (`f3v_kpi23_serie.json`); (b) RNF-03 con n = 3: caché vacía y llena con media ± desviación, KLM con W medido y sensibilidad W = 0/10, y la línea de 15 min (`f3v_b7_corridas.json`, `f3v_klm.json`); (c) tabla de Locust y Newman (`f3v_locust.json`, `f3v_newman.json`); (d) hechos por tabla de `f3v_completo` (`f3v_completo.json`) | dev-baja | F4-0 | F4-1 | 1) cada valor dibujado = valor del JSON (prueba en el script); 2) PNG a 300 ppp, con la paleta del proyecto, legible en blanco y negro | `docs/figuras/f4/…` |
| F4-4 | **Capturas reales de la aplicación** (requiere DECISIÓN 1): flujo DataOps de 3 pasos (Carga, Lectura de BETO con la pestaña «Texto preparado», Revisión con el formulario por tipo de caso), en V1 y V2, claro y oscuro; scorecard CMI con los 23 KPI y el detalle de KPI-23. Sesión iniciada por Lean en el navegador; no se guardan credenciales. Datos personales enmascarados (la máscara se queda; no usar «Revelar») | dev-baja | DECISIÓN 1 y 2 | F4-3 | 1) una captura por paso × versión × tema; 2) 0 CI, nombres o correos sin máscara (revisión visual de cada captura); 3) cada captura lleva en el pie la ruta y la fecha | `docs/figuras/f4/capturas/…` |
| F4-5 | **Entrega** `docs/cierres/FIGURAS_F4.md` con la tabla de la skill (archivo, figura del docx, pie, después de qué, datos de origen), y una sección «Retiradas o reemplazadas» frente a FIGURAS_F3V | dev-baja | F4-0…F4-4 | — | 1) cada fila con su fuente; 2) las figuras retiradas o reemplazadas, listadas con su motivo | `docs/cierres/FIGURAS_F4.md` |

## Comandos exactos por tarea
- Gráficos: `scripts/generar_figuras_f4.py` (nuevo, solo lee `docs/mediciones/`), matplotlib a 300 ppp, salida en `docs/figuras/f4/`.
- F4-1: `git worktree add ../gira_f4_pytest e9267cd`; pytest con `DATABASE_URL` hacia la tmpfs (igual que V-5); captura de la ventana con la herramienta de recortes de Windows o `Win+Shift+S`.
- F4-4: clon tmpfs (por ejemplo `beto_pg_f4`, 127.0.0.1:55636) con `f3v_completo`; una instancia de la API con `DATABASE_URL` hacia el clon y la web apuntando a esa API (otro puerto, nunca el gateway de la DW viva). Si no hay un dump de `f3v_completo`, se vuelve a cargar en el clon con el código de `e9267cd` y se comprueba que los conteos coincidan con `f3v_completo.json` (±0) antes de capturar. Lean inicia sesión en el navegador.

## Riesgos y control
- **No se cambia ninguna cifra:** si una figura no cuadra con la SFV, se corrige la figura o se retira. La SFV solo cambia por un plan del chat 2.
- **Capturas con datos reales:** solo con la máscara; ninguna captura muestra la CI, el nombre o el correo completos.
- **Sin commits de `frontend/`.** El commit lleva solo `scripts/generar_figuras_f4.py`, `docs/figuras/f4/`, las mediciones `f4_*` y `FIGURAS_F4.md`.

## DECISIONES PENDIENTES PARA LEAN
1. ~~DW viva~~ **Respondida (18-nov): se usa un clon.** F4-4 levanta la API y la web contra un clon tmpfs restaurado con la carga completa de `f3v_completo` (los 10 libros con el código final), en un puerto distinto de la DW viva. La DW viva no se toca. El pie de cada captura dice «entorno de pruebas con la carga completa de los 10 libros (`f3v_completo`)».
2. ~~Frontend V2~~ **Respondida (18-nov): Lean lo commitea antes de F4-4.** F4-4 empieza solo cuando `git status --short frontend/` esté vacío, y el pie de cada captura incluye el hash de ese commit.
3. **Gráfico 3.5 (OLS de matrícula, N = 33):** si F4-2 no encuentra la medición, ¿se retira (recomendado) o se pide una tarea al chat 2 para medirla y agregarla a la SFV?

## Al cerrar
Commit `docs(f4): figuras y capturas trazadas a la SFV` · `FIGURAS_F4.md` · aviso al chat 3: «Figuras F4 listas».

## PROMPT PARA CHAT 4
/gira-figuras
Ejecuta docs/cierres/PLAN_F4.md (F3 congelado, base `beto-integracion` e9267cd; fuente única: `docs/fuente_verdad_tesis.md` y `docs/mediciones/`).
Primero F4-0 (cada número de las 16 figuras de FIGURAS_F3V contra la SFV). Las capturas de pytest, cobertura y docker ps tienen que ser capturas reales de la terminal, no texto dibujado (F4-1). El Gráfico 3.5 y los 4.5 y 4.6 se quedan solo si cada cifra está en la SFV (F4-2). Agrega las figuras de KPI-23, RNF-03 (n = 3), Locust/Newman y f3v_completo (F4-3). Las capturas de la aplicación (F4-4) se toman sobre un clon con f3v_completo (nunca la DW viva) y empiezan solo cuando yo haya commiteado el frontend V2 (`git status --short frontend/` vacío; el hash va en el pie).
No cambies cifras ni código del sistema. Entrega FIGURAS_F4.md.
