-- ADW L0-3 · cifras de la DW equivalentes a las que muestra la web (formato: cifra|valor|valor2)
select 'est_distintos_acad' as cifra, count(distinct id_estudiante)::text as v1, null::text as v2 from fact_rendimiento_academico
union all select 'est_distintos_fin', count(distinct id_estudiante)::text, null from fact_situacion_financiera
union all select 'est_union_acad_fin', count(*)::text, null from (select id_estudiante from fact_rendimiento_academico union select id_estudiante from fact_situacion_financiera) x
union all select 'est_dim_no_deprecado', count(*)::text, null from dim_estudiante where not coalesce(deprecado,false)
union all select 'est_mora2_distintos_y_deuda', count(distinct id_estudiante)::text, round(sum(monto_deuda)::numeric,2)::text from fact_situacion_financiera where cuotas_impagas>=2
union all select 'deuda_total_todas_gestiones', round(sum(monto_deuda)::numeric,2)::text, null from fact_situacion_financiera
union all select 'deuda_estado_mora_prev', round(sum(monto_deuda) filter (where estado_cartera in ('Mora','Previsionable'))::numeric,2)::text, null from fact_situacion_financiera
union all select 'monto_pagado_total_y_filas', round(coalesce(sum(monto_pagado),0)::numeric,2)::text, count(monto_pagado)::text from fact_situacion_financiera
union all select 'rent_2026_ejecutado_y_meta', round(sum(r.monto_ejecutado)::numeric,2)::text, round(sum(r.monto_meta)::numeric,2)::text from fact_rentabilidad r join dim_tiempo t using(id_tiempo) where t.gestion=2026
union all select 'rent_2026_meta_hasta_mayo', round(sum(r.monto_meta)::numeric,2)::text, null from fact_rentabilidad r join dim_tiempo t using(id_tiempo) where t.gestion=2026 and t.mes<=5
union all select 'eval_puntuacion_ge1_y_docentes', count(*)::text, count(distinct id_docente)::text from fact_evaluacion_docente where puntuacion>=1
union all select 'eval_prom_escala5', round(avg(puntuacion)::numeric,3)::text, null from fact_evaluacion_docente where puntuacion>=1 and escala_max=5
union all select 'dim_docente', count(*)::text, null from dim_docente
union all select 'dim_docente_nombre_largo_gt60', count(*)::text, null from dim_docente where length(nombre_completo)>60
union all select 'dim_modulo_total_y_con_pos', count(*)::text, count(pos_code)::text from dim_modulo
union all select 'dim_modulo_nombre_numerico', count(*)::text, null from dim_modulo where nombre_modulo ~ '^[0-9 :.-]+$'
union all select 'dim_modulo_MOD-GEN', count(*)::text, null from dim_modulo where pos_code like 'MOD-GEN%'
union all select 'stg_pendientes', count(*)::text, null from stg_entidad_no_resuelta where not resuelto
union all select 'stg_pendientes_lote35', count(*)::text, null from stg_entidad_no_resuelta s join dim_origen_documental d using(id_documento) where not s.resuelto and d.id_lote=35
union all select 'dim_origen_documental', count(*)::text, null from dim_origen_documental
union all select 'lote', count(*)::text, null from lote
union all select 'log_auditoria_nlp', count(*)::text, null from log_auditoria_nlp
union all select 'riesgo_academico_prom_le70', count(distinct id_estudiante)::text, null from bi.vw_riesgo_estudiante where regla_a_academico = 1
union all select 'riesgo_financiero', count(distinct id_estudiante)::text, round(sum(deuda_total_bs)::numeric,2)::text from bi.vw_riesgo_estudiante where regla_f_financiero = 1
union all select 'riesgo_critico_k2', count(distinct id_estudiante)::text, null from bi.vw_riesgo_estudiante where k_reglas>=2;
