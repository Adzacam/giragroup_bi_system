/**
 * Utilidades de enrutamiento para la interfaz oficial (rutas raíz /*).
 * Mantiene compatibilidad de lectura para enlaces heredados /v2/*.
 */

export const V2_PREFIX = '/v2';

export const V2_ROLE_REDIRECTS = {
  ADMIN: '/dashboard',
  AUDITOR_CALIDAD: '/dataops/ingesta',
  DIRECTOR_ACADEMICO: '/academico/rendimiento',
  ANALISTA_FINANCIERO: '/financiero/recaudacion',
  ANALISTA_MARKETING: '/dashboard',
};

export function isV2Pathname(pathname = '') {
  return pathname === V2_PREFIX || pathname.startsWith(`${V2_PREFIX}/`);
}

export function toV1Path(path = '/') {
  if (!path) return '/';
  if (!isV2Pathname(path)) return path;
  const stripped = path.slice(V2_PREFIX.length);
  return stripped || '/';
}

export function toV2Path(path = '/') {
  return toV1Path(path);
}

export function toDataopsPath(subpath = '/ingesta') {
  const raw = String(subpath || '/ingesta').trim();
  const withoutV2 = raw.startsWith(`${V2_PREFIX}/`) ? raw.slice(V2_PREFIX.length) : raw;
  return withoutV2.startsWith('/dataops')
    ? withoutV2
    : `/dataops${withoutV2.startsWith('/') ? withoutV2 : `/${withoutV2}`}`;
}
