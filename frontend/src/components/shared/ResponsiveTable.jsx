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
        backgroundColor: 'var(--color-paper-white)',
        ...style,
      }}
    >
      <div style={{ overflowX: 'auto', width: '100%', WebkitOverflowScrolling: 'touch' }}>
        {children}
      </div>
    </div>
  );
}
