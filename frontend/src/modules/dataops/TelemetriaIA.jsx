import React from 'react';
import { Cpu, Zap, Activity, HardDrive, CheckCircle2 } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';

const MOCK_RUNS = [
  { id: 'BATCH-2026-0915-01', modelo: 'BETO v2.4 (dccuchile/bert-base-spanish-wwm-cased)', registros: 1248, latencia: '1.42s', memoria: '1,840 MB', estado: 'Completado' },
  { id: 'BATCH-2026-0914-04', modelo: 'BETO v2.4 (dccuchile/bert-base-spanish-wwm-cased)', registros: 840, latencia: '0.98s', memoria: '1,620 MB', estado: 'Completado' },
  { id: 'BATCH-2026-0912-02', modelo: 'BETO v2.4 (dccuchile/bert-base-spanish-wwm-cased)', registros: 512, latencia: '0.64s', memoria: '1,450 MB', estado: 'Completado' },
  { id: 'BATCH-2026-0910-01', modelo: 'RapidFuzz Matcher + Levenshtein', registros: 1540, latencia: '0.12s', memoria: '210 MB', estado: 'Completado' },
];

export default function TelemetriaIA() {
  useKineticScroll();

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <PageHeader
        category="FASE 6: INFRAESTRUCTURA &amp; INFERENCIA"
        title="Telemetría y Rendimiento IA"
        italicWord="GIRA-12"
        subtitle="Monitoreo de throughput, latencia de inferencia NLP en streaming (BETO v2.4) y aceleración de hardware en contenedor Docker."
      />

      {/* ── KPI Cards ────────────────────────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '20px',
          marginBottom: '32px',
        }}
      >
        <KpiCard
          label="Latencia P95 Inferencia"
          number="1.42"
          numberSuffix=" seg / lote"
          sublabel="Lotes de 32 documentos crudos"
          badgeText="Nominal"
          badgeType="success"
        />
        <KpiCard
          label="Aceleración Docker"
          number="CUDA 12.2"
          sublabel="NVIDIA TensorRT Compatible"
          badgeText="GPU Active"
          badgeType="peach"
        />
        <KpiCard
          label="Throughput de Tokens"
          number="482"
          numberSuffix=" tok/s"
          sublabel="NER Extracción de Entidades"
          badgeText="Alto Desempeño"
          badgeType="success"
        />
        <KpiCard
          label="Consumo VRAM / RAM"
          number="1.8"
          numberSuffix=" / 6.0 GB"
          sublabel="Buffer PyTorch Optimizado"
          badgeText="Estable"
          badgeType="neutral"
        />
      </div>

      {/* ── Especificaciones del Motor de Inferencia ─────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
          gap: '24px',
          marginBottom: '36px',
        }}
      >
        <div className="card-mist kinetic-card" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <Cpu size={20} color="var(--color-ink-black)" />
            <h3 className="serif-heading" style={{ fontSize: '20px', margin: 0 }}>
              Arquitectura del Modelo BETO v2.4
            </h3>
          </div>
          <p style={{ fontSize: '13.5px', color: 'var(--color-slate-gray)', lineHeight: 1.5, marginBottom: '20px' }}>
            Fine-tuned sobre corpus universitario boliviano para reconocer identidades: <code>[ESTUDIANTE]</code>, <code>[DOCENTE]</code>, <code>[MODULO]</code>, <code>[CALIFICACION]</code>.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', borderBottom: '1px solid var(--color-border)', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-slate-gray)' }}>Backend de Inferencia:</span>
              <strong style={{ fontFamily: 'var(--font-mono)' }}>PyTorch 2.2 + HuggingFace</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', borderBottom: '1px solid var(--color-border)', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-slate-gray)' }}>Tokenizador BPE:</span>
              <strong style={{ fontFamily: 'var(--font-mono)' }}>31,002 vocabularios</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', borderBottom: '1px solid var(--color-border)', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-slate-gray)' }}>Confidence Threshold:</span>
              <strong style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-alert-green)' }}>&ge; 0.85 (Doctrina Kimball)</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
              <span style={{ color: 'var(--color-slate-gray)' }}>Hook a PostgreSQL:</span>
              <strong style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-alert-green)' }}>pg_isready (12ms)</strong>
            </div>
          </div>
        </div>

        <div className="card-peach-accent kinetic-card" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <Zap size={20} color="var(--color-sienna-brown)" />
            <h3 className="serif-heading" style={{ fontSize: '20px', margin: 0, color: 'var(--color-sienna-brown)' }}>
              Protocolo de Ambigüedad Cero
            </h3>
          </div>
          <p style={{ fontSize: '13.5px', lineHeight: 1.5, opacity: 0.95, marginBottom: '18px' }}>
            Si el score del modelo no alcanza el 85% de certidumbre o si la regla GIRA-50 detecta una cédula incompleta, la inferencia se suspende automáticamente y el registro se desvía a la <strong>Bandeja de Revisión Humana</strong>.
          </p>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '12.5px', fontWeight: 600 }}>
            <CheckCircle2 size={16} />
            <span>Integridad referencial blindada en Staging</span>
          </div>
        </div>
      </div>

      {/* ── Tabla de Ejecuciones de Inferencia ───────────────── */}
      <h3 className="serif-heading" style={{ fontSize: '22px', marginBottom: '16px' }}>
        Lotes Recientes Procesados por el Motor NLP
      </h3>
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Identificador Lote</th>
              <th>Pipeline / Modelo</th>
              <th>Registros</th>
              <th>Latencia Total</th>
              <th>Consumo VRAM</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_RUNS.map((run) => (
              <tr key={run.id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12.5px', fontWeight: 600 }}>
                  {run.id}
                </td>
                <td style={{ fontSize: '13px' }}>{run.modelo}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{run.registros}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{run.latencia}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{run.memoria}</td>
                <td>
                  <span className="badge-status badge-status-completed">
                    <CheckCircle2 size={12} /> {run.estado}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
