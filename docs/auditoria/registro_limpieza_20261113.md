# REGISTRO FINAL PARA ENVÍO — 13-nov-2026

Versión ampliada tras revisar raíz, Power BI, output, docs y evidencias. Se conserva el registro de la primera limpieza y, a continuación, el detalle de esta ampliación. La carpeta temporal docs/limpieza se elimina por solicitud expresa; este documento y la evidencia final mínima tienen rutas estables.

# Registro de limpieza — fase 2

Autorización explícita del usuario; rama `limpieza-repo`. Respaldo `pre-limpieza` = `5850dd4b81b429cceafc3cbfb45aaa38ebdba524`. Fecha de cierre: 2026-11-13T11:09:01.510357-04:00. Código validado en `df033e90ca17223eaf69fdcccd9e3b77367e98f8`; el commit documental posterior contiene este registro y la actualización de referencias. Ningún historial se reescribió.

## Resultados antes y después

| Control | Offline inicial | DW aislada antes | DW aislada después |
| --- | --- | --- | --- |
| Pytest | 629 passed, 5 failed, 11 skipped, 7 xfailed | 634 passed, 0 failed, 11 skipped, 7 xfailed | 634 passed, 0 failed, 11 skipped, 7 xfailed |
| Colección | 652 únicas | 652 únicas | 652 únicas; mismo conjunto por mapa |
| Cobertura | 68,384758 % (9.619/14.066) | 68,448742 % (9.628/14.066) | 68,448742 % (9628/14.066) |
| Node | 5 passed | 5 passed en verificación de sprint5 | 5 passed; independientes de pytest |
| Frontend build | exit 0 | sin cambios de código frontend | exit 0; frontend_build_despues.txt |
| Compose config | exit 0 | compose.yml aislado exit 0 | config original y stack aislado exit 0 |
| Contenedores | no se levantaron | 2 DB tmpfs saludables | 9/9 healthchecks saludables, proyecto separado |


Diferencia de cobertura controlada: **0,000000 puntos**, dentro de ±0,1. Frente al offline: 0,063984 puntos; este contraste además cambia disponibilidad del DW. Comparación decisiva: misma copia de datos y mismos flags antes/después. No cambió omit ni el denominador (14.066). Las 58 sentencias frente a 14.008 son anteriores a esta limpieza; backend, pipeline y microservicios se conservaron por hash.

Los cinco fallos offline eran cuatro casos de test_forecasting y el contrato antes llamado test_loop4_validacion_estricta_contratos. Esperaban datos/método/horizonte y recibían sin_datos. Pasan con la copia aislada del snapshot. No se ocultaron con skip ni se modificaron sus aserciones.

## Conciliación de 650 y 652

`pytest --collect-only -q` contra una extracción temporal de `f3b37d9` dio 650 (collect_f3b37d9.txt). Los dos IDs nuevos de `ac9ea1f`, medidos antes de limpiar en `5850dd4`, son:

- `tests/test_person_resolver_preparado.py::test_el_catalogo_se_prepara_una_vez_y_se_rehace_si_cambia`
- `tests/test_person_resolver_preparado.py::test_preparado_equivale_al_algoritmo_original`

Después ambos están en tests/sprint3/test_person_resolver_preparado.py. No se añadieron/retiraron casos durante la limpieza; cero IDs perdidos/duplicados después de normalizar sólo rutas. Las aserciones AST originales y nuevas coinciden en todos los archivos de tests del mapa. La extracción/ZIP temporales de referencia se retiraron tras conservar la colección.

## Commits y verificaciones

Cada commit de ejecución tuvo una verificación posterior. Las rápidas por sprint omiten únicamente la prueba de filas extensas por su costo; la suite completa final sí la ejecuta. Las verificaciones de otros temas usan 18 pruebas smoke de infraestructura, ingesta y KPI. No fue necesario revertir ningún commit.

| Tema | Commit | Suite rápida posterior | Node | Revertido |
| --- | --- | --- | --- | --- |
| respaldo | 5b46c81d23585e7b2783a9ee81e026897c45b96d | exit 0 | exit 0 | no |
| generadores | f106550933f2a35c570c5f0d37883cb87713fccd | exit 0 | exit 0 | no |
| imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 | exit 0 | exit 0 | no |
| archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 | exit 0 | exit 0 | no |
| sprint1 | cfab9814c71116c704b5c934ba3d420422fe94f4 | exit 0 | exit 0 | no |
| sprint2 | edb1452f24abb1d559f27cf1cce957f2fcb48f88 | exit 0 | exit 0 | no |
| sprint3 | 200fad6098639b85d55ad72942831f1bf0c7bf4c | exit 0 | exit 0 | no |
| sprint4 | 38ebadbd4437f476133cf3b49d03a517dbe82d6c | exit 0 | exit 0 | no |
| sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 | exit 0 | exit 0 | no |
| sprint6 | 71e9aa785d96b61f9f5025cb1684acd60ae59d43 | exit 0 | exit 0 | no |
| transversales | df033e90ca17223eaf69fdcccd9e3b77367e98f8 | exit 0 | exit 0 | no |


Los logs de la primera fase se conservaron en su historial Git; la evidencia compacta vigente está en docs/evidencias/validacion_20261113/. El commit de cierre documental puede identificarse con `git log -1 -- docs/auditoria/registro_limpieza_20261113.md`; también recibe smoke posterior.

## Eliminado, archivado y movido

Los borrados y movimientos versionados se realizaron con git rm/git mv. Se retiraron 83 PNG de las cuatro carpetas aprobadas, cuatro alias v2 exactos (se hallaron cuatro, no cinco) y cinco scripts de terminal. No se regeneraron ni alteraron cifras de gráficos existentes. Archivos archivados conservan bytes/hash; Jira_Proyecto.csv era local e ignorado y se incorporó directamente en su ubicación archivada.

