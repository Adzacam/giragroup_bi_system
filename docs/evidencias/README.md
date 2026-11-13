# Evidencias

Se conservan el snapshot del 10-nov y su hash, huellas, inventarios de esquema, diccionario,
cifras finales del lote 1.387, corridas finales, recálculos Holt-Winters, capturas E2E y gráficos canónicos.

## Carpetas vigentes

- `graficos_v2/`: gráficos canónicos, sin alias.
- `regresion_A/`, `flujo_repetido_A2/`, `flujo_A_cache_vacia/`: comprobaciones finales de fase A.
- `una_pasada/`, `benchmark_beto/`, `deshacer_no_bloqueante/`: mediciones de las decisiones finales.
- `flujo_repetido/`: una línea base histórica coherente (sus tres réplicas constituyen una medición).
- `perfil_dataops/`: perfil base usado por el informe final; no confundir tiempos de perfilador con medición.
- `e2e/`: capturas y resultados reales conservados.
- `validacion_20261113/`: resultados compactos de las 652 pruebas y verificaciones de limpieza.

Las rondas intermedias, resúmenes antiguos, cobertura ronda 6 y primera versión A se archivaron
en `_archivo/docs/evidencias/`. No se borró ninguna cifra final ni se alteraron los JSON de negocio.
Un archivo sin referencias concluyentes se conserva para revisión; no se elimina por ese solo motivo.

Registro y mapa de movimientos: `docs/auditoria/registro_limpieza_20261113.md`.
