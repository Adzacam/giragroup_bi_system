import React from 'react';
import { CheckCircle2 } from 'lucide-react';
import { Line } from 'react-chartjs-2';
import ChartRevealV2 from '../../../v2/motion/ChartRevealV2';
import { CHART_PLUGINS_V2 } from '../../../v2/motion/chartAnimationsV2';

const NOTA = { fontSize: 12, color: 'var(--color-slate-gray)', margin: '8px 0 0', lineHeight: 1.45 };

export function fmtPct(val, decimals = 2) {
  if (typeof val !== 'number' || Number.isNaN(val)) return 'Sin dato';
  return `${(val * 100).toLocaleString('es-BO', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })} %`;
}

export function fmtNum(val, decimals = 4) {
  if (typeof val !== 'number' || Number.isNaN(val)) return 'Sin dato';
  return val.toLocaleString('es-BO', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function fmtInt(val) {
  if (typeof val !== 'number' || Number.isNaN(val)) return 'Sin dato';
  return val.toLocaleString('es-BO');
}

export default function BetoMetricasTablas({ porClase, matriz5x5, tokensEstAProg, ficha, epocas, curvaData, curvaOptions, ablacionF9 = [] }) {
  return (
    <>
      <div className="floating-artifact" style={{ padding: 16, marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>Desglose por clase (gold_510 · Modo C)</h3>
        <div style={{ overflowX: 'auto' }} tabIndex={0} role="region" aria-label="Desglose por clase">
          <table className="dataops-table" style={{ width: '100%', textAlign: 'left', fontSize: 12 }}>
            <thead>
              <tr><th>Clase</th><th>Soporte</th><th>TP</th><th>FN</th><th>FP</th><th>Precisión</th><th>Recall</th><th>F1 estricto</th><th>F1 relajado</th></tr>
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
        <p style={NOTA}>Qué significa: cada fila muestra qué tan bien BETO reconoce un tipo de dato. Módulos y docentes se leen sin errores; los nombres de programa son los más difíciles de recortar bien.</p>
      </div>

      <div className="floating-artifact" style={{ padding: 16, marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Matriz de confusión 5×5 (nivel token · {fmtInt(matriz5x5.n_tokens)} tokens)</h3>
        <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', marginBottom: 10 }}>
          Filas = etiqueta real, columnas = predicción. Única confusión entre entidades: {fmtInt(tokensEstAProg)} token PER_ESTUDIANTE → PROGRAMA.
        </p>
        <div style={{ overflowX: 'auto' }} tabIndex={0} role="region" aria-label="Matriz de confusión 5x5">
          <table className="dataops-table" style={{ width: '100%', textAlign: 'right', fontSize: 12 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>Real \ Predicho</th>
                {matriz5x5.clases.map((col) => <th key={col}>{col}</th>)}
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
                          ...(isError ? { background: 'var(--dataops-warning-bg)', boxShadow: 'inset 0 0 0 1.5px var(--dataops-warning-border)' } : {}),
                          fontWeight: isDiag || isError ? 700 : 400,
                          color: isError ? 'var(--dataops-warning-text)' : isDiag ? 'var(--dataops-success-text)' : 'var(--color-slate-gray)',
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
        <p style={NOTA}>Qué significa: la diagonal son los aciertos. La celda resaltada es el único caso en que BETO tomó el nombre de un estudiante por un programa.</p>
      </div>

      <div className="floating-artifact" style={{ padding: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>
          Entrenamiento por época ({fmtInt(ficha.epochs)} épocas · best_dev_f1 = {fmtNum(ficha.best_dev_f1, 4)})
        </h3>
        <div style={{ height: 240, marginBottom: 12 }} role="img" aria-label="Curva de entrenamiento por época: F1 y errores de entrenamiento y validación">
          <ChartRevealV2><Line data={curvaData} options={curvaOptions} plugins={CHART_PLUGINS_V2} /></ChartRevealV2>
        </div>
        <p style={{ ...NOTA, margin: '0 0 10px' }}>
          Qué significa: el modelo se entrenó 3 veces sobre los mismos ejemplos. Se conserva la época {ficha.best_epoch} (marcada como Mejor) porque logró el F1 más alto en validación; los errores bajan en cada vuelta.
        </p>
        <div style={{ overflowX: 'auto' }} tabIndex={0} role="region" aria-label="Entrenamiento por época">
          <table className="dataops-table" style={{ width: '100%', textAlign: 'left', fontSize: 12 }}>
            <thead>
              <tr><th>Época</th><th>Train loss</th><th>Dev loss</th><th>Dev F1</th><th>Dev precisión</th><th>Dev recall</th><th>Duración (s)</th></tr>
            </thead>
            <tbody>
              {epocas.map((ep) => {
                const isBest = ep.epoch === ficha.best_epoch;
                return (
                  <tr key={ep.epoch}>
                    <td>
                      <strong>Época {ep.epoch}</strong>{' '}
                      {isBest && <span className="chip-cat" style={{ fontSize: 10.5, marginLeft: 4, display: 'inline-flex', alignItems: 'center', gap: 4 }}><CheckCircle2 size={11} /> Mejor</span>}
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

      {ablacionF9.length > 0 && (
        <div className="floating-artifact" style={{ padding: 16, marginTop: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>Estudio de ablación (Modo A vs. Modo B · lote 10 archivos, F9)</h3>
          <div style={{ overflowX: 'auto' }} tabIndex={0} role="region" aria-label="Estudio de ablación Modo A vs Modo B">
            <table className="dataops-table" style={{ width: '100%', textAlign: 'left', fontSize: 12 }}>
              <thead>
                <tr><th>Configuración</th><th>Tiempo lote (s)</th><th>Casos pendientes HITL</th><th>Tasa de acuerdo</th></tr>
              </thead>
              <tbody>
                {ablacionF9.map((row) => (
                  <tr key={row.modo}>
                    <td><strong>{row.modo}</strong></td>
                    <td>{fmtNum(row.tiempo_s, 2)} s</td>
                    <td>{fmtInt(row.bandeja_pendientes)}</td>
                    <td>{row.tasa_acuerdo != null ? fmtPct(row.tasa_acuerdo) : 'N/A (sin BETO)'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={NOTA}>Fuente: docs/mediciones/f9_aporte_10archivos.json. El Modo B (cascada + BETO) reduce la bandeja de 405 a 141 casos pendientes (-65,2 %) manteniendo 100 % de acuerdo.</p>
        </div>
      )}
    </>
  );
}
