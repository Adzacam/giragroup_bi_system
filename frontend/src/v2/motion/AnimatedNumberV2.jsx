import React, { useRef } from 'react';
import { MOTION_DURATION_MS, useCountUpV2 } from './useCountUpV2';
import { useInViewOnceV2 } from './useInViewOnceV2';

/**
 * Renderiza una métrica con animación de conteo 0 -> N en 900ms,
 * activada cuando entra en pantalla (triggerOnView) o mediante `active`.
 */
export default function AnimatedNumberV2({
  value,
  duration = MOTION_DURATION_MS,
  enabled = true,
  active = true,
  triggerOnView = true,
  as: Tag = 'span',
  className = '',
  style = {},
  ...rest
}) {
  const elRef = useRef(null);
  const inView = useInViewOnceV2(elRef, { enabled: triggerOnView });
  const isActive = active && (triggerOnView ? inView : true);
  const display = useCountUpV2(value, { duration, enabled, active: isActive });

  return (
    <Tag
      ref={elRef}
      className={className}
      style={{ fontVariantNumeric: 'tabular-nums', ...style }}
      {...rest}
    >
      {display}
    </Tag>
  );
}
