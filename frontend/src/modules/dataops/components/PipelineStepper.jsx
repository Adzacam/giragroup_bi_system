import React from 'react';
import { FileUp, Split, Wand2, TableProperties, ShieldCheck, Database } from 'lucide-react';

const ICON_MAP = {
  1: FileUp,
  2: Split,
  3: Wand2,
  4: TableProperties,
  5: ShieldCheck,
  6: Database
};

export default function PipelineStepper({ stages, activeStep, onSelectStage, lotName = 'Lote: POS-2026-B_M3' }) {
  const defaultSteps = [
    { id: 1, name: 'Archivo Origen', time: '45ms', desc: 'Parseo UTF-8' },
    { id: 2, name: 'Dispatcher', time: '110ms', desc: 'Acta_POS' },
    { id: 3, name: 'Limpieza', time: '310ms', desc: 'Sanitizado' },
    { id: 4, name: 'Cabeceras', time: '140ms', desc: '12 Columnas' },
    { id: 5, name: 'Esquema', time: '195ms', desc: '95.8% Validez' },
    { id: 6, name: 'A Staging', time: '85ms', desc: 'INSERT batch' },
  ];

  const stepsToRender = (stages && stages.length === 6) ? stages : defaultSteps;

  return (
    <div className="floating-artifact" style={{ padding: '32px 24px', marginBottom: '32px', overflowX: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '36px', minWidth: '700px' }}>
        <h3 className="serif-heading" style={{ fontSize: '16px', margin: 0, color: 'var(--color-ink-black)' }}>
          Pipeline Workflow Execution Graph
        </h3>
        <span style={{
          backgroundColor: 'var(--color-mist-gray)',
          color: 'var(--color-slate-gray)',
          padding: '4px 12px',
          borderRadius: '9999px',
          fontSize: '12px',
          fontWeight: '600',
          fontFamily: 'var(--font-mono)'
        }}>
          {lotName}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative', minWidth: '700px' }}>
        {/* Background Connector Line */}
        <div style={{ position: 'absolute', top: '21px', left: '40px', right: '40px', height: '2px', backgroundColor: 'var(--color-border)', zIndex: 0 }} />

        {stepsToRender.map((step, index) => {
          const Icon = ICON_MAP[step.id] || FileUp;
          const isCompleted = activeStep === -1 || activeStep > index;
          const isActive = activeStep === index + 1;

          return (
            <div key={step.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative', zIndex: 1, width: '110px' }}>
              <div 
                className={`stepper-icon-wrap ${isCompleted ? 'completed' : ''} ${isActive ? 'active pulsing' : ''}`}
                style={{ 
                  width: '42px',
                  height: '42px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center', 
                  backgroundColor: isCompleted ? 'var(--color-alert-green)' : isActive ? '#3b82f6' : 'var(--color-paper-white)', 
                  color: isCompleted || isActive ? '#ffffff' : 'var(--color-slate-gray)',
                  border: isCompleted || isActive ? 'none' : '2px solid var(--color-border)',
                  boxShadow: isActive ? '0 0 0 4px rgba(59, 130, 246, 0.25)' : 'none',
                  transition: 'all 0.3s ease',
                  cursor: 'pointer'
                }}
                onClick={() => onSelectStage ? onSelectStage(step) : alert(`Etapa: ${step.name}\nTiempo: ${step.time}\nDetalle: ${step.desc}`)}
                title={`Etapa: ${step.name}`}
              >
                <Icon size={18} />
              </div>
              <div style={{ marginTop: '12px', textAlign: 'center' }}>
                <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-ink-black)' }}>{step.name}</div>
                <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', marginTop: '4px' }}>
                  {isCompleted && <span style={{ color: 'var(--color-alert-green)' }}>✔</span>} {step.time}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--color-ash-gray)', marginTop: '2px' }}>{step.desc}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
