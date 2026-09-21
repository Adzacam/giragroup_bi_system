import React from 'react';

export default function PageHeader({ category, title, italicWord, subtitle, action }) {
  return (
    <div style={{ marginBottom: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          {category && (
            <span
              style={{
                fontSize: '11.5px',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '1.2px',
                color: 'var(--color-slate-gray)',
                display: 'block',
                marginBottom: '6px',
              }}
            >
              {category}
            </span>
          )}
          <h1
            className="serif-display"
            style={{
              fontSize: 'clamp(28px, 3vw, 38px)',
              color: 'var(--color-ink-black)',
              margin: 0,
              lineHeight: 1.2,
            }}
          >
            {title} {italicWord && <em>{italicWord}</em>}
          </h1>
          {subtitle && (
            <p
              style={{
                fontSize: '14.5px',
                color: 'var(--color-slate-gray)',
                marginTop: '8px',
                marginBottom: 0,
                lineHeight: 1.5,
                maxWidth: '720px',
              }}
            >
              {subtitle}
            </p>
          )}
        </div>
        {action && <div>{action}</div>}
      </div>
    </div>
  );
}
