/**
 * Utilidades de enrutamiento para la Versión 2 (/v2/*)
 */

export const V2_PREFIX = '/v2';

export const V2_ROLE_REDIRECTS = {
  ADMIN: '/v2/dashboard',
  AUDITOR_CALIDAD: '/v2/dataops/ingesta',
  DIRECTOR_ACADEMICO: '/v2/academico/rendimiento',
  ANALISTA_FINANCIERO: '/v2/financiero/recaudacion',
  ANALISTA_MARKETING: '/v2/dashboard',
};

export function isV2Pathname(pathname = '') {
  return pathname === V2_PREFIX || pathname.startsWith(`${V2_PREFIX}/`);
}

export function toV2Path(path = '/') {
  if (!path) return V2_PREFIX;
  if (isV2Pathname(path)) return path;
  if (path === '/') return V2_PREFIX;
  return path.startsWith('/') ? `${V2_PREFIX}${path}` : `${V2_PREFIX}/${path}`;
}

export function toV1Path(path = '/') {
  if (!path) return '/';
  if (!isV2Pathname(path)) return path;
  const stripped = path.slice(V2_PREFIX.length);
  return stripped || '/';
}

export function toDataopsPath(subpath = '/ingesta', currentPathname) {
  const pathname = currentPathname ?? (typeof window !== 'undefined' ? window.location.pathname : '');
  const raw = String(subpath || '/ingesta').trim();
  const withoutV2 = raw.startsWith(`${V2_PREFIX}/`) ? raw.slice(V2_PREFIX.length) : raw;
  const normalized = withoutV2.startsWith('/dataops')
    ? withoutV2
    : `/dataops${withoutV2.startsWith('/') ? withoutV2 : `/${withoutV2}`}`;
  return isV2Pathname(pathname) ? toV2Path(normalized) : normalized;
}
