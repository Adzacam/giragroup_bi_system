import React, { useId, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { CheckCircle2 } from 'lucide-react';

const DUST_SPECKS = [
  { left: '12%', top: '18%', size: 1.5, delay: '0s', dur: '22s', op: 0.28 },
  { left: '24%', top: '64%', size: 1.2, delay: '-4s', dur: '26s', op: 0.22 },
  { left: '38%', top: '28%', size: 1.8, delay: '-9s', dur: '24s', op: 0.32 },
  { left: '47%', top: '76%', size: 1.2, delay: '-2s', dur: '28s', op: 0.20 },
  { left: '54%', top: '14%', size: 1.5, delay: '-11s', dur: '21s', op: 0.26 },
  { left: '63%', top: '52%', size: 1.3, delay: '-6s', dur: '25s', op: 0.22 },
  { left: '72%', top: '82%', size: 1.6, delay: '-14s', dur: '27s', op: 0.30 },
  { left: '84%', top: '36%', size: 1.4, delay: '-3s', dur: '23s', op: 0.25 },
  { left: '19%', top: '84%', size: 1.2, delay: '-8s', dur: '29s', op: 0.18 },
  { left: '89%', top: '68%', size: 1.5, delay: '-12s', dur: '24s', op: 0.26 },
  { left: '43%', top: '44%', size: 1.1, delay: '-5s', dur: '30s', op: 0.18 },
  { left: '59%', top: '34%', size: 1.4, delay: '-15s', dur: '26s', op: 0.22 },
  { left: '31%', top: '42%', size: 1.2, delay: '-7s', dur: '27s', op: 0.20 },
  { left: '76%', top: '19%', size: 1.6, delay: '-10s', dur: '22s', op: 0.28 },
];

const VERTICAL_LINES = [
  { x: 365, y1: 140, y2: 430, op: 0.14, dur: '11s', delay: '-2s' },
  { x: 410, y1: 260, y2: 720, op: 0.22, dur: '9.5s', delay: '-5s' },
  { x: 452, y1: 90, y2: 520, op: 0.16, dur: '13s', delay: '-1s' },
  { x: 498, y1: 190, y2: 810, op: 0.26, dur: '8.5s', delay: '-4s' },
  { x: 540, y1: 310, y2: 760, op: 0.18, dur: '12s', delay: '-7s' },
  { x: 585, y1: 120, y2: 590, op: 0.20, dur: '10.5s', delay: '-3s' },
  { x: 628, y1: 240, y2: 680, op: 0.13, dur: '14s', delay: '-6s' },
];

export default function LoginHeroPane() {
  const uid = useId().replace(/:/g, '');
  const location = useLocation();
  const [bgVersion, setBgVersion] = useState(() =>
    location.pathname.startsWith('/v2') ? 'v2' : 'v1'
  );
  const grainFilterId = `v2-hero-grain-${uid}`;
  const silverGradTrId = `v2-silver-tr-${uid}`;
  const silverGradBlId = `v2-silver-bl-${uid}`;
  const dropGradId = `v2-drop-grad-${uid}`;
  const circuitGradId = `v2-circuit-grad-${uid}`;

  return (
    <div
      className={`login-hero-pane v2-hero-pane ${bgVersion === 'v2' ? 'is-bg-v2' : 'is-bg-v1'}`}
      aria-label="Resumen de capacidades de GIRA Group BI"
    >
      {/* Capa 1: Lienzo Base */}
      <div className="v2-hero-obsidian-canvas" aria-hidden="true" />

      {/* Capa 2: Resplandores Difusos */}
      <div className="v2-hero-volumetric-clouds" aria-hidden="true">
        <div className="v2-cloud-bottom-left" />
        <div className="v2-cloud-top-right" />
      </div>

      {/* Partículas sutiles tipo polvo suspendido (solo en Fondo II) */}
      {bgVersion === 'v2' && (
        <div className="v2-hero-dust-layer" aria-hidden="true">
          {DUST_SPECKS.map((s, idx) => (
            <span
              key={idx}
              className="v2-hero-dust-speck"
              style={{
                left: s.left,
                top: s.top,
                width: `${s.size}px`,
                height: `${s.size}px`,
                opacity: s.op,
                animationDuration: s.dur,
                animationDelay: s.delay,
              }}
            />
          ))}
        </div>
      )}

      {/* Capa 3: Trazos SVG (V1 = 2 arcos 90° | V2 = líneas verticales centrales + circuitos laterales) */}
      <svg
        className="v2-hero-curved-lines-svg"
        viewBox="0 0 1000 1000"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id={silverGradTrId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0" />
            <stop offset="26%" stopColor="#CBD5E1" stopOpacity="0.72" />
            <stop offset="52%" stopColor="#FFFFFF" stopOpacity="1" />
            <stop offset="74%" stopColor="#F1B844" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#94A3B8" stopOpacity="0" />
          </linearGradient>
          <linearGradient id={silverGradBlId} x1="100%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0" />
            <stop offset="26%" stopColor="#CBD5E1" stopOpacity="0.72" />
            <stop offset="52%" stopColor="#FFFFFF" stopOpacity="1" />
            <stop offset="74%" stopColor="#F1B844" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#94A3B8" stopOpacity="0" />
          </linearGradient>
          <linearGradient id={dropGradId} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#CBD5E1" stopOpacity="0" />
            <stop offset="52%" stopColor="#F1B844" stopOpacity="0.75" />
            <stop offset="82%" stopColor="#FFFFFF" stopOpacity="0.98" />
            <stop offset="100%" stopColor="#F1B844" stopOpacity="0.90" />
          </linearGradient>
          <linearGradient id={circuitGradId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#94A3B8" stopOpacity="0.50" />
            <stop offset="48%" stopColor="#F1B844" stopOpacity="0.78" />
            <stop offset="75%" stopColor="#E2E8F0" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#CBD5E1" stopOpacity="0" />
          </linearGradient>
        </defs>

        {bgVersion === 'v1' ? (
          <g className="v2-hero-curve-group">
            <path
              d="M 620 44 L 860 44 Q 956 44 956 140 L 956 380"
              stroke={`url(#${silverGradTrId})`}
              className="v2-hero-curve-base"
              vectorEffect="non-scaling-stroke"
            />
            <path
              d="M 620 44 L 860 44 Q 956 44 956 140 L 956 380"
              stroke={`url(#${silverGradTrId})`}
              className="v2-hero-curve-glint"
              vectorEffect="non-scaling-stroke"
            />
            <path
              d="M 380 956 L 140 956 Q 44 956 44 860 L 44 620"
              stroke={`url(#${silverGradBlId})`}
              className="v2-hero-curve-base"
              vectorEffect="non-scaling-stroke"
            />
            <path
              d="M 380 956 L 140 956 Q 44 956 44 860 L 44 620"
              stroke={`url(#${silverGradBlId})`}
              className="v2-hero-curve-glint"
              vectorEffect="non-scaling-stroke"
              style={{ animationDelay: '-6s' }}
            />
          </g>
        ) : (
          <g className="v2-hero-circuit-group">
            {/* Líneas verticales finas en la franja central con segmentos luminosos descendentes */}
            {VERTICAL_LINES.map((ln, idx) => (
              <g key={idx}>
                <line
                  x1={ln.x}
                  y1={ln.y1}
                  x2={ln.x}
                  y2={ln.y2}
                  stroke="#CBD5E1"
                  strokeOpacity={ln.op}
                  strokeWidth="0.75"
                  vectorEffect="non-scaling-stroke"
                />
                <line
                  x1={ln.x}
                  y1={ln.y1}
                  x2={ln.x}
                  y2={ln.y2}
                  stroke={`url(#${dropGradId})`}
                  strokeWidth="1.2"
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                  className="v2-hero-vertical-drop"
                  style={{
                    animationDuration: ln.dur,
                    animationDelay: ln.delay,
                  }}
                />
              </g>
            ))}

            {/* Contornos de circuitos abstractos en laterales superiores e inferiores */}
            {[
              'M 0 115 L 135 115 Q 160 115 178 133 L 245 200',
              'M 0 155 L 95 155 Q 116 155 132 171 L 190 229',
              'M 1000 135 L 855 135 Q 830 135 812 153 L 735 230',
              'M 1000 185 L 895 185 Q 875 185 860 200 L 795 265',
              'M 0 845 L 145 845 Q 170 845 188 827 L 260 755',
              'M 0 890 L 105 890 Q 125 890 140 875 L 200 815',
              'M 1000 830 L 860 830 Q 835 830 817 812 L 745 740',
              'M 1000 880 L 895 880 Q 875 880 860 865 L 790 795',
            ].map((d, idx) => (
              <g key={d}>
                <path
                  d={d}
                  fill="none"
                  stroke={`url(#${circuitGradId})`}
                  strokeWidth="0.95"
                  vectorEffect="non-scaling-stroke"
                  opacity="0.55"
                />
                <path
                  d={d}
                  fill="none"
                  stroke={idx % 2 === 0 ? '#F1B844' : '#FFFFFF'}
                  strokeWidth="1.35"
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                  className="v2-hero-circuit-glint"
                  style={{ animationDelay: `${idx * -1.7}s` }}
                />
              </g>
            ))}
          </g>
        )}
      </svg>

      {/* Selector discreto de Fondo I / Fondo II */}
      <div className="v2-hero-bg-switcher" role="group" aria-label="Versión de fondo">
        <button
          type="button"
          onClick={() => setBgVersion('v1')}
          className={`v2-hero-bg-pill ${bgVersion === 'v1' ? 'is-active' : ''}`}
        >
          Fondo I
        </button>
        <button
          type="button"
          onClick={() => setBgVersion('v2')}
          className={`v2-hero-bg-pill ${bgVersion === 'v2' ? 'is-active' : ''}`}
        >
          Fondo II
        </button>
      </div>

      {/* Capa 4: Grano Cinematográfico Fino y Sutil */}
      <svg className="v2-hero-film-grain" aria-hidden="true">
        <filter id={grainFilterId}>
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.82"
            numOctaves="3"
            stitchTiles="stitch"
          />
        </filter>
        <rect width="100%" height="100%" filter={`url(#${grainFilterId})`} />
      </svg>

      {/* Tarjetas Ejecutivas Glassmórficas con Flotación Pura */}
      <div className="v2-hero-cards-stack">
        {/* Card Superior (Flotante Principal) */}
        <article className="v2-hero-glass-card v2-hero-card-a">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
              marginBottom: '14px',
              flexWrap: 'wrap',
            }}
          >
            <span className="v2-hero-card-eyebrow">
              RESOLUCIÓN DE IDENTIDAD · CASCADA 5 ETAPAS
            </span>
            <span className="v2-hero-card-badge">
              BETO NER + RAPIDFUZZ
            </span>
          </div>

          <h2 className="v2-hero-card-title">
            “Vinculación determinística y semántica: CI Exacta, Encabezado, Fuzzy, Regex y BETO.”
          </h2>

          <div className="v2-hero-card-status">
            <CheckCircle2 size={15} style={{ flexShrink: 0 }} />
            <span>Idempotencia garantizada y gobernanza Cero-PII en PostgreSQL</span>
          </div>
        </article>

        {/* Card Inferior (Flotante Secundaria — Glassmórfica Plata/Ámbar Sutil) */}
        <article className="v2-hero-glass-card v2-hero-glass-card-secondary v2-hero-card-b">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
              marginBottom: '12px',
              flexWrap: 'wrap',
            }}
          >
            <span className="v2-hero-card-eyebrow-gold">
              INTELIGENCIA EJECUTIVA · CMI &amp; ANALÍTICA PREDICTIVA
            </span>
            <span className="v2-hero-card-badge-gold">
              22 KPIS · m=12
            </span>
          </div>

          <h3 className="v2-hero-card-title" style={{ fontSize: '19px', marginBottom: '10px' }}>
            “Cuadro de Mando Integral en 4 perspectivas con proyección Holt-Winters y reglas IF/THEN.”
          </h3>

          <p className="v2-hero-card-desc">
            “Trazabilidad auditable desde la ingesta documental hasta el tablero directivo y Power BI según tu rol RBAC.”
          </p>
        </article>
      </div>
    </div>
  );
}
