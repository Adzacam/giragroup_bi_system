import React from 'react';
import { Layers, TrendingUp } from 'lucide-react';

export default function CmiModeSwitch({ activeMode, onSelectMode, triggerParentChild }) {
  return (
    <div className="v2-pill-segment cmi-mode-switch" role="tablist" aria-label="Modos del Cuadro de Mando Integral">
      <button
        type="button"
        role="tab"
        aria-selected={activeMode === 'A'}
        className={`v2-pill-segment-btn cmi-mode-btn ${activeMode === 'A' ? 'is-active' : ''}`}
        onClick={(e) => triggerParentChild(e.currentTarget, () => onSelectMode('A'))}
      >
        <Layers size={16} className={activeMode === 'A' ? 'cmi-icon-gold' : ''} aria-hidden="true" />
        <span>Perspectivas estratégicas</span>
      </button>

      <button
        type="button"
        role="tab"
        aria-selected={activeMode === 'B'}
        className={`v2-pill-segment-btn cmi-mode-btn ${activeMode === 'B' ? 'is-active' : ''}`}
        onClick={(e) => triggerParentChild(e.currentTarget, () => onSelectMode('B'))}
      >
        <TrendingUp size={16} className={activeMode === 'B' ? 'cmi-icon-gold' : ''} aria-hidden="true" />
        <span>Analítica predictiva</span>
      </button>
    </div>
  );
}
