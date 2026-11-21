import React from 'react';
import { RefreshCw, SlidersHorizontal, Download, FileSpreadsheet, FileText } from 'lucide-react';
import PageHeader from '../../../components/shared/PageHeader';

export default function CmiHeader({
  activeMode,
  puedeConfigurar,
  isRefreshing,
  lastUpdatedLabel,
  onRefresh,
  onToggleConfig,
  triggerParentChild,
  exportarState,
}) {
  const { isExporting, showExportMenu, setShowExportMenu, exportar } = exportarState;

  return (
    <div className="cmi-page-header">
      <PageHeader
        category="ADMINISTRACIÓN ESTRATÉGICA"
        title="Cuadro de Mando Integral"
        subtitle="Desempeño institucional en cuatro perspectivas estratégicas, con metas, semáforo y analítica predictiva unificada."
      />
      <div className="cmi-header-actions">
        <div className="cmi-refresh-group">
          <button
            type="button"
            onClick={onRefresh}
            disabled={isRefreshing}
            className="btn-academic cmi-header-btn"
            aria-label="Actualizar indicadores del CMI"
          >
            <RefreshCw size={14} className={isRefreshing ? 'cmi-spin' : ''} aria-hidden="true" />
            <span>Actualizar</span>
          </button>
          {lastUpdatedLabel && (
            <span className="cmi-updated-stamp" aria-live="polite">
              {lastUpdatedLabel}
            </span>
          )}
        </div>

        {puedeConfigurar && (
          <button
            type="button"
            onClick={(e) => triggerParentChild(e.currentTarget, onToggleConfig)}
            aria-pressed={activeMode === 'C'}
            className={`btn-academic cmi-header-btn ${activeMode === 'C' ? 'is-active' : ''}`}
          >
            <SlidersHorizontal size={14} className={activeMode === 'C' ? 'cmi-icon-gold' : ''} aria-hidden="true" />
            <span>Configuración</span>
          </button>
        )}

        <div className="cmi-export-wrap">
          <button
            type="button"
            onClick={() => setShowExportMenu(!showExportMenu)}
            disabled={isExporting}
            aria-expanded={showExportMenu}
            aria-haspopup="menu"
            className="btn-academic cmi-export-btn"
          >
            <Download size={14} className={`cmi-icon-gold ${isExporting ? 'animate-bounce' : ''}`} aria-hidden="true" />
            <span>{isExporting ? 'Exportando...' : 'Exportar CMI'}</span>
          </button>

          {showExportMenu && (
            <div className="cmi-export-menu" role="menu">
              <button type="button" role="menuitem" className="cmi-export-item" onClick={() => exportar('xlsx')}>
                <FileSpreadsheet size={15} color="var(--color-alert-green)" aria-hidden="true" />
                <span>Descargar Excel (.xlsx)</span>
              </button>
              <button type="button" role="menuitem" className="cmi-export-item" onClick={() => exportar('pdf')}>
                <FileText size={15} color="var(--color-alert-red)" aria-hidden="true" />
                <span>Descargar PDF (.pdf)</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
