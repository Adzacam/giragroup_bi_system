import React from 'react';
import {
  FileSpreadsheet, FileText, Cpu, ShieldCheck, History, Play,
  Sparkles, Gauge, BarChart3, Lock, GitCompare, AlertTriangle, Database, Link2, CheckCircle2,
} from 'lucide-react';

const CARDS_BY_STEP = {
  1: [
    { icon: FileSpreadsheet, title: 'Archivos leídos y limpiados', desc: 'Hojas usadas o ignoradas y cabeceras normalizadas.' },
    { icon: FileText, title: 'Formularios en línea (CSV)', desc: 'Detección automática de delimitador y codificación.' },
    { icon: Cpu, title: 'Exportes de aula virtual', desc: 'Adaptador específico para reportes de plataforma.' },
    { icon: CheckCircle2, title: 'Tipo de fuente detectado', desc: 'Clasificación por señales con opción de ajuste previo.' },
    { icon: History, title: 'Bitácora del procesamiento', desc: 'Línea de tiempo por etapa y huella SHA-256.' },
    { icon: Play, title: 'Procesamiento bajo demanda', desc: 'Ejecución en segundo plano con seguimiento en vivo.' },
  ],
  2: [
    { icon: FileText, title: 'Texto preparado', desc: 'Registros convertidos a contrato único antes del modelo.' },
    { icon: Sparkles, title: 'Entidades reconocidas', desc: 'Personas, docentes, módulos y programas resaltados IOB2.' },
    { icon: Gauge, title: 'Certeza por registro', desc: 'Bandas 85 % / 60 % y cascada de resolución.' },
    { icon: BarChart3, title: 'Calidad del modelo', desc: 'Matriz de confusión y F1 verificados sobre gold_510.' },
    { icon: Lock, title: 'Datos personales protegidos', desc: 'Cédulas y nombres enmascarados con revelación auditada.' },
  ],
  3: [
    { icon: GitCompare, title: 'Variaciones resueltas', desc: 'Similitud tipográfica en nombres y módulos.' },
    { icon: Link2, title: 'Coincidencias entre fuentes', desc: 'Emparejamiento por score combinado sin identificador común.' },
    { icon: CheckCircle2, title: 'Marcados para revisión', desc: 'Casos agrupados por motivo y banda de confianza.' },
    { icon: AlertTriangle, title: 'Inconsistencias registradas', desc: 'Avisos de bitácora visibles y accionables en bandeja.' },
    { icon: Database, title: 'Guardado en el almacén', desc: 'Carga idempotente de hechos académicos y financieros.' },
    { icon: ShieldCheck, title: 'Claves validadas por similitud', desc: 'Vinculación de códigos POS y módulos institucionales.' },
  ],
};

export default function SystemCapabilitiesStrip({ step = 1 }) {
  const cards = CARDS_BY_STEP[step] || CARDS_BY_STEP[1];
  return (
    <section
      aria-label="Qué hizo el sistema en este paso"
      className="floating-artifact"
      style={{ padding: '14px 18px', marginBottom: 18 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
        <h2 className="serif-heading" style={{ fontSize: 15, margin: 0, color: 'var(--color-ink-black)' }}>
          Qué hizo el sistema en este paso
        </h2>
        <span style={{ fontSize: 11.5, color: 'var(--color-slate-gray)' }}>
          Calidad integral del pipeline DataOps
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(175px, 1fr))', gap: 10 }}>
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <div
              key={c.title}
              style={{
                padding: '10px 12px',
                borderRadius: 10,
                border: '1px solid var(--color-border)',
                background: 'var(--color-mist-gray)',
                transition: 'border-color 0.25s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 4 }}>
                <Icon size={14} color="var(--color-gira-gold)" />
                <strong style={{ fontSize: 12, color: 'var(--color-ink-black)' }}>{c.title}</strong>
              </div>
              <p style={{ fontSize: 11, color: 'var(--color-slate-gray)', margin: 0, lineHeight: 1.4 }}>
                {c.desc}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
