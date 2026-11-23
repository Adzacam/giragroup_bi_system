import React from 'react';
import AnimatedProgressBarV2 from '../../../v2/motion/AnimatedProgressBarV2';
import { ORIGEN_INFO } from './RegistroBetoRow';

const fmt = value => typeof value === 'number' ? value.toLocaleString('es-BO') : 'Sin dato';

export default function BetoCascadaResumen({ cascada }) {
  if (!cascada) return null;
  const flags = cascada.flags || {};
  const cascadaActiva = flags.BETO_CASCADA_FINAL ?? (Number(cascada.beto_aceptadas ?? cascada.BETO ?? 0) > 0 || Number(cascada.beto_leidas ?? 0) > 0);
  const qcActivo = flags.BETO_ACUERDO_QC ?? (cascada.acuerdo_qc_pct != null);
  const lineasConfianza = cascada.lineas_confianza_beto;
  const betoResueltas = cascada.beto_aceptadas ?? cascada.BETO ?? 0;
  const etapas = cascada.etapas || [
    { etapa: 'CI_EXACTA', cantidad: cascada.CI_EXACTA ?? 0, porcentaje: 0 },
    { etapa: 'ENCABEZADO', cantidad: cascada.ENCABEZADO ?? 0, porcentaje: 0 },
    { etapa: 'FUZZY', cantidad: cascada.FUZZY ?? 0, porcentaje: 0 },
    { etapa: 'REGEX', cantidad: cascada.REGEX ?? 0, porcentaje: 0 },
    { etapa: 'BETO', cantidad: cascada.BETO ?? 0, porcentaje: 0 },
  ];
  return (
    <section className="floating-artifact rounded-2xl" aria-label="Resumen de cascada de resolución" style={{ padding: 20, marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, alignItems: 'baseline', marginBottom: 12 }}>
        <h3 className="serif-heading" style={{ fontSize: 16, margin: 0, color: 'var(--color-ink-black)' }}>Cascada de resolución por etapa</h3>
        <span style={{ fontSize: 12, color: 'var(--color-slate-gray)' }}>
          Total entidades evaluadas: <strong style={{ color: 'var(--color-ink-black)' }}>{fmt(cascada.total_entidades)}</strong>
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 10, marginBottom: 14 }} aria-label="Participación real de BETO">
        <div style={{ padding: 12, borderRadius: 12, background: 'var(--color-mist-gray)', border: '1px solid var(--color-border)', fontSize: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-slate-gray)', marginBottom: 4 }}>1. Índice de confianza</div>
          <p style={{ margin: 0, color: 'var(--color-ink-black)' }}>
            BETO calculó la confianza de <strong>{fmt(lineasConfianza)}</strong> líneas que las reglas no resolvieron
          </p>
        </div>
        <div style={{ padding: 12, borderRadius: 12, background: 'var(--color-mist-gray)', border: '1px solid var(--color-border)', fontSize: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-slate-gray)', marginBottom: 4 }}>2. Cascada final (residuales)</div>
          <p style={{ margin: 0, color: 'var(--color-ink-black)' }}>
            {cascadaActiva
              ? <>BETO resolvió <strong>{fmt(betoResueltas)}</strong> entidades residuales</>
              : <em>Esta etapa está desactivada por configuración</em>}
          </p>
        </div>
        <div style={{ padding: 12, borderRadius: 12, background: 'var(--color-mist-gray)', border: '1px solid var(--color-border)', fontSize: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-slate-gray)', marginBottom: 4 }}>3. Control de calidad (QC)</div>
          <p style={{ margin: 0, color: 'var(--color-ink-black)' }}>
            {qcActivo
              ? (cascada.acuerdo_qc_pct != null
                  ? <>BETO coincidió con las reglas en <strong>{cascada.acuerdo_qc_pct} %</strong></>
                  : <span>Sin comparaciones registradas en este lote</span>)
              : <em>Esta etapa está desactivada por configuración</em>}
          </p>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12 }}>
        {etapas.map((et) => {
          const info = ORIGEN_INFO[et.etapa] || ORIGEN_INFO.ENCABEZADO;
          return (
            <div key={et.etapa} style={{ padding: 12, borderRadius: 12, background: 'var(--color-mist-gray)', border: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 999, background: info.bg, color: info.color }}>{info.label}</span>
                <span style={{ fontSize: 12, fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: 'var(--color-ink-black)' }}>{fmt(et.cantidad)}</span>
              </div>
              <AnimatedProgressBarV2 value={Number(et.porcentaje || 0)} color={info.bar} height={6} ariaLabel={`${info.label}: ${et.porcentaje ?? 0} %`} />
              <p style={{ fontSize: 11, color: 'var(--color-slate-gray)', marginTop: 4 }}>{et.porcentaje ?? 0} % del total</p>
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: 14, padding: 12, borderRadius: 12, background: 'var(--dataops-info-bg)', color: 'var(--dataops-info-text)', fontSize: 12, lineHeight: 1.5 }}>
        <strong>Qué significa:</strong> El sistema resuelve primero por cédula exacta y encabezados confiables; luego aplica coincidencia aproximada y patrones, y reserva a BETO solo para las filas residuales sin sobrescribir vínculos exactos ni crear perfiles nuevos. Cuando una fuente no trae cédula (por ejemplo encuestas de evaluación docente), <em>Cédula exacta = 0</em> es esperable.
      </div>
    </section>
  );
}
