# CIERRE FU-L7 — 2026-11-21
Rama / commit: beto-integracion (pendiente de commit acotado)

Hecho (máx. 10 líneas):
- Catálogo de motivos nuevos añadido en `backend/services/bandeja_grupos.py`, `backend/services/revision_consulta.py` y `backend/routers/dataops/revision.py` (`GET /review-tray/motivos`): `HOJA_IGNORADA`, `NOTA_FUERA_DE_RANGO`, `RESPUESTA_EN_COLUMNA_EQUIVOCADA`, `CUOTAS_NEGATIVAS`, `CONFLICTO_META`, `VALOR_FUERA_DE_CATALOGO`, `PUNTUACION_FUERA_DE_ESCALA`, `ESCALA_NO_INFERIBLE`.
- `HOJA_IGNORADA` y `SIN_INFORMACION` marcados en `MOTIVOS_INFORMATIVOS` y excluidos de `grupos_pendientes`, `ids_del_grupo` e `iterar_casos` (0 casos en bandeja pendiente).
- Corregido el bug en `revision_consulta.py` (`grupos_publicos`): ahora propaga `patrones`, `patron` y `explicacion` (`regla`, `umbral`, `valor_enmascarado` vía `dataops_privacy.py`).
- Añadido `explicacion` estructurada sin PII en `caso_guardado` (`GET /review-tray`) y `grupos_publicos` (`GET /review-tray/grupos`).
- Descarte automático de filas vacías con `nivel_confianza <= 0.0` (`es_fila_vacia_sin_confianza`) y agrupación de `VALOR_FUERA_DE_CATALOGO` por valor normalizado.
- Evidencia generada en `docs/mediciones/fu_l7_bandeja_antes_despues.json` (0 PII).

No hecho y por qué:
- Ninguno en alcance de `FU-L7` (`FU-M2`).

Invariantes cambiados: no

Pruebas: `pytest tests/fu_l7 -v`: **4 passed / 0 failed**.

Servicios reconstruidos + estado de docker compose ps: `giragroup_api` reconstruido y activo (`Up`).

Cambios de esquema o API: nuevo endpoint `GET /api/v1/dataops/review-tray/motivos`; campos `patrones`, `patron`, `explicacion` y `descartadas_vacias` en `/review-tray/grupos` y `explicacion` en `/review-tray`.

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Motivos en catálogo | 27 | `fu_l7_bandeja_antes_despues.json`
- `HOJA_IGNORADA` en bandeja pendiente | 0 | `fu_l7_bandeja_antes_despues.json`
- Patrones detectados en tmpfs | 3 | `fu_l7_bandeja_antes_despues.json`

Impacto en el documento (sección o tabla): descripción de la bandeja de revisión humana HITL.

Riesgos abiertos: ninguno.

Pendiente para el chat 4: ninguno.
