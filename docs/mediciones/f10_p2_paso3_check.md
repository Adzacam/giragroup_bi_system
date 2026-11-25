# F10-3b: Paso 3 Tarjetas HITL y Banda Baja

- `revision_formularios.py` y `revision_hechos.py`: los casos con `confianza < 0.60` ahora reportan `en la banda baja (< 0,60)` en lugar de `[0,60; 0,85)`.
- `CasoDetallePanel.jsx`: chips contextualizados por área (`financiera`, `evaluacion_docente`, `comercial`, `academica`), recomendación explícita y línea original con entidades IOB2 una sola vez dentro de `<details>`.
