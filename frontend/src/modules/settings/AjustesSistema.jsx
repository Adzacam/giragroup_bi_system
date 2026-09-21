import React, { useState, useEffect } from 'react';
import {
  Sun, Moon, Trash2, Bell, BellOff, RefreshCw, Cpu, Database,
  ShieldCheck, HardDrive, CheckCircle2, AlertTriangle, Sparkles, Volume2, VolumeX
} from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import { useTheme } from '../../context/ThemeContext';
import useKineticScroll from '../../hooks/useKineticScroll';

export default function AjustesSistema() {
  useKineticScroll();
  const {
    theme,
    toggleTheme,
    setTheme,
    canvasEnabled,
    toggleCanvas,
    autoRefresh,
    setAutoRefresh,
  } = useTheme();

  const [notificationSound, setNotificationSound] = useState(() => {
    return localStorage.getItem('gira_notify_sound') !== 'false';
  });

  const [notificationLevel, setNotificationLevel] = useState(() => {
    return localStorage.getItem('gira_notify_level') || 'ALL';
  });

  const [cacheStatus, setCacheStatus] = useState('');
  const [storageSize, setStorageSize] = useState('0 KB');

  // Calculate local storage size
  const calculateStorage = () => {
    let total = 0;
    for (let x in localStorage) {
      if (localStorage.hasOwnProperty(x)) {
        total += (localStorage[x].length + x.length) * 2;
      }
    }
    setStorageSize((total / 1024).toFixed(1) + ' KB');
  };

  useEffect(() => {
    calculateStorage();
  }, []);

  const handleClearQueryCache = () => {
    // Purge temporary query caches, keep session intact
    sessionStorage.clear();
    const tempKeys = ['giragroup_visited'];
    tempKeys.forEach(k => localStorage.removeItem(k));
    calculateStorage();
    setCacheStatus('Caché de consultas y vistas en memoria purgada exitosamente.');
    setTimeout(() => setCacheStatus(''), 4000);
  };

  const handleFullReset = () => {
    if (window.confirm('¿Deseas restablecer todas las preferencias locales de la interfaz? (Esto cerrará tu sesión activa).')) {
      localStorage.clear();
      sessionStorage.clear();
      window.location.href = '/login';
    }
  };

  const handleSoundToggle = () => {
    const next = !notificationSound;
    setNotificationSound(next);
    localStorage.setItem('gira_notify_sound', String(next));
  };

  const handleNotificationLevelChange = (val) => {
    setNotificationLevel(val);
    localStorage.setItem('gira_notify_level', val);
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <PageHeader
        category="CONFIGURACIÓN &amp; PREFERENCIAS"
        title="Ajustes del"
        italicWord="Sistema"
        subtitle="Personalización de experiencia visual, gestión de almacenamiento y caché local, políticas de alertas y diagnóstico de plataforma."
      />

      {cacheStatus && (
        <div
          style={{
            padding: '14px 18px',
            marginBottom: '24px',
            backgroundColor: '#f0fdf4',
            border: '1px solid #bbf7d0',
            color: 'var(--color-alert-green)',
            borderRadius: 'var(--radius-inputs)',
            fontSize: '13.5px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <CheckCircle2 size={16} />
          <span>{cacheStatus}</span>
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
          gap: '24px',
        }}
      >
        {/* ── 1. Apariencia y Tema Visual ─────────────────────── */}
        <div className="card-mist kinetic-card" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            {theme === 'dark' ? <Moon size={20} color="var(--color-sienna-brown)" /> : <Sun size={20} color="var(--color-sienna-brown)" />}
            <h3 className="serif-heading" style={{ fontSize: '20px', margin: 0 }}>
              Apariencia &amp; Tema Visual
            </h3>
          </div>
          <p style={{ fontSize: '13.5px', color: 'var(--color-slate-gray)', lineHeight: 1.5, marginBottom: '20px' }}>
            Selecciona el modo de contraste para la visualización de paneles analíticos y reportes ejecutivos.
          </p>

          <div style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
            <button
              onClick={() => setTheme('light')}
              type="button"
              className={theme === 'light' ? 'btn-pill-dark' : 'btn-pill-ghost'}
              style={{ flex: 1, justifyContent: 'center', padding: '10px 16px', fontSize: '13.5px' }}
            >
              <Sun size={15} style={{ marginRight: '6px' }} /> Modo Claro
            </button>
            <button
              onClick={() => setTheme('dark')}
              type="button"
              className={theme === 'dark' ? 'btn-pill-dark' : 'btn-pill-ghost'}
              style={{ flex: 1, justifyContent: 'center', padding: '10px 16px', fontSize: '13.5px' }}
            >
              <Moon size={15} style={{ marginRight: '6px' }} /> Modo Oscuro
            </button>
          </div>

          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: '13.5px', display: 'block' }}>Canvas 3D Isométrico Interactivo</strong>
                <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                  Ondulación senoidal y seguimiento reactivo del cursor
                </span>
              </div>
              <button
                onClick={toggleCanvas}
                type="button"
                className={canvasEnabled ? 'btn-pill-dark' : 'btn-pill-ghost'}
                style={{ padding: '6px 14px', fontSize: '12px' }}
              >
                {canvasEnabled ? 'Activado' : 'Pausado'}
              </button>
            </div>
          </div>
        </div>

        {/* ── 2. Limpieza de Caché y Almacenamiento ────────────── */}
        <div className="card-mist kinetic-card" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <HardDrive size={20} color="var(--color-ink-black)" />
            <h3 className="serif-heading" style={{ fontSize: '20px', margin: 0 }}>
              Almacenamiento &amp; Limpieza de Caché
            </h3>
          </div>
          <p style={{ fontSize: '13.5px', color: 'var(--color-slate-gray)', lineHeight: 1.5, marginBottom: '18px' }}>
            Purga datos locales del cliente si experimentas lentitud o deseas forzar la recarga limpia de catálogos.
          </p>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', backgroundColor: 'rgba(242, 242, 243, 0.5)', borderRadius: '12px', marginBottom: '20px' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>Espacio en Almacenamiento Local:</span>
            <strong style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{storageSize}</strong>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <button
              onClick={handleClearQueryCache}
              type="button"
              className="btn-pill-ghost"
              style={{ justifyContent: 'center', padding: '10px 16px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <RefreshCw size={14} /> Limpiar Caché de Consultas y Vistas
            </button>
            <button
              onClick={handleFullReset}
              type="button"
              style={{
                background: 'none',
                border: '1px solid #fee2e2',
                color: 'var(--color-alert-red)',
                borderRadius: 'var(--radius-buttons)',
                padding: '10px 16px',
                fontSize: '13px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                transition: 'background-color 0.2s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#fef2f2')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
            >
              <Trash2 size={14} /> Purgar Todo y Restablecer Sesión
            </button>
          </div>
        </div>

        {/* ── 3. Políticas de Alertas y Notificaciones ────────── */}
        <div className="card-mist kinetic-card" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <Bell size={20} color="var(--color-ink-black)" />
            <h3 className="serif-heading" style={{ fontSize: '20px', margin: 0 }}>
              Alertas &amp; Notificaciones
            </h3>
          </div>
          <p style={{ fontSize: '13.5px', color: 'var(--color-slate-gray)', lineHeight: 1.5, marginBottom: '20px' }}>
            Configura el nivel de interrupción de eventos críticos y anomalías detectadas en el pipeline.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: '13.5px', display: 'block' }}>Sonido de Alerta de Campo Crítico</strong>
                <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>Aviso auditivo en disparadores GIRA-50</span>
              </div>
              <button
                onClick={handleSoundToggle}
                type="button"
                className={notificationSound ? 'btn-pill-dark' : 'btn-pill-ghost'}
                style={{ padding: '6px 12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                {notificationSound ? <Volume2 size={14} /> : <VolumeX size={14} />}
                {notificationSound ? 'Activo' : 'Mudo'}
              </button>
            </div>

            <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '8px' }}>
                Filtro de Severidad en Campanilla:
              </label>
              <select
                value={notificationLevel}
                onChange={(e) => handleNotificationLevelChange(e.target.value)}
                className="form-input"
                style={{ fontSize: '13px', padding: '8px 12px', cursor: 'pointer' }}
              >
                <option value="ALL">Todas las notificaciones (Info, Warning, Critical)</option>
                <option value="WARNING">Solo Advertencias y Críticas</option>
                <option value="CRITICAL">Solo Alertas Críticas (GIRA-50 y Fallas)</option>
              </select>
            </div>
          </div>
        </div>

        {/* ── 4. Actualización Automática (Polling) ───────────── */}
        <div className="card-mist kinetic-card" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <RefreshCw size={20} color="var(--color-ink-black)" />
            <h3 className="serif-heading" style={{ fontSize: '20px', margin: 0 }}>
              Frecuencia de Actualización
            </h3>
          </div>
          <p style={{ fontSize: '13.5px', color: 'var(--color-slate-gray)', lineHeight: 1.5, marginBottom: '20px' }}>
            Intervalo en el cual los tableros sincronizan automáticamente los datos con el Data Warehouse.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
            {[
              { label: 'Manual', val: 'manual' },
              { label: 'Cada 15s', val: '15s' },
              { label: 'Cada 30s', val: '30s' },
              { label: 'Cada 1 min', val: '1m' },
            ].map((opt) => (
              <button
                key={opt.val}
                type="button"
                onClick={() => setAutoRefresh(opt.val)}
                className={autoRefresh === opt.val ? 'btn-pill-dark' : 'btn-pill-ghost'}
                style={{ justifyContent: 'center', padding: '8px 12px', fontSize: '13px' }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── 5. Diagnóstico y Versión de Plataforma ────────────── */}
      <div style={{ marginTop: '36px' }}>
        <h3 className="serif-heading" style={{ fontSize: '22px', marginBottom: '16px' }}>
          Diagnóstico de Arquitectura &amp; Gobernanza
        </h3>
        <div
          className="floating-artifact kinetic-card"
          style={{
            padding: '28px',
            backgroundColor: 'var(--color-paper-white)',
            borderRadius: 'var(--radius-cards)',
            border: '1px solid var(--color-border)',
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '24px',
            }}
          >
            <div>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
                Plataforma Frontend
              </span>
              <div style={{ fontSize: '15px', fontWeight: 600, marginTop: '4px' }}>
                React 18.3 + Vite 6
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '2px' }}>
                Steep Design System (Newsreader &amp; Inter)
              </div>
            </div>

            <div>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
                Motor de Inferencia NLP
              </span>
              <div style={{ fontSize: '15px', fontWeight: 600, marginTop: '4px' }}>
                BETO v2.4 (Spanish BERT)
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-alert-green)', marginTop: '2px', fontWeight: 500 }}>
                ● Aceleración CUDA / PyTorch Activa
              </div>
            </div>

            <div>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
                Data Warehouse
              </span>
              <div style={{ fontSize: '15px', fontWeight: 600, marginTop: '4px' }}>
                PostgreSQL 16 (Constelación)
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '2px' }}>
                PoLP Enforced · RLS Habilitado
              </div>
            </div>

            <div>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
                Servidor Backend REST
              </span>
              <div style={{ fontSize: '15px', fontWeight: 600, marginTop: '4px' }}>
                FastAPI 0.136.0
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-alert-green)', marginTop: '2px', fontWeight: 500 }}>
                ● JWT + 2FA TOTP Integrado
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
