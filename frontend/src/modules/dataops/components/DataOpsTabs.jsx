import React from 'react';

/**
 * Componente de navegación por pestañas de alta fidelidad para el módulo DataOps.
 * Compatible con modo claro y oscuro, con soporte para badges y animaciones sutiles.
 * 
 * @param {Array<{ id: string, label: string, icon: React.ComponentType, count?: number, badgeColor?: string }>} tabs
 * @param {string} activeTab
 * @param {Function} onChangeTab
 */
export default function DataOpsTabs({ tabs = [], activeTab, onChangeTab }) {
  return (
    <div
      role="tablist"
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '8px',
        padding: '6px',
        borderRadius: '18px',
        backgroundColor: 'var(--color-mist-gray, #f2f2f3)',
        border: '1px solid var(--color-border, #ececec)',
        marginBottom: '24px',
        transition: 'all 0.2s ease',
      }}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        const IconComponent = tab.icon;

        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChangeTab(tab.id)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '9px 18px',
              borderRadius: '14px',
              fontSize: '13px',
              fontWeight: isActive ? 600 : 500,
              fontFamily: 'var(--font-sohne, inherit)',
              cursor: 'pointer',
              border: 'none',
              outline: 'none',
              transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
              backgroundColor: isActive
                ? 'var(--color-paper-white, #ffffff)'
                : 'transparent',
              color: isActive
                ? 'var(--color-ink-black, #17191c)'
                : 'var(--color-slate-gray, #777b86)',
              boxShadow: isActive
                ? '0 2px 8px rgba(0, 0, 0, 0.08)'
                : 'none',
            }}
          >
            {IconComponent && (
              <IconComponent
                size={16}
                style={{
                  color: isActive
                    ? 'var(--color-gira-gold, #D99B26)'
                    : 'inherit',
                  transition: 'color 0.18s ease',
                }}
              />
            )}
            <span>{tab.label}</span>

            {typeof tab.count === 'number' && (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  minWidth: '20px',
                  height: '20px',
                  padding: '0 6px',
                  borderRadius: '9999px',
                  fontSize: '11px',
                  fontWeight: 600,
                  fontFamily: 'var(--font-mono, monospace)',
                  backgroundColor: tab.badgeColor || (isActive ? 'var(--color-ink-black, #17191c)' : 'rgba(0, 0, 0, 0.08)'),
                  color: isActive ? '#ffffff' : 'inherit',
                }}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
