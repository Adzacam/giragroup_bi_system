import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('gira_user');
      if (!stored) return null;
      const parsed = JSON.parse(stored);
      // Auto-migración si el navegador tenía la sesión previa del mock inicial
      if (parsed?.role === 'Demo User' || parsed?.role === 'DEMO USER') {
        parsed.role = 'ADMIN';
        localStorage.setItem('gira_user', JSON.stringify(parsed));
      }
      return parsed;
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
    Object.keys(localStorage).forEach((k) => {
      if (k.startsWith('gira_trusted_device_')) {
        localStorage.removeItem(k);
      }
    });
    sessionStorage.clear();
    setToken(null);
    setUser(null);
  }, []);

  const value = {
    user,
    token,
    role: user?.role || null,
    login,
    logout,
    isAuthenticated: !!token && !!user,
  };

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
