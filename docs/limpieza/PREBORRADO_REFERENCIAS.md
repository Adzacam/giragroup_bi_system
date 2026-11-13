# Comprobaciones antes del borrado

Commit inicial: `5850dd4`. Comparación por recolección real con `f3b37d9`: 650 → 652; sin IDs retirados.

## Dos IDs añadidos

- `tests/test_person_resolver_preparado.py::test_el_catalogo_se_prepara_una_vez_y_se_rehace_si_cambia`
- `tests/test_person_resolver_preparado.py::test_preparado_equivale_al_algoritmo_original`

Se incorporaron en `ac9ea1f`; el MJS de cola también se añadió, pero Node no forma parte de la colección pytest.

## Citas de imágenes

La columna ruta señala la presencia literal de la ruta completa; basename señala un nombre de archivo; la última columna registra sólo el número de figura, sin referencia de archivo en esa línea. Índices de DOCX = párrafo XML. Las citas históricas se preservan y la tesis debe actualizar sus rutas/pies; no se considera que una cita numérica garantice una captura existente.

| Imagen | Ruta de archivo citada | Nombre de archivo citado | Sólo número de figura |
| --- | --- | --- | --- |
| docs/evidencias/graficos/figura_3_40_captura_pytest_475.png | docs/fuente_verdad_tesis.md:491; fuente_verdad_tesis.md:492 | no | docs/fuente_verdad_tesis.md:174; fuente_verdad_tesis.md:174 |
| docs/evidencias/graficos/figura_3_50_captura_cobertura_60_8.png | docs/fuente_verdad_tesis.md:492; fuente_verdad_tesis.md:493 | no | no |
| docs/evidencias/graficos/figura_3_5_esquema_constelacion_fisico.png | docs/fuente_verdad_tesis.md:490; fuente_verdad_tesis.md:491 | no | docs/figuras_src/figura_3_5_constelacion_dw.mmd:3; docs/revision_tesis_cap1_3_4_5.md:174; docs/tablas_v2.docx:480; docs/tablas_v2.md:162 |
| docs/evidencias/graficos/grafico_3_2_distribucion_lote_1387.png | docs/fuente_verdad_tesis.md:484; fuente_verdad_tesis.md:484 | no | no |
| docs/evidencias/graficos/grafico_3_4_serie_temporal_holt_winters.png | docs/fuente_verdad_tesis.md:485; fuente_verdad_tesis.md:485 | no | no |
| docs/evidencias/graficos/grafico_4_1_excepciones_calidad_lote.png | no | no | no |
| docs/evidencias/graficos/grafico_4_1_inconsistencias_corpus.png | docs/fuente_verdad_tesis.md:486; fuente_verdad_tesis.md:486 | no | no |
| docs/evidencias/graficos/grafico_4_2_confianza_probabilistica.png | docs/fuente_verdad_tesis.md:487; fuente_verdad_tesis.md:487 | no | no |
| docs/evidencias/graficos/grafico_4_2_distribucion_lote_1387.png | no | no | no |
| docs/evidencias/graficos/grafico_4_3_distribucion_archivo_lote_1387.png | docs/fuente_verdad_tesis.md:488; fuente_verdad_tesis.md:488 | no | no |
| docs/evidencias/graficos/grafico_4_3_resolucion_por_formato.png | no | no | no |
| docs/evidencias/graficos/grafico_4_4_kpi_cmi_perspectivas.png | no | fuente_verdad_tesis.md:489 | no |
| docs/evidencias/graficos/grafico_4_4_kpis_cmi.png | no | no | no |
| docs/evidencias/graficos/grafico_4_5_tiempo_consolidacion_semilog.png | docs/fuente_verdad_tesis.md:489; fuente_verdad_tesis.md:490 | no | no |
| docs/figuras/grafico_3_2_bandas_confianza_lote1387.png | no | no | no |
| docs/figuras/grafico_4_1_motivos_derivacion.png | no | no | no |
| docs/figuras/grafico_4_2_destino_lote.png | no | no | no |
| docs/figuras/grafico_4_3_consolidacion_por_origen.png | no | no | no |
| docs/figuras/grafico_4_4_kpi_por_perspectiva.png | no | no | no |
| docs/figuras/grafico_4_5_tiempo_consolidacion_semilog.png | no | docs/fuente_verdad_tesis.md:489; fuente_verdad_tesis.md:490 | no |
| docs/figuras_tesis/figura_3_10_codigo_despachador.png | no | no | no |
| docs/figuras_tesis/figura_3_11_codigo_lectura_hojas_formularios.png | no | no | no |
| docs/figuras_tesis/figura_3_12_diagrama_flujo_ner_beto_rapidfuzz.png | no | no | no |
| docs/figuras_tesis/figura_3_13_codigo_inicializacion_beto.png | no | no | no |
| docs/figuras_tesis/figura_3_14_codigo_emparejamiento_difuso.png | no | no | no |
| docs/figuras_tesis/figura_3_15_captura_logs_extraccion_hitl.png | no | no | no |
| docs/figuras_tesis/figura_3_9_diagrama_actividad_ingesta.png | no | no | no |
| docs/figuras_tesis/grafico_3_1_matriz_confusion_beto.png | no | no | no |
| docs/figuras_tesis/grafico_3_2_distribucion_confianza_probabilistica.png | no | no | no |
| docs/figuras_tesis/grafico_3_3_metricas_por_tipo_entidad.png | no | no | no |
| docs/images/figura_1_40_resumen_pytest.png | no | no | no |
| docs/images/figura_3_12_diagrama_flujo_beto_rapidfuzz.png | no | no | no |
| docs/images/figura_3_16_diagrama_casos_de_uso_backend.png | no | no | no |
| docs/images/figura_3_17_captura_logs_extraccion_semantica.png | no | no | no |
| docs/images/figura_3_17_diagrama_secuencia_jwt_pipeline.png | docs/INFORME_CONSIDERACIONES_SEGURIDAD_GIRAGROUP_BI.md:507 | no | no |
| docs/images/figura_3_22_captura_respuesta_json_forecast.png | no | no | no |
| docs/images/figura_3_23_diagrama_casos_de_uso_frontend.png | no | no | no |
| docs/images/figura_3_24_mockup_login_e_ingesta.png | docs/INFORME_CONSIDERACIONES_SEGURIDAD_GIRAGROUP_BI.md:502 | no | no |
| docs/images/figura_3_25_captura_respuesta_json_forecast.png | no | no | no |
| docs/images/figura_3_25_mockup_hitl_y_alertas.png | no | no | no |
| docs/images/figura_3_26_mockup_cmi_powerbi.png | no | no | no |
| docs/images/figura_3_2_arquitectura_fisica_orquestacion.png | docs/INFORME_CONSIDERACIONES_SEGURIDAD_GIRAGROUP_BI.md:517 | no | no |
| docs/images/figura_3_31_dashboard_cmi_academico.png | no | no | no |
| docs/images/figura_3_32_dashboard_cmi_financiero.png | no | no | no |
| docs/images/figura_3_33_diagrama_secuencia_e2e.png | no | no | no |
| docs/images/figura_3_34_captura_pytest_cobertura.png | docs/INFORME_CONSIDERACIONES_SEGURIDAD_GIRAGROUP_BI.md:522 | no | no |
| docs/images/figura_3_35_captura_postman_runner.png | docs/INFORME_CONSIDERACIONES_SEGURIDAD_GIRAGROUP_BI.md:527 | no | no |
| docs/images/figura_3_35_captura_pytest_cobertura.png | no | no | no |
| docs/images/figura_3_36_captura_seguridad_owasp.png | docs/INFORME_CONSIDERACIONES_SEGURIDAD_GIRAGROUP_BI.md:512 | no | no |
| docs/images/figura_3_36_validacion_postman.png | no | docs/INFORME_CONSIDERACIONES_SEGURIDAD_GIRAGROUP_BI.md:527 | no |
| docs/images/figura_3_37_captura_docker_ps.png | no | no | no |
| docs/images/figura_3_37_pruebas_verificacion_sprint5.png | no | no | no |
| docs/images/figura_3_39_captura_pytest_cobertura.png | no | docs/INFORME_CONSIDERACIONES_SEGURIDAD_GIRAGROUP_BI.md:522 | no |
| docs/images/figura_3_3_diagrama_despliegue_docker_compose.png | no | no | no |
| docs/images/figura_3_40_captura_pytest_475.png | no | docs/fuente_verdad_tesis.md:491; fuente_verdad_tesis.md:492 | docs/fuente_verdad_tesis.md:174; fuente_verdad_tesis.md:174 |
| docs/images/figura_3_41_evidencia_objetivo_2_esquema_constelacion.png | no | no | no |
| docs/images/figura_3_42_captura_seguridad_owasp.png | no | docs/INFORME_CONSIDERACIONES_SEGURIDAD_GIRAGROUP_BI.md:512 | no |
| docs/images/figura_3_42_evidencia_objetivo_3_lote_unificado.png | no | no | no |
| docs/images/figura_3_43_captura_docker_ps_9_servicios.png | docs/INFORME_CONSIDERACIONES_SEGURIDAD_GIRAGROUP_BI.md:532 | no | no |
| docs/images/figura_3_43_evidencia_objetivo_4_entidades_beto_rapidfuzz.png | no | no | no |
| docs/images/figura_3_44_evidencia_objetivo_5_proyecciones_cmi.png | no | no | docs/revision_tesis_cap1_3_4_5.md:93; docs/tablas_v2.docx:490; docs/tablas_v2.md:164 |
| docs/images/figura_3_45_evidencia_objetivo_6_reporte_pruebas_calidad.png | no | no | no |
| docs/images/figura_3_4_modelo_conceptual_hefesto.png | no | no | no |
| docs/images/figura_3_50_captura_cobertura_60_8.png | no | docs/fuente_verdad_tesis.md:492; fuente_verdad_tesis.md:493 | no |
| docs/images/figura_3_5_esquema_constelacion_fisico.png | no | docs/fuente_verdad_tesis.md:490; fuente_verdad_tesis.md:491 | docs/figuras_src/figura_3_5_constelacion_dw.mmd:3; docs/revision_tesis_cap1_3_4_5.md:174; docs/tablas_v2.docx:480; docs/tablas_v2.md:162 |
| docs/images/figura_3_6_diagrama_clases_orm_pydantic.png | no | no | no |
| docs/images/figura_3_9_diagrama_actividad_ingesta.png | no | no | no |
| docs/images/grafico_3_1_matriz_confusion_beto.png | no | no | no |
| docs/images/grafico_3_2_distribucion_confianza_probabilistica.png | no | no | no |
| docs/images/grafico_3_2_distribucion_lote_1387.png | no | docs/fuente_verdad_tesis.md:484; fuente_verdad_tesis.md:484 | no |
| docs/images/grafico_3_3_desempeno_metricas_beto.png | no | no | no |
| docs/images/grafico_3_3_desempeno_metricas_por_entidad.png | no | no | no |
| docs/images/grafico_3_4_serie_temporal_holt_winters.png | no | docs/fuente_verdad_tesis.md:485; fuente_verdad_tesis.md:485 | no |
| docs/images/grafico_3_5_tendencia_lineal_ols.png | no | no | no |
| docs/images/grafico_4_1_excepciones_calidad_lote.png | no | no | no |
| docs/images/grafico_4_1_inconsistencias_corpus.png | no | docs/fuente_verdad_tesis.md:486; fuente_verdad_tesis.md:486 | no |
| docs/images/grafico_4_2_confianza_probabilistica.png | no | docs/fuente_verdad_tesis.md:487; fuente_verdad_tesis.md:487 | no |
| docs/images/grafico_4_2_distribucion_lote_1387.png | no | no | no |
| docs/images/grafico_4_3_distribucion_archivo_lote_1387.png | no | docs/fuente_verdad_tesis.md:488; fuente_verdad_tesis.md:488 | no |
| docs/images/grafico_4_3_resolucion_por_formato.png | no | no | no |
| docs/images/grafico_4_4_disponibilidad_kpi_cmi.png | no | no | no |
| docs/images/grafico_4_5_tiempo_consolidacion_semilog.png | no | docs/fuente_verdad_tesis.md:489; fuente_verdad_tesis.md:490 | no |
| docs/images/grafico_4_6_evaluacion_likert_pre_post.png | no | no | no |

