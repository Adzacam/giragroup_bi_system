import React from 'react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import MasterDataView from '../MasterDataView';
import DataOpsTabs from '../components/DataOpsTabs';

const mockRole = { value: 'ADMIN' };
const mockQueryData = { value: null };

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: mockQueryData.value, error: null, isFetching: false, refetch: vi.fn() }),
}));

vi.mock('../../../context/AuthContext', () => ({
  useAuth: () => ({ role: mockRole.value, user: { username: 'admin', role: mockRole.value } }),
}));

vi.mock('../../../context/NotificationContext', () => ({
  useNotifications: () => ({ refreshNotifications: vi.fn() }),
}));

vi.mock('../../../v2/transitions/useParentChildTransitionV2', () => ({
  useParentChildTransitionV2: () => ({ triggerParentChild: (_el, cb) => cb() }),
}));

vi.mock('../../../services/sileoToast', () => ({
  sileoToast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
  confirmar: vi.fn(async () => true),
}));

vi.mock('../../../api/queryClient', () => ({
  queryClient: { invalidateQueries: vi.fn() },
  DATAOPS_QUERY_KEY: ['dataops'],
}));

function renderStatic() {
  return renderToStaticMarkup(
    <MemoryRouter>
      <MasterDataView />
    </MemoryRouter>,
  );
}

describe('CAT-L5 / CAT-L7 — MasterDataView', () => {
  beforeEach(() => {
    mockRole.value = 'ADMIN';
    mockQueryData.value = {
      status: 'success',
      tipo: 'modulos',
      resumen: { total_sin_uso: 3 },
      data: [
        { id: 1, nombre: 'Módulo Con Uso', codigo: 'POS-5001', programa: 'Diplomado BI', institucion: 'GiraGroup Posgrado', en_uso: 12 },
        { id: 2, nombre: 'Módulo Sin Uso', codigo: 'POS-5002', programa: null, institucion: 'GiraGroup Posgrado', en_uso: 0 },
      ],
      pagination: { page: 1, page_size: 20, total_items: 2, total_pages: 1 },
    };
  });

  it('renderiza paginación de 20, filtros de módulos, columna En uso y botón ADMIN de limpieza', () => {
    const html = renderStatic();
    expect(html).toContain('veinte registros por página');
    expect(html).toContain('Solo genéricos');
    expect(html).toContain('Sin programa');
    expect(html).toContain('Solo en uso');
    expect(html).toContain('Solo sin uso');
    expect(html).toContain('12 hecho(s)');
    expect(html).toContain('Sin uso (0)');
    expect(html).toContain('Limpiar módulos sin uso (3)');
    expect(html).toContain('cat-native-dialog');
  });

  it('oculta acción masiva de limpieza para rol no ADMIN', () => {
    mockRole.value = 'AUDITOR_CALIDAD';
    const html = renderStatic();
    expect(html).not.toContain('Limpiar módulos sin uso (3)');
  });

  it('aplica min-width:0 al input de búsqueda y tokens adaptativos en MasterDataView.css', () => {
    const html = renderStatic();
    expect(html).toContain('min-width:0');

    const css = readFileSync(resolve(__dirname, '../MasterDataView.css'), 'utf8');
    expect(css).not.toMatch(/--color-surface\b/);
    expect(css).not.toMatch(/--color-ink(?!-black)\b/);
    expect(css).toContain('flex-wrap: wrap');
    expect(css).toContain('--dataops-success-bg');
    expect(css).toContain('--dataops-info-bg');
    expect(css).toContain('--dataops-gold-bg');
  });

  it('usa tokens adaptativos para los badges count en DataOpsTabs (activo e inactivo)', () => {
    const html = renderToStaticMarkup(
      <DataOpsTabs
        activeTab="a"
        onChangeTab={() => {}}
        tabs={[
          { id: 'a', label: 'Activa', count: 5 },
          { id: 'b', label: 'Inactiva', count: 12 },
        ]}
      />,
    );
    expect(html).toContain('var(--color-paper-white, #ffffff)');
    expect(html).toContain('var(--color-ink-black, #17191c)');
    expect(html).not.toContain('background-color:rgba(0, 0, 0, 0.08)');
    expect(html).toContain('border:1px solid var(--color-border, #ececec)');
  });

  it('alinea data-label="Años con techo / Escala" en la tabla de instituciones', () => {
    const jsx = readFileSync(resolve(__dirname, '../MasterDataView.jsx'), 'utf8');
    expect(jsx).toContain('<th>Años con techo / Escala</th>');
    expect(jsx).toContain('data-label="Años con techo / Escala"');
    expect(jsx).not.toContain('data-label="Detalle"');
  });
});
