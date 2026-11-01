// Registro del Service Worker (solo en build de producción: en `vite dev` interferiría con HMR).
export function registrarServiceWorker() {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch((error) => {
      console.warn('No se pudo registrar el Service Worker:', error);
    });
  });
}

// Borra las respuestas de API cacheadas: se llama al cerrar sesión.
export function limpiarCacheApi() {
  navigator.serviceWorker?.controller?.postMessage({ type: 'CLEAR_API_CACHE' });
}
