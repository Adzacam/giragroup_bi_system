import React from 'react';

const TAG_TONE = {
  ESTUDIANTE: { bg: 'var(--dataops-info-bg)', color: 'var(--dataops-info-text)', label: 'PER_ESTUDIANTE' },
  PER_ESTUDIANTE: { bg: 'var(--dataops-info-bg)', color: 'var(--dataops-info-text)', label: 'PER_ESTUDIANTE' },
  DOCENTE: { bg: 'var(--dataops-gold-bg, rgba(217, 155, 38, 0.14))', color: 'var(--color-gira-gold, #D99B26)', label: 'PER_DOCENTE' },
  PER_DOCENTE: { bg: 'var(--dataops-gold-bg, rgba(217, 155, 38, 0.14))', color: 'var(--color-gira-gold, #D99B26)', label: 'PER_DOCENTE' },
  MÓDULO: { bg: 'var(--dataops-success-bg)', color: 'var(--dataops-success-text)', label: 'MODULO' },
  MODULO: { bg: 'var(--dataops-success-bg)', color: 'var(--dataops-success-text)', label: 'MODULO' },
  PROGRAMA: { bg: 'var(--dataops-warning-bg)', color: 'var(--dataops-warning-text)', label: 'PROGRAMA' },
};

function resolveStyle(tipo) {
  const key = String(tipo || '').toUpperCase();
  return TAG_TONE[key] || { bg: 'var(--color-mist-gray)', color: 'var(--color-ink-black)', label: key || 'ENTIDAD' };
}

/**
 * Resalta entidades IOB2 (de `beto_ents` con spans start/end, o fallback por coincidencia de token)
 * usando tokens CSS existentes y mostrando tipo + confianza.
 */
export default function EntityHighlightText({ text = '', betoEnts = [], entidades = [] }) {
  if (!text) return <span style={{ color: 'var(--color-slate-gray)' }}>Sin texto disponible</span>;

  const spans = Array.isArray(betoEnts) && betoEnts.length > 0
    ? [...betoEnts]
        .filter((e) => typeof e.start === 'number' && typeof e.end === 'number' && e.end > e.start && e.end <= text.length)
        .sort((a, b) => a.start - b.start)
    : [];

  if (spans.length > 0) {
    const parts = [];
    let cursor = 0;
    spans.forEach((sp, idx) => {
      if (sp.start < cursor) return;
      if (sp.start > cursor) {
        parts.push(<span key={`txt-${idx}`}>{text.slice(cursor, sp.start)}</span>);
      }
      const st = resolveStyle(sp.tipo);
      const pct = sp.score != null ? ` ${Math.round(Number(sp.score) * 100)}%` : '';
      parts.push(
        <mark
          key={`ent-${idx}`}
          style={{
            background: st.bg,
            color: st.color,
            padding: '1px 5px',
            borderRadius: 6,
            fontWeight: 600,
            marginInline: 1,
          }}
          title={`${st.label}${pct}`}
        >
          {text.slice(sp.start, sp.end)}
          <span style={{ fontSize: 10, opacity: 0.85, marginLeft: 4, fontFamily: 'var(--font-mono)' }}>
            [{st.label}{pct}]
          </span>
        </mark>
      );
      cursor = sp.end;
    });
    if (cursor < text.length) {
      parts.push(<span key="txt-end">{text.slice(cursor)}</span>);
    }
    return <span style={{ lineHeight: 1.6, wordBreak: 'break-word' }}>{parts}</span>;
  }

  // Fallback cuando no hay spans de offsets: mostrar texto y chips de entidades detectadas
  const chips = (entidades || []).filter((e) => e?.token && ['ESTUDIANTE', 'DOCENTE', 'MÓDULO', 'MODULO', 'PROGRAMA'].includes(String(e.label || '').toUpperCase()));
  return (
    <div>
      <span style={{ lineHeight: 1.5, wordBreak: 'break-word' }}>{text}</span>
      {chips.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
          {chips.map((e, i) => {
            const st = resolveStyle(e.label);
            const conf = e.confianza ?? e.betoConfidence;
            return (
              <span
                key={i}
                style={{
                  fontSize: 10.5,
                  padding: '2px 7px',
                  borderRadius: 999,
                  background: st.bg,
                  color: st.color,
                  fontWeight: 600,
                }}
              >
                {st.label}: {e.token}{conf != null ? ` (${Math.round(Number(conf) * 100)}%)` : ''}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
