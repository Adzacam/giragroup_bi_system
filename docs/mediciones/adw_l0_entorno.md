# ADW L0 — entorno de la evidencia (2026-11-20)

## Copia tmpfs usada
- Contenedor `adw_pg_tmpfs` (postgres:16-alpine, `--tmpfs /var/lib/postgresql/data` 4 GB, `127.0.0.1:55433`), base `giragroup_db`.
- **Origen: `pg_dump` de solo lectura de la DW viva `giragroup_db`** (no del snapshot). Motivo: `snapshot_dw_20261110_1201` es anterior a las recargas del 18–20-nov y no contiene los datos auditados (evaluación 14.234 filas en el snapshot frente a 715.217 en la DW viva; académico 22.618 frente a 25.191). `scripts/aislada_tmpfs.sh up` restauraría el snapshot y no reproduciría la auditoría.
- Verificación de la copia: académico 25.191 · evaluación 715.217 · `carga_fila_origen` 1.636.142 · staging 10.830, iguales a la DW viva.
- La DW viva y el snapshot no se modificaron (solo `pg_dump`).
- El contenedor es efímero (tmpfs): se pierde al detenerlo. Se reproduce con las órdenes de `scripts/auditoria_dw/ejecutar_l0.sh` tras recrearlo.

## Scripts y salidas (L0-1)
`scripts/auditoria_dw/adw_*.sql` → `sh scripts/auditoria_dw/ejecutar_l0.sh` → 1 CSV por bloque:

| Bloque | CSV | Filas | Hallazgos que respalda |
|---|---|---|---|
| KPI (23 × gestiones) | `adw_l0_kpi.csv` | 92 | A1–A4, A9–A12 |
| Evaluación docente | `adw_l0_evaluacion.csv` | 41 | A1, C2 |
| Cartera | `adw_l0_cartera.csv` | 10 | A3 |
| Rentabilidad | `adw_l0_rentabilidad.csv` | 48 | A4, C5 |
| Marketing | `adw_l0_marketing.csv` | 5 | A5 |
| Académico | `adw_l0_academico.csv` | 2 | A2, A6, D1 |
| Staging | `adw_l0_staging.csv` | 23 | pregunta 3 |
| Tareas DataOps | `adw_l0_tareas.csv` | 16 | C1, D3 |
| `carga_fila_origen` | `adw_l0_carga_fila_origen.csv` | 10 | C3 |

## Cotejo con la auditoría (lo que confirman los CSV)
- **A1/C2:** doc 42 sigue como `ACTA` / `CENTESIMAL_100`; puntuaciones = 0: 2024 docente 4.947 + 192, institucional 2.862; 2025 docente 77.673 + 1.483, institucional 75.032. Respuestas válidas institucionales 2024 = 1.050 (doc 42) + 41 (doc 40) = 1.091, como en DA1.
- **A2:** `con_asistencia` = 0 y `incumplimiento_cero` = todas las filas (14.285 + 10.744 = 25.029; ver nota).
- **A3:** 2024 `Mora`: 2.959 filas, 2.902 con 0 cuotas, 1 con ≥ 2.
- **A5:** `leads` = 0, `reservas` = 0 en todas las gestiones; `*_captacion` vacías. (La auditoría preguntaba por qué `reservas` está lleno: **no lo está**; L6-0 debe partir de este dato.)
- **C1:** tareas 45, 47 y 49 en ERROR con 0 procesados; 182 s, 878 s y 180 s (la 47 duró 878 s, no 180 s).
- **C3:** razones claves/hechos: 2,00 · 2,12 · 2,19 · 2,88 · 3,52.

## Diferencias frente al texto de la auditoría (a corregir en el plan)
1. **Académico:** la auditoría habla de 25.191 hechos, pero por gestión suman 14.285 + 10.744 = **25.029**; 162 filas tienen `id_tiempo` NULL (verificado con `LEFT JOIN`) y ninguna vista por gestión las cuenta. Es un hallazgo nuevo (**A13**) para L3/L5.
2. **Tarea 47:** duró 878 s, no 180 s: «exactamente 180 s» solo vale para las tareas 45 y 49.
3. **Marketing `reservas`:** es 0 en todas las filas, no «lleno» (ver DA6).

## Pendiente de L0
- **L0-2 (capturas por módulo) y L0-3 (cruce web ↔ DW): bloqueados.** El navegador integrado está en la pantalla de inicio de sesión; el login pide 2FA y no se permite introducir credenciales ni generar un token de servicio. Hace falta que **Lean inicie sesión** en el navegador integrado (`http://localhost:5173`). Tras eso, las capturas a 1440 px, `adw_l0_cifras_web.csv` y `adw_l0_cruce_web_dw.csv` se hacen en una sesión corta. Lista de pantallas: CMI (3 modos); Académico (rendimiento, docente, catálogo, proyección); Financiero (recaudación, cartera, metas, proyección); DataOps; Auditoría; Reportes.
