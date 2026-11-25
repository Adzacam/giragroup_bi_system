import React, { useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { X, Cpu } from 'lucide-react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend } from 'chart.js';
import Button from '../../../components/shared/Button';
import betoMetricas from '../../../constants/betoMetricas.json';
import AnimatedNumberV2 from '../../../v2/motion/AnimatedNumberV2';
import { withChartAnimationsV2 } from '../../../v2/motion/chartAnimationsV2';
import BetoMetricasTablas, { fmtInt, fmtNum, fmtPct } from './BetoMetricasTablas';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

export function buildCurvaEpocas(epocas, bestEpoch) {
  const best = (ep) => ep.epoch === bestEpoch;
  return {
    labels: epocas.map((ep) => `Época ${ep.epoch}${best(ep) ? ' (Mejor)' : ''}`),
    datasets: [
      { label: 'F1 en validación', data: epocas.map((ep) => ep.dev_f1), yAxisID: 'y', borderColor: '#2F7D4F', backgroundColor: '#2F7D4F', pointRadius: epocas.map((ep) => (best(ep) ? 8 : 4)), pointStyle: epocas.map((ep) => (best(ep) ? 'star' : 'circle')), tension: 0.25 },
      { label: 'Error de entrenamiento', data: epocas.map((ep) => ep.train_loss), yAxisID: 'y1', borderColor: '#D99B26', backgroundColor: '#D99B26', borderDash: [6, 4], tension: 0.25 },
      { label: 'Error de validación', data: epocas.map((ep) => ep.dev_loss), yAxisID: 'y1', borderColor: '#8A8F98', backgroundColor: '#8A8F98', borderDash: [2, 3], tension: 0.25 },
    ],
  };
}

function MetricaFila({ etiqueta, valor }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, fontSize: 13 }}>
      <span style={{ color: 'var(--color-slate-gray)' }}>{etiqueta}</span>
      <strong style={{ fontFamily: 'var(--font-mono)' }}><AnimatedNumberV2 value={fmtPct(valor)} /></strong>
    </div>
  );
}

