import React, { useMemo } from 'react';
import { Bar, Line } from 'react-chartjs-2';
import { AlertTriangle, CheckCircle2, HelpCircle } from 'lucide-react';
import { useTheme } from '../../../../context/ThemeContext';
import { SEMAFORO, fmtValor, MAPA_ESTRATEGICO } from '../cmiFormat';
import { getChartTokens, buildChartOptions } from '../chartTheme';
import { CHART_PLUGINS_V2 } from '../../../../v2/motion/chartAnimationsV2';
import ChartRevealV2 from '../../../../v2/motion/ChartRevealV2';
import { Tendencia, avance } from './TarjetaKpi';

export default function VistaGeneralCmi({ scorecard, resumen, searchQuery, onOpenKpi, onSelectPerspectiva }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const tokens = useMemo(() => getChartTokens(isDark), [isDark]);

  const todosKpis = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return scorecard.perspectivas.flatMap((p) =>
      p.kpis
        .filter((k) => !q || k.codigo.toLowerCase().includes(q) || k.nombre.toLowerCase().includes(q))
        .map((k) => ({ ...k, perspNombre: p.nombre }))
    );
  }, [scorecard, searchQuery]);

  const alertas = useMemo(() => (
    todosKpis
      .filter((k) => k.semaforo === 'ROJO' || k.semaforo === 'AMBAR')
      .sort((a, b) => {
        if (a.semaforo !== b.semaforo) return a.semaforo === 'ROJO' ? -1 : 1;
        return (avance(a) ?? 1) - (avance(b) ?? 1);
      })
  ), [todosKpis]);

  const cobertura = useMemo(() => {
    const sinDato = todosKpis.filter((k) => k.valor === null);
    const sinUmbral = todosKpis.filter((k) => k.valor !== null && k.semaforo === 'SIN_UMBRAL');
    const evaluados = todosKpis.length - sinDato.length - sinUmbral.length;
    return { total: todosKpis.length, evaluados, sinDato, sinUmbral };
  }, [todosKpis]);

  const perspBarData = useMemo(() => {
    const gestiones = resumen?.gestiones || [];
    const idxActual = gestiones.indexOf(scorecard.gestion);
    const prevGestion = idxActual > 0 ? gestiones[idxActual - 1] : null;
    const prevMap = Object.fromEntries(
      (resumen?.perspectivas_por_gestion || [])
        .filter((r) => r.gestion === prevGestion)
        .map((r) => [r.codigo, r.indice])
    );
    const ordered = MAPA_ESTRATEGICO
      .map((c) => scorecard.perspectivas.find((p) => p.codigo === c))
      .filter(Boolean);

    return {
      labels: ordered.map((p) => p.nombre),
      datasets: [
        ...(prevGestion ? [{
          label: `Gestión ${prevGestion}`,
          data: ordered.map((p) => prevMap[p.codigo] ?? 0),
          backgroundColor: tokens.metaBarBg,
          borderRadius: 6,
        }] : []),
        {
          label: `Gestión ${scorecard.gestion}`,
          data: ordered.map((p) => p.indice ?? 0),
          backgroundColor: tokens.gold,
          borderRadius: 6,
        },
      ],
    };
  }, [resumen, scorecard, tokens]);

  const globalLineData = useMemo(() => {
    const serie = resumen?.global_por_gestion || [];
    if (!serie.length) return null;
    const lineColor = isDark ? tokens.gold : tokens.navy;
    const pointColor = isDark ? tokens.goldLight : tokens.gold;
    return {
      labels: serie.map((g) => String(g.gestion)),
      datasets: [{
        label: 'Índice Global CMI (0–100)',
        data: serie.map((g) => g.indice),
        borderColor: lineColor,
        backgroundColor: pointColor,
        pointBackgroundColor: pointColor,
        pointBorderColor: lineColor,
        borderWidth: 2.5,
        pointRadius: 4,
        tension: 0.25,
      }],
    };
  }, [resumen, tokens, isDark]);

  const chartOpts = useMemo(() => buildChartOptions(isDark, {
    scales: {
      x: { grid: { color: tokens.grid }, ticks: { color: tokens.muted, font: { size: 10 } } },
      y: { min: 0, max: 100, grid: { color: tokens.grid }, ticks: { color: tokens.muted, font: { size: 10 } } },
    },
  }), [isDark, tokens]);

  return (
    <div className="cmi-overview-grid">
      {/* 1. Matriz de semáforo de los 23 KPI */}
      <section className="cmi-card cmi-ov-card cmi-ov-span2" aria-labelledby="cmi-ov-heat">
        <div className="cmi-ov-head">
          <div>
            <span className="cmi-eyebrow">Mapa de calor institucional</span>
            <h3 id="cmi-ov-heat">Matriz de semáforo ({todosKpis.length} indicadores)</h3>
          </div>
          <span className="cmi-eyebrow">Clic en un indicador para ver su evolución</span>
        </div>
        <div className="cmi-heatmap-rows">
          {[
            ...MAPA_ESTRATEGICO.map((cod) => scorecard.perspectivas.find((p) => p.codigo === cod)).filter(Boolean),
            ...scorecard.perspectivas.filter((p) => !MAPA_ESTRATEGICO.includes(p.codigo)),
          ].map((p) => {
            const kpis = p.kpis.filter((k) => !searchQuery.trim() || k.codigo.toLowerCase().includes(searchQuery.trim().toLowerCase()) || k.nombre.toLowerCase().includes(searchQuery.trim().toLowerCase()));
            if (!kpis.length) return null;
            return (
              <div key={p.codigo} className="cmi-heatmap-row">
                <button type="button" className="cmi-heatmap-persp" onClick={() => onSelectPerspectiva(p.codigo)}>
                  {p.nombre}
                </button>
                <div className="cmi-heatmap-cells">
                  {kpis.map((k) => {
                    const sem = SEMAFORO[k.semaforo] || SEMAFORO.SIN_UMBRAL;
                    const sinDato = k.valor === null;
                    return (
                      <button
                        key={k.codigo}
                        type="button"
                        className={`cmi-heat-cell ${sinDato ? 'is-empty' : ''}`}
                        style={{ '--cell-color': sem.color }}
                        onClick={() => onOpenKpi(k.codigo)}
                        title={`${k.codigo} · ${k.nombre}: ${fmtValor(k.valor, k.unidad)} (${sinDato ? 'Sin dato' : sem.label})`}
                        aria-label={`${k.codigo} ${k.nombre}: ${fmtValor(k.valor, k.unidad)}`}
                      >
                        <span className="cmi-heat-code">{k.codigo}</span>
                        <span className="cmi-heat-val">{fmtValor(k.valor, k.unidad, { compacto: true })}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 2. Índice por perspectiva frente a la gestión anterior */}
      <section className="cmi-card cmi-ov-card" aria-labelledby="cmi-ov-persp">
        <span className="cmi-eyebrow">Comparativa interanual</span>
        <h3 id="cmi-ov-persp">Índice por perspectiva vs. gestión anterior</h3>
        <div className="cmi-ov-chart">
          <ChartRevealV2>
            <Bar data={perspBarData} options={chartOpts} plugins={CHART_PLUGINS_V2} />
          </ChartRevealV2>
        </div>
      </section>

      {/* 3. Evolución del índice global por gestión */}
      <section className="cmi-card cmi-ov-card" aria-labelledby="cmi-ov-evol">
        <span className="cmi-eyebrow">Serie histórica</span>
        <h3 id="cmi-ov-evol">Evolución del índice global por gestión</h3>
        <div className="cmi-ov-chart">
          {globalLineData ? (
            <ChartRevealV2>
              <Line data={globalLineData} options={chartOpts} plugins={CHART_PLUGINS_V2} />
            </ChartRevealV2>
          ) : (
            <div className="cmi-pred-empty">Cargando serie histórica de gestiones...</div>
          )}
        </div>
      </section>

      {/* 4. Alertas prioritarias */}
      <section className="cmi-card cmi-ov-card" aria-labelledby="cmi-ov-alertas">
        <div className="cmi-ov-head">
          <div>
            <span className="cmi-eyebrow">Atención prioritaria</span>
            <h3 id="cmi-ov-alertas">Alertas prioritarias ({alertas.length})</h3>
          </div>
          <AlertTriangle size={18} className="cmi-text-gold" aria-hidden="true" />
        </div>
        {alertas.length === 0 ? (
          <div className="cmi-ov-ok-state">
            <CheckCircle2 size={18} className="cmi-text-ok" aria-hidden="true" />
            <span>Todos los indicadores evaluables están en meta para {scorecard.gestion}.</span>
          </div>
        ) : (
          <ul className="cmi-alert-list">
            {alertas.map((k) => {
              const sem = SEMAFORO[k.semaforo] || SEMAFORO.AMBAR;
              return (
                <li key={k.codigo}>
                  <button type="button" className="cmi-alert-item" onClick={() => onOpenKpi(k.codigo)}>
                    <i className="cmi-dot" style={{ background: sem.color }} />
                    <div className="cmi-alert-main">
                      <strong>{k.codigo} · {k.nombre}</strong>
                      <span>{k.perspNombre} · Meta {k.sentido === 'MIN' ? '≤' : '≥'} {fmtValor(k.meta, k.unidad, { compacto: true })}</span>
                    </div>
                    <div className="cmi-alert-right">
                      <b className="cmi-mono">{fmtValor(k.valor, k.unidad, { compacto: true })}</b>
                      <Tendencia kpi={k} />
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* 5. Cobertura del CMI */}
      <section className="cmi-card cmi-ov-card" aria-labelledby="cmi-ov-cob">
        <div className="cmi-ov-head">
          <div>
            <span className="cmi-eyebrow">Trazabilidad de datos</span>
            <h3 id="cmi-ov-cob">Cobertura del CMI · {scorecard.gestion}</h3>
          </div>
          <HelpCircle size={18} className="cmi-muted" aria-hidden="true" />
        </div>
        <div className="cmi-cob-summary">
          <div><b className="cmi-mono cmi-text-ok">{cobertura.evaluados}</b><span>Evaluados</span></div>
          <div><b className="cmi-mono cmi-text-gold">{cobertura.sinUmbral.length}</b><span>Sin umbral</span></div>
          <div><b className="cmi-mono cmi-muted">{cobertura.sinDato.length}</b><span>Sin dato</span></div>
        </div>
        {cobertura.sinDato.length > 0 && (
          <ul className="cmi-cob-list">
            {cobertura.sinDato.map((k) => (
              <li key={k.codigo}>
                <button type="button" className="cmi-cob-item" onClick={() => onOpenKpi(k.codigo)}>
                  <span className="cmi-kpi-code">{k.codigo}</span>
                  <span>{k.motivo_sin_dato || 'Sin registros consolidados para esta gestión.'}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
