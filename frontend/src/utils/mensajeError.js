/** Texto legible de un error de API: `detail` puede ser string, lista (validación) u objeto { mensaje }. Nunca devuelve un objeto. */
export function mensajeError(err, fallback = 'Error inesperado') {
  const d = err?.response?.data?.detail;
  if (typeof d === 'string' && d) return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || x?.mensaje || String(x)).join('; ') || fallback;
  if (d && typeof d === 'object') return d.mensaje || d.message || fallback;
  return err?.message || fallback;
}
