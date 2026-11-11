import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { invalidateDataopsCache } from '../api/dataopsApi';
import { clearKpiMemoryCache } from '../api/kpiApi';
import { limpiarCacheApi } from '../services/pwa';
import { queryClient } from '../api/queryClient';
import { clearLoteFlowSession } from '../modules/dataops/context/LoteFlowContext';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('gira_user');
      if (!stored) return null;
      return JSON.parse(stored);
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem('gira_token'));

  const login = useCallback((userData, accessToken) => {
    localStorage.setItem('gira_token', accessToken);
    localStorage.setItem('gira_user', JSON.stringify(userData));
    setToken(accessToken);
    setUser(userData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('gira_token');
    localStorage.removeItem('gira_user');
    localStorage.removeItem('gira_notifications_cache');
    localStorage.removeItem('gira_last_login_date');
    localStorage.removeItem('last_active_batch_id');
    // Se preserva gira_trusted_device_* para cumplir la vigencia de 30 días del dispositivo confiable
    sessionStorage.clear();
    // Limpieza de todos los cachés en memoria para prevenir retención de datos entre sesiones
    invalidateDataopsCache();
    clearKpiMemoryCache();
    limpiarCacheApi();
    clearLoteFlowSession(); // borradores del flujo de lote (ya cubiertos por sessionStorage.clear, explícito por claridad)
    queryClient.clear(); // contexto de lote, bandeja y lecturas BETO en caché de React Query
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(() => ({
    user,
    token,
    role: user?.role || null,
    login,
    logout,
    isAuthenticated: !!token && !!user,
  }), [user, token, login, logout]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

/** Renders children only if user has one of the allowed roles */
export const RoleGuard = ({ children, allowedRoles }) => {
  const { role } = useAuth();
  if (!allowedRoles.includes(role)) return null;
  return children;
};
