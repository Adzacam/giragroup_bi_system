import React from 'react';

export default function KpiCard({
  numberPrefix,
  number,
  numberSuffix,
  label,
  sublabel,
  badgeText,
  badgeType = 'neutral', // 'success', 'danger', 'warning', 'peach', 'neutral'
  className = '',
  style = {},
}) {
  const getBadgeStyle = () => {
    switch (badgeType) {
      case 'success':
        return { bg: 'rgba(27, 135, 84, 0.16)', color: 'var(--color-alert-green)', border: '1px solid rgba(27, 135, 84, 0.28)' };
      case 'danger':
        return { bg: 'rgba(217, 56, 58, 0.16)', color: 'var(--color-alert-red)', border: '1px solid rgba(217, 56, 58, 0.28)' };
      case 'warning':
        return { bg: 'rgba(180, 83, 9, 0.16)', color: 'var(--color-alert-amber)', border: '1px solid rgba(180, 83, 9, 0.28)' };
      case 'peach':
        return { bg: 'rgba(251, 225, 209, 0.25)', color: 'var(--color-sienna-brown)', border: '1px solid rgba(251, 225, 209, 0.35)' };
      default:
        return { bg: 'var(--color-mist-gray)', color: 'var(--color-ink-black)', border: '1px solid var(--color-border)' };
    }
  };

  const badgeStyle = getBadgeStyle();

  return (
    <div
      className={`card-mist kinetic-card ${className}`}
      style={{
        padding: '24px 28px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        borderRadius: 'var(--radius-cards)',
        ...style,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
        <span
          style={{
            fontSize: '11px',
            textTransform: 'uppercase',
            fontWeight: 600,
            letterSpacing: '0.8px',
            color: 'var(--color-slate-gray)',
          }}
        >
          {label}
        </span>
        {badgeText && (
          <span
            style={{
              fontSize: '11px',
              fontWeight: 600,
              padding: '2px 9px',
              borderRadius: '9999px',
              backgroundColor: badgeStyle.bg,
              color: badgeStyle.color,
              border: badgeStyle.border || 'none',
            }}
          >
            {badgeText}
          </span>
        )}
      </div>

      <div>
        <div
          className="serif-display"
          style={{
            fontSize: 'clamp(28px, 3.2vw, 42px)',
            lineHeight: 1.1,
            color: 'var(--color-ink-black)',
            marginBottom: '8px',
          }}
        >
          {numberPrefix}
          {number}
          {numberSuffix}
        </div>

        {sublabel && (
          <div
            style={{
              fontSize: '13px',
              color: badgeType === 'success'
                ? 'var(--color-alert-green)'
                : badgeType === 'danger'
                ? 'var(--color-alert-red)'
                : 'var(--color-slate-gray)',
              lineHeight: 1.4,
            }}
          >
            {sublabel}
          </div>
        )}
      </div>
    </div>
  );
}
