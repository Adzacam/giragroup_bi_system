import React, { useEffect, useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import cmiApi from '../../../../api/cmiApi';
import CmiDetalleKpi from '../CmiDetalleKpi';
import { useParentChildTransitionV2 } from '../../../../v2/transitions/useParentChildTransitionV2';
import { useContainerTransformV2 } from '../../../../v2/transitions/useContainerTransformV2';
import IndiceGlobal, { Leyenda } from './IndiceGlobal';
import MapaEstrategico from './MapaEstrategico';
import SeccionPerspectiva from './SeccionPerspectiva';
import MapaHorizontalV2 from './MapaHorizontalV2';
import VistaGeneralCmi from './VistaGeneralCmi';
import DesglosePerspectiva from './DesglosePerspectiva';
import { isV2Active } from './TarjetaKpi';
import '../cmi.css';

function leerPerspectivaUrl() {
  if (typeof window === 'undefined') return null;
  return new URLSearchParams(window.location.search).get('p');
}

export default function CmiScorecard() {
  const v2 = isV2Active();
  const [gestion, setGestion] = useState(null);
  const [activa, setActiva] = useState(() => (v2 ? leerPerspectivaUrl() : null));
  const [detalle, setDetalle] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const { triggerParentChild } = useParentChildTransitionV2();
  const { triggerContainerExpand, triggerContainerCollapse } = useContainerTransformV2();

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['cmi', 'scorecard', gestion],
    queryFn: () => cmiApi.getScorecard(gestion),
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });

  const { data: resumen } = useQuery({
    queryKey: ['cmi', 'resumen'],
    queryFn: () => cmiApi.getResumen(),
    enabled: v2,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!v2 || typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    if (activa) url.searchParams.set('p', activa);
    else url.searchParams.delete('p');
    window.history.replaceState({}, '', url.pathname + url.search);
  }, [v2, activa]);

  const seleccionarPerspectiva = (codigo, triggerEl) => {
    const next = activa === codigo ? null : codigo;
    if (next && triggerEl) {
      triggerContainerExpand(triggerEl, () => setActiva(next), { focusTargetId: 'cmi-scorecard-panel' });
    } else if (!next) {
      triggerContainerCollapse(() => setActiva(null));
    } else {
      setActiva(next);
    }
  };

  const irAV1 = (codigo) => {
    setActiva(codigo);
    document.getElementById(`cmi-${codigo}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (isLoading) {
    return (
      <div className="cmi" aria-busy="true">
        <div className="cmi-hero">
          <div className="cmi-skeleton" style={{ height: 320 }} />
          <div className="cmi-skeleton" style={{ height: 320 }} />
        </div>
        <div className="cmi-skeleton" style={{ height: 180 }} />
      </div>
    );
  }
  if (isError) {
    return (
      <div className="cmi">
        <div className="cmi-card cmi-error" role="alert">
          No se pudo cargar el Cuadro de Mando Integral.{' '}
          <button className="cmi-btn" style={{ marginLeft: 8 }} onClick={() => refetch()}>Reintentar</button>
        </div>
      </div>
    );
  }
  if (!data?.gestiones?.length) {
    return (
      <div className="cmi">
        <div className="cmi-card cmi-empty">Aún no hay datos consolidados en el Data Warehouse para calcular el CMI.</div>
      </div>
    );
  }

  const perspActiva = v2 && activa ? data.perspectivas.find((p) => p.codigo === activa) : null;

  return (
    <div className="cmi" style={{ opacity: isFetching ? 0.7 : 1, transition: 'opacity .2s' }}>
      <div className="cmi-toolbar">
        <div className="cmi-segment" role="group" aria-label="Gestión">
          {data.gestiones.map((g) => (
            <button
              key={g}
              type="button"
              aria-pressed={g === data.gestion}
              onClick={(e) => triggerParentChild(e.currentTarget, () => setGestion(g), { focusTargetId: 'cmi-scorecard-hero' })}
            >
              {g}
            </button>
          ))}
        </div>
        {v2 && !perspActiva && (
          <div className="cmi-search-wrap cmi-toolbar-search">
            <Search size={14} className="cmi-search-icon" aria-hidden="true" />
            <input
              type="search"
              className="cmi-input cmi-search-input"
              placeholder="Buscar KPI (ej. KPI-01)..."
              aria-label="Buscar KPI en el Cuadro de Mando"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        )}
        <Leyenda />
      </div>

      {v2 ? (
        <>
          <div className="cmi-hero-v2 v2-parent-child-subpanel" id="cmi-scorecard-hero" tabIndex={-1}>
            <IndiceGlobal global={data.global} gestion={data.gestion} compact />
            <MapaHorizontalV2
              perspectivas={data.perspectivas}
              activa={activa}
              onSelect={seleccionarPerspectiva}
            />
          </div>

          <div id="cmi-scorecard-panel" tabIndex={-1}>
            {perspActiva ? (
              <DesglosePerspectiva
                perspectiva={perspActiva}
                gestion={data.gestion}
                onVolver={() => seleccionarPerspectiva(null)}
                onAbrirKpi={setDetalle}
              />
            ) : (
              <VistaGeneralCmi
                scorecard={data}
                resumen={resumen}
                searchQuery={searchQuery}
                onOpenKpi={setDetalle}
                onSelectPerspectiva={(cod) => seleccionarPerspectiva(cod)}
              />
            )}
          </div>
        </>
      ) : (
        <>
          <div className="cmi-hero v2-parent-child-subpanel" id="cmi-scorecard-hero" tabIndex={-1}>
            <IndiceGlobal global={data.global} gestion={data.gestion} />
            <MapaEstrategico perspectivas={data.perspectivas} activa={activa} onSelect={irAV1} />
          </div>
          {data.perspectivas.map((p) => <SeccionPerspectiva key={p.codigo} p={p} onAbrir={setDetalle} />)}
        </>
      )}

      {detalle && <CmiDetalleKpi codigo={detalle} onClose={() => setDetalle(null)} />}
    </div>
  );
}