| Acción | Ruta anterior | Ruta actual | Bytes originales | Motivo/tema | Commit |
| --- | --- | --- | --- | --- | --- |
| eliminado | docs/evidencias/graficos/figura_3_40_captura_pytest_475.png |  | 313664 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/figura_3_50_captura_cobertura_60_8.png |  | 379152 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/figura_3_5_esquema_constelacion_fisico.png |  | 864645 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/grafico_3_2_distribucion_lote_1387.png |  | 88424 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/grafico_3_4_serie_temporal_holt_winters.png |  | 218776 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/grafico_4_1_excepciones_calidad_lote.png |  | 112857 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/grafico_4_1_inconsistencias_corpus.png |  | 112857 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/grafico_4_2_confianza_probabilistica.png |  | 88424 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/grafico_4_2_distribucion_lote_1387.png |  | 88424 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/grafico_4_3_distribucion_archivo_lote_1387.png |  | 184676 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/grafico_4_3_resolucion_por_formato.png |  | 184676 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/grafico_4_4_kpi_cmi_perspectivas.png |  | 121962 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/grafico_4_4_kpis_cmi.png |  | 121962 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos/grafico_4_5_tiempo_consolidacion_semilog.png |  | 145352 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos_v2/grafico_4_1_inconsistencias_corpus.png |  | 178619 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos_v2/grafico_4_2_confianza_probabilistica.png |  | 122530 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos_v2/grafico_4_3_distribucion_archivo_lote_1387.png |  | 134341 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/evidencias/graficos_v2/grafico_4_4_kpis_cmi.png |  | 121962 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras/grafico_3_2_bandas_confianza_lote1387.png |  | 65852 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras/grafico_4_1_motivos_derivacion.png |  | 98449 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras/grafico_4_2_destino_lote.png |  | 100400 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras/grafico_4_3_consolidacion_por_origen.png |  | 62119 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras/grafico_4_4_kpi_por_perspectiva.png |  | 121962 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras/grafico_4_5_tiempo_consolidacion_semilog.png |  | 149026 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras_tesis/figura_3_10_codigo_despachador.png |  | 254847 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras_tesis/figura_3_11_codigo_lectura_hojas_formularios.png |  | 218718 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras_tesis/figura_3_12_diagrama_flujo_ner_beto_rapidfuzz.png |  | 256097 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras_tesis/figura_3_13_codigo_inicializacion_beto.png |  | 225628 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras_tesis/figura_3_14_codigo_emparejamiento_difuso.png |  | 210039 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras_tesis/figura_3_15_captura_logs_extraccion_hitl.png |  | 264302 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras_tesis/figura_3_9_diagrama_actividad_ingesta.png |  | 261594 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras_tesis/grafico_3_1_matriz_confusion_beto.png |  | 140492 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras_tesis/grafico_3_2_distribucion_confianza_probabilistica.png |  | 118773 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/figuras_tesis/grafico_3_3_metricas_por_tipo_entidad.png |  | 132576 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_1_40_resumen_pytest.png |  | 342505 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_12_diagrama_flujo_beto_rapidfuzz.png |  | 398975 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_16_diagrama_casos_de_uso_backend.png |  | 591100 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_17_captura_logs_extraccion_semantica.png |  | 348561 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_17_diagrama_secuencia_jwt_pipeline.png |  | 271855 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_22_captura_respuesta_json_forecast.png |  | 411106 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_23_diagrama_casos_de_uso_frontend.png |  | 611000 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_24_mockup_login_e_ingesta.png |  | 222862 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_25_captura_respuesta_json_forecast.png |  | 331523 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_25_mockup_hitl_y_alertas.png |  | 279156 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_26_mockup_cmi_powerbi.png |  | 307466 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_2_arquitectura_fisica_orquestacion.png |  | 588332 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_31_dashboard_cmi_academico.png |  | 197592 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_32_dashboard_cmi_financiero.png |  | 197074 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_33_diagrama_secuencia_e2e.png |  | 260776 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_34_captura_pytest_cobertura.png |  | 256585 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_35_captura_postman_runner.png |  | 247543 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_35_captura_pytest_cobertura.png |  | 256585 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_36_captura_seguridad_owasp.png |  | 252312 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_36_validacion_postman.png |  | 247543 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_37_captura_docker_ps.png |  | 216942 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_37_pruebas_verificacion_sprint5.png |  | 451454 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_39_captura_pytest_cobertura.png |  | 391545 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_3_diagrama_despliegue_docker_compose.png |  | 538617 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_40_captura_pytest_475.png |  | 313664 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_41_evidencia_objetivo_2_esquema_constelacion.png |  | 173878 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_42_captura_seguridad_owasp.png |  | 373735 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_42_evidencia_objetivo_3_lote_unificado.png |  | 262493 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_43_captura_docker_ps_9_servicios.png |  | 219177 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_43_evidencia_objetivo_4_entidades_beto_rapidfuzz.png |  | 243762 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_44_evidencia_objetivo_5_proyecciones_cmi.png |  | 191559 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_45_evidencia_objetivo_6_reporte_pruebas_calidad.png |  | 237920 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_4_modelo_conceptual_hefesto.png |  | 396303 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_50_captura_cobertura_60_8.png |  | 379152 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_5_esquema_constelacion_fisico.png |  | 864645 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_6_diagrama_clases_orm_pydantic.png |  | 490720 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/figura_3_9_diagrama_actividad_ingesta.png |  | 364494 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_3_1_matriz_confusion_beto.png |  | 167241 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_3_2_distribucion_confianza_probabilistica.png |  | 112279 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_3_2_distribucion_lote_1387.png |  | 88424 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_3_3_desempeno_metricas_beto.png |  | 163383 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_3_3_desempeno_metricas_por_entidad.png |  | 113755 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_3_4_serie_temporal_holt_winters.png |  | 218776 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_3_5_tendencia_lineal_ols.png |  | 137481 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_4_1_excepciones_calidad_lote.png |  | 112857 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_4_1_inconsistencias_corpus.png |  | 112857 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_4_2_confianza_probabilistica.png |  | 88424 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_4_2_distribucion_lote_1387.png |  | 88424 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_4_3_distribucion_archivo_lote_1387.png |  | 184676 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_4_3_resolucion_por_formato.png |  | 184676 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_4_4_disponibilidad_kpi_cmi.png |  | 121962 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_4_5_tiempo_consolidacion_semilog.png |  | 145352 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | docs/images/grafico_4_6_evaluacion_likert_pre_post.png |  | 145032 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | scripts/generar_figura_1_40.py |  | 5179 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | scripts/generar_figura_3_37_sprint5_tests.py |  | 7631 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | scripts/generar_figura_3_39_pytest_cobertura.py |  | 8437 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | scripts/generar_figura_3_42_seguridad.py |  | 7491 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| eliminado | scripts/generar_figura_docker_ps_9_servicios.py |  | 5461 | imagenes | 998c8ed680b4155ef92660843c9735e0269d3184 |
| archivado | docs/INFORME_CONSIDERACIONES_SEGURIDAD_GIRAGROUP_BI.md | _archivo/docs/INFORME_CONSIDERACIONES_SEGURIDAD_GIRAGROUP_BI.md | 54751 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado (antes ignorado) | docs/Proyecto de grado/Jira_Proyecto.csv | _archivo/docs/Proyecto de grado/Jira_Proyecto.csv | 32853 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_01_catalogo_tablas.csv | _archivo/docs/apendices/csv/F_01_catalogo_tablas.csv | 2792 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_02_fact_rendimiento_academico.csv | _archivo/docs/apendices/csv/F_02_fact_rendimiento_academico.csv | 2486 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_03_fact_situacion_financiera.csv | _archivo/docs/apendices/csv/F_03_fact_situacion_financiera.csv | 2521 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_04_fact_cobranzas_proyectadas.csv | _archivo/docs/apendices/csv/F_04_fact_cobranzas_proyectadas.csv | 807 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_05_fact_evaluacion_docente.csv | _archivo/docs/apendices/csv/F_05_fact_evaluacion_docente.csv | 1016 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_06_fact_marketing.csv | _archivo/docs/apendices/csv/F_06_fact_marketing.csv | 788 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_07_fact_rentabilidad.csv | _archivo/docs/apendices/csv/F_07_fact_rentabilidad.csv | 896 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_08_fact_forecast.csv | _archivo/docs/apendices/csv/F_08_fact_forecast.csv | 1073 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_09_dim_tiempo.csv | _archivo/docs/apendices/csv/F_09_dim_tiempo.csv | 992 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_10_dim_estudiante.csv | _archivo/docs/apendices/csv/F_10_dim_estudiante.csv | 1780 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_11_dim_docente.csv | _archivo/docs/apendices/csv/F_11_dim_docente.csv | 527 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_12_dim_modulo.csv | _archivo/docs/apendices/csv/F_12_dim_modulo.csv | 789 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_13_dim_origen_documental.csv | _archivo/docs/apendices/csv/F_13_dim_origen_documental.csv | 1410 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_14_dim_categoria_financiera.csv | _archivo/docs/apendices/csv/F_14_dim_categoria_financiera.csv | 632 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_15_dim_meta.csv | _archivo/docs/apendices/csv/F_15_dim_meta.csv | 546 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_16_cat_institucion.csv | _archivo/docs/apendices/csv/F_16_cat_institucion.csv | 549 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_17_cat_categoria_financiera.csv | _archivo/docs/apendices/csv/F_17_cat_categoria_financiera.csv | 595 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_18_cat_docente.csv | _archivo/docs/apendices/csv/F_18_cat_docente.csv | 435 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_18_staging_registros_crudos.csv | _archivo/docs/apendices/csv/F_18_staging_registros_crudos.csv | 1912 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_19_cat_modulo.csv | _archivo/docs/apendices/csv/F_19_cat_modulo.csv | 423 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_19_stg_entidad_no_resuelta.csv | _archivo/docs/apendices/csv/F_19_stg_entidad_no_resuelta.csv | 2504 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_20_log_pipeline_ingesta.csv | _archivo/docs/apendices/csv/F_20_log_pipeline_ingesta.csv | 808 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_20_staging_registros_crudos.csv | _archivo/docs/apendices/csv/F_20_staging_registros_crudos.csv | 1912 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_21_log_inconsistencias.csv | _archivo/docs/apendices/csv/F_21_log_inconsistencias.csv | 1175 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_21_stg_entidad_no_resuelta.csv | _archivo/docs/apendices/csv/F_21_stg_entidad_no_resuelta.csv | 2504 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_22_log_auditoria_nlp.csv | _archivo/docs/apendices/csv/F_22_log_auditoria_nlp.csv | 631 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_22_log_pipeline_ingesta.csv | _archivo/docs/apendices/csv/F_22_log_pipeline_ingesta.csv | 808 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_23_log_inconsistencias.csv | _archivo/docs/apendices/csv/F_23_log_inconsistencias.csv | 1175 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_23_schema_migrations.csv | _archivo/docs/apendices/csv/F_23_schema_migrations.csv | 270 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_24_log_auditoria_nlp.csv | _archivo/docs/apendices/csv/F_24_log_auditoria_nlp.csv | 631 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_24_users.csv | _archivo/docs/apendices/csv/F_24_users.csv | 1386 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_25_notifications.csv | _archivo/docs/apendices/csv/F_25_notifications.csv | 975 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_25_schema_migrations.csv | _archivo/docs/apendices/csv/F_25_schema_migrations.csv | 270 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_26_lote.csv | _archivo/docs/apendices/csv/F_26_lote.csv | 562 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_26_users.csv | _archivo/docs/apendices/csv/F_26_users.csv | 1386 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_27_notifications.csv | _archivo/docs/apendices/csv/F_27_notifications.csv | 975 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_27_relaciones.csv | _archivo/docs/apendices/csv/F_27_relaciones.csv | 2897 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_28_lote.csv | _archivo/docs/apendices/csv/F_28_lote.csv | 562 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/F_29_relaciones.csv | _archivo/docs/apendices/csv/F_29_relaciones.csv | 3015 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_01_catalogo_tablas.csv | _archivo/docs/apendices/csv/G_01_catalogo_tablas.csv | 1381 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_02_cat_programa.csv | _archivo/docs/apendices/csv/G_02_cat_programa.csv | 1268 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_03_cat_modulo.csv | _archivo/docs/apendices/csv/G_03_cat_modulo.csv | 681 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_04_cat_docente.csv | _archivo/docs/apendices/csv/G_04_cat_docente.csv | 594 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_05_cat_escuela.csv | _archivo/docs/apendices/csv/G_05_cat_escuela.csv | 327 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_06_cat_tipo_programa.csv | _archivo/docs/apendices/csv/G_06_cat_tipo_programa.csv | 389 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_07_cat_modalidad.csv | _archivo/docs/apendices/csv/G_07_cat_modalidad.csv | 370 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_08_cat_estado_academico.csv | _archivo/docs/apendices/csv/G_08_cat_estado_academico.csv | 416 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_09_cat_estado_reprobado.csv | _archivo/docs/apendices/csv/G_09_cat_estado_reprobado.csv | 415 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_10_cat_estado_arca.csv | _archivo/docs/apendices/csv/G_10_cat_estado_arca.csv | 381 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_11_cat_tipo_cartera.csv | _archivo/docs/apendices/csv/G_11_cat_tipo_cartera.csv | 578 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_12_cat_concepto_financiero.csv | _archivo/docs/apendices/csv/G_12_cat_concepto_financiero.csv | 1015 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_13_cat_historico_equivalencia.csv | _archivo/docs/apendices/csv/G_13_cat_historico_equivalencia.csv | 857 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_14_cat_etiqueta_clasificacion.csv | _archivo/docs/apendices/csv/G_14_cat_etiqueta_clasificacion.csv | 844 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_15_cat_mapeo_columna.csv | _archivo/docs/apendices/csv/G_15_cat_mapeo_columna.csv | 580 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_16_cat_guia_texto_plano.csv | _archivo/docs/apendices/csv/G_16_cat_guia_texto_plano.csv | 656 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_17_ref_metas_gestion.csv | _archivo/docs/apendices/csv/G_17_ref_metas_gestion.csv | 824 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/apendices/csv/G_18_relaciones.csv | _archivo/docs/apendices/csv/G_18_relaciones.csv | 396 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/auditoria/plan_maestro_ejecucion.md | _archivo/docs/auditoria/plan_maestro_ejecucion.md | 21134 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/auditoria/production_readiness_2026-11-01.md | _archivo/docs/auditoria/production_readiness_2026-11-01.md | 23143 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/performance/informe_rendimiento.md | _archivo/docs/performance/informe_rendimiento.md | 66073 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/testing/Makefile | _archivo/docs/testing/Makefile | 4020 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/testing/ci.yml | _archivo/docs/testing/ci.yml | 3374 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/testing/diff_aislamiento_smtp_db.patch | _archivo/docs/testing/diff_aislamiento_smtp_db.patch | 4724 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/testing/informe_pruebas.md | _archivo/docs/testing/informe_pruebas.md | 22505 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/testing/skeletons/test_auth_otp.py | _archivo/docs/testing/skeletons/test_auth_otp.py | 3835 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/testing/skeletons/test_forecast_constraints.py | _archivo/docs/testing/skeletons/test_forecast_constraints.py | 2280 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/testing/skeletons/test_health.py | _archivo/docs/testing/skeletons/test_health.py | 2358 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/testing/skeletons/test_ingestion_security.py | _archivo/docs/testing/skeletons/test_ingestion_security.py | 2377 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/testing/skeletons/test_kpis.py | _archivo/docs/testing/skeletons/test_kpis.py | 3675 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/testing/skeletons/test_ner_thresholds.py | _archivo/docs/testing/skeletons/test_ner_thresholds.py | 2143 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/testing/skeletons/test_risk_rules.py | _archivo/docs/testing/skeletons/test_risk_rules.py | 3490 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| archivado | docs/testing/test.sh | _archivo/docs/testing/test.sh | 2198 | archivo | 4af30f1ad5bfcb76912a8dafd2eaceab26228800 |
| movido | tests/test_esquema_alineado_ddl.py | tests/sprint1/test_esquema_alineado_ddl.py | 4201 | sprint1 | cfab9814c71116c704b5c934ba3d420422fe94f4 |
| movido | tests/test_migraciones_arranque.py | tests/sprint1/test_migraciones_arranque.py | 3711 | sprint1 | cfab9814c71116c704b5c934ba3d420422fe94f4 |
| movido | tests/test_datos_reales_pipeline.py | tests/sprint2/test_datos_reales_pipeline.py | 11957 | sprint2 | edb1452f24abb1d559f27cf1cce957f2fcb48f88 |
| movido | tests/test_fecha_corte_moodle.py | tests/sprint2/test_fecha_corte_moodle.py | 1629 | sprint2 | edb1452f24abb1d559f27cf1cce957f2fcb48f88 |
| movido | tests/test_formatos_genericos.py | tests/sprint2/test_formatos_genericos.py | 2629 | sprint2 | edb1452f24abb1d559f27cf1cce957f2fcb48f88 |
| movido | tests/test_cedula_prefijo_ci.py | tests/sprint3/test_cedula_prefijo_ci.py | 1436 | sprint3 | 200fad6098639b85d55ad72942831f1bf0c7bf4c |
| movido | tests/test_coherencia_estado_notas.py | tests/sprint3/test_coherencia_estado_notas.py | 3850 | sprint3 | 200fad6098639b85d55ad72942831f1bf0c7bf4c |
| movido | tests/test_extractor_estudiante_ci.py | tests/sprint3/test_extractor_estudiante_ci.py | 2809 | sprint3 | 200fad6098639b85d55ad72942831f1bf0c7bf4c |
| movido | tests/test_fecha_fuera_de_rango.py | tests/sprint3/test_fecha_fuera_de_rango.py | 1152 | sprint3 | 200fad6098639b85d55ad72942831f1bf0c7bf4c |
| movido | tests/test_fk_resolver_padron.py | tests/sprint3/test_fk_resolver_padron.py | 1915 | sprint3 | 200fad6098639b85d55ad72942831f1bf0c7bf4c |
| movido | tests/test_person_resolver.py | tests/sprint3/test_person_resolver.py | 3826 | sprint3 | 200fad6098639b85d55ad72942831f1bf0c7bf4c |
| movido | tests/test_person_resolver_preparado.py | tests/sprint3/test_person_resolver_preparado.py | 5146 | sprint3 | 200fad6098639b85d55ad72942831f1bf0c7bf4c |
| movido | tests/test_pipeline_financiero.py | tests/sprint3/test_pipeline_financiero.py | 3828 | sprint3 | 200fad6098639b85d55ad72942831f1bf0c7bf4c |
| movido | tests/test_reduccion_hitl.py | tests/sprint3/test_reduccion_hitl.py | 2314 | sprint3 | 200fad6098639b85d55ad72942831f1bf0c7bf4c |
| movido | tests/test_auth_and_rbac.py | tests/sprint4/test_auth_and_rbac.py | 22342 | sprint4 | 38ebadbd4437f476133cf3b49d03a517dbe82d6c |
| movido | tests/test_cmi_historial.py | tests/sprint4/test_cmi_historial.py | 2390 | sprint4 | 38ebadbd4437f476133cf3b49d03a517dbe82d6c |
| movido | tests/test_forecasting.py | tests/sprint4/test_forecasting.py | 11663 | sprint4 | 38ebadbd4437f476133cf3b49d03a517dbe82d6c |
| movido | tests/test_holtwinters_cobertura.py | tests/sprint4/test_holtwinters_cobertura.py | 4531 | sprint4 | 38ebadbd4437f476133cf3b49d03a517dbe82d6c |
| movido | tests/test_kpi_service.py | tests/sprint4/test_kpi_service.py | 8997 | sprint4 | 38ebadbd4437f476133cf3b49d03a517dbe82d6c |
| movido | tests/test_rentabilidad_ejecutado_meta.py | tests/sprint4/test_rentabilidad_ejecutado_meta.py | 4470 | sprint4 | 38ebadbd4437f476133cf3b49d03a517dbe82d6c |
| movido | tests/test_risk_service.py | tests/sprint4/test_risk_service.py | 15872 | sprint4 | 38ebadbd4437f476133cf3b49d03a517dbe82d6c |
| movido | tests/test_staging_idempotente.py | tests/sprint4/test_staging_idempotente.py | 955 | sprint4 | 38ebadbd4437f476133cf3b49d03a517dbe82d6c |
| movido | e2e/ciclo_ui.mjs | tests/sprint5/ciclo_ui.mjs | 7615 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | e2e/mapeo_ui.mjs | tests/sprint5/mapeo_ui.mjs | 2422 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/revision_cola.test.mjs | tests/sprint5/revision_cola.test.mjs | 1987 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/revision_espera.test.mjs | tests/sprint5/revision_espera.test.mjs | 1037 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_bandeja_grupos.py | tests/sprint5/test_bandeja_grupos.py | 13309 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_bandeja_hechos_en_revision.py | tests/sprint5/test_bandeja_hechos_en_revision.py | 9534 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_bandeja_hitl_ruido_y_un_clic.py | tests/sprint5/test_bandeja_hitl_ruido_y_un_clic.py | 8465 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_catalogo_modulos.py | tests/sprint5/test_catalogo_modulos.py | 2932 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_dataops_catalogo_bitacora.py | tests/sprint5/test_dataops_catalogo_bitacora.py | 9415 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_dataops_censura.py | tests/sprint5/test_dataops_censura.py | 1703 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_dataops_ingesta_historial.py | tests/sprint5/test_dataops_ingesta_historial.py | 6651 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_dataops_integridad.py | tests/sprint5/test_dataops_integridad.py | 10477 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_dataops_lectura_beto.py | tests/sprint5/test_dataops_lectura_beto.py | 13487 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_dataops_revision.py | tests/sprint5/test_dataops_revision.py | 12282 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_dataops_texto_preparado.py | tests/sprint5/test_dataops_texto_preparado.py | 6906 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_dedup_por_contenido.py | tests/sprint5/test_dedup_por_contenido.py | 2510 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_elegir_tipo_fuente.py | tests/sprint5/test_elegir_tipo_fuente.py | 978 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_email_redesign_and_forgot_password.py | tests/sprint5/test_email_redesign_and_forgot_password.py | 8292 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_evaluacion_docente_revision.py | tests/sprint5/test_evaluacion_docente_revision.py | 3919 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_ingesta_sin_timeout.py | tests/sprint5/test_ingesta_sin_timeout.py | 9041 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_powerbi_retencion.py | tests/sprint5/test_powerbi_retencion.py | 2057 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/test_reportes_export.py | tests/sprint5/test_reportes_export.py | 11338 | sprint5 | 9c0086618417149310b7374fc96131bdfec2dd30 |
| movido | tests/load/locust_readiness.py | tests/sprint6/locust_readiness.py | 5314 | sprint6 | 71e9aa785d96b61f9f5025cb1684acd60ae59d43 |
| movido | tests/test_otp_entorno_pruebas.py | tests/sprint6/test_otp_entorno_pruebas.py | 1914 | sprint6 | 71e9aa785d96b61f9f5025cb1684acd60ae59d43 |
| movido | tests/test_sprint4_verification_loops.py | tests/sprint6/test_seguridad_y_resiliencia_api.py | 14562 | sprint6 | 71e9aa785d96b61f9f5025cb1684acd60ae59d43 |
| movido | tests/test_agnostic_classifier_and_dw_reset.py | tests/transversales/test_agnostic_classifier_and_dw_reset.py | 17524 | transversales | df033e90ca17223eaf69fdcccd9e3b77367e98f8 |


