import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Cpu, CheckCircle2 } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import Button from '../../../components/shared/Button';
import betoMetricas from '../../../constants/betoMetricas.json';
import AnimatedNumberV2 from '../../../v2/motion/AnimatedNumberV2';
import ChartRevealV2 from '../../../v2/motion/ChartRevealV2';
import { CHART_PLUGINS_V2, withChartAnimationsV2 } from '../../../v2/motion/chartAnimationsV2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

function fmtPct(val, decimals = 2) {
  if (typeof val !== 'number' || Number.isNaN(val)) return 'Sin dato';
  return `${(val * 100).toLocaleString('es-BO', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })} %`;
}

function fmtNum(val, decimals = 4) {
  if (typeof val !== 'number' || Number.isNaN(val)) return 'Sin dato';
  return val.toLocaleString('es-BO', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtInt(val) {
  if (typeof val !== 'number' || Number.isNaN(val)) return 'Sin dato';
  return val.toLocaleString('es-BO');
}

/** Datos de la curva de épocas: 3 puntos = epoch_history. */
export function buildCurvaEpocas(epocas, bestEpoch) {
  const best = (ep) => ep.epoch === bestEpoch;
  return {
    labels: epocas.map((ep) => `Época ${ep.epoch}${best(ep) ? ' (Mejor)' : ''}`),
    datasets: [
      {
        label: 'F1 en validación',
        data: epocas.map((ep) => ep.dev_f1),
        yAxisID: 'y',
        borderColor: '#2F7D4F',
        backgroundColor: '#2F7D4F',
        pointRadius: epocas.map((ep) => (best(ep) ? 8 : 4)),
        pointStyle: epocas.map((ep) => (best(ep) ? 'star' : 'circle')),
        tension: 0.25,
      },
      {
        label: 'Error de entrenamiento',
        data: epocas.map((ep) => ep.train_loss),
        yAxisID: 'y1',
        borderColor: '#D99B26',
        backgroundColor: '#D99B26',
        borderDash: [6, 4],
        tension: 0.25,
      },
      {
        label: 'Error de validación',
        data: epocas.map((ep) => ep.dev_loss),
        yAxisID: 'y1',
        borderColor: '#8A8F98',
        backgroundColor: '#8A8F98',
        borderDash: [2, 3],
        tension: 0.25,
      },
    ],
  };
}

const NOTA = { fontSize: 12, color: 'var(--color-slate-gray)', margin: '8px 0 0', lineHeight: 1.45 };

function MetricaFila({ etiqueta, valor }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, fontSize: 13 }}>
      <span style={{ color: 'var(--color-slate-gray)' }}>{etiqueta}</span>
      <strong style={{ fontFamily: 'var(--font-mono)' }}>
        <AnimatedNumberV2 value={fmtPct(valor)} />
      </strong>
    </div>
  );
}

