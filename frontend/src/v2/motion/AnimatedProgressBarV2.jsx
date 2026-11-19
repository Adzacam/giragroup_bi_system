import React, { useEffect, useRef, useState } from 'react';
import { MOTION_DURATION_MS, MOTION_EASING_CSS, prefersReducedMotion } from './useCountUpV2';
import { useInViewOnceV2 } from './useInViewOnceV2';

/**
 * Barra de progreso animada de 0% a X% en 900ms con desaceleración suave,
 * activada cuando entra en pantalla (triggerOnView) o mediante `active`.
 */
export default function AnimatedProgressBarV2({
  value = 0,
  max = 100,
  color = 'var(--color-gira-gold)',
  trackColor,
  height,
  duration = MOTION_DURATION_MS,
  indeterminate = false,
  active = true,
  triggerOnView = true,
  className = '',
  barClassName = '',
  style = {},
  barStyle = {},
  ariaLabel = 'Progreso',
  ...rest
}) {
  const containerRef = useRef(null);
  const inView = useInViewOnceV2(containerRef, { enabled: triggerOnView });
  const isActive = active && (triggerOnView ? inView : true);

  const numericVal = Number(value);
  const numericMax = Number(max) || 100;
  const pct = Number.isFinite(numericVal)
    ? Math.max(0, Math.min(100, (numericVal / numericMax) * 100))
    : 0;

  const skipMotion = prefersReducedMotion() || typeof requestAnimationFrame === 'undefined';
  const [renderedPct, setRenderedPct] = useState(() => (skipMotion ? pct : 0));

  useEffect(() => {
    if (indeterminate) return undefined;
    if (skipMotion) {
      setRenderedPct(pct);
      return undefined;
    }
    if (!isActive) {
      setRenderedPct(0);
      return undefined;
    }

    let raf2 = null;
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => {
        setRenderedPct(pct);
      });
    });

    return () => {
      cancelAnimationFrame(raf1);
      if (raf2) cancelAnimationFrame(raf2);
    };
  }, [pct, skipMotion, indeterminate, isActive]);

  const finalWidth = indeterminate ? '35%' : `${skipMotion ? pct : renderedPct}%`;

  const containerStyle = {
    ...(height !== undefined ? { height } : {}),
    ...(trackColor ? { background: trackColor } : {}),
    ...style,
  };

  const fillStyle = {
    width: finalWidth,
    background: color,
    transition: skipMotion || indeterminate ? undefined : `width ${duration}ms ${MOTION_EASING_CSS}`,
    ...barStyle,
  };

  return (
    <div
      ref={containerRef}
      className={className}
      style={containerStyle}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={indeterminate ? undefined : Math.round(pct)}
      aria-label={ariaLabel}
      {...rest}
    >
      <i className={barClassName} style={fillStyle} />
    </div>
  );
}
