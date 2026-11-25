# F12-4 — Verificación Visual `/browser` (`1280×800`, claro y oscuro)
- **URL:** `http://localhost:5173/dataops/revision` → `http://localhost:5173/dataops/lote/1/revision`
- **Modo claro y modo oscuro:** PASS (`0` errores de consola, `0` respuestas HTTP >= 400 en 50 peticiones).
- **Por grupos:** `126` grupos (`26` págs.), 0 `#hash` en títulos, 3 chips de banda + 8 chips de reglas clicables.
- **Casos pendientes (`patron=parcial`):** `609` casos (`31` págs.), selector `Prioridad`, `Similitud` `46.8 %` / `31.4 %`, revelación con auditoría operativa y barra `Confirmar seleccionados` / `Descartar seleccionados`.
- **Casos pendientes (`patron=muy_distinto`):** `121` casos (`7` págs.), botones en lote ocultos y aviso de revisión individual obligatoria.
- **Integridad Lote #1:** inspección de solo lectura (sin mutaciones sobre `giragroup_db`).
