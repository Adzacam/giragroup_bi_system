import React, { useEffect, useRef, useState } from 'react';
import { useTheme } from '../../context/ThemeContext';

/**
 * Botón circular (46px) con animación orbital y trazado SVG de la "G" de GIRA Group.
 * En reposo la "G" siempre está completa (stroke-dashoffset: 0) y derecha (rotate(0deg)).
 * Al abrir/cerrar ejecuta @keyframes v2-gira-spin-draw.
 */
export default function GiraAnimatedLogoButton({
  isOpen = false,
  onClick,
  ariaLabel = 'Abrir o cerrar menú lateral',
  title = 'Menú de módulos GIRA',
  className = '',
}) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [animating, setAnimating] = useState(false);
  const firstRender = useRef(true);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    setAnimating(true);
    const t = setTimeout(() => setAnimating(false), 580);
    return () => clearTimeout(t);
  }, [isOpen]);

  const handleClick = (e) => {
    setAnimating(true);
    setTimeout(() => setAnimating(false), 580);
    onClick?.(e);
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label={ariaLabel}
      aria-expanded={isOpen}
      title={title}
      className={`v2-gira-logo-btn ${isOpen ? 'is-open' : 'is-closed'} ${isDark ? 'is-dark' : 'is-light'} ${animating ? 'is-animating' : ''} ${className}`}
    >
      <svg
        viewBox="0 0 180 180"
        width="34"
        height="34"
        className="v2-gira-logo-svg"
        aria-hidden="true"
      >
        {/* Medallón interior (navy en claro, superficie oscura en oscuro) */}
        <circle
          cx="90"
          cy="90"
          r="76"
          className="v2-gira-medallion"
        />
        {/* Anillo dorado exterior sutil */}
        <circle
          cx="90"
          cy="90"
          r="71"
          fill="none"
          strokeWidth="2.5"
          className="v2-gira-ring"
        />
        {/* Destello dorado */}
        <circle
          cx="131"
          cy="49"
          r="5"
          className="v2-gira-sparkle"
        />
        {/* Trazado geométrico oficial de la 'G' de GIRA (Versión 1) centrado en el medallón circular */}
        <g transform="translate(8.5, 11.5)">
          <path
            d="M 83 29 L 123 69 Q 133 79 123 89 L 91 121 Q 81 131 71 121 L 40 90 Q 30 80 40 70 L 53 57 Q 63 47 73 57 L 96 81"
            fill="none"
            strokeWidth="12"
            strokeLinecap="round"
            strokeLinejoin="round"
            pathLength="100"
            className="v2-gira-g-path"
          />
        </g>
      </svg>
    </button>
  );
}
