# Auditoría Visual y Técnica FV3-1 — 2026-11-24

- **Origen auditado**: `http://localhost:5173` (sesión `admin_general`, rol `Administrador`, `data-theme="light"` y `data-theme="dark"`).
- **Rutas visitadas**: 16 rutas (`/v2/dashboard`, `/v2/dataops/*`, `/v2/academico/*`, `/v2/financiero/*`, `/v2/reportes`, `/v2/ajustes`, `/v2/admin/usuarios`).
- **Consola JS**: 0 excepciones fatales sin capturar.
- **Cookies / Almacenamiento**: Sin cookies `Set-Cookie`/`Cookie` en `5173`; sesión y preferencias en `localStorage` (`11.7 KB` reportados en `/v2/ajustes`).
- **Red**: Fallos `502 Bad Gateway` en `/api/v1/*` durante la auditoría en vivo (permitió evaluar el comportamiento de estados de error y resiliencia en todas las vistas).

## Hallazgos priorizados (Contraste / Claro-Oscuro / Heurísticas de Nielsen)

1. **[CRÍTICO · Contraste Oscuro]** `Exportar CMI` (`/v2/dashboard`): el icono de descarga tiene color dorado sobre fondo dorado en modo oscuro, haciéndolo casi invisible.
2. **[CRÍTICO · Modo Oscuro / Popover]** Menú desplegable de usuario (`NavbarV2`):
   - Botón `Cerrar Sesión` mantiene fondo pastel claro de Modo Claro en Modo Oscuro.
   - Ancho insuficiente del popover: `2FA Verificado` se recorta (`2FA Verific...`), usuario/correo truncados y `Mi Perfil` envuelve en 3 líneas.
3. **[CRÍTICO · Layout / Heurística #8]** `MobileBottomNavV2` (`Navegación Móvil en Pastilla V2`): permanece fija también en escritorio (`1280×800`) y solapa contenido inferior en múltiples vistas (`/v2/dashboard`, `/v2/dataops/ingesta`, `/v2/academico/rendimiento`, `/v2/financiero/metas`, `/v2/reportes`, `/v2/ajustes`).
4. **[ALTO · Accesibilidad / Heurística #3]** Modal `Crear Nuevo Usuario` (`/v2/admin/usuarios`): carece de `role="dialog"`, `aria-modal="true"`, cierre con `Escape` y foco inicial/retorno, a diferencia de `Perfil de Usuario & Credenciales`.
5. **[ALTO · Heurística #1 y #9]** Visibilidad de errores de red vs valores en `0`:
   - `SidebarV2` muestra `Base de datos: Conectada` en verde incluso con `502 Bad Gateway` en `/api/v1/*`.
   - `/v2/dataops/datos-maestros` queda en `Consultando registros...` indefinidamente si la consulta falla.
   - `/v2/academico/docente`, `/v2/financiero/recaudacion` y `/v2/financiero/cartera` muestran badge verde `Verificado` / `Sin saldo · Bs. 0` cuando la petición falla.
   - `/v2/dataops/revision` muestra `Selecciona un lote desde el historial de carga.` sin enlace o botón directo al historial.
6. **[MEDIO · Consistencia / Contraste]**
   - `/v2/academico/rendimiento`: badge `ALERTA CRÍTICA` con contraste apagado en modo oscuro.
   - `/v2/financiero/proyeccion`: placeholder `Bs. —k / año` y grilla de 4 tarjetas apilada verticalmente en escritorio.
   - `/v2/admin/usuarios`: política de contraseña inconsistente (`Mínimo 8 caracteres` vs `mínimo 6 caracteres`) y badge `(Tu sesión)` partido en dos líneas.
   - Falta `<meta name="color-scheme" content="light dark">` en `index.html` y `color-scheme: light` explícito en `[data-ui-version="v2"]`.
