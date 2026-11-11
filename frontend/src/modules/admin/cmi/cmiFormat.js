// Formato y semántica compartidos por el scorecard y la configuración del CMI.
// Los colores y la regla de semáforo son los mismos que usa el tema de Power BI.

export const SEMAFORO = {
  VERDE: { label: 'En meta', color: 'var(--cmi-ok)' },
  AMBAR: { label: 'En alerta', color: 'var(--cmi-warn)' },
  ROJO: { label: 'Crítico', color: 'var(--cmi-bad)' },
  SIN_UMBRAL: { label: 'Informativo', color: 'var(--cmi-muted)' },
};

export const UNIDAD = { PCT: '%', BS: 'Bs', CANT: 'estudiantes', PTS: 'pts' };

const nf = (dec) => new Intl.NumberFormat('es-BO', { maximumFractionDigits: dec, minimumFractionDigits: 0 });

export function fmtValor(v, unidad, { compacto = false } = {}) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  if (unidad === 'PCT') return `${nf(1).format(n)} %`;
  if (unidad === 'PTS') return nf(1).format(n);
  if (unidad === 'BS') {
    if (compacto && Math.abs(n) >= 1e6) return `Bs ${nf(2).format(n / 1e6)} M`;
    if (compacto && Math.abs(n) >= 1e3) return `Bs ${nf(1).format(n / 1e3)} mil`;
    return `Bs ${nf(0).format(n)}`;
  }
  return nf(0).format(n);
}

export function fmtDelta(d, unidad) {
  if (d === null || d === undefined || Number(d) === 0) return null;
  const n = Number(d);
  const signo = n > 0 ? '+' : '−';
  const abs = Math.abs(n);
  if (unidad === 'PCT') return `${signo}${nf(1).format(abs)} pp`;
  return `${signo}${fmtValor(abs, unidad, { compacto: true })}`;
}

// Banda de un índice 0–100 con los mismos cortes que el semáforo puntúa (100 / 60 / 20)
export function bandaIndice(indice) {
  if (indice === null || indice === undefined) return 'SIN_UMBRAL';
  if (indice >= 80) return 'VERDE';
  if (indice >= 50) return 'AMBAR';
  return 'ROJO';
}

// Orden causa → efecto del mapa estratégico (de la base a la cima)
export const MAPA_ESTRATEGICO = ['APRENDIZAJE', 'PROCESOS_INTERNOS', 'CLIENTES', 'FINANCIERA'];