Los cuatro alias retirados tienen igualdad SHA-256 verificada con su canónico en PREBORRADO_REFERENCIAS.md. Los diez PNG canónicos de graficos_v2 conservan sus hashes originales. Se mantienen todos los otros PNG/JPG en evidencias, incluidos E2E.

## Mapa completo de tests

Conftest raíz y soporte tests/dataops_parches.py permanecen en su ruta. Ajustados imports de fixtures, búsqueda de raíz, SQLite temporal, Makefile, imports MJS y README. CI conserva explícitamente los mismos 26 archivos históricos y sus flags, para evitar ampliar silenciosamente su selección al mover tests; la validación de 652 se hizo con toda la suite. backend/test_upload.py y backend/tests/test_lote_estado_flujo.py siguen fuera de testpaths y no se incorporaron a la colección.

| Archivo anterior | Archivo actual | Tema |
| --- | --- | --- |
| backend/test_upload.py | backend/test_upload.py | fuera de testpaths actual; conservar hasta decisión expresa |
| backend/tests/test_lote_estado_flujo.py | backend/tests/test_lote_estado_flujo.py | fuera de testpaths actual; conservar hasta decisión expresa |
| e2e/ciclo_ui.mjs | tests/sprint5/ciclo_ui.mjs | plataforma web/DataOps E2E |
| e2e/mapeo_ui.mjs | tests/sprint5/mapeo_ui.mjs | plataforma web/DataOps E2E |
| tests/load/locust_readiness.py | tests/sprint6/locust_readiness.py | carga, seguridad y validación de calidad |
| tests/readiness/test_production_readiness.py | tests/readiness/test_production_readiness.py | puertas de salida |
| tests/revision_cola.test.mjs | tests/sprint5/revision_cola.test.mjs | plataforma web y DataOps |
| tests/revision_espera.test.mjs | tests/sprint5/revision_espera.test.mjs | plataforma web y DataOps |
| tests/sprint1/test_esquema_constelacion_hefesto.py | tests/sprint1/test_esquema_constelacion_hefesto.py | conservar suite existente |
| tests/sprint1/test_infraestructura_y_docker.py | tests/sprint1/test_infraestructura_y_docker.py | conservar suite existente |
| tests/sprint1/test_modelos_orm_sqlalchemy.py | tests/sprint1/test_modelos_orm_sqlalchemy.py | conservar suite existente |
| tests/sprint1/test_usuarios_semilla_rbac.py | tests/sprint1/test_usuarios_semilla_rbac.py | conservar suite existente |
| tests/sprint2/test_bloques_detector.py | tests/sprint2/test_bloques_detector.py | conservar suite existente |
| tests/sprint2/test_categorizacion_y_cierre.py | tests/sprint2/test_categorizacion_y_cierre.py | conservar suite existente |
| tests/sprint2/test_ingesta.py | tests/sprint2/test_ingesta.py | conservar suite existente |
| tests/sprint3/test_area2_confianza_telemetria.py | tests/sprint3/test_area2_confianza_telemetria.py | conservar suite existente |
| tests/sprint3/test_area3_normalizacion_matching_fk.py | tests/sprint3/test_area3_normalizacion_matching_fk.py | conservar suite existente |
| tests/sprint3/test_area4_calidad_auditoria.py | tests/sprint3/test_area4_calidad_auditoria.py | conservar suite existente |
| tests/sprint3/test_asymmetric_flattener_and_summary.py | tests/sprint3/test_asymmetric_flattener_and_summary.py | conservar suite existente |
| tests/sprint3/test_catalogos_db.py | tests/sprint3/test_catalogos_db.py | conservar suite existente |
| tests/sprint3/test_cross_source_reconciliation.py | tests/sprint3/test_cross_source_reconciliation.py | conservar suite existente |
| tests/sprint3/test_financial_and_quality_post_steps.py | tests/sprint3/test_financial_and_quality_post_steps.py | conservar suite existente |
| tests/sprint3/test_financial_catalog_matching.py | tests/sprint3/test_financial_catalog_matching.py | conservar suite existente |
| tests/sprint3/test_financial_rules_engine.py | tests/sprint3/test_financial_rules_engine.py | conservar suite existente |
| tests/sprint3/test_financial_validator.py | tests/sprint3/test_financial_validator.py | conservar suite existente |
| tests/sprint3/test_formatter_gira40.py | tests/sprint3/test_formatter_gira40.py | conservar suite existente |
| tests/sprint3/test_ner_engine_gira10.py | tests/sprint3/test_ner_engine_gira10.py | conservar suite existente |
| tests/sprint4/test_alert_engine.py | tests/sprint4/test_alert_engine.py | conservar suite existente |
| tests/sprint4/test_alertas_tempranas_vista3.py | tests/sprint4/test_alertas_tempranas_vista3.py | conservar suite existente |
| tests/sprint4/test_anonimizacion.py | tests/sprint4/test_anonimizacion.py | conservar suite existente |
| tests/sprint4/test_cmi_y_laboratorio_predictivo.py | tests/sprint4/test_cmi_y_laboratorio_predictivo.py | conservar suite existente |
| tests/sprint4/test_dw_loader.py | tests/sprint4/test_dw_loader.py | conservar suite existente |
| tests/sprint4/test_kpis_and_catalogs.py | tests/sprint4/test_kpis_and_catalogs.py | conservar suite existente |
| tests/sprint4/test_rbac_enforcement.py | tests/sprint4/test_rbac_enforcement.py | conservar suite existente |
| tests/test_agnostic_classifier_and_dw_reset.py | tests/transversales/test_agnostic_classifier_and_dw_reset.py | archivo mixto: ingesta (2), NER (3) y seguridad del reset DW (4/6); conservar entero para evitar dividir IDs |
| tests/test_auth_and_rbac.py | tests/sprint4/test_auth_and_rbac.py | identidad de acceso y RBAC |
| tests/test_bandeja_grupos.py | tests/sprint5/test_bandeja_grupos.py | plataforma web y DataOps |
| tests/test_bandeja_hechos_en_revision.py | tests/sprint5/test_bandeja_hechos_en_revision.py | plataforma web y DataOps |
| tests/test_bandeja_hitl_ruido_y_un_clic.py | tests/sprint5/test_bandeja_hitl_ruido_y_un_clic.py | plataforma web y DataOps |
| tests/test_catalogo_modulos.py | tests/sprint5/test_catalogo_modulos.py | plataforma web y DataOps |
| tests/test_cedula_prefijo_ci.py | tests/sprint3/test_cedula_prefijo_ci.py | identidad, normalización, reglas financieras y calidad de entidades |
| tests/test_cmi_historial.py | tests/sprint4/test_cmi_historial.py | DW, KPI, CMI, alertas, pronósticos y staging |
| tests/test_coherencia_estado_notas.py | tests/sprint3/test_coherencia_estado_notas.py | identidad, normalización, reglas financieras y calidad de entidades |
| tests/test_dataops_catalogo_bitacora.py | tests/sprint5/test_dataops_catalogo_bitacora.py | plataforma web y DataOps |
| tests/test_dataops_censura.py | tests/sprint5/test_dataops_censura.py | plataforma web y DataOps |
| tests/test_dataops_ingesta_historial.py | tests/sprint5/test_dataops_ingesta_historial.py | plataforma web y DataOps |
| tests/test_dataops_integridad.py | tests/sprint5/test_dataops_integridad.py | plataforma web y DataOps |
| tests/test_dataops_lectura_beto.py | tests/sprint5/test_dataops_lectura_beto.py | plataforma web y DataOps |
| tests/test_dataops_revision.py | tests/sprint5/test_dataops_revision.py | plataforma web y DataOps |
| tests/test_dataops_texto_preparado.py | tests/sprint5/test_dataops_texto_preparado.py | plataforma web y DataOps |
| tests/test_datos_reales_pipeline.py | tests/sprint2/test_datos_reales_pipeline.py | lectura e ingesta de fuentes |
| tests/test_dedup_por_contenido.py | tests/sprint5/test_dedup_por_contenido.py | plataforma web y DataOps |
| tests/test_elegir_tipo_fuente.py | tests/sprint5/test_elegir_tipo_fuente.py | plataforma web y DataOps |
| tests/test_email_redesign_and_forgot_password.py | tests/sprint5/test_email_redesign_and_forgot_password.py | plataforma web y DataOps |
| tests/test_esquema_alineado_ddl.py | tests/sprint1/test_esquema_alineado_ddl.py | esquema e infraestructura |
| tests/test_evaluacion_docente_revision.py | tests/sprint5/test_evaluacion_docente_revision.py | plataforma web y DataOps |
| tests/test_extractor_estudiante_ci.py | tests/sprint3/test_extractor_estudiante_ci.py | identidad, normalización, reglas financieras y calidad de entidades |
| tests/test_fecha_corte_moodle.py | tests/sprint2/test_fecha_corte_moodle.py | lectura e ingesta de fuentes |
| tests/test_fecha_fuera_de_rango.py | tests/sprint3/test_fecha_fuera_de_rango.py | identidad, normalización, reglas financieras y calidad de entidades |
| tests/test_fk_resolver_padron.py | tests/sprint3/test_fk_resolver_padron.py | identidad, normalización, reglas financieras y calidad de entidades |
| tests/test_forecasting.py | tests/sprint4/test_forecasting.py | DW, KPI, CMI, alertas, pronósticos y staging |
| tests/test_formatos_genericos.py | tests/sprint2/test_formatos_genericos.py | lectura e ingesta de fuentes |
| tests/test_holtwinters_cobertura.py | tests/sprint4/test_holtwinters_cobertura.py | DW, KPI, CMI, alertas, pronósticos y staging |
| tests/test_ingesta_sin_timeout.py | tests/sprint5/test_ingesta_sin_timeout.py | plataforma web y DataOps |
| tests/test_kpi_service.py | tests/sprint4/test_kpi_service.py | DW, KPI, CMI, alertas, pronósticos y staging |
| tests/test_migraciones_arranque.py | tests/sprint1/test_migraciones_arranque.py | esquema e infraestructura |
| tests/test_otp_entorno_pruebas.py | tests/sprint6/test_otp_entorno_pruebas.py | seguridad y entorno de pruebas |
| tests/test_person_resolver.py | tests/sprint3/test_person_resolver.py | identidad, normalización, reglas financieras y calidad de entidades |
| tests/test_person_resolver_preparado.py | tests/sprint3/test_person_resolver_preparado.py | identidad, normalización, reglas financieras y calidad de entidades |
| tests/test_pipeline_financiero.py | tests/sprint3/test_pipeline_financiero.py | identidad, normalización, reglas financieras y calidad de entidades |
| tests/test_powerbi_retencion.py | tests/sprint5/test_powerbi_retencion.py | plataforma web y DataOps |
| tests/test_reduccion_hitl.py | tests/sprint3/test_reduccion_hitl.py | identidad, normalización, reglas financieras y calidad de entidades |
| tests/test_rentabilidad_ejecutado_meta.py | tests/sprint4/test_rentabilidad_ejecutado_meta.py | DW, KPI, CMI, alertas, pronósticos y staging |
| tests/test_reportes_export.py | tests/sprint5/test_reportes_export.py | plataforma web y DataOps |
| tests/test_risk_service.py | tests/sprint4/test_risk_service.py | DW, KPI, CMI, alertas, pronósticos y staging |
| tests/test_sprint4_verification_loops.py | tests/sprint6/test_seguridad_y_resiliencia_api.py | carga, seguridad y validación de calidad |
| tests/test_staging_idempotente.py | tests/sprint4/test_staging_idempotente.py | DW, KPI, CMI, alertas, pronósticos y staging |

