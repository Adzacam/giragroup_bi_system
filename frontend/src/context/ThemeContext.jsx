import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';

const ThemeContext = createContext({
  theme: 'light',
  isDark: false,
  toggleTheme: () => {},
  setTheme: () => {},
  canvasEnabled: false,
  toggleCanvas: () => {},
  autoRefresh: '30s',
  setAutoRefresh: () => {},
});

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    return localStorage.getItem('gira_theme') || 'light';
  });

  const [canvasEnabled, setCanvasEnabled] = useState(() => {
    const stored = localStorage.getItem('gira_canvas_enabled');
    return stored !== null ? stored === 'true' : false;
  });

  const [autoRefresh, setAutoRefreshState] = useState(() => {
    return localStorage.getItem('gira_auto_refresh') || '30s';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('gira_theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'));
  }, []);

  const setTheme = useCallback((newTheme) => {
    setThemeState(newTheme);
  }, []);

  const toggleCanvas = useCallback(() => {
    setCanvasEnabled((prev) => {
      const next = !prev;
      localStorage.setItem('gira_canvas_enabled', String(next));
      return next;
    });
  }, []);

  const setAutoRefresh = useCallback((val) => {
    setAutoRefreshState(val);
    localStorage.setItem('gira_auto_refresh', val);
  }, []);

  const value = useMemo(() => ({
    theme,
    isDark: theme === 'dark',
    toggleTheme,
    setTheme,
    canvasEnabled,
    toggleCanvas,
    autoRefresh,
    setAutoRefresh,
  }), [theme, toggleTheme, setTheme, canvasEnabled, toggleCanvas, autoRefresh, setAutoRefresh]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);

export default ThemeContext;
