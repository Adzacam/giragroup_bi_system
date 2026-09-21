import React, { useState, useEffect } from 'react';
import { X, Activity } from 'lucide-react';

export default function BetoDrawer({ isOpen, onClose }) {
  const [activeSteps, setActiveSteps] = useState([]);

  useEffect(() => {
    if (isOpen) {
      setActiveSteps([]);
      const delays = [250, 600, 1300, 2000, 2600];
      const steps = [
        "1. Texto crudo recibido: '4892019 LP? | Daza Adriano | Modulo 3 | 75 pts'",
        "2. Tokenización BPE → 8 tokens generados",
        "3. BETO inferencia:\n   - Entidad: Estudiante (Confianza: 0.94)\n   - Entidad: Módulo (Confianza: 0.88)\n   - Entidad: Nota (Confianza: 0.97)",
        "4. RapidFuzz Cross-Source:\n   - Nombre: Homonimia 88%\n   - Módulo: Match asignatura 92%",
        "5. Disparador GIRA-50 Activado:\n   [ERROR] CI dudoso detectado ('?').\n   [ACCIÓN] requiere_revision = True"
      ];

      delays.forEach((delay, index) => {
        setTimeout(() => {
          setActiveSteps(prev => [...prev, { id: index, text: steps[index], isError: index === 4 }]);
        }, delay);
      });
    } else {
      setActiveSteps([]);
    }
  }, [isOpen]);

  return (
    <>
      {/* Overlay to close drawer */}
      {isOpen && (
        <div 
          style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.4)', zIndex: 999 }}
          onClick={onClose}
        />
      )}
      
      {/* Drawer */}
      <div 
        className="beto-drawer"
        style={{ 
          position: 'fixed', top: 0, right: 0, bottom: 0, width: '500px', backgroundColor: '#0f1113', 
          zIndex: 1000, padding: '24px', display: 'flex', flexDirection: 'column',
          transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: '-10px 0 30px rgba(0,0,0,0.5)',
          fontFamily: 'JetBrains Mono, monospace', color: '#e2e8f0'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px', borderBottom: '1px solid #2d3748', paddingBottom: '16px' }}>
          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: '600', color: '#a0aec0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={16} color="#63b3ed" /> PIPELINE TELEMETRY · BETO v2.4
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#a0aec0', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {activeSteps.map((step) => (
            <div 
              key={step.id} 
              className="beto-step"
              style={{ 
                marginBottom: '20px', 
                whiteSpace: 'pre-wrap', 
                borderLeft: `2px solid ${step.isError ? '#e53e3e' : '#374151'}`, 
                paddingLeft: '12px',
                fontSize: '13px',
                lineHeight: '1.6',
                color: step.isError ? '#fc8181' : '#e2e8f0',
                animation: 'fadeInUp 0.3s ease-out forwards'
              }}
            >
              {step.text}
            </div>
          ))}
          {/* Simple keyframes inside component for simplicity, better in a css file but works here */}
          <style>
            {`
              @keyframes fadeInUp {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
              }
            `}
          </style>
        </div>

        <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid #2d3748', display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#718096' }}>
          <span>Status: <span style={{ color: '#48bb78', fontWeight: '600' }}>CONNECTED</span></span>
          <span>PostgreSQL Hook: <span style={{ color: '#48bb78' }}>VALID</span></span>
        </div>
      </div>
    </>
  );
}
