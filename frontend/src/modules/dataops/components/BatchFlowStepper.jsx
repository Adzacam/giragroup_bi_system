import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { UploadCloud, FileText, Cpu, UserCheck, CheckCircle2 } from 'lucide-react';
import { useParentChildTransitionV2 } from '../../../v2/transitions/useParentChildTransitionV2';
import { toDataopsPath } from '../../../v2/utils/v2Routes';

export default function BatchFlowStepper({ currentStep = 1, batchId = null, pendientesCount = 0, allCompleted = false }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { triggerParentChild } = useParentChildTransitionV2();
  const effectiveBatchId = batchId || localStorage.getItem('last_active_batch_id');

  const steps = [
    {
      num: 1,
      title: 'Carga',
      subtitle: '¿Qué estoy cargando y reglas?',
      path: '/dataops/ingesta',
      icon: UploadCloud,
      available: true
    },
    {
      num: 2,
      title: 'Lectura de BETO',
      subtitle: '¿Qué entendió el modelo?',
      path: effectiveBatchId ? `/dataops/lote/${effectiveBatchId}/beto` : '/dataops/beto',
      icon: Cpu,
      available: true
    },
    {
      num: 3,
      title: `Revisión ${pendientesCount > 0 ? `(${pendientesCount})` : ''}`,
      subtitle: '¿Qué debo decidir yo?',
      path: effectiveBatchId ? `/dataops/lote/${effectiveBatchId}/revision` : '/dataops/revision',
      icon: UserCheck,
      available: true,
      badge: pendientesCount > 0 ? pendientesCount : null
    }
  ];

  const handleStepClick = (step, sourceEl) => {
    if (step.available) {
      const target = toDataopsPath(step.path, location.pathname);
      triggerParentChild(sourceEl, () => navigate(target));
    }
  };

  return (
    <div className="floating-artifact v2-stepper-pill" style={{
      padding: '16px 28px',
      marginBottom: '28px',
      overflowX: 'auto',
      borderRadius: '32px',
      backgroundColor: 'var(--color-paper-white)',
      width: '100%',
      display: 'block'
    }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, minmax(150px, 1fr))',
        alignItems: 'start',
        gap: '12px',
        position: 'relative',
        width: '100%',
        minWidth: '480px'
      }}>
        {/* Línea conectora de fondo */}
        <div style={{
          position: 'absolute',
          top: '36px',
          left: '16.67%',
          right: '16.67%',
          height: '2px',
          backgroundColor: 'var(--color-border)',
          zIndex: 0
        }} />

        {steps.map((step) => {
          const isCompleted = allCompleted || step.num < currentStep;
          const isCurrent = !allCompleted && step.num === currentStep;
          const Icon = step.icon;

          return (
            <div
              key={step.num}
              className={`v2-stepper-step ${isCurrent ? 'is-active' : ''}`}
              aria-current={isCurrent ? 'step' : undefined}
              onClick={(e) => handleStepClick(step, e.currentTarget)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                position: 'relative',
                zIndex: 1,
                cursor: step.available ? 'pointer' : 'not-allowed',
                opacity: step.available ? 1 : 0.45,
                transition: 'all 0.2s ease',
                padding: '12px 10px',
                borderRadius: '22px',
                border: isCurrent ? '1.8px solid var(--color-gira-gold)' : '1.8px solid transparent',
                backgroundColor: isCurrent ? 'var(--color-mist-gray)' : 'transparent'
              }}
            >
              {/* Círculo del icono */}
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: isCompleted
                    ? '#1B8754'
                    : isCurrent
                    ? 'var(--color-gira-gold, #D99B26)'
                    : 'var(--color-paper-white)',
                  color: isCompleted || isCurrent ? '#ffffff' : 'var(--color-slate-gray)',
                  border: isCompleted || isCurrent ? 'none' : '2px solid var(--color-border)',
                  boxShadow: isCurrent
                    ? '0 0 0 5px rgba(217, 155, 38, 0.25)'
                    : isCompleted
                    ? '0 2px 6px rgba(27, 135, 84, 0.25)'
                    : 'none',
                  transition: 'all 0.3s ease',
                  position: 'relative'
                }}
              >
                {isCompleted ? <CheckCircle2 size={22} /> : <Icon size={20} />}
                
                {step.badge && (
                  <span style={{
                    position: 'absolute',
                    top: '-4px',
                    right: '-4px',
                    backgroundColor: '#ef4444',
                    color: '#ffffff',
                    fontSize: '11px',
                    fontWeight: '700',
                    borderRadius: '9999px',
                    padding: '2px 6px',
                    lineHeight: '1',
                    border: '2px solid var(--color-paper-white)'
                  }}>
                    {step.badge}
                  </span>
                )}
              </div>

              {/* Etiqueta y subtítulo */}
              <div style={{ marginTop: '10px', textAlign: 'center' }}>
                <div style={{
                  fontSize: '13px',
                  fontWeight: isCurrent ? '700' : '600',
                  color: isCurrent ? 'var(--dataops-info-text)' : isCompleted ? 'var(--color-ink-black)' : 'var(--color-slate-gray)'
                }}>
                  {step.num === 1 ? '①' : step.num === 2 ? '②' : step.num === 3 ? '③' : '④'} {step.title}
                </div>
                <div style={{
                  fontSize: '11px',
                  color: 'var(--color-ash-gray)',
                  marginTop: '2px',
                  lineHeight: '1.2'
                }}>
                  {step.subtitle}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
