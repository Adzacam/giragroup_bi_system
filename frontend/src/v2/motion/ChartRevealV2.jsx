import React, { useRef } from 'react';
import { useInViewOnceV2 } from './useInViewOnceV2';

/**
 * Monta su contenido (por ejemplo una gráfica Chart.js) únicamente cuando la sección
 * entra en pantalla, de modo que la animación punto a punto arranque al ser visible.
 */
export default function ChartRevealV2({
  children,
  className = '',
  style = {},
  threshold = 0.15,
}) {
  const containerRef = useRef(null);
  const inView = useInViewOnceV2(containerRef, { threshold });

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: '100%', height: '100%', ...style }}
    >
      {inView ? children : null}
    </div>
  );
}
