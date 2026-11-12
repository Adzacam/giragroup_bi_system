import React from 'react';
import { Loader2 } from 'lucide-react';

// 75 s -> '1 min 15 s'; 3700 s -> '1 h 1 min'
export const fmtDuracion = (seg) => {
  if (seg === null || seg === undefined) return '—';
  const s = Math.max(0, Math.round(seg));
  if (s < 60) return `${s} s`;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h ? `${h} h ${m} min` : `${m} min ${s % 60} s`;
};

/**
 * Avance de una tarea larga de DataOps: barra, registros procesados, tiempo transcurrido y restante estimado.
 * Con `tarea` null (aún sin dato del servidor) muestra una barra indeterminada con el tiempo local.
 */
export default function ProgresoTarea({ titulo, tarea, segundosLocal = 0, nota }) {
  const pct = tarea?.porcentaje ?? 0;
  const total = tarea?.total || 0;
  const indeterminado = !tarea || !total;
  const transcurrido = tarea?.transcurrido_seg ?? segundosLocal;
  return (
    <div role="status" aria-live="polite" style={{
      border: '1px solid var(--dataops-gold-border)', background: 'var(--dataops-gold-bg)',
      borderRadius: '14px', padding: '14px 16px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13.5px', fontWeight: 700, color: 'var(--color-ink-black)' }}>
        <Loader2 size={15} className="spin" style={{ animation: 'spin 1s linear infinite', color: 'var(--color-gira-gold)' }} />
        {titulo}
        {!indeterminado && <span style={{ marginLeft: 'auto', fontVariantNumeric: 'tabular-nums' }}>{pct.toFixed(1)} %</span>}
      </div>
      <div style={{ height: '8px', borderRadius: '999px', background: 'var(--color-border)', overflow: 'hidden', margin: '10px 0 8px' }}>
        <div style={{
          height: '100%', borderRadius: '999px', background: 'var(--color-gira-gold)',
          width: indeterminado ? '35%' : `${Math.max(2, pct)}%`,
          transition: 'width .6s ease',
          animation: indeterminado ? 'progreso-indet 1.4s ease-in-out infinite' : 'none',
        }} />
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 16px', fontSize: '12.5px', color: 'var(--color-slate-gray)', fontVariantNumeric: 'tabular-nums' }}>
        {total > 0 && <span>{(tarea.procesados || 0).toLocaleString('es-BO')} de {total.toLocaleString('es-BO')} registros</span>}
        <span>Transcurrido: {fmtDuracion(transcurrido)}</span>
        {tarea?.restante_seg != null && <span>Restante estimado: ~{fmtDuracion(tarea.restante_seg)}</span>}
      </div>
      {nota && <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '6px' }}>{nota}</div>}
      <style>{`@keyframes progreso-indet{0%{margin-left:-35%}100%{margin-left:100%}}@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
