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
        return { bg: '#dcfce7', color: 'var(--color-alert-green)' };
      case 'danger':
        return { bg: '#fee2e2', color: 'var(--color-alert-red)' };
      case 'warning':
        return { bg: '#fef3c7', color: 'var(--color-alert-amber)' };
      case 'peach':
        return { bg: 'var(--color-blush-peach)', color: 'var(--color-sienna-brown)' };
      default:
        return { bg: 'var(--color-mist-gray)', color: 'var(--color-ink-black)' };
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