## Figuras que requieren captura real o regeneración

La última autorización permitió retirar los PNG y scripts enumerados sin generar reemplazos ficticios. No hay nuevas capturas PNG en este trabajo: las salidas reales TXT, JUnit, JSON y healthchecks son verificables y sirven de origen para las capturas pendientes.

| Figura | Estado y fuente real requerida |
| --- | --- |
| 1.40; 3.39; 3.40; 3.50 | Capturar terminal real de la suite completa y coverage; archivos despues_pytest.txt / despues/coverage.json. No reutilizar paneles 650/632 ni 493/475. |
| 3.37 sprint5 | Capturar la corrida real de tests/sprint5 y Node; validacion/checks/sprint5/. |
| 3.42 | Capturar cabeceras HTTP reales y comprobaciones de seguridad; no dibujar respuestas cURL. |
| Docker ps / 3.37 en mixto | Capturar docker compose ps del proyecto aislado con 9 healthchecks; healthchecks.jsonl y stack_up.txt. |
| 3.15 | mostrar_logs_figura_3_15.py emite logging.info/warning con valores fijos: sí, simulación. Se conserva; sustituir por logs reales de ingesta. |
| 3.17 | mostrar_logs_figura_3_17.py y generar_figura_3_17_logs.py usan líneas fijas: sí. El diagrama de secuencia homónimo de sprint4 es conceptual y se conserva. |
| 3.22 | generar_figuras_tesis_sprint4.py::generar_figura_3_22 usa json_alumnos/json_metas literales: sí. Se conserva, recapturar API real. |
| 3.25 | generar_figura_3_25_json.py usa JSON literal: sí. El mockup HITL de sprint5 es conceptual; ambos productores se conservan sin retiro adicional. |
| 3.35 | runner_text contiene 18/18 Tests Passed y duraciones fijas: sí. Se conserva; requiere Postman/Newman real. |
| 3.36 | curl_output contiene HTTP/1.1 y cabeceras fijas: sí. Se conserva; requiere HTTP real. |
| Diagramas PNG retirados | Regenerar desde los scripts de diagramas conservados; la constelación mantiene docs/figuras_src/figura_3_5_constelacion_dw.mmd. |


