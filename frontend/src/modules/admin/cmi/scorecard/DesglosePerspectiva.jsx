import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Search } from 'lucide-react';
import { Bar, Doughnut } from 'react-chartjs-2';
import cmiApi from '../../../../api/cmiApi';
import { useTheme } from '../../../../context/ThemeContext';
import { SEMAFORO, bandaIndice } from '../cmiFormat';
import { getChartTokens, buildChartOptions } from '../chartTheme';
import { CHART_PLUGINS_V2 } from '../../../../v2/motion/chartAnimationsV2';
import ChartRevealV2 from '../../../../v2/motion/ChartRevealV2';
import AnimatedNumberV2 from '../../../../v2/motion/AnimatedNumberV2';
import TarjetaKpi, { avance } from './TarjetaKpi';
import GraficoPersonalizadoBody from './GraficoPersonalizadoBody';
import KpisPersonalizadosSection from './KpisPersonalizadosSection';

const CHIPS = [
  ['TODOS', 'Todos'],
  ['VERDE', 'En meta'],
  ['AMBAR', 'En alerta'],
  ['ROJO', 'Crítico'],
  ['SIN_DATO', 'Sin dato'],
];

export default function DesglosePerspectiva({ perspectiva, gestion, onVolver, onAbrirKpi, customChartsSlot = null }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const tokens = useMemo(() => getChartTokens(isDark), [isDark]);

  const [busqueda, setBusqueda] = useState('');
  const [chip, setChip] = useState('TODOS');
  const [orden, setOrden] = useState('codigo');

  const { data: detalle, isLoading: loadingDet } = useQuery({
    queryKey: ['cmi', 'persp-detalle', perspectiva.codigo, gestion],
    queryFn: () => cmiApi.getDetallePerspectiva(perspectiva.codigo, gestion),
    staleTime: 60_000,
  });

  const kpisFiltrados = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    return perspectiva.kpis
      .filter((k) => {
        if (q && !k.codigo.toLowerCase().includes(q) && !k.nombre.toLowerCase().includes(q)) return false;
        if (chip === 'SIN_DATO') return k.valor === null;
        if (chip !== 'TODOS') return k.valor !== null && k.semaforo === chip;
        return true;
      })
      .sort((a, b) => {
        if (orden === 'nombre') return a.nombre.localeCompare(b.nombre, 'es');
        if (orden === 'brecha') return (avance(a) ?? 2) - (avance(b) ?? 2);
        return a.codigo.localeCompare(b.codigo, 'es');
      });
  }, [perspectiva.kpis, busqueda, chip, orden]);

  const chartAvance = useMemo(() => {
    const conAvance = perspectiva.kpis.filter((k) => avance(k) !== null);
    if (!conAvance.length) return null;
    return {
      labels: conAvance.map((k) => k.codigo),
      datasets: [{
        label: '% Avance a meta',
        data: conAvance.map((k) => Math.round(avance(k) * 100)),
        backgroundColor: conAvance.map((k) => (k.semaforo === 'VERDE' ? tokens.ok : k.semaforo === 'AMBAR' ? tokens.gold : tokens.bad)),
        borderRadius: 6,
      }],
    };
  }, [perspectiva.kpis, tokens]);

  const series = detalle?.series || {};
  const chartOpts = useMemo(() => buildChartOptions(isDark), [isDark]);
  const pctOpts = useMemo(() => buildChartOptions(isDark, {
    scales: {
      x: { grid: { color: tokens.grid }, ticks: { color: tokens.muted, font: { size: 10 } } },
      y: { min: 0, max: 110, grid: { color: tokens.grid }, ticks: { color: tokens.muted, font: { size: 10 } } },
    },
  }), [isDark, tokens]);

  const banda = bandaIndice(perspectiva.indice);
  const graficasPerspectiva = useMemo(() => {
    const out = [];
    if (perspectiva.codigo === 'FINANCIERA') {
      const mm = series.metas_mensual || [];
      out.push({
        titulo: 'Meta vs. ejecutado mensual (Bs)',
        data: mm.length ? {
          labels: mm.map((r) => r.nombre_mes || `M${r.mes}`),
          datasets: [
            { label: 'Meta', data: mm.map((r) => r.meta ?? 0), backgroundColor: tokens.metaBarBg, borderRadius: 6 },
            { label: 'Ejecutado', data: mm.map((r) => r.ejecutado ?? 0), backgroundColor: tokens.gold, borderRadius: 6 },
          ],
        } : null,
        tipo: 'bar',
        empty: 'No hay metas mensuales registradas para esta gestión.',
      });
      const ce = series.cartera_estado || [];
      out.push({
        titulo: 'Cartera por estado (Bs deuda)',
        data: ce.length ? {
          labels: ce.map((r) => r.estado_cartera),
          datasets: [{ data: ce.map((r) => r.deuda_bs ?? 0), backgroundColor: [tokens.navy, tokens.gold, tokens.bad, tokens.ok] }],
        } : null,
        tipo: 'doughnut',
        empty: 'No hay registros de cartera para esta gestión.',
      });
    } else if (perspectiva.codigo === 'CLIENTES') {
      const ip = series.inscritos_programa || [];
      out.push({
        titulo: 'Inscritos por programa',
        data: ip.length ? {
          labels: ip.map((r) => r.programa.slice(0, 26)),
          datasets: [{ label: 'Inscritos', data: ip.map((r) => r.inscritos), backgroundColor: tokens.navy, borderRadius: 6 }],
        } : null,
        tipo: 'bar',
        empty: 'No hay inscripciones por programa en esta gestión.',
      });
      const cf = series.conversion_fuente || [];
      out.push({
        titulo: 'Captación por fuente',
        data: cf.length ? {
          labels: cf.map((r) => r.fuente),
          datasets: [
            { label: 'Interesados', data: cf.map((r) => r.interesados ?? 0), backgroundColor: tokens.metaBarBg, borderRadius: 6 },
            { label: 'Inscritos', data: cf.map((r) => r.inscritos ?? 0), backgroundColor: tokens.ok, borderRadius: 6 },
          ],
        } : null,
        tipo: 'bar',
        empty: 'No hay cifras de captación comprobables por fuente en esta gestión.',
      });
    } else if (perspectiva.codigo === 'PROCESOS_INTERNOS') {
      const dd = series.dataops_documento || [];
      out.push({
        titulo: 'Documentos DataOps por fuente',
        data: dd.length ? {
          labels: dd.map((r) => r.tipo_fuente),
          datasets: [
            { label: 'Consolidado directo', data: dd.map((r) => r.consolidado_directo ?? 0), backgroundColor: tokens.ok, borderRadius: 6 },
            { label: 'Revisión HITL', data: dd.map((r) => r.revision_hitl ?? 0), backgroundColor: tokens.gold, borderRadius: 6 },
          ],
        } : null,
        tipo: 'bar',
        empty: 'No hay documentos procesados en DataOps.',
      });
    } else if (perspectiva.codigo === 'APRENDIZAJE') {
      const re = series.riesgo_estudiante || [];
      out.push({
        titulo: 'Estudiantes en riesgo por nivel',
        data: re.length ? {
          labels: re.map((r) => r.nivel_prioridad),
          datasets: [{ label: 'Estudiantes', data: re.map((r) => r.estudiantes), backgroundColor: [tokens.bad, tokens.gold, tokens.ok], borderRadius: 6 }],
        } : null,
        tipo: 'bar',
        empty: 'No hay registros de riesgo estudiantil para esta gestión.',
      });
    }
    return out;
  }, [perspectiva.codigo, series, tokens]);

  return (
    <section className="cmi-drill-wrap" id={`cmi-${perspectiva.codigo}`} aria-labelledby="cmi-drill-title">
      <div className="cmi-drill-top">
        <button type="button" className="cmi-btn" onClick={onVolver}>
          <ArrowLeft size={14} aria-hidden="true" />
          <span>Volver a vista general</span>
        </button>
        <div className="cmi-section-meta">
          <i className="cmi-dot" style={{ background: SEMAFORO[banda].color }} />
          <span>Índice</span>
          <span className="cmi-num">{perspectiva.indice !== null ? <AnimatedNumberV2 value={perspectiva.indice} /> : '—'}</span>
        </div>
      </div>

      <header className="cmi-drill-head">
        <div className="cmi-eyebrow">Perspectiva · peso {perspectiva.peso} %</div>
        <h2 id="cmi-drill-title">{perspectiva.nombre}</h2>
        <p><strong>Objetivo:</strong> {perspectiva.objetivo}</p>
      </header>

      <div className="cmi-filter-bar" role="region" aria-label="Filtros de indicadores">
        <div className="cmi-search-wrap">
          <Search size={14} className="cmi-search-icon" aria-hidden="true" />
          <input
            type="search"
            className="cmi-input cmi-search-input"
            placeholder="Buscar indicador por código o nombre..."
            aria-label="Buscar indicador por código o nombre"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </div>
        <div className="cmi-chip-group" role="group" aria-label="Filtrar por semáforo">
          {CHIPS.map(([val, lbl]) => (
            <button
              key={val}
              type="button"
              className={`cmi-filter-chip ${chip === val ? 'is-active' : ''}`}
              aria-pressed={chip === val}
              onClick={() => setChip(val)}
            >
              {lbl}
            </button>
          ))}
        </div>
        <select
          className="cmi-input cmi-select-compact"
          aria-label="Ordenar indicadores"
          value={orden}
          onChange={(e) => setOrden(e.target.value)}
        >
          <option value="codigo">Orden: Código</option>
          <option value="brecha">Orden: Mayor brecha</option>
          <option value="nombre">Orden: Nombre</option>
        </select>
      </div>

      {kpisFiltrados.length === 0 ? (
        <div className="cmi-card cmi-empty">Ningún indicador coincide con los filtros seleccionados.</div>
      ) : (
        <div className="cmi-kpis">
          {kpisFiltrados.map((k) => (
            <TarjetaKpi key={k.codigo} kpi={k} onAbrir={onAbrirKpi} forceClassicCard />
          ))}
        </div>
      )}

      <div className="cmi-drill-charts">
        {graficasPerspectiva.map((g, i) => (
          <article key={i} className="cmi-card cmi-ov-card">
            <span className="cmi-eyebrow">Analítica de perspectiva</span>
            <h3>{g.titulo}</h3>
            <div className="cmi-ov-chart">
              {loadingDet ? (
                <div className="cmi-pred-empty">Cargando serie analítica...</div>
              ) : g.data ? (
                <ChartRevealV2>
                  {g.tipo === 'doughnut'
                    ? <Doughnut data={g.data} options={{ responsive: true, maintainAspectRatio: false }} plugins={CHART_PLUGINS_V2} />
                    : <Bar data={g.data} options={chartOpts} plugins={CHART_PLUGINS_V2} />}
                </ChartRevealV2>
              ) : (
                <div className="cmi-pred-empty">{g.empty}</div>
              )}
            </div>
          </article>
        ))}

        <article className="cmi-card cmi-ov-card">
          <span className="cmi-eyebrow">Cumplimiento relativo</span>
          <h3>Avance a meta de sus KPI (%)</h3>
          <div className="cmi-ov-chart">
            {chartAvance ? (
              <ChartRevealV2>
                <Bar data={chartAvance} options={pctOpts} plugins={CHART_PLUGINS_V2} />
              </ChartRevealV2>
            ) : (
              <div className="cmi-pred-empty">No hay indicadores con meta y dato en esta gestión.</div>
            )}
          </div>
        </article>

        {customChartsSlot}

        {(detalle?.graficos_personalizados || []).map((g) => (
          <article key={g.id} className="cmi-card cmi-ov-card">
            <span className="cmi-eyebrow">Gráfica personalizada</span>
            <h3>{g.titulo}</h3>
            <div className="cmi-ov-chart">
              <GraficoPersonalizadoBody
                tipo={g.tipo_grafico}
                titulo={g.titulo}
                filas={g.datos?.filas}
                tokens={tokens}
                chartOpts={chartOpts}
              />
            </div>
          </article>
        ))}
      </div>

      <KpisPersonalizadosSection items={detalle?.kpis_personalizados} />
    </section>
  );
}