## Alias SHA-256 en graficos_v2

Se encontraron 4 alias exactos, no cinco. No se inventa un quinto borrado.

- `8ed0d840c66fd796dd49a44ce73be1144eca3750f1a19968707fa31a7be01e58`: `docs/evidencias/graficos_v2/grafico_4_1_calidad_corpus.png`; `docs/evidencias/graficos_v2/grafico_4_1_inconsistencias_corpus.png`
- `9391633f048ff2ccf989e3949223a5f351269b66abf2378474f76e3d00b70bb0`: `docs/evidencias/graficos_v2/grafico_4_2_confianza_probabilistica.png`; `docs/evidencias/graficos_v2/grafico_4_2_resoluciones_cascada.png`
- `3a990527729509fe3ebad0bb6862db5bad64dd78cb3025ed23fe2d75033b6bfe`: `docs/evidencias/graficos_v2/grafico_4_3_distribucion_archivo_lote_1387.png`; `docs/evidencias/graficos_v2/grafico_4_3_vinculacion_por_archivo.png`
- `50de765c9afdf200229e84935f2f77bf7b1e7eed363a2865bb7d551c8340956c`: `docs/evidencias/graficos_v2/grafico_4_4_kpi_cmi_perspectivas.png`; `docs/evidencias/graficos_v2/grafico_4_4_kpis_cmi.png`

