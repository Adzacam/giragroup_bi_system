# F0 B-3 — resultado provisional

Seis filas de conteos se recuperaron de spans guardados tras una inferencia local A/B/C. La escritura del reporte inicial falló por un escalar numpy; la procedencia inicial no quedó persistida. Estos resultados son provisionales hasta repetir con el sidecar que fija los hashes antes de inferir.

Gold completo y visible con el tokenizer actual: **510** entidades. No se reproduce **503**, ni hay siete IDs demostrables de exclusión. La truncación a 128 no explica esta diferencia con los bytes actuales. No se alteró gold ni modelo para forzar una conciliación.

[Conteos](f0_b3_conteos.json), [resultados provisionales](f0_b3_ablacion.json), [spans sin texto](f0_b3_predicciones.json). B-3 permanece parcialmente pendiente.