Los productores generar_graficos_* y el oficial graficos_tesis_v2 escriben sólo en graficos_v2, sin copias a images/output/artefactos externos ni creación de los alias retirados. Se retiraron únicamente las funciones 3.34/3.37 del mixto sprint5_6 y 3.40/3.50 de ronda_final. e2e/lib.mjs no lee graficos/: se conservaron sus capturas. El generador de la fuente de verdad usa las rutas canónicas y las métricas reales de esta ejecución. Los productores históricos conservan sus datos previos; no fueron ejecutados para sobrescribir gráficos finales.

## Tamaño y conservación

| Métrica | Bytes |
| --- | --- |
| Árbol original versionado (pre-limpieza) | 73916648 |
| Retirados del árbol de trabajo por borrado | 21214486 |
| Archivados; sin ahorro local | 314320 |
| Árbol original después, descontando sólo borrados | 52702162 |
| Total local de referencia fase1 (sin .git/entregables) | 2328289218 |
| Local comparable estimado sin nuevos entregables | 2307074732 |


Los entregables/logs de auditoría y los builds temporales agregan bytes; “retirados” no afirma ahorro neto del disco. Git conserva todos los objetos históricos y no se compactó ni reescribió. Archivar no libera espacio local. No se borraron entornos/dependencias del disco: los regenerables ya estaban ignorados y no tenían entradas versionadas que quitar con git rm --cached. Se añadieron patrones de perfiles y exclusiones, con excepción para perfiles de evidencia.