## E2E

`e2e/lib.mjs` no contiene lectura ni ruta a graficos/: lee OTP desde docker logs y escribe capturas en E2E_SALIDA (por defecto docs/evidencias/e2e). Estos PNG/JPG se conservan. No se ejecutaron acciones E2E sobre datos vivos.

## Productores adicionales, sólo revisión

Se conservan sin retirar estas funciones/scripts, por instrucción expresa.

- `scripts/generar_figuras_tesis_sprint4.py:122` generar_figura_3_17: revisar cuerpo: diagrama/mockup o valores fijados en ax.text; no se consulta un servicio en ejecución.
- `scripts/generar_figuras_tesis_sprint4.py:203` generar_figura_3_22: revisar cuerpo: diagrama/mockup o valores fijados en ax.text; no se consulta un servicio en ejecución.
- `scripts/generar_figuras_tesis_sprint4.py:329` copiar_a_cerebro: revisar cuerpo: diagrama/mockup o valores fijados en ax.text; no se consulta un servicio en ejecución.
- `scripts/generar_figura_3_17_logs.py:25` generar_figura_3_17: revisar cuerpo: diagrama/mockup o valores fijados en ax.text; no se consulta un servicio en ejecución.
- `scripts/generar_figura_3_25_json.py:25` generar_figura_3_25: revisar cuerpo: diagrama/mockup o valores fijados en ax.text; no se consulta un servicio en ejecución.
- `scripts/generar_figuras_tesis_sprint5_6.py:153` generar_figura_3_25: revisar cuerpo: diagrama/mockup o valores fijados en ax.text; no se consulta un servicio en ejecución.
- `scripts/generar_figuras_tesis_sprint5_6.py:543` generar_figura_3_35: revisar cuerpo: diagrama/mockup o valores fijados en ax.text; no se consulta un servicio en ejecución.
- `scripts/generar_figuras_tesis_sprint5_6.py:584` generar_figura_3_36: texto/carga fija a revisar (curl_output, HTTP/1.1).
- `scripts/generar_figuras_tesis_sprint5_6.py:674` copiar_a_cerebro: revisar cuerpo: diagrama/mockup o valores fijados en ax.text; no se consulta un servicio en ejecución.
