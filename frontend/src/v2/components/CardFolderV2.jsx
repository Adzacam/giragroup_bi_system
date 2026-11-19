import React, { useState } from 'react';
import { ArrowUpRight } from 'lucide-react';
import AnimatedNumberV2 from '../motion/AnimatedNumberV2';
import AnimatedProgressBarV2 from '../motion/AnimatedProgressBarV2';

/**
 * Componente CardFolderV2 inspirado en Framer Card Folder:
 *  - Capa 1 (Back Cover, z-index 1): border-radius 30px
 *  - Capa 2 (Inner Sliding Card, z-index 2): emerge a -78px y -8deg al hacer hover/focus
 *  - Capa 3 (Front Pocket Flap, z-index 3): bolsillo frontal con pestaña curva SVG
 */
export default function CardFolderV2({
  code = '01',
  title,
  summary,
  badge,
  statusColor,
  value,
  trend,
  progress = null,
  metaText,
  previousText,
  previewMetric,
  previewLabel,
  onOpen,
  className = '',
}) {
  const [isHovered, setIsHovered] = useState(false);
  const displayValue = value ?? previewMetric ?? '—';
  const innerPrimary = metaText || previewLabel || 'Vista ejecutiva';
  const innerSecondary = previousText || (previewMetric && value ? previewMetric : 'Ver evolución →');

  return (
    <button
      type="button"
      onClick={(e) => onOpen?.(e.currentTarget)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onFocus={() => setIsHovered(true)}
      onBlur={() => setIsHovered(false)}
      className={`v2-card-folder ${className}`}
      aria-label={`Abrir detalle: ${title}`}
    >
      {/* Capa 1: Back Cover */}
      <div className="v2-folder-back" aria-hidden="true" />

      {/* Capa 2: Inner Sliding Card (Emerge al hover; Meta/Anterior a la izquierda, Valor/Tendencia a la derecha y barra debajo) */}
      <div className="v2-folder-inner" aria-hidden="true">
        <div className="v2-folder-inner-grid">
          <div className="v2-folder-inner-left">
            <span className="v2-folder-inner-label">{innerPrimary}</span>
            <span className="v2-folder-inner-metric">{innerSecondary}</span>
          </div>
          <div className="v2-folder-inner-right">
            <span className="v2-folder-value cmi-num">
              <AnimatedNumberV2 value={displayValue} triggerOnView={false} active={isHovered} />
            </span>
            {trend && <div className="v2-folder-inner-trend">{trend}</div>}
          </div>
        </div>
        {progress !== null && progress !== undefined && (
          <AnimatedProgressBarV2
            className="cmi-progress v2-folder-progress"
            value={progress * 100}
            max={100}
            color={statusColor || 'var(--color-gira-gold)'}
            triggerOnView={false}
            active={isHovered}
            ariaLabel="Avance hacia la meta"
          />
        )}
      </div>

      {/* Capa 3: Front Pocket Flap con pestaña curva SVG (visible en reposo) */}
      <div className="v2-folder-front">
        <svg
          className="v2-folder-ear-svg"
          viewBox="0 0 150 32"
          width="150"
          height="32"
          aria-hidden="true"
        >
          <path
            d="M20 0C8.954 0 0 8.954 0 20v12h150v-2h-25.95a20 20 0 0 1-13.324-5.085L88.528 5.085A20 20 0 0 0 75.203 0Z"
            fill="currentColor"
          />
        </svg>

        <div className="v2-folder-front-header">
          <span className="v2-folder-code" data-v2-card-title="true">{code}</span>
          <div className="v2-folder-header-right">
            {badge && (
              <span className="cmi-pill v2-folder-semaforo">
                {statusColor && <i className="cmi-dot" style={{ background: statusColor }} />}
                {badge}
              </span>
            )}
            <span className="v2-folder-arrow" aria-hidden="true">
              <ArrowUpRight size={14} />
            </span>
          </div>
        </div>

        <div className="v2-folder-front-body">
          <div className="v2-folder-title">{title}</div>
          {summary && <div className="v2-folder-summary">{summary}</div>}
        </div>
      </div>
    </button>
  );
}
