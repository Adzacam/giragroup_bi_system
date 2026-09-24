import React, { useState, useRef } from 'react';
import { CheckCircle2 } from 'lucide-react';

export default function LoginHeroPane() {
  const heroRef = useRef(null);
  const card1Ref = useRef(null);
  const card2Ref = useRef(null);
  const [card1Offset, setCard1Offset] = useState({ x: 0, y: 0 });
  const [card2Offset, setCard2Offset] = useState({ x: 0, y: 0 });
  const [mousePos, setMousePos] = useState({ x: 340, y: 260 });

  // Mouse repulsion physics and bounded boundary detection
  const handleHeroMouseMove = (e) => {
    if (!heroRef.current) return;
    const rect = heroRef.current.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    setMousePos({ x: mx, y: my });

    if (card1Ref.current) {
      const c1Rect = card1Ref.current.getBoundingClientRect();
      const c1x = c1Rect.left - rect.left + c1Rect.width / 2;
      const c1y = c1Rect.top - rect.top + c1Rect.height / 2;
      const dist1 = Math.hypot(mx - c1x, my - c1y);
      if (dist1 < 160) {
        const force = (160 - dist1) / 160;
        const angle = Math.atan2(c1y - my, c1x - mx);
        const ox = Math.max(-30, Math.min(30, Math.cos(angle) * force * 35));
        const oy = Math.max(-25, Math.min(25, Math.sin(angle) * force * 30));
        setCard1Offset({ x: ox, y: oy });
      } else {
        setCard1Offset({ x: 0, y: 0 });
      }
    }

    if (card2Ref.current) {
      const c2Rect = card2Ref.current.getBoundingClientRect();
      const c2x = c2Rect.left - rect.left + c2Rect.width / 2;
      const c2y = c2Rect.top - rect.top + c2Rect.height / 2;
      const dist2 = Math.hypot(mx - c2x, my - c2y);
      if (dist2 < 160) {
        const force = (160 - dist2) / 160;
        const angle = Math.atan2(c2y - my, c2x - mx);
        const ox = Math.max(-30, Math.min(30, Math.cos(angle) * force * 35));
        const oy = Math.max(-25, Math.min(25, Math.sin(angle) * force * 30));
        setCard2Offset({ x: ox, y: oy });
      } else {
        setCard2Offset({ x: 0, y: 0 });
      }
    }
  };

  const handleHeroMouseLeave = () => {
    setCard1Offset({ x: 0, y: 0 });
    setCard2Offset({ x: 0, y: 0 });
  };

  return (
    <div 
      ref={heroRef}
      onMouseMove={handleHeroMouseMove}
      onMouseLeave={handleHeroMouseLeave}
      className="login-hero-pane" 
      style={{
        padding: '60px 48px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
        backdropFilter: 'blur(10px)',
      }}
    >
      {/* Radial Peach Gradient Ambient Glow sensible al movimiento del mouse */}
      <div 
        className="login-hero-glow" 
        style={{
          position: 'absolute',
          left: `${mousePos.x - 300}px`,
          top: `${mousePos.y - 300}px`,
          width: '600px',
          height: '600px',
          pointerEvents: 'none',
          borderRadius: '50%',
          transition: 'left 0.12s ease-out, top 0.12s ease-out',
        }} 
      />

      {/* Floating Card 1: Inferencia NLP */}
      <div 
        ref={card1Ref}
        className="floating-artifact kinetic-card in-view ambient-float-a"
        style={{
          padding: '24px 28px',
          maxWidth: '440px',
          marginBottom: '24px',
          zIndex: 2,
          boxShadow: 'var(--shadow-artifact)',
          transform: `translate3d(${card1Offset.x}px, ${card1Offset.y}px, 0)`,
          transition: 'transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <span style={{
            fontSize: '11px',
            textTransform: 'uppercase',
            fontWeight: 600,
            color: 'var(--color-ash-gray)',
            letterSpacing: '0.8px',
          }}>
            Inferencia NLP en Tiempo Real
          </span>
          <span style={{
            fontSize: '12px',
            color: 'var(--color-sienna-brown)',
            background: 'var(--color-blush-peach)',
            padding: '3px 10px',
            borderRadius: '9999px',
            fontWeight: 600,
          }}>
            BETO v2.4
          </span>
        </div>
        <div style={{
          fontFamily: 'var(--font-signifier)',
          fontSize: '22px',
          lineHeight: 1.3,
          color: 'var(--color-ink-black)',
        }}>
          "Doble validación de confianza: Extracción NER + RapidFuzz Cross-Source."
        </div>
        <div style={{
          marginTop: '14px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '13px',
          color: 'var(--color-alert-green)',
        }}>
          <CheckCircle2 size={16} />
          <span>Alineado a Doctrina Kimball (Sin ambigüedades)</span>
        </div>
      </div>

      {/* Floating Card 2: Disparador Campo Crítico */}
      <div 
        ref={card2Ref}
        className="card-peach-accent kinetic-card in-view ambient-float-b"
        style={{
          maxWidth: '460px',
          marginLeft: '28px',
          boxShadow: '0 18px 40px rgba(93, 42, 26, 0.08)',
          zIndex: 3,
          transform: `translate3d(${card2Offset.x}px, ${card2Offset.y}px, 0)`,
          transition: 'transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease',
        }}
      >
        <span style={{
          fontSize: '11px',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.9px',
        }}>
          Disparador de Integridad de Datos
        </span>
        <h3 className="serif-heading" style={{ fontSize: '24px', margin: '8px 0 12px 0' }}>
          Si falta la Cédula de Identidad en cualquier fuente, la regla de validación fuerza revisión visual inmediata.
        </h3>
        <p style={{ fontSize: '13.5px', opacity: 0.9, lineHeight: 1.5 }}>
          Garantía de integridad referencial para las dimensiones de alumnos y docentes en PostgreSQL.
        </p>
      </div>
    </div>
  );
}
