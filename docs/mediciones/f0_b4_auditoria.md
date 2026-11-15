# F0 B-4 — auditoría de corpus

Auditoría de los bytes existentes; no se regeneró ni entrenó. Las intersecciones por texto/tokens son verificables; la independencia de familias y la revisión humana del gold no son verificables con la procedencia conservada.

| Cruce | Texto exacto (pares) | Texto normalizado (pares) | Tokens exactos (pares) | Tokens normalizados (pares) | Firma familiar inferida (pares) |
|---|---:|---:|---:|---:|---:|
| train_dev | 0 | 0 | 0 | 0 | 0 |
| train_gold | 0 | 0 | 0 | 0 | 0 |
| dev_gold | 0 | 0 | 0 | 0 | 0 |

Las firmas familiares comparan el conjunto de entidades de cada registro, sin títulos docentes. No sustituyen IDs de padre/origen. Los cruces por valor individual de entidad en el JSON permiten detectar personas o entidades institucionales compartidas, sin publicar sus nombres.

El generador aumenta antes de dividir 80/20, con semilla 42 y un único pool de entidades para train/dev. `list(set(...))` impide garantizar reproducción solo con esa semilla. No se guardan IDs de origen ni familias. Los nombres de gold se excluyen mediante coincidencia lowercase, sin normalización robusta; los cruces observados se informan sin inferir ausencia de fuga.

Aumentos reales: sinónimos, permutación, títulos, tildes, casing de encabezado, ruido y plantillas. `apply_typo` no se invoca. De cuatro plantillas declaradas solo dos son alcanzables. El checkpoint se selecciona por dev F1 entre tres épocas; no hay early stopping implementado.

`output/test_gold_revision.csv` contiene únicamente línea, token y etiqueta automática. No demuestra anotación o revisión humana independiente. La afirmación histórica de revisión de layouts adversarios no acredita revisión del gold real.

Hashes, tamaños, soporte y grupos de IDs: [f0_b4_auditoria.json](f0_b4_auditoria.json). No se publica texto ni CI.

En train–dev se comparten valores normalizados de **1 estudiante(s)** y **143 docente(s)**. Esto evidencia reutilización de personas/pools entre particiones aunque no haya filas textualmente duplicadas. Los cruces por persona ausentes en gold no demuestran independencia de procedencia.
