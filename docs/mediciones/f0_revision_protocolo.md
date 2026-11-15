# F0 — protocolo de revisión pendiente

Estado: pendiente. No hay corridas válidas F0 disponibles para preparar candidatos reales ni muestra de desacuerdos; los CSV contienen solo encabezados. Esto no acredita una población vacía ni una tasa de cero.

1. Tras A-1/A-2, sellar con SHA-256 los artefactos completos y extraer los IDs elegibles de a3/a123 en una copia desechable posterior a las huellas. Conservar ranking y puntuaciones previas de forma inmutable y privada.
2. Realizar censo si N≤100 o seleccionar al menos 100 casos con semilla 42 si N>100. Publicar población, tamaño, IDs seleccionados y cobertura. Evitar contar el mismo caso replicado como decisiones independientes.
3. Al revisor mostrar texto/contexto privado y candidatos con IDs opacos en orden independiente del ranking BETO. No mostrar puntuaciones ni posición; fijar y fechar la decisión antes de revelar el ranking. Guardar evidencia verificable de esa independencia. No usar `simular_revision.py`.
4. Registrar elección, rechazo y sin candidato; incluir motivo en toda exclusión y cobertura respecto de todos los elegibles. Las decisiones históricas solo son admisibles si su independencia es verificable. No escribir aprobaciones en la base viva.
5. Calcular top-1 = coincidencias / decisiones humanas válidas. Si N=0, publicar N/D y null, nunca 0 %. Conservar rechazos y casos sin candidato aunque se excluyan justificadamente del denominador.
6. Para A-3, muestrear por archivo/tipo/rol con ≥1 por estrato no vacío y semilla 42. Guardar N_h y n_h, revisar fragmentación (incluido ED + GAR), truncamiento y tipo distinto. Separar etiqueta técnica de validación humana; publicar porcentajes por estrato y estimación ponderada.
7. A-6 se calcula después con las mismas unidades y denominadores F0, por caché y réplica. Conservar numerador/denominador de KPI-10/11/18, bandas, staging, descartes y hechos cargados en revisión. El contraste a3→a123 es combinado. No restar los porcentajes del lote histórico 1.387.

Para continuar se necesitan los artefactos válidos de A-1/A-2 y, para A-4, decisiones reales de un revisor que siga este protocolo. No se solicita revisión humana de candidatos inexistentes.