export default function BetoMetricasModal({ isOpen, onClose }) {
  useEffect(() => {
    if (!isOpen || typeof window === 'undefined') return undefined;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener('keydown', onKey);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const {
    ficha_modelo: ficha,
    epocas,
    gold_510_modo_c: modoC,
    desglose_por_clase: porClase,
    matriz_confusion_5x5: matriz5x5,
  } = betoMetricas;

  const idxEst = matriz5x5.clases.indexOf('PER_ESTUDIANTE');
  const idxProg = matriz5x5.clases.indexOf('PROGRAMA');
  const tokensEstAProg =
    idxEst >= 0 && idxProg >= 0 ? matriz5x5.matriz[idxEst]?.[idxProg] ?? 0 : 0;

  const curvaData = buildCurvaEpocas(epocas, ficha.best_epoch);
  const curvaOptions = withChartAnimationsV2({
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, font: { size: 11 } } } },
    scales: {
      y: { position: 'left', title: { display: true, text: 'F1 validación' }, min: 0.99, max: 1 },
      y1: { position: 'right', title: { display: true, text: 'Error' }, grid: { drawOnChartArea: false }, min: 0 },
    },
  });

  const modalContent = (
    <div
      className="modal-backdrop show"
      style={{ zIndex: 2000, padding: 16 }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Métricas del Modelo BETO"
        style={{
          maxWidth: 880,
          width: '100%',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: 24,
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: 12,
            marginBottom: 18,
          }}
        >
          <div>
            <h2
              className="serif-heading"
              style={{
                fontSize: 20,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                margin: 0,
              }}
            >
              <Cpu size={20} color="var(--color-gira-gold, #D99B26)" />
              Métricas del Modelo BETO
            </h2>
            <p
              style={{
                fontSize: 12.5,
                color: 'var(--color-slate-gray)',
                marginTop: 4,
              }}
            >
              Evaluación reproducible sobre el conjunto de referencia gold_510 (Modo C, sin heurísticas de encabezado).
            </p>
          </div>
          <Button
            variant="ghost"
            type="button"
            aria-label="Cerrar Métricas del Modelo BETO"
            onClick={onClose}
            style={{ padding: '6px 10px' }}
          >
            <X size={16} />
          </Button>
        </div>

        {/* 1. Ficha del modelo */}
        <div
          className="floating-artifact"
          style={{ padding: 16, marginBottom: 16 }}
        >
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>
            Ficha del modelo
          </h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
              gap: 10,
              fontSize: 12.5,
            }}
          >
            <div>
              <span style={{ color: 'var(--color-slate-gray)' }}>Modelo base: </span>
              <strong>{ficha.model_base}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--color-slate-gray)' }}>Esquema de etiquetas: </span>
              <strong>{ficha.num_etiquetas} etiquetas IOB2</strong>
            </div>
            <div>
              <span style={{ color: 'var(--color-slate-gray)' }}>Mejor F1 en validación: </span>
              <strong>{fmtNum(ficha.best_dev_f1, 4)}</strong> (época {ficha.best_epoch})
            </div>
            <div>
              <span style={{ color: 'var(--color-slate-gray)' }}>Particiones: </span>
              <strong>
                {fmtInt(ficha.train_size)} train / {fmtInt(ficha.dev_size)} dev / {fmtInt(ficha.test_gold_size)} test
              </strong>
            </div>
          </div>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 6,
              marginTop: 10,
            }}
          >
            {ficha.etiquetas_iob2.map((tag) => (
              <span key={tag} className="chip-cat" style={{ fontSize: 11 }}>
                {tag}
              </span>
            ))}
          </div>
        </div>

        {/* 2. Métricas gold_510 Modo C */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 12,
            marginBottom: 16,
          }}
        >
          {[
            { key: 'estricto', titulo: 'F1 estricto (gold_510 · Modo C)', m: modoC.estricto },
            { key: 'relajado', titulo: 'F1 relajado (gold_510 · Modo C)', m: modoC.relajado },
          ].map(({ key, titulo, m }) => (
            <div key={key} className="floating-artifact" style={{ padding: 14 }}>
              <p style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>{titulo}</p>
              <p style={{ fontSize: 24, fontWeight: 700, margin: '4px 0 8px' }}>
                <AnimatedNumberV2 value={fmtPct(m.f1)} />
              </p>
              <MetricaFila etiqueta="Precisión" valor={m.precision} />
              <MetricaFila etiqueta="Recall" valor={m.recall} />
              <p style={{ fontSize: 11.5, color: 'var(--color-slate-gray)', marginTop: 6 }}>
                TP {fmtInt(m.tp)} / {fmtInt(m.support)} · FP {fmtInt(m.fp)} · FN {fmtInt(m.fn)}
              </p>
            </div>
          ))}
        </div>
        <p style={{ ...NOTA, margin: '-6px 0 16px' }}>
          Qué significa: la precisión indica cuántos datos que BETO marcó eran correctos; el recall, cuántos de los datos reales logró encontrar.
          El criterio estricto exige el mismo recorte exacto del dato; el relajado acepta coincidencias parciales.
        </p>

        {/* 3. Desglose por clase */}
        <div
          className="floating-artifact"
          style={{ padding: 16, marginBottom: 16 }}
        >
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>
            Desglose por clase (gold_510 · Modo C)
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table
              className="dataops-table"
              style={{ width: '100%', textAlign: 'left', fontSize: 12 }}
            >
              <thead>
                <tr>
                  <th>Clase</th>
                  <th>Soporte</th>
                  <th>TP</th>
                  <th>FN</th>
                  <th>FP</th>
                  <th>Precisión</th>
                  <th>Recall</th>
                  <th>F1 estricto</th>
                  <th>F1 relajado</th>
                </tr>
              </thead>
              <tbody>
                {porClase.map((row) => (
                  <tr key={row.clase}>
                    <td><strong>{row.clase}</strong></td>
                    <td>{fmtInt(row.support)}</td>
                    <td>{fmtInt(row.tp)}</td>
                    <td>{fmtInt(row.fn)}</td>
                    <td>{fmtInt(row.fp)}</td>
                    <td>{fmtPct(row.precision)}</td>
                    <td>{fmtPct(row.recall)}</td>
                    <td><strong>{fmtPct(row.f1_estricto)}</strong></td>
                    <td>{fmtPct(row.f1_relajado)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={NOTA}>
            Qué significa: cada fila muestra qué tan bien BETO reconoce un tipo de dato. Módulos y docentes se leen sin errores; los nombres de programa son los más difíciles de recortar bien.
          </p>
        </div>

        {/* 4. Matriz de confusión 5×5 */}
        <div
          className="floating-artifact"
          style={{ padding: 16, marginBottom: 16 }}
        >
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>
            Matriz de confusión 5×5 (nivel token · {fmtInt(matriz5x5.n_tokens)} tokens)
          </h3>
          <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', marginBottom: 10 }}>
            Filas = etiqueta real, columnas = predicción. Única confusión entre entidades: {fmtInt(tokensEstAProg)} token PER_ESTUDIANTE → PROGRAMA.
          </p>
          <div style={{ overflowX: 'auto' }}>
            <table
              className="dataops-table"
              style={{ width: '100%', textAlign: 'right', fontSize: 12 }}
            >
              <thead>
                <tr>
                  <th style={{ textAlign: 'left' }}>Real \ Predicho</th>
                  {matriz5x5.clases.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matriz5x5.clases.map((rowLabel, rIdx) => (
                  <tr key={rowLabel}>
                    <td style={{ textAlign: 'left', fontWeight: 700 }}>{rowLabel}</td>
                    {matriz5x5.matriz[rIdx].map((cellVal, cIdx) => {
                      const isDiag = rIdx === cIdx;
                      const isError = !isDiag && cellVal > 0;
                      return (
                        <td
                          key={`${rowLabel}-${matriz5x5.clases[cIdx]}`}
                          data-confusion={isError ? 'true' : undefined}
                          style={{
                            ...(isError
                              ? {
                                  background: 'var(--dataops-warning-bg)',
                                  boxShadow: 'inset 0 0 0 1.5px var(--dataops-warning-border)',
                                }
                              : {}),
                            fontWeight: isDiag || isError ? 700 : 400,
                            color: isError
                              ? 'var(--dataops-warning-text)'
                              : isDiag
                              ? 'var(--dataops-success-text)'
                              : 'var(--color-slate-gray)',
                          }}
                        >
                          {fmtInt(cellVal)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={NOTA}>
            Qué significa: la diagonal son los aciertos. La celda resaltada es el único caso en que BETO tomó el nombre de un estudiante por un programa.
          </p>
        </div>

        {/* 5. Historial de las 3 épocas */}
        <div className="floating-artifact" style={{ padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>
            Entrenamiento por época ({fmtInt(ficha.epochs)} épocas · best_dev_f1 = {fmtNum(ficha.best_dev_f1, 4)})
          </h3>
          <div style={{ height: 240, marginBottom: 12 }} role="img" aria-label="Curva de entrenamiento por época: F1 y errores de entrenamiento y validación">
            <ChartRevealV2>
              <Line data={curvaData} options={curvaOptions} plugins={CHART_PLUGINS_V2} />
            </ChartRevealV2>
          </div>
          <p style={{ ...NOTA, margin: '0 0 10px' }}>
            Qué significa: el modelo se entrenó 3 veces sobre los mismos ejemplos. Se conserva la época {ficha.best_epoch} (marcada como Mejor) porque logró el F1 más alto en validación; los errores bajan en cada vuelta.
          </p>
          <div style={{ overflowX: 'auto' }}>
            <table
              className="dataops-table"
              style={{ width: '100%', textAlign: 'left', fontSize: 12 }}
            >
              <thead>
                <tr>
                  <th>Época</th>
                  <th>Train loss</th>
                  <th>Dev loss</th>
                  <th>Dev F1</th>
                  <th>Dev precisión</th>
                  <th>Dev recall</th>
                  <th>Duración (s)</th>
                </tr>
              </thead>
              <tbody>
                {epocas.map((ep) => {
                  const isBest = ep.epoch === ficha.best_epoch;
                  return (
                    <tr key={ep.epoch}>
                      <td>
                        <strong>Época {ep.epoch}</strong>{' '}
                        {isBest && (
                          <span
                            className="chip-cat"
                            style={{
                              fontSize: 10.5,
                              marginLeft: 4,
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 4,
                            }}
                          >
                            <CheckCircle2 size={11} /> Mejor
                          </span>
                        )}
                      </td>
                      <td>{fmtNum(ep.train_loss, 4)}</td>
                      <td>{fmtNum(ep.dev_loss, 4)}</td>
                      <td><strong>{fmtNum(ep.dev_f1, 4)}</strong></td>
                      <td>{fmtNum(ep.dev_precision, 4)}</td>
                      <td>{fmtNum(ep.dev_recall, 4)}</td>
                      <td>{fmtNum(ep.time_sec, 2)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );

  if (typeof document !== 'undefined' && document.body) {
    return createPortal(modalContent, document.body);
  }
  return modalContent;
}
