import React from 'react';

export default function GiraLogo({ size = 46, showText = true, variant = 'auto' }) {
  const isGold = variant === 'gold';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
      <svg 
        width={size} 
        height={size} 
        viewBox="0 0 100 100" 
        fill="none" 
        style={{
          borderRadius: '12px',
          background: '#0C1E33',
          padding: '6px',
          boxShadow: isGold 
            ? '0 4px 16px rgba(217, 155, 38, 0.35)' 
            : '0 4px 12px rgba(12, 30, 51, 0.25)',
          border: isGold ? '1px solid #D99B26' : '1px solid rgba(255,255,255,0.08)'
        }}
      >
        <path 
          d="M 50 18 L 74 42 C 77 45, 77 51, 74 54 L 54 74 C 51 77, 45 77, 42 74 L 26 58 C 23 55, 23 49, 26 46 L 44 28 C 46 26, 49 26, 51 28 L 56 33 C 57 34, 57 36, 56 37 L 42 51 C 41 52, 41 54, 42 55 L 48 61 C 49 62, 51 62, 52 61 L 63 50 C 64 49, 64 47, 63 46 L 46 29" 
          stroke={isGold ? "#D99B26" : "#ffffff"} 
          strokeWidth="9" 
          strokeLinecap="round" 
          strokeLinejoin="round"
        />
        <text 
          x="50" 
          y="93" 
          textAnchor="middle" 
          fill={isGold ? "#F1B844" : "#D99B26"} 
          fontFamily="'Plus Jakarta Sans', sans-serif" 
          fontSize="14" 
          fontWeight="700" 
          letterSpacing="1.2"
        >
          Group
        </text>
      </svg>
      {showText && (
        <div>
          <div style={{ fontWeight: 700, letterSpacing: '0.5px', fontSize: '16px', color: 'var(--color-ink-black)', lineHeight: 1.2 }}>
            GIRA <span style={{ color: 'var(--color-gira-gold)', fontWeight: 700 }}>Group</span>
          </div>
          <div style={{ fontSize: '10px', color: 'var(--color-slate-gray)', letterSpacing: '1px', textTransform: 'uppercase', fontWeight: 600 }}>
            BI &amp; DATAOPS SUITE
          </div>
        </div>
      )}
    </div>
  );
}
