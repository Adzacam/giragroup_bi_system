import React from 'react';

export default function PageHeader({ category, title, italicWord, subtitle, description, action }) {
  const displaySubtitle = subtitle || description;

  return (
    <div style={{ marginBottom: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          {category && (
            <span
              style={{
                fontFamily: 'var(--font-sohne)',
                fontSize: '11.5px',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '1.2px',
                color: 'var(--color-gira-gold)',
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
              fontFamily: 'var(--font-signifier)',
              fontWeight: 400,
              fontSize: 'clamp(28px, 3vw, 38px)',
              color: 'var(--color-ink-black)',
              margin: 0,
              lineHeight: 1.2,
            }}
          >
            {title} {italicWord && <em>{italicWord}</em>}
          </h1>
          {displaySubtitle && (
            <p
              style={{
                fontFamily: 'var(--font-sohne)',
                fontSize: '14.5px',
                fontWeight: 400,
                color: 'var(--color-slate-gray)',
                marginTop: '8px',
                marginBottom: 0,
                lineHeight: 1.5,
                maxWidth: '720px',
              }}
            >
              {displaySubtitle}
            </p>
          )}
        </div>
        {action && <div>{action}</div>}
      </div>
    </div>
  );
}
