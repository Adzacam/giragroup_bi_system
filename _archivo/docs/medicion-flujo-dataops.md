# Medición del flujo DataOps completo con los 10 archivos (12 de noviembre de 2026)

Base aislada con el DW reiniciado (copia del snapshot del 10 de noviembre con las tablas de hechos, staging, logs y documentos vaciadas). Archivos: los 10 del ciclo mensual (mes 2026-03, hojas sin fecha completas), por los endpoints reales de los pasos ① a ④. Script: `scripts/medir_flujo_dataops.py`. Evidencia: `docs/evidencias/flujo_dataops_10_archivos_dw_reiniciada.json` y `revision_simulada_flujo_dataops.json`.

| Etapa | Tiempo | Tipo |
|---|---:|---|
| ① Carga de los 10 archivos (8 s) y ③ lectura de BETO de 14.989 registros | 895,6 s (14,9 min) | medido |
| Consolidación al Data Warehouse (85.630 hechos; 6.656 entidades a staging; 68 derivados a revisión) | 742,0 s (12,4 min) | medido |
| ④ Revisión: máquina | 1,0 s | medido |
| ④ Revisión: persona (194 casos, 12 grupos: 5 en bloque y 7 manuales con 71 casos; 20 casos rechazados por la regla de presupuesto) | 2.262 s (37,7 min) | **simulado** |
| **Total** | **3.900 s (65 min)** | máquina 27,3 min medidos + 37,7 min estimados |

Supuestos de la parte humana: 6 s de lectura por grupo, 2 s de acción, 20 s por caso manual y 10 s de espera con Deshacer por acción (la pantalla del paso ④ solo admite una operación pendiente). Sin la espera de 10 s, la parte humana sería de 25 min.

## Comparación con la medición anterior (`/api/v1/pipeline/process`)

- Máquina: 69,1 s frente a 1.637,6 s. La ruta anterior resuelve por reglas y solo usa BETO donde hace falta; la ruta de DataOps lee con BETO cada línea.
- Revisión: 188 casos en 37 grupos, todos aprobables en bloque (296 s simulados) frente a 194 casos en 12 grupos con 7 manuales (2.262 s simulados). Los 71 casos manuales son los que el loop 4 deja fuera de la aprobación en bloque (filas de presupuesto leídas como personas y combinaciones no admitidas).

## Conclusión

Ninguna de las dos rutas mide exactamente "9 minutos". Con la ruta de DataOps vigente, el tiempo de máquina (27,3 min) ya supera la meta RNF-03 de 15 min; el tiempo humano es una estimación y depende de cuántos casos quedan manuales.
