import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

let mockTheme = 'light';
vi.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ theme: mockTheme, toggleTheme: vi.fn() }),
}));

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ role: 'ADMIN', user: { nombre: 'Admin Test', email: 'admin@gira.bo', rol: 'ADMIN' }, logout: vi.fn() }),
}));

vi.mock('../../context/NotificationContext', () => ({
  useNotifications: () => ({
    notifications: [],
    unreadCount: 0,
    refreshNotifications: vi.fn(),
    markAsRead: vi.fn(),
    markAllAsRead: vi.fn(),
  }),
}));

vi.mock('../context/UiVersionContext', () => ({
  V2_FONT_PRESETS: [
    { id: 'augen', label: 'Augen Pro' },
    { id: 'jakarta', label: 'Jakarta' },
    { id: 'inter-tight', label: 'Inter Tight' },
    { id: 'gira-original', label: 'GIRA Original' },
  ],
  useUiVersion: () => ({ fontPreset: 'augen', setFontPreset: vi.fn(), uiVersion: 'v2' }),
}));

vi.mock('../../components/notifications/NotificationBell', () => ({
  default: () => <div data-testid="notification-bell" />,
}));

vi.mock('../../components/layout/UserProfileDropdown', () => ({
  default: () => <div data-testid="user-profile-dropdown" />,
}));

vi.mock('../../components/shared/TareasSegundoPlano', () => ({
  default: () => <div data-testid="tareas-segundo-plano" />,
}));

import GiraAnimatedLogoButton from '../components/GiraAnimatedLogoButton';
import NavbarV2 from '../layout/NavbarV2';
import MainLayoutV2 from '../layout/MainLayoutV2';
import CmiScorecard from '../../modules/admin/cmi/CmiScorecard';

describe('Renderizado real de componentes V2 (L1-R2, L2-R2, L3-R2)', () => {
  beforeEach(() => {
    mockTheme = 'light';
    globalThis.document = {
      documentElement: {
        getAttribute: (attr) => (attr === 'data-ui-version' ? 'v2' : null),
      },
    };
  });

  it('GiraAnimatedLogoButton renderiza SVG 180x180 con "G" centrada en Claro y Oscuro', () => {
    mockTheme = 'light';
    const lightHtml = renderToStaticMarkup(<GiraAnimatedLogoButton isOpen={false} />);
    expect(lightHtml).toContain('viewBox="0 0 180 180"');
    expect(lightHtml).toContain('M 83 29 L 123 69 Q 133 79 123 89 L 91 121 Q 81 131 71 121 L 40 90 Q 30 80 40 70 L 53 57 Q 63 47 73 57 L 96 81');
    expect(lightHtml).toContain('is-light');
    expect(lightHtml).toContain('is-closed');

    mockTheme = 'dark';
    const darkHtml = renderToStaticMarkup(<GiraAnimatedLogoButton isOpen={true} />);
    expect(darkHtml).toContain('is-dark');
    expect(darkHtml).toContain('is-open');
  });

  it('NavbarV2 renderiza una única pastilla larga con marca GIRA Group y sin links de módulos ni botón Aa', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/v2/dashboard']}>
        <NavbarV2 isSidebarOpen={false} onToggleSidebar={() => {}} navigateV2={() => {}} />
      </MemoryRouter>
    );
    expect(html).toContain('v2-topbar-pill');
    expect(html).toContain('GIRA');
    expect(html).toContain('Group');
    expect(html).toContain('BI &amp; Intelligence System');
    expect(html).not.toContain('FontSwitcherPopoverV2');
    expect(html).not.toContain('>Aa<');
    expect(html).not.toContain('>DataOps<');
    expect(html).not.toContain('>Académico<');
  });

  it('MainLayoutV2 renderiza NavbarV2, SidebarV2 y MobileBottomNavV2 (visible <= 960px)', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/v2/dashboard']}>
        <MainLayoutV2 />
      </MemoryRouter>
    );
    expect(html).toContain('v2-shell-root');
    expect(html).toContain('v2-topbar-pill');
    expect(html).toContain('v2-sidebar');
    expect(html).toContain('v2-mobile-bottom-wrap');
  });

  it('CmiScorecard renderiza en V2 sin crash de Rules of Hooks y conecta CardFolderV2', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    // 1. Estado loading inicial
    const loadingHtml = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <CmiScorecard />
      </QueryClientProvider>
    );
    expect(loadingHtml).toContain('aria-busy="true"');

    // 2. Estado con datos precargados en cache (simula transición sin error de hooks)
    qc.setQueryData(['cmi', 'scorecard', null], {
      gestion: 2026,
      gestiones: [2023, 2024, 2025, 2026],
      global: { indice: 84, verdes: 8, ambar: 3, rojos: 1, sin_evaluar: 0 },
      perspectivas: [
        {
          codigo: 'FIN',
          nombre: 'Perspectiva Financiera',
          objetivo: 'Sostenibilidad',
          peso: 30,
          indice: 88,
          verdes: 3,
          ambar: 1,
          rojos: 0,
          indicadores: 4,
          kpis: [
            {
              codigo: 'FIN-01',
              nombre: 'Margen Operativo',
              descripcion: 'Rentabilidad neta',
              valor: 24.5,
              meta: 20,
              sentido: 'MAX',
              unidad: '%',
              semaforo: 'VERDE',
              delta: 2.1,
              tendencia: 'MEJORA',
              valor_anterior: 22.4,
            },
          ],
        },
      ],
    });

    const loadedHtml = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <CmiScorecard />
      </QueryClientProvider>
    );
    expect(loadedHtml).toContain('v2-card-folder');
    expect(loadedHtml).toContain('FIN-01');
    expect(loadedHtml).toContain('Margen Operativo');
    expect(loadedHtml).toContain('v2-parent-child-subpanel');
    expect(loadedHtml).toContain('2026');
  });
});
