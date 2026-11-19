import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Cpu, CheckCircle2 } from 'lucide-react';
import Button from '../../../components/shared/Button';
import betoMetricas from '../../../constants/betoMetricas.json';

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
        aria-label="Métricas del modelo BETO"
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
              Métricas del modelo BETO
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
            aria-label="Cerrar métricas del modelo"
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
          <div className="floating-artifact" style={{ padding: 14 }}>
            <p style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>
              F1 estricto (gold_510 · Modo C)
            </p>
            <p style={{ fontSize: 24, fontWeight: 700, marginTop: 4 }}>
              {fmtPct(modoC.estricto.f1)}
            </p>
            <p style={{ fontSize: 11.5, color: 'var(--color-slate-gray)', marginTop: 4 }}>
              TP {fmtInt(modoC.estricto.tp)} / {fmtInt(modoC.estricto.support)} · FP {fmtInt(modoC.estricto.fp)} · FN {fmtInt(modoC.estricto.fn)}
            </p>
          </div>
          <div className="floating-artifact" style={{ padding: 14 }}>
            <p style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>
              F1 relajado (gold_510 · Modo C)
            </p>
            <p style={{ fontSize: 24, fontWeight: 700, marginTop: 4 }}>
              {fmtPct(modoC.relajado.f1)}
            </p>
            <p style={{ fontSize: 11.5, color: 'var(--color-slate-gray)', marginTop: 4 }}>
              TP {fmtInt(modoC.relajado.tp)} / {fmtInt(modoC.relajado.support)} · FP {fmtInt(modoC.relajado.fp)} · FN {fmtInt(modoC.relajado.fn)}
            </p>
          </div>
        </div>

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
                          style={{
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
        </div>

        {/* 5. Historial de las 3 épocas */}
        <div className="floating-artifact" style={{ padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>
            Entrenamiento por época ({fmtInt(ficha.epochs)} épocas · best_dev_f1 = {fmtNum(ficha.best_dev_f1, 4)})
          </h3>
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
