import React from 'react';

export default function ResponsiveTable({ children, className = '', style = {} }) {
  return (
    <div
      className={`floating-artifact ${className}`}
      style={{
        borderRadius: 'var(--radius-cards)',
        overflow: 'hidden',
        border: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-subtle)',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        ...style,
      }}
    >
      <div style={{ overflowX: 'auto', width: '100%', WebkitOverflowScrolling: 'touch' }}>
        {children}
      </div>
    </div>
  );
}
