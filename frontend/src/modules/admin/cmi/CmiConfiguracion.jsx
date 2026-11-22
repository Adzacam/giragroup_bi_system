import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import cmiApi from '../../../api/cmiApi';
import ConfigKppTab from './config/ConfigKppTab';
import ConfigGraficosTab from './config/ConfigGraficosTab';
import PanelPerspectiva from './config/PanelPerspectiva';
import './cmi.css';

const COLORES_PERSPECTIVA = [
  'var(--color-gira-navy)',
  'var(--color-gira-gold)',
  'var(--color-alert-green)',
  'var(--color-slate-gray)',
];

export default function CmiConfiguracion() {
  const [tab, setTab] = useState('indicadores');
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['cmi', 'config'],
    queryFn: cmiApi.getConfig,
    staleTime: 30_000,
  });

  if (isLoading) return <div className="cmi"><div className="cmi-skeleton" style={{ height: 420 }} /></div>;
  if (isError) {
    return (
      <div className="cmi">
        <div className="cmi-card cmi-error" role="alert">
          No se pudo cargar la configuración del CMI.{' '}
          <button className="cmi-btn" onClick={() => refetch()}>Reintentar</button>
        </div>
      </div>
    );
  }

  const perspectivas = data.perspectivas || [];
  const activas = perspectivas.filter((p) => p.activa);
  const sumaPesos = activas.reduce((s, p) => s + Number(p.peso), 0);
  const puedeEditarPersp = !!data.puede_editar_perspectivas;

  const tabs = [
    ...(puedeEditarPersp ? [{ id: 'perspectivas', label: 'Perspectivas' }] : []),
    { id: 'indicadores', label: 'Indicadores (23 oficiales)' },
    { id: 'kpp', label: 'KPI personalizados' },
    { id: 'graficas', label: 'Gráficas' },
  ];
  const activeTab = tabs.some((t) => t.id === tab) ? tab : tabs[0]?.id;

  return (
    <div className="cmi">
      <div className="cmi-card cmi-cfg-intro">
        <p>
          Define la meta y los umbrales de semáforo de los indicadores en tus perspectivas visibles, o crea indicadores y
          gráficas personalizadas desde el catálogo sin PII. Los cambios se aplican al actualizar.
        </p>
        {puedeEditarPersp && (
          <div className="cmi-weights" aria-label="Distribución de pesos entre perspectivas activas">
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
              <span className="cmi-eyebrow">Pesos de perspectivas</span>
              <strong style={{ color: Math.round(sumaPesos) === 100 ? 'var(--cmi-ok)' : 'var(--cmi-warn)' }}>{sumaPesos} %</strong>
            </div>
            <div className="cmi-stack">
              {activas.map((p) => (
                <i key={p.codigo} title={`${p.nombre}: ${p.peso} %`}
                   style={{ width: `${sumaPesos ? (p.peso / sumaPesos) * 100 : 0}%`, background: COLORES_PERSPECTIVA[(p.orden - 1) % 4] }} />
              ))}
            </div>
            {Math.round(sumaPesos) !== 100 && (
              <span style={{ fontSize: 11.5, color: 'var(--color-slate-gray)' }}>
                Los pesos no suman 100 %; el índice se normaliza sobre {sumaPesos} %.
              </span>
            )}
          </div>
        )}
      </div>

      <div className="cmi-chip-group" role="tablist" aria-label="Secciones de configuración" style={{ marginBottom: 16 }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={activeTab === t.id}
            className={`cmi-filter-chip ${activeTab === t.id ? 'is-active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'perspectivas' && puedeEditarPersp && perspectivas.map((p) => (
        <PanelPerspectiva key={p.codigo} p={p} color={COLORES_PERSPECTIVA[(p.orden - 1) % 4]} puedeEditarPerspectiva />
      ))}

      {activeTab === 'indicadores' && perspectivas.map((p) => (
        <PanelPerspectiva key={p.codigo} p={p} color={COLORES_PERSPECTIVA[(p.orden - 1) % 4]} soloIndicadores />
      ))}

      {activeTab === 'kpp' && (
        <ConfigKppTab
          perspectivas={perspectivas}
          medidas={data.catalogo_medidas || []}
          kpisPersonalizados={data.kpis_personalizados || []}
        />
      )}

      {activeTab === 'graficas' && (
        <ConfigGraficosTab
          perspectivas={perspectivas}
          medidas={data.catalogo_medidas || []}
          graficos={data.graficos_personalizados || []}
        />
      )}
    </div>
  );
}