Se verificaron por SHA-256 **628 archivos protegidos** conservados. Microservicios completos, backend/pipeline, modelo/fixtures versionados, seeds/migraciones, figuras_src y evidencias finales se mantienen. Las seis copias backend/scripts se conservaron: además de sus referencias históricas, retirarlas cambia el alcance/denominador de cobertura. Makefile y .env se conservaron; .env sigue fuera de Git. Se conservan inventario_tablas*.json, tiempos_ciclo_mensual*.json (incluida corrida3 previa a A), root diccionario_datos.csv por compatibilidad y todos los __init__.py. Los CSV de apendices (los nueve duplicados y los restantes) se archivaron por aprobación expresa.

## Cambios para la tesis y citas

PREBORRADO_REFERENCIAS.md distingue rutas de archivo, basename y simples números de figura antes de borrar. RUTAS_CITADAS_CAMBIADAS.tsv enumera cada ruta afectada y todas sus ubicaciones previas. Las referencias en evidencias históricas/JSON y el DOCX de tablas se conservan como evidencia: no se reescribieron binarios ni mediciones. Las referencias en Markdown vigente se actualizaron; las capturas sin reemplazo quedan expresamente pendientes.

1. Tabla 3.29, GCB-42 y matriz de trazabilidad: aplicar MAPA_TESTS.tsv y el desglose actual por sprint; total 652, 634/11/7/0, con commit y fecha.
2. Tabla 3.30 y cobertura: usar 14.066 y la cobertura medida aquí, sin mezclar el denominador 14.008 o cifras 493/475. Se actualizó la sección D de ambas fuentes de verdad y su generador.
3. Actualizar referencias a docs históricos y CSV a _archivo/<ruta-original>; el diccionario textual vigente permanece en docs/apendices/diccionario_datos.md.
4. Actualizar las referencias gráficas a los nombres canónicos y obtener las capturas reales listadas arriba antes de publicar la tesis. El DOCX tablas_v2 y los pies/citas numéricas deben revisarse editorialmente.
5. No cambian las cifras finales de negocio del snapshot, sus huellas ni los informes de medición finales. El dump original conserva SHA-256 14d45f5a128f44543927911dc0ad453f681d524ac05037203f5c0c2787e3a2eb. No se conectó a la DW viva ni se tocaron sus contenedores/volúmenes.


### Medición efectiva después

Mismo alcance local que fase 1: se excluyen .git y docs/limpieza; incluye dependencias y cachés conservadas. La variación neta también refleja bytes de documentación modificada y cachés de pruebas; no equivale sólo a los borrados.

| Medición | Bytes |
| --- | --- |
| Local antes | 2328289218 |
| Local después, medido | 2308215885 |
| Árbol versionado después, sin entregables de limpieza | 52711393 |


Detalle reproducible: validacion/TAMANOS.json. Los entregables nuevos se mantienen separados para no presentar su crecimiento como ahorro.

### Cierre del SQLite temporal

El commit documental 0f9f49c pasó su smoke posterior (18 passed). Se conservan ignoradas tanto tests/test_auth_temp.db (remanente anterior) como tests/sprint5/test_auth_temp.db (ruta actual), sin borrar bases locales ni dependencias. El ajuste ec6e865 pasó su verificación posterior (18 passed); el log local está en validacion/checks/registro/ignores/.

El commit documental 0f9f49c y el ajuste ec6e865 completan los commits de ejecución listados arriba. Esta medición final toma tamaños del disco, con sus finales de línea reales; conserva las mismas exclusiones que fase 1. La revisión documental posterior no cambia código, pruebas ni datos.

## Ampliación solicitada sobre las capturas

| Tema | Commit | Verificación posterior |
| --- | --- | --- |
| archivar fuentes Power BI | e0f6d2d68e12a95013bbae442ab2dddd9c9aafa7 | 8 passed |
| ordenar documentos y archivar evidencias intermedias | e46dd3fa682ec8689aca281788997c8eb4ae7b8c | 8 passed |
| ordenar raiz y salidas historicas | 3973c29a5cfc96665628a776db79bbedba1d06b1 | 17 passed |

### Cambios por archivo

No se borraron fuentes ni datos para decidir que eran innecesarios. Lo histórico se archivó, lo vigente se agrupó y se actualizaron lectores/productores y referencias. Los archivos locales que estaban ignorados siguen ignorados; no se incorporaron datos personales al versionado al moverlos.

