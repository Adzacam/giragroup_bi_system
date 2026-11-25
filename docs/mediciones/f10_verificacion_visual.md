# F10-6: Verificación visual en vivo (`http://localhost:5173`, `1280×800`, Claro y Oscuro)

1. **Paso 1 (`/v2/dataops/ingesta`) — PASS (Claro y Oscuro)**
   - `0` errores de consola JS.
   - Botón `Ir a Lectura de BETO` visible y funcional al inspeccionar `Lote #5`.
2. **Paso 2 (`/v2/dataops/lote/5/beto`) — PASS (Claro y Oscuro)**
   - Botones de cabecera (`Métricas del Modelo BETO` y `Actualizar`) estables (`0px` layout shift).
   - `20` filas por página con chips compactos y `1` desplegable `Ver línea original y desglose de entidades` (`0` duplicación de `raw_text`).
   - Botones `Consolidar / Insertar al DW` e `Ir a Revisión` visibles.
3. **Modal `Métricas del Modelo BETO` — PASS (Claro y Oscuro)**
   - Bloque **Perfil activo en producción (F9 · RNF-03)** (`10,93 min` < `15 min`, `99,52 %` acuerdo) y tabla **Estudio de ablación (Modo A vs. Modo B · lote 10 archivos, F9)** (`89,87 s / 405` vs `119,82 s / 141 / 100,00 %`) renderizados correctamente.
   - Hover sobre la curva de entrenamiento Chart.js (`Época 2 (Mejor)`) muestra tooltip sin reiniciar animación; cierre con `Escape` y botón `X`.
4. **Paso 3 (`/v2/dataops/lote/5/revision?vista=PENDIENTES`) — PASS (Claro y Oscuro)**
   - Navegación `Paso 2 → Paso 3 → Paso 2 → Paso 3` mantiene el conteo exacto (`Casos en la selección = 3.780`, `En revisión = 2543`, `0` duplicación).
   - Tarjetas muestran chips por área, recomendación y `1` desplegable `Ver línea original y entidades IOB2` (`0` texto duplicado).
   - Selección de casos `#3932`, `#3933`, `#3934` mantiene el scroll sin saltar arriba (`y = -1506` estable).
5. **CMI (`/v2/dashboard`, `/v2/cmi`, `/v2/academico/rendimiento`, `/v2/financiero/recaudacion`) — PASS (Claro y Oscuro)**
   - Hover sobre gráficas Chart.js muestra tooltips sin reinicio de animación; cambio de pestañas y rutas sin reinicios ni errores `401`/`403` de cookies/sesión (`0` errores JS).
