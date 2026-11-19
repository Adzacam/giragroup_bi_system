import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ theme: 'light', toggleTheme: vi.fn() }),
}));

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ role: 'ADMIN', user: { nombre: 'Admin', rol: 'ADMIN' } }),
}));

vi.mock('../../context/NotificationContext', () => ({
  useNotifications: () => ({
    notifications: [
      { id: 1, title: 'Alerta Roja', message: 'Mora alta', severity: 'critica', is_read: false, created_at: '2026-11-16T10:00:00Z' },
      { id: 2, title: 'Aviso', message: 'Revisar lote', severity: 'ADVERTENCIA', is_read: true, created_at: '2026-11-16T09:00:00Z' },
      { id: 3, title: 'Info', message: 'Consolidado', severity: 'info', is_read: true, created_at: '2026-11-16T08:00:00Z' },
    ],
    unreadCount: 1,
    loading: false,
    markAsRead: vi.fn(),
    markAllRead: vi.fn(),
  }),
}));

vi.mock('../../hooks/useKineticScroll', () => ({ default: () => {} }));

import CardFolderV2 from '../components/CardFolderV2';
import CmiDetalleKpi from '../../modules/admin/cmi/CmiDetalleKpi';
import CuadroMandoIntegral from '../../modules/admin/CuadroMandoIntegral';
import CmiPowerBi from '../../modules/admin/cmi/CmiPowerBi';
import NotificationsPage from '../../modules/notifications/NotificationsPage';
import { notificationService } from '../../services/notificationService';

describe('Ronda 3 (L1-R3 a L4-R3)', () => {
  beforeEach(() => {
    globalThis.document = {
      documentElement: {
        getAttribute: (attr) => (attr === 'data-ui-version' ? 'v2' : null),
      },
    };
  });

  it('L1-R3: CardFolderV2 muestra KPI-XX pequeño, título destacado, valor, progreso y Meta/Anterior en hoja interior', () => {
    const html = renderToStaticMarkup(
      <CardFolderV2
        code="FIN-01"
        title="Margen Operativo"
        badge="En meta"
        statusColor="#1B8754"
        value="24,5 %"
        trend={<span>+2,1 pp</span>}
        progress={0.85}
        metaText="Meta ≥ 20 %"
        previousText="Anterior 22,4 %"
        summary="Rentabilidad neta"
      />
    );
    expect(html).toContain('v2-folder-code');
    expect(html).toContain('FIN-01');
    expect(html).toContain('Margen Operativo');
    expect(html).toContain('24,5 %');
    expect(html).toContain('role="progressbar"');
    expect(html).toContain('Meta ≥ 20 %');
    expect(html).toContain('Anterior 22,4 %');

    const innerStart = html.indexOf('class="v2-folder-inner"');
    const frontStart = html.indexOf('class="v2-folder-front"');
    expect(innerStart).toBeGreaterThan(-1);
    expect(frontStart).toBeGreaterThan(innerStart);

    const innerHtml = html.slice(innerStart, frontStart);
    const frontHtml = html.slice(frontStart);

    expect(innerHtml).toContain('v2-folder-inner-left');
    expect(innerHtml).toContain('Meta ≥ 20 %');
    expect(innerHtml).toContain('Anterior 22,4 %');
    expect(innerHtml).toContain('v2-folder-inner-right');
    expect(innerHtml).toContain('24,5 %');
    expect(innerHtml).toContain('+2,1 pp');
    expect(innerHtml).toContain('role="progressbar"');

    expect(frontHtml).toContain('FIN-01');
    expect(frontHtml).toContain('En meta');
    expect(frontHtml).toContain('Margen Operativo');
    expect(frontHtml).toContain('Rentabilidad neta');
    expect(frontHtml).not.toContain('role="progressbar"');
    expect(frontHtml).not.toContain('24,5 %');
  });

  it('L2-R3: CmiDetalleKpi incluye cabecera flex, 6 tarjetas resumen, Variación (Δ) y ficha metodológica', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(['cmi', 'historial', 'FIN-01'], {
      codigo: 'FIN-01',
      nombre: 'Margen Operativo',
      unidad: '%',
      sentido: 'MAX',
      perspectiva: 'Financiera',
      descripcion: 'Rentabilidad neta institucional.',
      serie: [
        { gestion: 2024, valor: 18.0, meta: 20, semaforo: 'AMBAR' },
        { gestion: 2025, valor: 22.4, meta: 20, semaforo: 'VERDE' },
        { gestion: 2026, valor: 24.5, meta: 20, semaforo: 'VERDE' },
      ],
    });

    const html = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <CmiDetalleKpi codigo="FIN-01" onClose={() => {}} />
      </QueryClientProvider>
    );
    expect(html).toContain('cmi cmi-modal-fondo');
    expect(html).toContain('cmi-modal-header');
    expect(html).toContain('cmi-modal-cerrar');
    expect(html).toContain('% Cumplimiento');
    expect(html).toContain('Promedio / Rango');
    expect(html).toContain('Variación (Δ)');
    expect(html).toContain('cmi-modal-ficha');
    expect(html).toContain('Ficha metodológica del indicador');
  });

  it('L3-R3: CuadroMandoIntegral sin Macroinstitucional, con Configuración en cabecera y Glosario en vista A', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const html = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <CuadroMandoIntegral />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(html).toContain('Cuadro de Mando Integral');
    expect(html).not.toContain('Macroinstitucional');
    expect(html).toContain('Configuración');
    expect(html).toContain('Ayuda y glosario');
  });

  it('L3-R3: CmiPowerBi habilita botón Eliminar solo para versiones > 1 (v1 protegida)', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(['powerbi', 'informe'], {
      vigente: { version: 2, subido_en: '2026-11-16T10:00:00Z', subido_por: 'admin', tamano_bytes: 204800 },
      conexion: { servidor: '127.0.0.1:5434', base_datos: 'giragroup_db', usuario: 'powerbi_reader' },
      puede_editar: true,
      max_versiones: 3,
    });
    qc.setQueryData(['powerbi', 'versiones'], [
      { version: 2, vigente: false, subido_en: '2026-11-16T10:00:00Z', subido_por: 'admin', tamano_bytes: 204800 },
      { version: 1, vigente: true, subido_en: '2026-11-15T10:00:00Z', subido_por: 'admin', tamano_bytes: 102400 },
    ]);

    const html = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <CmiPowerBi />
      </QueryClientProvider>
    );
    expect(html).toContain('Eliminar v2');
    expect(html).not.toContain('Eliminar v1');
  });

  it('L4-R3: notificationService normaliza severidades y NotificationsPage renderiza pastilla con conteos y cascada', () => {
    expect(notificationService.normalizeSeverity('critica')).toBe('CRITICAL');
    expect(notificationService.normalizeSeverity('HIGH')).toBe('CRITICAL');
    expect(notificationService.normalizeSeverity('advertencia')).toBe('WARNING');
    expect(notificationService.normalizeSeverity('info')).toBe('INFO');

    const html = renderToStaticMarkup(<NotificationsPage />);
    expect(html).toContain('v2-pill-segment');
    expect(html).toContain('Todas');
    expect(html).toContain('Críticas');
    expect(html).toContain('Advertencias');
    expect(html).toContain('Informativas');
    expect(html).toContain('v2-notif-cascade-item');
  });
});
