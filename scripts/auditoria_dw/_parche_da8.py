"""Parche DA8: metas y recaudacion del pronostico financiero con TODAS las categorias (PROGRAMAS + TECHOS_CERRADOS)."""


def parchear(ruta, cambios):
    s = open(ruta, encoding="utf-8").read()
    for a, b in cambios:
        assert s.count(a) == 1, (ruta, s.count(a), a[:70])
        s = s.replace(a, b)
    open(ruta, "w", encoding="utf-8").write(s)


parchear("backend/services/forecast_service.py", [(
    """_SQL_META_VS_EJECUTADO = text(\"\"\"
    SELECT dt.gestion, dt.mes,
           SUM(fr.monto_meta)::float AS meta,
           SUM(fr.monto_ejecutado)::float AS ejecutado
    FROM public.fact_rentabilidad fr
    JOIN public.dim_categoria_financiera dcf ON fr.id_categoria = dcf.id_categoria
    JOIN public.dim_tiempo dt ON fr.id_tiempo = dt.id_tiempo
    WHERE dcf.nombre_categoria = 'PROGRAMAS'
    GROUP BY dt.gestion, dt.mes""",
    """# ADW DA8 (Lean, 2026-11-20): meta y recaudacion cuentan TODAS las categorias (PROGRAMAS + TECHOS_CERRADOS), igual que
# el CMI (bi.vw_metas_mensual). Antes solo PROGRAMAS y la misma pantalla contradecia al CMI (31,4 % frente a 31,7 %).
_SQL_META_VS_EJECUTADO = text(\"\"\"
    SELECT dt.gestion, dt.mes,
           SUM(fr.monto_meta)::float AS meta,
           SUM(fr.monto_ejecutado)::float AS ejecutado
    FROM public.fact_rentabilidad fr
    JOIN public.dim_tiempo dt ON fr.id_tiempo = dt.id_tiempo
    GROUP BY dt.gestion, dt.mes""")])

parchear("pipeline/analytics/time_series_extractor.py", [(
    """    "META_MENSUAL_PROGRAMAS": \"\"\"
        SELECT
            dt.periodo_mes,
            COALESCE(fr.monto_ejecutado, fr.monto_meta)::numeric AS valor
        FROM public.fact_rentabilidad fr
        JOIN public.dim_categoria_financiera dcf ON fr.id_categoria = dcf.id_categoria
        JOIN public.dim_tiempo dt ON fr.id_tiempo = dt.id_tiempo
        WHERE dcf.nombre_categoria = 'PROGRAMAS'
          AND COALESCE(fr.monto_ejecutado, fr.monto_meta) IS NOT NULL
        ORDER BY dt.periodo_mes;
    \"\"\",""",
    """    # ADW DA8: todas las categorias (el nombre de la clave se conserva). Por mes: lo ejecutado si el mes tiene algun dato
    # ejecutado; si no, la meta. Nunca se mezcla ejecutado de una categoria con meta de otra dentro del mismo mes.
    "META_MENSUAL_PROGRAMAS": \"\"\"
        SELECT
            dt.periodo_mes,
            (CASE WHEN COUNT(fr.monto_ejecutado) > 0 THEN SUM(fr.monto_ejecutado) ELSE SUM(fr.monto_meta) END)::numeric AS valor
        FROM public.fact_rentabilidad fr
        JOIN public.dim_tiempo dt ON fr.id_tiempo = dt.id_tiempo
        GROUP BY dt.periodo_mes
        HAVING COUNT(fr.monto_ejecutado) > 0 OR COUNT(fr.monto_meta) > 0
        ORDER BY dt.periodo_mes;
    \"\"\","""),
    ("""        FROM public.fact_rentabilidad fr
        JOIN public.dim_categoria_financiera dcf ON fr.id_categoria = dcf.id_categoria
        JOIN public.dim_tiempo dt ON fr.id_tiempo = dt.id_tiempo
        WHERE dcf.nombre_categoria = 'PROGRAMAS'
          AND fr.monto_ejecutado IS NOT NULL
          AND dt.gestion < EXTRACT(YEAR FROM CURRENT_DATE)""",
     """        FROM public.fact_rentabilidad fr
        JOIN public.dim_tiempo dt ON fr.id_tiempo = dt.id_tiempo
        WHERE fr.monto_ejecutado IS NOT NULL
          AND dt.gestion < EXTRACT(YEAR FROM CURRENT_DATE)"""),
])
print("ok")