| Ruta anterior | Ruta actual | Motivo | Bytes | Versionado |
| --- | --- | --- | --- | --- |
| powerbi/cmi/01_power_query.pq | _archivo/powerbi/cmi/01_power_query.pq | Fuentes de autoría Power BI: archivo aprobado; PBIX activo conservado | 3943 | sí |
| powerbi/cmi/02_medidas_cmi.dax | _archivo/powerbi/cmi/02_medidas_cmi.dax | Fuentes de autoría Power BI: archivo aprobado; PBIX activo conservado | 7207 | sí |
| powerbi/cmi/03_tema_giragroup_cmi.json | _archivo/powerbi/cmi/03_tema_giragroup_cmi.json | Fuentes de autoría Power BI: archivo aprobado; PBIX activo conservado | 2125 | sí |
| powerbi/cmi/04_tabular_editor.cs | _archivo/powerbi/cmi/04_tabular_editor.cs | Fuentes de autoría Power BI: archivo aprobado; PBIX activo conservado | 9297 | sí |
| powerbi/cmi/05_generar_paginas.py | _archivo/powerbi/cmi/05_generar_paginas.py | Fuentes de autoría Power BI: archivo aprobado; PBIX activo conservado | 19438 | sí |
| powerbi/cmi/README.md | _archivo/powerbi/cmi/README.md | Fuentes de autoría Power BI: archivo aprobado; PBIX activo conservado | 6346 | sí |
| docs/dataops-loop1.md | _archivo/docs/dataops-loop1.md | Bitácora de iteración histórica; contenido preservado | 3574 | sí |
| docs/dataops-loop2.md | _archivo/docs/dataops-loop2.md | Bitácora de iteración histórica; contenido preservado | 4300 | sí |
| docs/dataops-loop3.md | _archivo/docs/dataops-loop3.md | Bitácora de iteración histórica; contenido preservado | 4365 | sí |
| docs/dataops-loop4.md | _archivo/docs/dataops-loop4.md | Bitácora de iteración histórica; contenido preservado | 6159 | sí |
| docs/dataops-loop5.md | _archivo/docs/dataops-loop5.md | Bitácora de iteración histórica; contenido preservado | 5787 | sí |
| docs/dataops-loop6.md | _archivo/docs/dataops-loop6.md | Bitácora de iteración histórica; contenido preservado | 8360 | sí |
| docs/dataops-loop7.md | docs/architecture/dataops_router.md | Arquitectura vigente del router | 2525 | sí |
| docs/estimacion-fase-c.md | docs/mediciones/estimacion-fase-c.md | Medición final, perfil o línea base histórica relevante; no se modifica la evidencia | 8091 | sí |
| docs/optimizacion-flujo-dataops-A.md | docs/mediciones/optimizacion-flujo-dataops-A.md | Medición final, perfil o línea base histórica relevante; no se modifica la evidencia | 8657 | sí |
| docs/medicion-flujo-dataops-repetida.md | docs/mediciones/medicion-flujo-dataops-repetida.md | Medición final, perfil o línea base histórica relevante; no se modifica la evidencia | 3763 | sí |
| docs/perfil-flujo-dataops.md | docs/mediciones/perfil-flujo-dataops.md | Medición final, perfil o línea base histórica relevante; no se modifica la evidencia | 4618 | sí |
| docs/medicion-flujo-dataops.md | _archivo/docs/medicion-flujo-dataops.md | Primera medición sustituida por medición repetida; conservar histórico | 2150 | sí |
| docs/propuesta-correccion-inscripciones.md | docs/propuestas/propuesta-correccion-inscripciones.md | Propuesta pendiente: se organiza, nunca se ejecuta SQL | 5505 | sí |
| docs/propuesta-correccion-inscripciones.sql | docs/propuestas/propuesta-correccion-inscripciones.sql | Propuesta pendiente: se organiza, nunca se ejecuta SQL | 5600 | sí |
| docs/propuesta-integridad-loop6.json | docs/propuestas/propuesta-integridad-loop6.json | Propuesta pendiente: se organiza, nunca se ejecuta SQL | 56561 | sí |
| docs/propuesta-integridad-loop6.md | docs/propuestas/propuesta-integridad-loop6.md | Propuesta pendiente: se organiza, nunca se ejecuta SQL | 5198 | sí |
| docs/diseno_mockups_giragroup_bi.md | docs/diseno/diseno_mockups_giragroup_bi.md | Diseño conceptual por tema | 34374 | sí |
| docs/tablas_v2.md | docs/tesis/tablas_v2.md | Material editorial de tesis, agrupado; DOCX sin modificar | 55560 | sí |
| docs/tablas_v2.docx | docs/tesis/tablas_v2.docx | Material editorial de tesis, agrupado; DOCX sin modificar | 71250 | sí |
| docs/revision_tesis_cap1_3_4_5.md | docs/tesis/revision_tesis_cap1_3_4_5.md | Material editorial de tesis, agrupado; DOCX sin modificar | 24487 | sí |
| docs/postman_collection.json | docs/api/postman_collection.json | Colección de pruebas API, agrupada | 14996 | sí |
| docs/evidencias/cobertura_ronda6.json | _archivo/docs/evidencias/cobertura_ronda6.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 597099 | sí |
| docs/evidencias/pytest_completo_intermedio.txt | _archivo/docs/evidencias/pytest_completo_intermedio.txt | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 34642 | sí |
| docs/evidencias/pytest_completo_sin_env.txt | _archivo/docs/evidencias/pytest_completo_sin_env.txt | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 5398 | sí |
| docs/evidencias/ciclo_completo_antiguo_respuestas.json | _archivo/docs/evidencias/ciclo_completo_antiguo_respuestas.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 474 | sí |
| docs/evidencias/ciclo_completo_evaluacion_docente.json | _archivo/docs/evidencias/ciclo_completo_evaluacion_docente.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 433 | sí |
| docs/evidencias/ciclo_completo_n1.json | _archivo/docs/evidencias/ciclo_completo_n1.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 16832 | sí |
| docs/evidencias/ciclo_completo_n2.json | _archivo/docs/evidencias/ciclo_completo_n2.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 16826 | sí |
| docs/evidencias/corrida_final_ronda4_antes.json | _archivo/docs/evidencias/corrida_final_ronda4_antes.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 15297 | sí |
| docs/evidencias/corrida_final_ronda5.json | _archivo/docs/evidencias/corrida_final_ronda5.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 14934 | sí |
| docs/evidencias/corrida_final_1.json | _archivo/docs/evidencias/corrida_final_1.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 14934 | sí |
| docs/evidencias/corrida_final_2.json | _archivo/docs/evidencias/corrida_final_2.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 14934 | sí |
| docs/evidencias/lote_1387_uploads_data_arquitectura_b_dw_casi_vacio.json | _archivo/docs/evidencias/lote_1387_uploads_data_arquitectura_b_dw_casi_vacio.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 5362 | sí |
| docs/evidencias/lote_1387_uploads_data_arquitectura_b_previo_tarea1.json | _archivo/docs/evidencias/lote_1387_uploads_data_arquitectura_b_previo_tarea1.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 1738 | sí |
| docs/evidencias/lote_1387_uploads_data_arquitectura_b_regla_previa_dw_parcial.json | _archivo/docs/evidencias/lote_1387_uploads_data_arquitectura_b_regla_previa_dw_parcial.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 5370 | sí |
| docs/evidencias/lote_1387_uploads_data_arquitectura_b_ronda1_escalonada.json | _archivo/docs/evidencias/lote_1387_uploads_data_arquitectura_b_ronda1_escalonada.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 6134 | sí |
| docs/evidencias/lote_1387_uploads_data_arquitectura_b_ronda2_estado_C_sin_filtro_correos.json | _archivo/docs/evidencias/lote_1387_uploads_data_arquitectura_b_ronda2_estado_C_sin_filtro_correos.json | Corrida, ensayo o regresión intermedia sustituida; archivar sin eliminar | 6337 | sí |
| docs/evidencias/RESUMEN_RONDA2.md | _archivo/docs/evidencias/RESUMEN_RONDA2.md | Resumen histórico; conservar ronda 10 y las evidencias finales | 7163 | sí |
| docs/evidencias/RESUMEN_RONDA3.md | _archivo/docs/evidencias/RESUMEN_RONDA3.md | Resumen histórico; conservar ronda 10 y las evidencias finales | 6050 | sí |
| docs/evidencias/RESUMEN_RONDA4.md | _archivo/docs/evidencias/RESUMEN_RONDA4.md | Resumen histórico; conservar ronda 10 y las evidencias finales | 9048 | sí |
| docs/evidencias/RESUMEN_RONDA5.md | _archivo/docs/evidencias/RESUMEN_RONDA5.md | Resumen histórico; conservar ronda 10 y las evidencias finales | 7355 | sí |
| docs/evidencias/RESUMEN_RONDA6.md | _archivo/docs/evidencias/RESUMEN_RONDA6.md | Resumen histórico; conservar ronda 10 y las evidencias finales | 7310 | sí |
| docs/evidencias/RESUMEN_RONDA7.md | _archivo/docs/evidencias/RESUMEN_RONDA7.md | Resumen histórico; conservar ronda 10 y las evidencias finales | 6672 | sí |
| docs/evidencias/RESUMEN_RONDA8.md | _archivo/docs/evidencias/RESUMEN_RONDA8.md | Resumen histórico; conservar ronda 10 y las evidencias finales | 4363 | sí |
| docs/evidencias/RESUMEN_RONDA9.md | _archivo/docs/evidencias/RESUMEN_RONDA9.md | Resumen histórico; conservar ronda 10 y las evidencias finales | 7575 | sí |
| docs/evidencias/RESUMEN_TAREAS.md | _archivo/docs/evidencias/RESUMEN_TAREAS.md | Bitácora previa de tareas; preservada en archivo | 7514 | sí |
| docs/evidencias/flujo_repetido_A/corridas.json | _archivo/docs/evidencias/flujo_repetido_A/corridas.json | Versión previa: A2 y validación actual son las vigentes | 2644 | sí |
| docs/evidencias/flujo_repetido_A/flujo_corrida_1.json | _archivo/docs/evidencias/flujo_repetido_A/flujo_corrida_1.json | Versión previa: A2 y validación actual son las vigentes | 6696 | sí |
| docs/evidencias/flujo_repetido_A/flujo_corrida_2.json | _archivo/docs/evidencias/flujo_repetido_A/flujo_corrida_2.json | Versión previa: A2 y validación actual son las vigentes | 6693 | sí |
| docs/evidencias/flujo_repetido_A/flujo_corrida_3.json | _archivo/docs/evidencias/flujo_repetido_A/flujo_corrida_3.json | Versión previa: A2 y validación actual son las vigentes | 6696 | sí |
| docs/evidencias/flujo_repetido_A/huella_corrida_1.json | _archivo/docs/evidencias/flujo_repetido_A/huella_corrida_1.json | Versión previa: A2 y validación actual son las vigentes | 5585 | sí |
| docs/evidencias/flujo_repetido_A/huella_corrida_2.json | _archivo/docs/evidencias/flujo_repetido_A/huella_corrida_2.json | Versión previa: A2 y validación actual son las vigentes | 5585 | sí |
| docs/evidencias/flujo_repetido_A/huella_corrida_3.json | _archivo/docs/evidencias/flujo_repetido_A/huella_corrida_3.json | Versión previa: A2 y validación actual son las vigentes | 5546 | sí |
| docs/evidencias/flujo_repetido_A/recursos_corrida_1.json | _archivo/docs/evidencias/flujo_repetido_A/recursos_corrida_1.json | Versión previa: A2 y validación actual son las vigentes | 47034 | sí |
| docs/evidencias/flujo_repetido_A/recursos_corrida_2.json | _archivo/docs/evidencias/flujo_repetido_A/recursos_corrida_2.json | Versión previa: A2 y validación actual son las vigentes | 39172 | sí |
| docs/evidencias/flujo_repetido_A/recursos_corrida_3.json | _archivo/docs/evidencias/flujo_repetido_A/recursos_corrida_3.json | Versión previa: A2 y validación actual son las vigentes | 44849 | sí |
| docs/evidencias/flujo_repetido_A/resumen.json | _archivo/docs/evidencias/flujo_repetido_A/resumen.json | Versión previa: A2 y validación actual son las vigentes | 3501 | sí |
| docs/evidencias/regresion_s3/junit.xml | _archivo/docs/evidencias/regresion_s3/junit.xml | Versión previa: A2 y validación actual son las vigentes | 72080 | sí |
| docs/evidencias/regresion_s3/pytest_cov.txt | _archivo/docs/evidencias/regresion_s3/pytest_cov.txt | Versión previa: A2 y validación actual son las vigentes | 42425 | sí |
| confianza.csv | data/reproducibilidad/graficos/confianza.csv | Datos de entrada de gráficos: usados, reubicar actualizando productores/lectores | 133 | sí |
| inscritos.csv | data/reproducibilidad/graficos/inscritos.csv | Datos de entrada de gráficos: usados, reubicar actualizando productores/lectores | 700 | sí |
| recaudacion.csv | data/reproducibilidad/graficos/recaudacion.csv | Datos de entrada de gráficos: usados, reubicar actualizando productores/lectores | 64 | sí |
| test.conll | data/ner/test.conll | Corpus de evaluación usado por scripts NER; conservar bytes | 68783 | sí |
| metricas_ner.json | docs/evidencias/ner_evaluacion/metricas_ner.json | Resultado NER de autoría; conservar sin confundirlo con métricas finales del snapshot | 822 | sí |
| grafico_3_4.png | _archivo/raiz/grafico_3_4.png | Artefacto o documento histórico fuera de lugar; conservar sin borrar. Canonical SFV/diccionario permanece en docs | 217876 | sí |
| grafico_3_5.png | _archivo/raiz/grafico_3_5.png | Artefacto o documento histórico fuera de lugar; conservar sin borrar. Canonical SFV/diccionario permanece en docs | 137481 | sí |
| sprint2_test_resultado.md | _archivo/raiz/sprint2_test_resultado.md | Artefacto o documento histórico fuera de lugar; conservar sin borrar. Canonical SFV/diccionario permanece en docs | 0 | sí |
| sprint2_v2_resultado.md | _archivo/raiz/sprint2_v2_resultado.md | Artefacto o documento histórico fuera de lugar; conservar sin borrar. Canonical SFV/diccionario permanece en docs | 2446 | sí |
| fuente_verdad_tesis.md | _archivo/raiz/fuente_verdad_tesis.md | Artefacto o documento histórico fuera de lugar; conservar sin borrar. Canonical SFV/diccionario permanece en docs | 60010 | sí |
| diccionario_datos.csv | _archivo/raiz/diccionario_datos.csv | Artefacto o documento histórico fuera de lugar; conservar sin borrar. Canonical SFV/diccionario permanece en docs | 47828 | sí |
| run_sprint2.py | scripts/run_sprint2.py | Ejecutable manual de ingesta: agrupar scripts y mantener imports | 11325 | sí |
| locustfile.py | tests/sprint6/locust_carga_api.py | Escenario de carga: agrupar en sprint6, no añadirlo a pytest | 3587 | sí |
| output/figura_arquitectura_ner_rapidfuzz.png | _archivo/output/figura_arquitectura_ner_rapidfuzz.png | Exportación histórica o render de autoría; no es entrada operativa del pipeline | 685137 | sí |
| output/figura_arquitectura_ner_rapidfuzz.svg | docs/figuras_src/figura_arquitectura_ner_rapidfuzz.svg | Fuente vectorial de diagrama; conservar por tema | 10349 | sí |
| output/figura_casos_de_uso_general_sprint2.png | _archivo/output/figura_casos_de_uso_general_sprint2.png | Exportación histórica o render de autoría; no es entrada operativa del pipeline | 1449700 | sí |
| output/figura_casos_de_uso_general_sprint2.svg | docs/figuras_src/figura_casos_de_uso_general_sprint2.svg | Fuente vectorial de diagrama; conservar por tema | 10668 | sí |
| output/grafico_3_1_matriz_confusion_beto.png | _archivo/output/grafico_3_1_matriz_confusion_beto.png | Exportación histórica o render de autoría; no es entrada operativa del pipeline | 167241 | sí |
| output/grafico_3_3_desempeno_metricas_beto.png | _archivo/output/grafico_3_3_desempeno_metricas_beto.png | Exportación histórica o render de autoría; no es entrada operativa del pipeline | 163383 | sí |
| output/inventario_loc_proyecto.csv | _archivo/output/inventario_loc_proyecto.csv | Exportación histórica o render de autoría; no es entrada operativa del pipeline | 1778 | no; sigue local e ignorado |
| output/lote1387_beto_local.csv | _archivo/output/lote1387_beto_local.csv | Exportación histórica o render de autoría; no es entrada operativa del pipeline | 102343 | no; sigue local e ignorado |
| output/metricas_ner_robusto.json | _archivo/output/metricas_ner_robusto.json | Exportación histórica o render de autoría; no es entrada operativa del pipeline | 3577 | sí |
| output/reporte_robustez_layouts.json | _archivo/output/reporte_robustez_layouts.json | Exportación histórica o render de autoría; no es entrada operativa del pipeline | 1921 | sí |
| output/sprint2_documentos.csv | _archivo/output/sprint2_documentos.csv | Exportación histórica o render de autoría; no es entrada operativa del pipeline | 7056 | sí |
| output/tabla_3_19_recuento_uploads.csv | _archivo/output/tabla_3_19_recuento_uploads.csv | Exportación histórica o render de autoría; no es entrada operativa del pipeline | 6055 | no; sigue local e ignorado |

