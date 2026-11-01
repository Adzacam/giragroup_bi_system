import React, { useState } from 'react';
import { ChevronDown, ChevronUp, UserCheck, Shield } from 'lucide-react';
import { DEMO_ACCOUNTS } from '../../../constants/systemConstants';

export default function DemoAccountsSelector({ currentEmail, onSelectAccount, defaultOpen = false }) {
  if (!import.meta.env.DEV) {
    return null;
  }

  const [isOpen, setIsOpen] = useState(defaultOpen);

  const activeAccount = DEMO_ACCOUNTS.find((a) => a.email === currentEmail);

  return (
    <div
      style={{
        marginTop: '16px',
        width: '100%',
        borderRadius: '14px',
        border: '1px solid var(--color-border)',
        backgroundColor: 'var(--color-paper-white)',
        overflow: 'hidden',
        transition: 'all 0.25s ease',
      }}
    >
      {/* Botón Acordeón Discreto [▾] Rol de Acceso (Validado) */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        style={{
          width: '100%',
          padding: '10px 14px',
          background: 'none',
          border: 'none',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          color: 'var(--color-ink-black)',
          fontSize: '12px',
          fontWeight: 600,
          textAlign: 'left',
          transition: 'background-color 0.2s',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-fog-white)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
        aria-expanded={isOpen}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Shield size={14} color="var(--color-sienna-brown, #D99B26)" />
          <span style={{ letterSpacing: '0.3px' }}>
            Rol de Acceso (Validado)
          </span>
          {activeAccount && (
            <span
              style={{
                fontSize: '10px',
                fontWeight: 700,
                color: 'var(--color-sienna-brown, #D99B26)',
                backgroundColor: 'rgba(217, 155, 38, 0.12)',
                padding: '2px 8px',
                borderRadius: '9999px',
                border: '1px solid rgba(217, 155, 38, 0.3)',
              }}
            >
              {activeAccount.label.split(' ')[0]}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--color-slate-gray)' }}>
          <span style={{ fontSize: '11px', fontWeight: 500 }}>
            {isOpen ? 'Ocultar' : 'Desplegar'}
          </span>
          {isOpen ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </div>
      </button>

      {/* Contenido Desplegable con las 4 Cuentas Demo */}
      {isOpen && (
        <div
          style={{
            padding: '12px 14px 14px 14px',
            borderTop: '1px solid var(--color-border)',
            backgroundColor: 'var(--color-fog-white)',
          }}
        >
          <div
            style={{
              fontSize: '11px',
              color: 'var(--color-slate-gray)',
              marginBottom: '10px',
              lineHeight: 1.4,
            }}
          >
            Seleccione un rol institucional para auto-completar credenciales demo y validar la gobernanza RBAC:
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '8px',
            }}
          >
            {DEMO_ACCOUNTS.map((account) => {
              const isSelected = currentEmail === account.email;
              return (
                <button
                  key={account.email}
                  type="button"
                  onClick={() => onSelectAccount(account.email, 'giragroup2026')}
                  style={{
                    padding: '9px 11px',
                    borderRadius: '10px',
                    border: isSelected
                      ? '1.5px solid var(--color-gira-gold, #D99B26)'
                      : '1px solid var(--color-border)',
                    backgroundColor: isSelected
                      ? 'var(--color-mist-gray)'
                      : 'var(--color-paper-white)',
                    textAlign: 'left',
                    cursor: 'pointer',
                    transition: 'all 0.18s ease',
                    position: 'relative',
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.backgroundColor = 'var(--color-mist-gray)';
                      e.currentTarget.style.borderColor = 'var(--color-sienna-brown, #D99B26)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.backgroundColor = 'var(--color-paper-white)';
                      e.currentTarget.style.borderColor = 'var(--color-border)';
                    }
                  }}
                  title={`Cargar credenciales de ${account.label}`}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '3px',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '11.5px',
                        fontWeight: 600,
                        color: 'var(--color-ink-black)',
                        lineHeight: 1.25,
                      }}
                    >
                      {account.label}
                    </span>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        color: isSelected
                          ? 'var(--color-gira-gold, #D99B26)'
                          : 'var(--color-ash-gray)',
                      }}
                    >
                      {isSelected ? '●' : '○'}
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: '10.5px',
                      color: 'var(--color-slate-gray)',
                      fontFamily: 'var(--font-mono)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {account.email}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
