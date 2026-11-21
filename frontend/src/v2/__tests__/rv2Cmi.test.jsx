import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import MapaHorizontalV2 from '../../modules/admin/cmi/scorecard/MapaHorizontalV2';
import VistaGeneralCmi from '../../modules/admin/cmi/scorecard/VistaGeneralCmi';
import DesglosePerspectiva from '../../modules/admin/cmi/scorecard/DesglosePerspectiva';
import PrediccionPage from '../../modules/admin/cmi/prediccion/PrediccionPage';
import DetallePrediccion from '../../modules/admin/cmi/prediccion/DetallePrediccion';
import GraficoPersonalizadoBody from '../../modules/admin/cmi/scorecard/GraficoPersonalizadoBody';
import ConfigGraficosTab from '../../modules/admin/cmi/config/ConfigGraficosTab';
import { sileoToast } from '../../services/sileoToast';

vi.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ theme: 'light', toggleTheme: vi.fn() }),
}));

const MOCK_SCORECARD = {
  gestion: 2026,
  gestiones: [2024, 2025, 2026],
  global: { indice: 78, verdes: 10, ambar: 4, rojos: 2, sin_evaluar: 7, indicadores: 23 },
  perspectivas: [
    { codigo: 'FINANCIERA', nombre: 'Financiera', objetivo: 'Sostenibilidad', peso: 30, orden: 1, indicadores: 6, verdes: 4, ambar: 1, rojos: 1, sin_evaluar: 0, indice: 83, kpis: [
      { codigo: 'KPI-01', nombre: 'Margen Neto', descripcion: 'Rentabilidad', unidad: 'PCT', sentido: 'MAX', valor: 22, valor_anterior: 18, delta: 4, meta: 20, semaforo: 'VERDE', tendencia: 'MEJORA' },
      { codigo: 'KPI-02', nombre: 'Morosidad', descripcion: 'Cartera vencida', unidad: 'PCT', sentido: 'MIN', valor: 14, valor_anterior: 10, delta: 4, meta: 8, semaforo: 'ROJO', tendencia: 'EMPEORA' },
    ] },
    { codigo: 'CLIENTES', nombre: 'Estudiantes y mercado', objetivo: 'Captación', peso: 25, orden: 2, indicadores: 6, verdes: 3, ambar: 2, rojos: 1, sin_evaluar: 0, indice: 75, kpis: [] },
    { codigo: 'PROCESOS_INTERNOS', nombre: 'Procesos internos', objetivo: 'Calidad', peso: 25, orden: 3, indicadores: 6, verdes: 2, ambar: 1, rojos: 0, sin_evaluar: 3, indice: 86, kpis: [] },
    { codigo: 'APRENDIZAJE', nombre: 'Aprendizaje y crecimiento', objetivo: 'Talento', peso: 20, orden: 4, indicadores: 5, verdes: 1, ambar: 0, rojos: 0, sin_evaluar: 4, indice: 100, kpis: [] },
  ],
};

