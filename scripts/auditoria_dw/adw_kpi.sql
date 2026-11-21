-- ADW L0 · bloque KPI: los 23 KPI de bi.vw_cmi_scorecard en todas las gestiones (solo SELECT)
SELECT gestion, perspectiva, codigo, nombre, unidad, valor, meta, umbral_verde, umbral_ambar, semaforo, puntaje
FROM bi.vw_cmi_scorecard
ORDER BY gestion, codigo;