export default function BetoMetricasModal({ isOpen, onClose }) {
  useEffect(() => {
    if (!isOpen || typeof window === 'undefined') return undefined;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => { document.body.style.overflow = prevOverflow; window.removeEventListener('keydown', onKey); };
  }, [isOpen, onClose]);

  const { ficha_modelo: ficha, epocas, gold_510_modo_c: modoC, desglose_por_clase: porClase, matriz_confusion_5x5: matriz5x5, ablacion_f9: ablacionF9, perfil_activo_f9: perfilF9 } = betoMetricas;
  const idxEst = matriz5x5.clases.indexOf('PER_ESTUDIANTE');
  const idxProg = matriz5x5.clases.indexOf('PROGRAMA');
  const tokensEstAProg = idxEst >= 0 && idxProg >= 0 ? matriz5x5.matriz[idxEst]?.[idxProg] ?? 0 : 0;
  const curvaData = useMemo(() => buildCurvaEpocas(epocas, ficha.best_epoch), [epocas, ficha.best_epoch]);
  const curvaOptions = useMemo(() => withChartAnimationsV2({
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, font: { size: 11 } } } },
    scales: {
      y: { position: 'left', title: { display: true, text: 'F1 validación' }, min: 0.99, max: 1 },
      y1: { position: 'right', title: { display: true, text: 'Error' }, grid: { drawOnChartArea: false }, min: 0 },
    },
  }), []);

  if (!isOpen) return null;

  const modalContent = (
    <div className="modal-backdrop show" style={{ zIndex: 2000, padding: 16 }} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <section className="modal-panel" role="dialog" aria-modal="true" aria-label="Métricas del Modelo BETO" style={{ maxWidth: 880, width: '100%', maxHeight: '90vh', overflowY: 'auto', overscrollBehavior: 'contain', padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 18 }}>
          <div>
            <h2 className="serif-heading" style={{ fontSize: 20, display: 'flex', alignItems: 'center', gap: 8, margin: 0 }}>
              <Cpu size={20} color="var(--color-gira-gold, #D99B26)" /> Métricas del Modelo BETO
            </h2>
            <p style={{ fontSize: 12.5, color: 'var(--color-slate-gray)', marginTop: 4 }}>
              Evaluación reproducible sobre el conjunto de referencia gold_510 (Modo C, sin heurísticas de encabezado).
            </p>
          </div>
          <Button variant="ghost" type="button" aria-label="Cerrar Métricas del Modelo BETO" onClick={onClose} style={{ padding: '6px 10px' }}><X size={16} /></Button>
        </div>

        <div className="floating-artifact" style={{ padding: 16, marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>Ficha del modelo</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 10, fontSize: 12.5 }}>
            <div><span style={{ color: 'var(--color-slate-gray)' }}>Modelo base: </span><strong>{ficha.model_base}</strong></div>
            <div><span style={{ color: 'var(--color-slate-gray)' }}>Esquema de etiquetas: </span><strong>{ficha.num_etiquetas} etiquetas IOB2</strong></div>
            <div><span style={{ color: 'var(--color-slate-gray)' }}>Mejor F1 en validación: </span><strong>{fmtNum(ficha.best_dev_f1, 4)}</strong> (época {ficha.best_epoch})</div>
            <div><span style={{ color: 'var(--color-slate-gray)' }}>Particiones: </span><strong>{fmtInt(ficha.train_size)} train / {fmtInt(ficha.dev_size)} dev / {fmtInt(ficha.test_gold_size)} test</strong></div>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
            {ficha.etiquetas_iob2.map((tag) => <span key={tag} className="chip-cat" style={{ fontSize: 11 }}>{tag}</span>)}
          </div>
          <div style={{ marginTop: 12, padding: 10, borderRadius: 10, background: 'var(--color-mist-gray)', border: '1px solid var(--color-border)', fontSize: 12 }}>
            <strong>Perfil activo en producción (F9 · RNF-03):</strong>{' '}
            <span>
              Carga histórica fría de 10 libros en <strong>{fmtNum(perfilF9?.tiempo_completo_min ?? 10.93, 2)} min</strong> (&lt; {perfilF9?.rnf03_limite_min ?? 15} min RNF-03), tasa de acuerdo regla–BETO de <strong>{fmtPct(perfilF9?.tasa_acuerdo_completo ?? 0.9952)}</strong> y cuantización INT8 en CPU (F1 estricto <strong>89,63 %</strong> · F1 relajado <strong>95,18 %</strong> en gold_510 Modo C).
            </span>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 16 }}>
          {[{ key: 'estricto', titulo: 'F1 estricto (gold_510 · Modo C)', m: modoC.estricto }, { key: 'relajado', titulo: 'F1 relajado (gold_510 · Modo C)', m: modoC.relajado }].map(({ key, titulo, m }) => (
            <div key={key} className="floating-artifact" style={{ padding: 14 }}>
              <p style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>{titulo}</p>
              <p style={{ fontSize: 24, fontWeight: 700, margin: '4px 0 8px' }}><AnimatedNumberV2 value={fmtPct(m.f1)} /></p>
              <MetricaFila etiqueta="Precisión" valor={m.precision} />
              <MetricaFila etiqueta="Recall" valor={m.recall} />
              <p style={{ fontSize: 11.5, color: 'var(--color-slate-gray)', marginTop: 6 }}>
                TP {fmtInt(m.tp)} / {fmtInt(m.support)} · FP {fmtInt(m.fp)} · FN {fmtInt(m.fn)}
              </p>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', margin: '-6px 0 16px', lineHeight: 1.45 }}>
          Qué significa: la precisión indica cuántos datos que BETO marcó eran correctos; el recall, cuántos de los datos reales logró encontrar. El criterio estricto exige el mismo recorte exacto del dato; el relajado acepta coincidencias parciales.
        </p>

        <BetoMetricasTablas porClase={porClase} matriz5x5={matriz5x5} tokensEstAProg={tokensEstAProg} ficha={ficha} epocas={epocas} curvaData={curvaData} curvaOptions={curvaOptions} ablacionF9={ablacionF9} />
      </section>
    </div>
  );

  if (typeof document !== 'undefined' && document.body) {
    return createPortal(modalContent, document.body);
  }
  return modalContent;
}