### Qué permanece en su lugar

- Raíz: configuración Docker/Git, .env, pyproject, conftest, Makefile, README y arranque/apagado/reconstrucción. Son contratos de ejecución. .coverage es un cache local ignorado; no forma parte del repositorio.
- Power BI: PBIX y guía activos en powerbi/dashboards; las seis fuentes se archivaron por aprobación expresa.
- output: cinco JSONL operativos (sprint2_documentos, sprint3_entidades_procesadas, inconsistencias, hechos persistidos, telemetría). El primero lo leen pruebas del formateador y el pipeline; el segundo lo lee el planificador.
- output/backups: intacto; nunca se inspeccionaron/modificaron sus datos. output/lote1387_archivos y test_gold_revision.csv se conservan como potencial reproducción/DUDOSO; ausencia de referencias no autoriza borrar.
- docs/evidencias: snapshot, huellas, inventarios de tablas, diccionario, finales de lote 1.387, KLM/ciclo_r8 citados, f1/ablación finales, JSON/JPG/PNG E2E, gráficos canónicos, perfiles y escenarios finales. Se archivaron los intermedios enumerados, nunca el snapshot ni los datos de negocio finales.
- Propuestas SQL: agrupadas en docs/propuestas; no se ejecutó ninguna.
- CSV de gráficos y corpus CONLL: son entradas usadas, no basura; se agruparon en data y se corrigieron sus rutas de código.

### Estado de carpetas de evidencias

| Carpeta actual | Archivos | Decisión |
| --- | --- | --- |
| docs/evidencias/benchmark_beto | 11 | conservar: evidencia final, línea base relevante o datos por revisar |
| docs/evidencias/deshacer_no_bloqueante | 1 | conservar: evidencia final, línea base relevante o datos por revisar |
| docs/evidencias/e2e | 11 | conservar: evidencia final, línea base relevante o datos por revisar |
| docs/evidencias/figuras_v2 | 0 | quitar carpeta vacía |
| docs/evidencias/flujo_A_cache_vacia | 11 | conservar: evidencia final, línea base relevante o datos por revisar |
| docs/evidencias/flujo_cache_vacia_A | 0 | quitar carpeta vacía |
| docs/evidencias/flujo_repetido | 8 | conservar: evidencia final, línea base relevante o datos por revisar |
| docs/evidencias/flujo_repetido_A | 0 | quitar carpeta vacía |
| docs/evidencias/flujo_repetido_A2 | 11 | conservar: evidencia final, línea base relevante o datos por revisar |
| docs/evidencias/graficos_v2 | 10 | conservar: evidencia final, línea base relevante o datos por revisar |
| docs/evidencias/ner_evaluacion | 1 | conservar: evidencia final, línea base relevante o datos por revisar |
| docs/evidencias/perfil_dataops | 4 | conservar: evidencia final, línea base relevante o datos por revisar |
| docs/evidencias/regresion_A | 4 | conservar: evidencia final, línea base relevante o datos por revisar |
| docs/evidencias/regresion_s3 | 0 | quitar carpeta vacía |
| docs/evidencias/una_pasada | 1 | conservar: evidencia final, línea base relevante o datos por revisar |
| docs/evidencias/validacion_20261113 | 13 | conservar: evidencia final, línea base relevante o datos por revisar |

Se quitan únicamente carpetas vacías al finalizar. Las carpetas flujo_repetido_A y regresion_s3 se archivaron completas; A2 y la validación actual permanecen. Una medición con tres réplicas no equivale a tres versiones obsoletas: se preserva su conjunto.

### Validación final de la ampliación

| Control | Resultado |
| --- | --- |
| Commit probado | 3973c29a5cfc96665628a776db79bbedba1d06b1 |
| Colección | 652 IDs únicos; mismo conjunto que antes |
| Pytest completo | 634 passed, 11 skipped, 7 xfailed, 0 failed |
| Cobertura | 68.44874164652353 %; 9628/14066 |
| Tolerancia vs base aislada | 0.0 puntos; límite ±0,1 |
| Node | 5 passed |
| Código runtime | backend/pipeline/services/frontend/db idéntico al cierre anterior |
| Evidencia vigente | docs/evidencias/validacion_20261113 |
| Snapshot | hash intacto; sin conexión a DW viva |

El build frontend y los nueve healthchecks aislados pasaron en la fase anterior; el código del frontend/runtime no cambió en esta ampliación. Sus resultados se conservan en la evidencia compacta. La última comprobación completa se realizó con PostgreSQL tmpfs aislada y nunca con la base viva.

### Retirada de docs/limpieza

Se eliminan inventarios auxiliares, scripts de auditoría de una sola ejecución, intentos fallidos, cachés y logs redundantes de esa carpeta. Se conserva únicamente este registro en docs/auditoria/registro_limpieza_20261113.md y el conjunto compacto de resultados reales en docs/evidencias/validacion_20261113. El detalle previo permanece también en el historial Git, sin reescribirlo. La copia para enviar está fuera del repositorio.

Las capturas reales pendientes y las correcciones editoriales del DOCX siguen siendo las enumeradas arriba; organizar archivos no equivale a recrear esas capturas.

Auxiliares retirados de docs/limpieza: 303 archivos, 18868939 bytes lógicos (incluidos cachés/builds locales). Es una retirada adicional de material creado durante la auditoría, separada de los 21.214.486 bytes de PNG/scripts retirados inicialmente. Los resultados compactos se conservaron antes de eliminar.
