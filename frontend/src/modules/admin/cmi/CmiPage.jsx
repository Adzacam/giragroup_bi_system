import React, { useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import CmiScorecard from './scorecard/CmiScorecard';
import CmiConfiguracion from './CmiConfiguracion';
import GlosarioCmi from './GlosarioCmi';
import CmiHeader from './CmiHeader';
import CmiModeSwitch from './CmiModeSwitch';
import PrediccionPage from './prediccion/PrediccionPage';
import useExportarCmi from './useExportarCmi';
import useActualizarCmi from './useActualizarCmi';
import useKineticScroll from '../../../hooks/useKineticScroll';
import { useParentChildTransitionV2 } from '../../../v2/transitions/useParentChildTransitionV2';
import { useAuth } from '../../../context/AuthContext';
import forecastApi from '../../../api/forecastApi';
import './cmi.css';

const ROLES_CONFIG = new Set(['ADMIN', 'ANALISTA_FINANCIERO', 'ANALISTA_MARKETING']);

export default function CmiPage() {
  useKineticScroll();
  const { role } = useAuth();
  const puedeConfigurar = ROLES_CONFIG.has(role);
  const [activeMode, setActiveMode] = useState('A');
  const [horizonte, setHorizonte] = useState(6);
  const [searchProg, setSearchProg] = useState('');
  const { triggerParentChild } = useParentChildTransitionV2();
  const exportarState = useExportarCmi();

  const {
    data: macroData = null,
    isLoading: isLoadingMacro,
    refetch: refetchMacro,
  } = useQuery({
    queryKey: ['analiticaPredictivaMacro', horizonte],
    queryFn: async () => {
      try {
        const res = await forecastApi.getAnaliticaPredictivaMacro(horizonte);
        if (res && res.status === 'success') return res;
      } catch (err) {
        console.warn('Backend /forecast/analitica-macro error:', err.message);
      }
      return null;
    },
    enabled: activeMode === 'B',
    staleTime: 60_000,
    gcTime: 300_000,
    placeholderData: keepPreviousData,
  });

  const { isRefreshing, lastUpdatedLabel, actualizar } = useActualizarCmi({
    activeMode,
    refetchMacro,
  });

  return (
    <div className="cmi-page-shell">
      <CmiHeader
        activeMode={activeMode}
        puedeConfigurar={puedeConfigurar}
        isRefreshing={isRefreshing || isLoadingMacro}
        lastUpdatedLabel={lastUpdatedLabel}
        onRefresh={actualizar}
        onToggleConfig={() => setActiveMode(activeMode === 'C' ? 'A' : 'C')}
        triggerParentChild={triggerParentChild}
        exportarState={exportarState}
      />

      <CmiModeSwitch
        activeMode={activeMode}
        onSelectMode={setActiveMode}
        triggerParentChild={triggerParentChild}
      />

      <div className="v2-parent-child-panel">
        {activeMode === 'A' && <GlosarioCmi tema="scorecard" />}
        {activeMode === 'B' && <GlosarioCmi tema="prediccion" />}
        {activeMode === 'C' && puedeConfigurar && <GlosarioCmi tema="configuracion" />}
        {activeMode === 'A' && <CmiScorecard />}
        {activeMode === 'C' && puedeConfigurar && <CmiConfiguracion />}
      </div>

      {activeMode === 'B' && (
        <PrediccionPage
          macroData={macroData}
          isLoading={isLoadingMacro}
          horizonte={horizonte}
          onHorizonteChange={setHorizonte}
          onRecalcular={() => refetchMacro()}
          searchProg={searchProg}
          onSearchProgChange={setSearchProg}
        />
      )}
    </div>
  );
}
