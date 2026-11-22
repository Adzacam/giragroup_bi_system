import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { toV2Path, toV1Path } from '../utils/v2Routes';

export const V2_FONT_PRESETS = [
  {
    id: 'augen',
    label: 'Augen Pro (Geist 350/400)',
    shortLabel: 'Augen Pro',
    description: 'Una sola fuente geométrica, peso 350 en títulos y tracking -0.020em',
  },
  {
    id: 'jakarta',
    label: 'Plus Jakarta Sans Unificada',
    shortLabel: 'Jakarta',
    description: 'Tipografía institucional continua en toda la interfaz',
  },
  {
    id: 'inter-tight',
    label: 'Inter Tight Unificada',
    shortLabel: 'Inter Tight',
    description: 'Alta densidad analítica con tracking compacto -0.020em',
  },
  {
    id: 'gira-original',
    label: 'Gira Original (Newsreader + Jakarta)',
    shortLabel: 'Gira Classic',
    description: 'Títulos editoriales serif combinados con UI sans-serif',
  },
];

const STORAGE_KEY = 'gira_v2_font_preset';

const UiVersionContext = createContext({
  uiVersion: 'v2',
  fontPreset: 'augen',
  setFontPreset: () => {},
  toV2Path,
  toV1Path,
});

export function UiVersionProvider({ children }) {
  const [fontPreset, setFontPresetState] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved && V2_FONT_PRESETS.some((p) => p.id === saved)) {
        return saved;
      }
    } catch {
      // ignore storage errors
    }
    return 'augen';
  });

  const setFontPreset = useCallback((nextPreset) => {
    if (!V2_FONT_PRESETS.some((p) => p.id === nextPreset)) return;
    setFontPresetState(nextPreset);
    try {
      localStorage.setItem(STORAGE_KEY, nextPreset);
    } catch {
      // ignore storage errors
    }
    if (typeof document !== 'undefined' && document.documentElement.getAttribute('data-ui-version') === 'v2') {
      document.documentElement.setAttribute('data-v2-font', nextPreset);
    }
  }, []);

  useEffect(() => {
    if (typeof document !== 'undefined' && document.documentElement.getAttribute('data-ui-version') === 'v2') {
      document.documentElement.setAttribute('data-v2-font', fontPreset);
    }
  }, [fontPreset]);

  return (
    <UiVersionContext.Provider
      value={{
        uiVersion: 'v2',
        fontPreset,
        setFontPreset,
        toV2Path,
        toV1Path,
      }}
    >
      {children}
    </UiVersionContext.Provider>
  );
}

export function useUiVersion() {
  return useContext(UiVersionContext);
}
