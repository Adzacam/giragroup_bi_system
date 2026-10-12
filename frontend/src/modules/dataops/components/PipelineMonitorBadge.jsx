import React from 'react';
import { FileText, CheckCircle2, AlertTriangle, Activity, Code2, Layers } from 'lucide-react';

export default function PipelineMonitorBadge({
  eyebrow = 'Pipeline Monitor',
  title = 'Motor de Parseo & Conversión a Texto Plano',
  autoProcessedPct = 95.8,
  reviewRequiredPct = 4.2,
  totalRecords = 1440,
  autoCount = 1380,
  reviewCount = 60,
  isProcessing = false,
}) {
  return (
    <div
      style={{
        padding: '20px 24px',
        borderRadius: '20px',
        backgroundColor: 'var(--color-paper-white, #ffffff)',
        border: '1px solid var(--color-border, #ececec)',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.04)',
        marginBottom: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '12px',
              backgroundColor: 'rgba(217, 155, 38, 0.12)',
              color: 'var(--color-gira-gold, #D99B26)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <FileText size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  color: 'var(--color-gira-gold, #D99B26)',
                }}
              >
                {eyebrow}
              </span>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '10.5px',
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  backgroundColor: isProcessing ? 'rgba(217, 155, 38, 0.15)' : 'rgba(27, 135, 84, 0.12)',
                  color: isProcessing ? '#b45309' : '#1b8754',
                }}
              >
                <Activity size={12} className={isProcessing ? 'animate-spin' : ''} />
                {isProcessing ? 'Serializando en Tiempo Real' : 'Motor de Texto Plano Activo'}
              </span>
            </div>
            <h4
              style={{
                fontFamily: 'var(--font-signifier, serif)',
                fontSize: '18px',
                fontWeight: 400,
                color: 'var(--color-ink-black, #17191c)',
                margin: 0,
              }}
            >
              {title}
            </h4>
          </div>
        </div>

        {/* Badges Técnicos del Pipeline de Texto Plano */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <div
            style={{
              padding: '6px 12px',
              borderRadius: '12px',
              backgroundColor: 'rgba(12, 30, 51, 0.05)',
              border: '1px solid rgba(12, 30, 51, 0.15)',
              fontSize: '12px',
              color: 'var(--color-ink-black, #0C1E33)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Layers size={14} color="#D99B26" />
            <span>Formatos: <strong>Excel (.xlsx), Forms (.csv), Moodle (.xml)</strong></span>
          </div>

          <div
            style={{
              padding: '6px 12px',
              borderRadius: '12px',
              backgroundColor: 'rgba(27, 135, 84, 0.08)',
              border: '1px solid rgba(27, 135, 84, 0.2)',
              fontSize: '12px',
              color: '#1b8754',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Code2 size={14} />
            <span>Codificación: <strong>UTF-8 Estricto</strong></span>
          </div>
        </div>
      </div>

      {/* Barra de progreso de distribución de la serialización */}
      <div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '12px',
            marginBottom: '8px',
            flexWrap: 'wrap',
            gap: '8px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle2 size={15} color="#1b8754" />
            <span style={{ fontWeight: 500 }}>
              Serializados a Texto Plano:{' '}
              <strong style={{ color: '#1b8754' }}>
                {autoProcessedPct}% ({autoCount.toLocaleString()} filas)
              </strong>
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertTriangle size={15} color="#b45309" />
            <span style={{ fontWeight: 500 }}>
              Alertas de Estructura / Parseo:{' '}
              <strong style={{ color: '#b45309' }}>
                {reviewRequiredPct}% ({reviewCount.toLocaleString()} filas)
              </strong>
            </span>
          </div>
        </div>

        {/* Visual Progress Bar */}
        <div
          style={{
            height: '10px',
            borderRadius: '9999px',
            backgroundColor: 'rgba(217, 155, 38, 0.2)',
            overflow: 'hidden',
            display: 'flex',
          }}
        >
          <div
            style={{
              width: `${autoProcessedPct}%`,
              backgroundColor: '#1b8754',
              borderRadius: '9999px 0 0 9999px',
              transition: 'width 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          />
          <div
            style={{
              width: `${reviewRequiredPct}%`,
              backgroundColor: '#b45309',
              borderRadius: '0 9999px 9999px 0',
              transition: 'width 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          />
        </div>
      </div>
    </div>
  );
}