describe('RV2 — Reestructuración Vista V2 (L3, L4, L5, L6)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('L3: MapaHorizontalV2 ordena Aprendizaje → Procesos → Clientes → Financiera con conectores', () => {
    const html = renderToStaticMarkup(
      <MapaHorizontalV2 perspectivas={MOCK_SCORECARD.perspectivas} activa={null} onSelect={() => {}} />
    );
    const posApr = html.indexOf('Abrir detalle: Aprendizaje y crecimiento');
    const posProc = html.indexOf('Abrir detalle: Procesos internos');
    const posCli = html.indexOf('Abrir detalle: Estudiantes y mercado');
    const posFin = html.indexOf('Abrir detalle: Financiera');
    expect(posApr).toBeGreaterThan(-1);
    expect(posApr).toBeLessThan(posProc);
    expect(posProc).toBeLessThan(posCli);
    expect(posCli).toBeLessThan(posFin);
    expect(html).toContain('cmi-map-connector');
  });

  it('L3: VistaGeneralCmi renderiza matriz de semáforo, alertas prioritarias y cobertura', () => {
    const html = renderToStaticMarkup(
      <VistaGeneralCmi
        scorecard={MOCK_SCORECARD}
        resumen={{ gestiones: [2025, 2026], global_por_gestion: [{ gestion: 2025, indice: 70 }, { gestion: 2026, indice: 78 }], perspectivas_por_gestion: [] }}
        searchQuery=""
        onOpenKpi={() => {}}
        onSelectPerspectiva={() => {}}
      />
    );
    expect(html).toContain('Matriz de semáforo');
    expect(html).toContain('Alertas prioritarias (1)');
    expect(html).toContain('KPI-02');
    expect(html).toContain('Cobertura del CMI');
  });

  it('L4: DesglosePerspectiva muestra botón Volver, filtros y tarjetas V1 arriba', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const html = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <DesglosePerspectiva
          perspectiva={MOCK_SCORECARD.perspectivas[0]}
          gestion={2026}
          onVolver={() => {}}
          onAbrirKpi={() => {}}
        />
      </QueryClientProvider>
    );
    expect(html).toContain('Volver a vista general');
    expect(html).toContain('KPI-01');
    expect(html).toContain('Margen Neto');
    expect(html).toContain('En alerta');
    expect(html).toContain('Avance a meta de sus KPI');
  });

  it('L5: PrediccionPage muestra franja ejecutiva, sub-pestañas y DetallePrediccion drawer', () => {
    const macroMock = {
      status: 'success',
      caso1_demanda_global: {
        n_observaciones: 40,
        periodos_historicos: ['2023-01', '2026-04'],
        valores_historicos: [100, 120],
        periodos_proyectados: ['2026-05'],
        forecast_hw: [130],
        ic_lower_95: [110],
        ic_upper_95: [150],
        mape_pct: 8.5,
        rmse: 12.1,
        pendiente_ols_mes: 1.5,
        cagr_historico_pct: 6.2,
      },
      caso3_metas_mensuales: { mes_actual: { periodo: '2026-04', cumplimiento_proyectado_pct: 94.2, meta_mes_bs: 100000, cierre_proyectado_hw_bs: 94200 }, meses_etiquetas: [], meta_catalogo_bs: [], ejecutado_real_bs: [] },
      caso4_metas_anuales: { gestion_actual: 2026, porcentaje_avance_meta: 41.5, meta_anual_institucional_bs: 1200000, recaudado_acumulado_bs: 498000, anios_historicos: [2024, 2025], valores_historicos_bs: [900000, 1050000], proyecciones_ols: [] },
    };
    const html = renderToStaticMarkup(
      <PrediccionPage
        macroData={macroMock}
        isLoading={false}
        horizonte={6}
        onHorizonteChange={() => {}}
        onRecalcular={() => {}}
        searchProg=""
        onSearchProgChange={() => {}}
      />
    );
    expect(html).toContain('Inscritos proyectados (6 m)');
    expect(html).toContain('Calidad del modelo');
    expect(html).toContain('Cumplimiento proyectado del mes');
    expect(html).toContain('Avance de la meta anual');
    expect(html).toContain('Demanda');
    expect(html).toContain('Programas');
    expect(html).toContain('Metas mensuales');
    expect(html).toContain('Tendencia anual');

    const drawerHtml = renderToStaticMarkup(
      <DetallePrediccion
        modalDetail={{ titulo: 'Caso 4', tipo: 'caso4', data: macroMock.caso4_metas_anuales }}
        onClose={() => {}}
      />
    );
    expect(drawerHtml).toContain('cmi-drawer');
    expect(drawerHtml).toContain('OLS anual — solo descriptiva');
  });

  it('L6: sileoToast.promise existe para el flujo de actualización del CMI', () => {
    expect(typeof sileoToast.promise).toBe('function');
  });

  it('L7: GraficoPersonalizadoBody renderiza tabla accesible y filtra grupos ocultos', () => {
    const html = renderToStaticMarkup(
      <GraficoPersonalizadoBody
        tipo="table"
        titulo="Inscripciones por modalidad"
        filas={[
          { etiqueta: 'Presencial', valor: 120, n_registros: 120, oculto: false },
          { etiqueta: 'Oculto', valor: null, n_registros: '< 5', oculto: true },
        ]}
        tokens={{ navy: '#0C1E33', gold: '#D99B26', ok: '#1b8754', bad: '#b91c1c' }}
        chartOpts={{}}
      />
    );
    expect(html).toContain('role="region"');
    expect(html).toContain('Presencial');
    expect(html).not.toContain('Oculto');
  });

  it('L7: ConfigGraficosTab incluye opción de gráfica tipo Área', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const html = renderToStaticMarkup(
      <QueryClientProvider client={qc}>
        <ConfigGraficosTab
          perspectivas={MOCK_SCORECARD.perspectivas}
          medidas={[{ codigo: 'MED_TEST', nombre: 'Medida', perspectiva: 'FINANCIERA', agregaciones_permitidas: ['SUM'], dimensiones_permitidas: [{ codigo: 'mes', label: 'Mes' }] }]}
          graficos={[]}
        />
      </QueryClientProvider>
    );
    expect(html).toContain('value="area"');
    expect(html).toContain('Área');
  });
});
