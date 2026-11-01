/*
 * Service Worker de GiraGroup BI.
 * - Assets estáticos con hash de Vite, fuentes e íconos: Cache-First.
 * - Navegación (HTML): Network-First con la shell en caché como respaldo sin conexión.
 * - API: Network-First solo para lecturas GET de tableros (lista blanca). Auth, usuarios, DataOps,
 *   auditoría, notificaciones y pipeline nunca se cachean: llevan datos personales o efectos.
 * - Al cerrar sesión la app envía CLEAR_API_CACHE para que otro usuario del equipo no vea respuestas ajenas.
 */
const VERSION = 'v1';
const CACHE_ESTATICO = `gira-static-${VERSION}`;
const CACHE_API = `gira-api-${VERSION}`;
const CACHE_SHELL = `gira-shell-${VERSION}`;
const SHELL = ['/', '/manifest.webmanifest', '/favicon.svg', '/icons/icon-192.png'];

const API_CACHEABLE = [
  '/api/v1/kpis',
  '/api/v1/forecast',
  '/api/v1/catalogs',
  '/api/v1/alertas',
];
const TIMEOUT_RED_MS = 4000;
const MAX_ENTRADAS_API = 60;

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_SHELL).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  const vigentes = new Set([CACHE_ESTATICO, CACHE_API, CACHE_SHELL]);
  event.waitUntil(
    caches.keys()
      .then((claves) => Promise.all(claves.filter((k) => k.startsWith('gira-') && !vigentes.has(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', (event) => {
  if (event.data?.type === 'CLEAR_API_CACHE') {
    event.waitUntil(caches.delete(CACHE_API));
  }
});

const esEstatico = (url) =>
  url.origin === self.location.origin
    ? url.pathname.startsWith('/assets/') || url.pathname.startsWith('/icons/') || /\.(svg|png|ico|woff2?)$/.test(url.pathname)
    : url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com';

async function cacheFirst(request) {
  const enCache = await caches.match(request);
  if (enCache) return enCache;
  const respuesta = await fetch(request);
  if (respuesta.ok || respuesta.type === 'opaque') {
    const cache = await caches.open(CACHE_ESTATICO);
    cache.put(request, respuesta.clone());
  }
  return respuesta;
}

async function recortar(cache) {
  const claves = await cache.keys();
  await Promise.all(claves.slice(0, Math.max(0, claves.length - MAX_ENTRADAS_API)).map((k) => cache.delete(k)));
}

async function networkFirst(request, nombreCache, respaldo) {
  const cache = await caches.open(nombreCache);
  try {
    const controlador = new AbortController();
    const temporizador = setTimeout(() => controlador.abort(), TIMEOUT_RED_MS);
    const respuesta = await fetch(request, { signal: controlador.signal });
    clearTimeout(temporizador);
    if (respuesta.ok) {
      await cache.put(request, respuesta.clone());
      if (nombreCache === CACHE_API) recortar(cache);
    }
    return respuesta;
  } catch (error) {
    const enCache = (await cache.match(request)) || (respaldo && (await caches.match(respaldo)));
    if (enCache) return enCache;
    throw error;
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);

  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, CACHE_SHELL, '/'));
    return;
  }
  if (url.origin === self.location.origin && url.pathname.startsWith('/api/')) {
    if (API_CACHEABLE.some((p) => url.pathname.startsWith(p))) {
      event.respondWith(networkFirst(request, CACHE_API));
    }
    return;
  }
  if (esEstatico(url)) {
    event.respondWith(cacheFirst(request));
  }
});
