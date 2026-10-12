import React from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileText, Cpu, UserCheck, CheckCircle2 } from 'lucide-react';

export default function BatchFlowStepper({ currentStep = 1, batchId = null, pendientesCount = 0 }) {
  const navigate = useNavigate();

  const steps = [
    {
      num: 1,
      title: 'Ingesta',
      subtitle: '¿Qué estoy cargando y reglas?',
      path: '/dataops/ingesta',
      icon: UploadCloud,
      available: true
    },
    {
      num: 2,
      title: 'Texto plano',
      subtitle: '¿Cómo se transformó mi archivo?',
      path: batchId ? `/dataops/lote/${batchId}/texto` : '/dataops/ingesta',
      icon: FileText,
      available: Boolean(batchId)
    },
    {
      num: 3,
      title: 'Lectura de BETO',
      subtitle: '¿Qué entendió el modelo?',
      path: batchId ? `/dataops/lote/${batchId}/beto` : '/dataops/ingesta',
      icon: Cpu,
      available: Boolean(batchId)
    },
    {
      num: 4,
      title: `Revisión humana ${pendientesCount > 0 ? `(${pendientesCount})` : ''}`,
      subtitle: '¿Qué debo decidir yo?',
      path: batchId ? `/dataops/revision?lote=${batchId}` : '/dataops/revision',
      icon: UserCheck,
      available: true,
      badge: pendientesCount > 0 ? pendientesCount : null
    }
  ];

  const handleStepClick = (step) => {
    if (step.available) {
      navigate(step.path);
    }
  };

  return (
    <div className="floating-artifact" style={{
      padding: '20px 24px',
      marginBottom: '28px',
      overflowX: 'auto',
      backgroundColor: 'var(--color-paper-white)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'relative',
        minWidth: '680px'
      }}>
        {/* Línea conectora de fondo */}
        <div style={{
          position: 'absolute',
          top: '24px',
          left: '50px',
          right: '50px',
          height: '2px',
          backgroundColor: 'var(--color-border)',
          zIndex: 0
        }} />

        {steps.map((step) => {
          const isCompleted = step.num < currentStep;
          const isCurrent = step.num === currentStep;
          const Icon = step.icon;

          return (
            <div
              key={step.num}
              onClick={() => handleStepClick(step)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                position: 'relative',
                zIndex: 1,
                cursor: step.available ? 'pointer' : 'not-allowed',
                opacity: step.available ? 1 : 0.45,
                transition: 'all 0.2s ease',
                width: '150px'
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
                    ? '#10b981'
                    : isCurrent
                    ? '#2563eb'
                    : 'var(--color-paper-white)',
                  color: isCompleted || isCurrent ? '#ffffff' : 'var(--color-slate-gray)',
                  border: isCompleted || isCurrent ? 'none' : '2px solid var(--color-border)',
                  boxShadow: isCurrent
                    ? '0 0 0 5px rgba(37, 99, 235, 0.2)'
                    : isCompleted
                    ? '0 2px 6px rgba(16, 185, 129, 0.25)'
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
