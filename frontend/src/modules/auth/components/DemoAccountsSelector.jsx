import React from 'react';
import { DEMO_ACCOUNTS } from '../../../constants/systemConstants';

export default function DemoAccountsSelector({ currentEmail, onSelectAccount }) {
  return (
    <div style={{ marginTop: '32px', paddingTop: '20px', borderTop: '1px solid var(--color-border)' }}>
      <div style={{
        fontSize: '11px',
        textTransform: 'uppercase',
        letterSpacing: '0.8px',
        color: 'var(--color-slate-gray)',
        fontWeight: 600,
        marginBottom: '10px'
      }}>
        Acceso Rápido de Demostración
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
        {DEMO_ACCOUNTS.map((account) => (
          <button
            key={account.email}
            type="button"
            onClick={() => onSelectAccount(account.email, 'giragroup2026')}
            style={{
              padding: '8px 10px',
              borderRadius: '10px',
              border: currentEmail === account.email ? '1px solid var(--color-ink-black)' : '1px solid var(--color-border)',
              background: currentEmail === account.email ? 'var(--color-mist-gray)' : 'var(--color-paper-white)',
              textAlign: 'left',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            <div style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
              {account.label}
            </div>
            <div style={{
              fontSize: '10px',
              color: 'var(--color-slate-gray)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}>
              {account.email}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
