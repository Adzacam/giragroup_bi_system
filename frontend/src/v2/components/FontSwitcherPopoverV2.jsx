import React, { useState, useRef, useEffect } from 'react';
import { Check, Type } from 'lucide-react';
import { useUiVersion, V2_FONT_PRESETS } from '../context/UiVersionContext';

export default function FontSwitcherPopoverV2() {
  const { fontPreset, setFontPreset } = useUiVersion();
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handleOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const handleEscape = (e) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  const activePreset = V2_FONT_PRESETS.find((p) => p.id === fontPreset) || V2_FONT_PRESETS[0];

  return (
    <div className="v2-font-switcher" ref={containerRef} style={{ position: 'relative' }}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="v2-pill-icon-btn"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label="Cambiar tipografía en vivo"
        title={`Tipografía: ${activePreset.shortLabel}`}
      >
        <span style={{ fontSize: '12px', fontWeight: 500, letterSpacing: '-0.02em' }}>Aa</span>
      </button>

      {open && (
        <div
          role="listbox"
          aria-label="Selector de fuente tipográfica V2"
          className="v2-font-popover"
        >
          <div className="v2-font-popover-header">
            <Type size={13} />
            <span>Tipografía en vivo (V2)</span>
          </div>
          <div className="v2-font-popover-list">
            {V2_FONT_PRESETS.map((preset) => {
              const selected = preset.id === fontPreset;
              return (
                <button
                  key={preset.id}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => {
                    setFontPreset(preset.id);
                    setOpen(false);
                  }}
                  className={`v2-font-option ${selected ? 'is-selected' : ''}`}
                >
                  <div className="v2-font-option-text">
                    <span className="v2-font-option-title">{preset.label}</span>
                    <span className="v2-font-option-desc">{preset.description}</span>
                  </div>
                  {selected && <Check size={14} className="v2-font-option-check" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
