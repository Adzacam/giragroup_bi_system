# F8-2 Layout Check (`1280×800`, Claro y Oscuro)

1. **`UserProfileDropdown.jsx`**: añadido `flexShrink: 0` al avatar circular (`42px × 42px`) para evitar compresión ovalada.
2. **`GestionUsuarios.jsx`**: compactados padding (`4px 10px` / `4px 8px`), gap (`6px`) y tipografía (`11.5px`) en la columna `Acciones` con `whiteSpace: 'nowrap'` para evitar scroll horizontal en `1280×800`.
3. **`v2-layout.css`**: añadida regla explícita `@media (min-width: 769px) { .v2-mobile-bottom-wrap { display: none !important; } }` para que la barra inferior móvil nunca aparezca ni solape tarjetas en `1280×800`.

## Verificación visual en navegador (`http://localhost:5173`, `1280×800`, claro y oscuro)
- **Avatar `UserProfileDropdown`**: `34×34` en botón y `42×42` circular (`flex-shrink: 0`) en el menú desplegable, sin aplastamiento en ambos temas.
- **`/v2/admin/usuarios`**: ajuste limpio (`1134.67px === 1134.67px`, `0px` de desborde horizontal) en claro y oscuro. (En V1 `/admin/usuarios`, la tabla tiene `21px` de scroll interno dentro de su tarjeta debido al sidebar fijo de `276px`, sin desborde de página).
- **`/v2/academico/rendimiento`**: `.v2-mobile-bottom-wrap` oculto (`isVisible === false`), sin solapamiento con acciones inferiores en ambos temas.
- **Consola JS / Vite**: `0` errores JS de página; `25/25` suites Vitest aprobadas y build Vite limpio (`dist/`).
