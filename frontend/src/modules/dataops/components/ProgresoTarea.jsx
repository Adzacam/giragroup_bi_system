import React, { useEffect, useRef, useState } from 'react';
import { Loader2, XCircle } from 'lucide-react';
import AnimatedProgressBarV2 from '../../../v2/motion/AnimatedProgressBarV2';
import Button from '../../../components/shared/Button';

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
export default function ProgresoTarea({ titulo, tarea, segundosLocal = 0, nota, onCancel, canceling = false, cancelLabel = 'Cancelar' }) {
  const total = tarea?.total || 0;
  const pct = tarea?.porcentaje != null
    ? Math.min(100, Number(tarea.porcentaje))
    : (total > 0 ? Math.min(100, ((tarea?.procesados || 0) / total) * 100) : 0);
  const indeterminado = !tarea || !total;
  const transcurrido = tarea?.transcurrido_seg ?? segundosLocal;
  const emaRef = useRef(null);
  const [restanteSuave, setRestanteSuave] = useState(tarea?.restante_seg ?? null);

  useEffect(() => {
    const raw = tarea?.restante_seg;
    if (raw == null || !Number.isFinite(Number(raw))) {
      emaRef.current = null;
      setRestanteSuave(null);
      return;
    }
    const val = Number(raw);
    emaRef.current = emaRef.current == null ? val : emaRef.current * 0.75 + val * 0.25;
    setRestanteSuave(Math.round(emaRef.current));
  }, [tarea?.restante_seg, tarea?.procesados]);

  return (
    <div role="status" aria-live="polite" style={{
      border: '1px solid var(--dataops-gold-border)', background: 'var(--dataops-gold-bg)',
      borderRadius: '14px', padding: '14px 16px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', fontSize: '13.5px', fontWeight: 700, color: 'var(--color-ink-black)' }}>
        <Loader2 size={15} className="spin" style={{ animation: 'spin 1s linear infinite', color: 'var(--color-gira-gold)' }} />
        <span>{titulo}</span>
        {!indeterminado && (
          <span style={{ marginLeft: 'auto', fontVariantNumeric: 'tabular-nums' }}>
            {pct.toFixed(1)} %
          </span>
        )}
        {onCancel && (
          <Button
            variant="ghost"
            className="dataops-btn-danger"
            isLoading={canceling}
            loadingText="Cancelando…"
            onClick={onCancel}
            style={{ marginLeft: indeterminado ? 'auto' : '8px', padding: '5px 11px', fontSize: '12px' }}
          >
            <XCircle size={13} /> {cancelLabel}
          </Button>
        )}
      </div>
      {indeterminado ? (
        <div style={{ height: '8px', borderRadius: '999px', background: 'var(--color-border)', overflow: 'hidden', margin: '10px 0 8px' }}>
          <div style={{
            height: '100%', borderRadius: '999px', background: 'var(--color-gira-gold)',
            width: '35%',
            animation: 'progreso-indet 1.4s ease-in-out infinite',
          }} />
        </div>
      ) : (
        <AnimatedProgressBarV2
          value={Math.max(2, pct)}
          max={100}
          color="var(--color-gira-gold)"
          trackColor="var(--color-border)"
          style={{ height: '8px', borderRadius: '999px', overflow: 'hidden', margin: '10px 0 8px', position: 'relative' }}
          barStyle={{ display: 'block', height: '100%', borderRadius: '999px' }}
          ariaLabel={titulo}
        />
      )}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 16px', fontSize: '12.5px', color: 'var(--color-slate-gray)', fontVariantNumeric: 'tabular-nums' }}>
        {total > 0 && <span>{(tarea.procesados || 0).toLocaleString('es-BO')} de {total.toLocaleString('es-BO')} registros</span>}
        <span>Transcurrido: {fmtDuracion(transcurrido)}</span>
        {restanteSuave != null && <span>Restante estimado: ~{fmtDuracion(restanteSuave)}</span>}
      </div>
      {nota && <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '6px' }}>{nota}</div>}
      <style>{`@keyframes progreso-indet{0%{margin-left:-35%}100%{margin-left:100%}}@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
