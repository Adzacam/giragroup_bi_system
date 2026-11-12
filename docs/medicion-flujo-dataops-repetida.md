# Medición repetida del flujo DataOps (10 archivos, DW reiniciado)

3 corridas sobre copias aisladas del snapshot del 10 de nov (DW vaciado, migración 014), sin la suite de pruebas ni otros procesos, con 30 s de reposo antes de cada una.
Muestreo de CPU/RAM cada 5 s (psutil en el equipo; `docker stats` en `giragroup_api` y `giragroup_db`). Equipo: 24 hilos, 16 GiB para Docker. Desviación estándar muestral (n−1).
Scripts: `scripts/medir_flujo_repetido.py`, `scripts/medir_flujo_dataops.py`, `scripts/agregar_flujo_repetido.py`. Evidencia: `docs/evidencias/flujo_repetido/`.

## Parte máquina (medida)

| Etapa | Media | DE | Mín–Máx |
|---|---:|---:|---:|
| Carga de los 10 archivos | 8,5 s | 0,7 | 7,7–9,1 |
| Lectura BETO (15.926 líneas) | 888,5 s (14,8 min) | 19,9 | 866,9–906,0 |
| Velocidad de lectura BETO | 17,93 líneas/s | 0,40 | 17,58–18,37 |
| Consolidación | 834,0 s (13,9 min) | 96,1 | 769,0–944,4 |
| Revisión, parte máquina (aprobaciones) | 1,0 s | — | 1 sola medición |
| **Total máquina** | **1.732 s (28,9 min)** | **112,4** | 1.645–1.858 |

El DW resultante fue idéntico en las 3 corridas (mismos conteos por tabla), por lo que la bandeja es la misma.
La corrida usó la lectura BETO del lote: la DE mayor está en la consolidación (±12 %), la lectura es estable (±2 %).

## Recursos (media de las 3 corridas; máximo entre paréntesis)

| Recurso | Valor |
|---|---|
| CPU del equipo | 31 % (57 %) |
| RAM usada del equipo | 23,5 GiB (25,8 GiB) |
| `giragroup_api` CPU | 76 % (≈1 núcleo; pico 249 %) |
| `giragroup_api` RAM | 1,25 GiB (1,43 GiB) |
| `giragroup_db` CPU | 3,7 % (pico 39 %) |
| `giragroup_db` RAM | 0,26 GiB (0,38 GiB) |

La API usa ≈1 núcleo de 24: el proceso es secuencial y limitado por CPU de un hilo, no por memoria ni por la base de datos.

## Parte humana (KLM sobre los casos reales)

Bandeja tras consolidar (la misma en cada corrida): **194 casos en 12 grupos**: 5 en bloque (APROBAR) + 1 de corrección de fecha (8 casos) → 6 aprobables con un clic, y **7 grupos manuales con 71 casos** (51, 10, 5, 2, 1, 1, 1). De los 71, 20 se rechazan por la regla de presupuesto.

Parámetros KLM (Card, Moran y Newell, 1980), en segundos: K 0,28; P 1,10; H 0,40; M 1,35; clic (BB) 0,20; espera de Deshacer W 10.
Supuestos propios: 2 M por grupo y por caso (leer y decidir); fecha = 6 teclas; 5 grupos por página (P + clic para cambiar de página). El caso manual se modela como aprobarlo tal cual (sin edición), igual que el simulador.

| | Con espera de 10 s | Sin espera |
|---|---:|---:|
| Grupos en bloque (5) | 56,0 s | 16,0 s |
| Corregir fecha (1) | 18,7 s | 8,7 s |
| Casos manuales (71) | 994,0 s | 284,0 s |
| Paginación | 2,6 s | 2,6 s |
| **Parte humana** | **1.071 s (17,9 min)** | **311 s (5,2 min)** |

## Total estimado

| | Con espera | Sin espera |
|---|---:|---:|
| Máquina medida | 28,9 min | 28,9 min |
| Humano (KLM) | 17,9 min | 5,2 min |
| **Total** | **46,7 min** | **34,1 min** |

Contra la meta RNF-03 (15 min) y los 9 min de la tesis: no se cumple ni siquiera sin la espera; la máquina sola (28,9 min) ya la supera.

## Limitaciones
- Las 3 corridas simularon la revisión **antes** de consolidar y vieron 0 casos (la bandeja se llena al consolidar). El script ya se corrigió para revisar después de consolidar, pero las corridas no se repitieron. Los grupos y casos de la parte humana salen de la corrida anterior con la misma entrada (`revision_simulada_flujo_dataops.json`); como el DW fue idéntico en las 3 corridas, es la misma bandeja. El 1,0 s de la revisión máquina es una sola medición.
- La parte humana es un modelo (KLM), no una medición con personas.
- La corrida 3 se relanzó porque la sesión se cerró durante la primera tanda.
