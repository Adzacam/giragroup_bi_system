import React from 'react';

/**
 * GiraGroupLogo — Componente oficial de identidad visual de GiraGroup
 * Renderiza el símbolo geométrico y la marca con trazados SVG puros (cero dependencia de fuentes externas).
 * 
 * Props:
 * @param {number} size - Tamaño en píxeles (ancho y alto). Default: 100
 * @param {boolean} isGold - Si es true, el símbolo adopta el color dorado de la marca. Default: false
 * @param {string} variant - 'auto' | 'gold' | 'default'. Soporte retrocompatible.
 * @param {boolean} showGroup - Muestra u oculta la palabra 'Group' vectorizada. Default: true
 * @param {boolean} showText - Si es true, muestra la leyenda lateral institucional (GIRA Group / BI & DataOps). Default: false
 * @param {string} className - Clases CSS adicionales.
 * @param {object} style - Estilos en línea para el contenedor o SVG.
 */
export const GiraGroupLogo = ({
  size = 100,
  isGold = false,
  variant = 'auto',
  showGroup = true,
  showText = false,
  className = '',
  style = {},
}) => {
  const effectiveIsGold = isGold || variant === 'gold';

  const colors = {
    background: '#1B354D',
    symbol: effectiveIsGold ? '#D99B26' : '#FFFFFF',
    text: '#D99B26',
  };

  const svgContent = (
    <svg
      width={size}
      height={size}
      viewBox="0 0 180 180"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="GiraGroup"
      className={!showText ? className : undefined}
      style={{
        display: 'block',
        flexShrink: 0,
        borderRadius: 12,
        background: colors.background,
        boxShadow: effectiveIsGold
          ? '0 4px 16px rgba(217,155,38,0.25)'
          : '0 4px 12px rgba(12,30,51,0.25)',
        border: effectiveIsGold
          ? '1px solid rgba(217,155,38,0.5)'
          : '1px solid rgba(255,255,255,0.08)',
        ...(!showText ? style : {}),
      }}
    >
      {/* Símbolo geométrico principal */}
      <g
        fill="none"
        stroke={colors.symbol}
        strokeWidth="11.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path
          d="
            M 83 29
            L 123 69
            Q 133 79 123 89
            L 91 121
            Q 81 131 71 121
            L 40 90
            Q 30 80 40 70
            L 53 57
            Q 63 47 73 57
            L 96 81
          "
        />
      </g>

      {/* Nombre de la marca "Group" vectorizado con trazados puros (independiente de fuentes del sistema) */}
      {showGroup && (
        <path
          fill={colors.text}
          fillRule="evenodd"
          d="
            M 65.8,141.2 A 2.7,2.7 0 0,1 68.5,138.5 L 75.8,138.5 L 75.8,140.7 L 68.6,140.7 A 0.7,0.7 0 0,0 67.9,141.4 L 67.9,145.6 A 0.7,0.7 0 0,0 68.6,146.3 L 73.8,146.3 L 73.8,144.5 L 71.0,144.5 L 71.0,142.5 L 76.2,142.5 L 76.2,146.5 A 2.0,2.0 0 0,1 74.2,148.5 L 68.5,148.5 A 2.7,2.7 0 0,1 65.8,145.8 Z
            M 77.8,141.2 L 82.5,141.2 A 1.8,1.8 0 0,1 84.3,143.0 L 84.3,143.4 L 82.1,143.4 A 0.8,0.8 0 0,0 81.3,142.8 L 79.8,142.8 L 79.8,148.5 L 77.8,148.5 Z
            M 87.0,141.2 L 92.2,141.2 A 2.0,2.0 0 0,1 94.2,143.2 L 94.2,146.5 A 2.0,2.0 0 0,1 92.2,148.5 L 87.0,148.5 A 2.0,2.0 0 0,1 85.0,146.5 L 85.0,143.2 A 2.0,2.0 0 0,1 87.0,141.2 Z
            M 87.2,143.2 L 92.0,143.2 A 0.8,0.8 0 0,1 92.8,144.0 L 92.8,145.7 A 0.8,0.8 0 0,1 92.0,146.5 L 87.2,146.5 A 0.8,0.8 0 0,1 86.4,145.7 L 86.4,144.0 A 0.8,0.8 0 0,1 87.2,143.2 Z
            M 95.3,141.2 L 97.3,141.2 L 97.3,145.8 A 0.8,0.8 0 0,0 98.1,146.6 L 100.7,146.6 A 0.8,0.8 0 0,0 101.5,145.8 L 101.5,141.2 L 103.5,141.2 L 103.5,146.3 A 2.2,2.2 0 0,1 101.3,148.5 L 97.5,148.5 A 2.2,2.2 0 0,1 95.3,146.3 Z
            M 105.1,141.2 L 112.2,141.2 A 2.0,2.0 0 0,1 114.2,143.2 L 114.2,146.5 A 2.0,2.0 0 0,1 112.2,148.5 L 107.1,148.5 L 107.1,152.0 L 105.1,152.0 Z
            M 107.1,143.2 L 112.0,143.2 A 0.8,0.8 0 0,1 112.8,144.0 L 112.8,145.7 A 0.8,0.8 0 0,1 112.0,146.5 L 107.1,146.5 Z
          "
        />
      )}
    </svg>
  );

  if (showText) {
    return (
      <div
        className={className}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
          ...style,
        }}
      >
        {svgContent}
        <div>
          <div
            style={{
              fontWeight: 700,
              letterSpacing: '0.5px',
              fontSize: '16px',
              color: 'var(--color-ink-black)',
              lineHeight: 1.2,
            }}
          >
            GIRA <span style={{ color: 'var(--color-gira-gold, #D99B26)', fontWeight: 700 }}>Group</span>
          </div>
          <div
            style={{
              fontSize: '10px',
              color: 'var(--color-slate-gray)',
              letterSpacing: '1px',
              textTransform: 'uppercase',
              fontWeight: 600,
            }}
          >
            BI &amp; DATAOPS SUITE
          </div>
        </div>
      </div>
    );
  }

  return svgContent;
};

export const GiraLogo = GiraGroupLogo;
export default GiraGroupLogo;
