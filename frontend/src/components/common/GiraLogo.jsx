import React from 'react';

export default function GiraLogo({ size = 46, showText = true }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
      <svg 
        width={size} 
        height={size} 
        viewBox="0 0 100 100" 
        fill="none" 
        style={{
          borderRadius: '12px',
          background: '#0c2340',
          padding: '6px',
          boxShadow: '0 4px 12px rgba(12, 35, 64, 0.2)'
        }}
      >
        <path 
          d="M 50 18 L 74 42 C 77 45, 77 51, 74 54 L 54 74 C 51 77, 45 77, 42 74 L 26 58 C 23 55, 23 49, 26 46 L 44 28 C 46 26, 49 26, 51 28 L 56 33 C 57 34, 57 36, 56 37 L 42 51 C 41 52, 41 54, 42 55 L 48 61 C 49 62, 51 62, 52 61 L 63 50 C 64 49, 64 47, 63 46 L 46 29" 
          stroke="#ffffff" 
          strokeWidth="9" 
          strokeLinecap="round" 
          strokeLinejoin="round"
        />
        <text 
          x="50" 
          y="93" 
          textAnchor="middle" 
          fill="#d99b26" 
          fontFamily="'Inter', sans-serif" 
          fontSize="14" 
          fontWeight="700" 
          letterSpacing="1.5"
        >
          Group
        </text>
      </svg>
      {showText && (
        <div>
          <div style={{ fontWeight: 700, letterSpacing: '1.5px', fontSize: '15px', color: 'var(--color-ink-black)' }}>
            GIRAGROUP
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
            BI &amp; Analytics Governance
          </div>
        </div>
      )}
    </div>
  );
}
