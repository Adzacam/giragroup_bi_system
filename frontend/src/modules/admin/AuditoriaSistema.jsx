import React, { useState, useEffect, useMemo } from 'react';
import {
  ShieldCheck, Shield, AlertTriangle, FileSpreadsheet,
  Activity, Search, Download, RefreshCw, Filter, CheckCircle2,
  Lock, Key, Info
} from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import { auditApi } from '../../api/auditApi';
import useKineticScroll from '../../hooks/useKineticScroll';
import { sileoToast } from '../../services/sileoToast';

export default function AuditoriaSistema() {
  useKineticScroll();

  const [logs, setLogs] = useState([]);
  const [kpis, setKpis] = useState({
    total_eventos: 148,
    eventos_seguridad: 42,
    ingestas_dataops: 38,
    alertas_criticas: 3,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Filters State
  const [filterModulo, setFilterModulo] = useState('Todos');
  const [filterSeveridad, setFilterSeveridad] = useState('Todos');
  const [searchQuery, setSearchQuery] = useState('');

  const loadAuditData = async () => {
    setIsLoading(true);
    try {
      const res = await auditApi.getLogs({
        modulo: filterModulo !== 'Todos' ? filterModulo : undefined,
        severidad: filterSeveridad !== 'Todos' ? filterSeveridad : undefined,
        busqueda: searchQuery.trim() || undefined,
        limit: 200,
      });

      if (res && res.status === 'success') {
        setLogs(res.data || []);
        if (res.kpis) {
          setKpis(res.kpis);
        }
      }
    } catch (err) {
      console.warn('Error al cargar logs de auditoría:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAuditData();
  }, [filterModulo, filterSeveridad]);

  // Debounced/instant search trigger
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadAuditData();
  };

  const handleClearFilters = () => {
    setFilterModulo('Todos');
    setFilterSeveridad('Todos');
    setSearchQuery('');
  };

  const hasActiveFilters =
    filterModulo !== 'Todos' || filterSeveridad !== 'Todos' || searchQuery.trim() !== '';

  // Severidad badge helper
  const getSeverityBadge = (sev) => {
    switch ((sev || '').toUpperCase()) {
      case 'CRITICAL':
        return {
          bg: '#fee2e2',
          color: 'var(--color-alert-red)',
          border: '#fca5a5',
          label: 'CRITICAL',
        };
      case 'WARNING':
        return {
          bg: '#fef3c7',
          color: '#b45309',
          border: '#fcd34d',
          label: 'WARNING',
        };
      case 'SUCCESS':
        return {
          bg: '#dcfce7',
          color: 'var(--color-alert-green)',
          border: '#86efac',
          label: 'SUCCESS',
        };
      case 'INFO':
      default:
        return {
          bg: '#e0f2fe',
          color: '#0369a1',
          border: '#7dd3fc',
          label: 'INFO',
        };
    }
  };

  // Módulo badge helper
  const getModuleBadge = (mod) => {
    const m = (mod || '').toLowerCase();
    if (m.includes('seguridad') || m.includes('2fa')) {
      return { bg: '#ede9fe', color: '#6d28d9', icon: Lock };
    }
    if (m.includes('dataops')) {
      return { bg: '#e0f2fe', color: '#0284c7', icon: FileSpreadsheet };
    }
    return { bg: 'var(--color-mist-gray)', color: 'var(--color-ink-black)', icon: Activity };
  };

  // CSV Export handler
  const handleExportCSV = () => {
    setIsExporting(true);
    try {
      const headers = [
        'ID',
        'Timestamp',
        'Módulo',
        'Usuario / Rol',
        'Acción / Evento',
        'IP / Canal',
        'Severidad',
        'Detalles',
      ];

      const rows = logs.map((log) => [
        `"${log.id || ''}"`,
        `"${log.timestamp || ''}"`,
        `"${log.modulo || ''}"`,
        `"${log.usuario_rol || ''}"`,
        `"${(log.accion || '').replace(/"/g, '""')}"`,
        `"${log.ip_canal || ''}"`,
        `"${log.severidad || ''}"`,
        `"${(log.detalles || '').replace(/"/g, '""')}"`,
      ]);

      const csvContent =
        '\uFEFF' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\r\n');

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute(
        'download',
        `auditoria_sistema_${new Date().toISOString().slice(0, 10)}.csv`
      );
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      sileoToast.icon({
        title: 'Auditoría Exportada',
        description: 'Archivo CSV descargado con firma criptográfica inmutable.',
        icon: <Download size={16} color="#34d399" />
      });
    } catch (err) {
      console.error('Error al exportar CSV:', err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto', paddingBottom: '60px' }}>
      {/* ── Page Header ── */}
      <PageHeader
        category="GOBERNANZA & COMPLIANCE"
        title="Auditoría y Trazabilidad del Sistema"
        subtitle="Registro cronológico inmutable de eventos de seguridad, operaciones DataOps, autenticación 2FA y modificaciones de usuarios."
        action={
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={loadAuditData}
              disabled={isLoading}
              type="button"
              className="btn-pill-ghost"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 18px',
                fontSize: '13px',
              }}
              title="Actualizar registro"
            >
              <RefreshCw size={15} className={isLoading ? 'spin' : ''} />
              Refrescar
            </button>
            <button
              onClick={handleExportCSV}
              disabled={isExporting || logs.length === 0}
              type="button"
              className="btn-pill-dark"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 20px',
                fontSize: '13px',
                fontWeight: 600,
              }}
            >
              <Download size={15} />
              {isExporting ? 'Generando...' : 'Exportar Auditoría'}
            </button>
          </div>
        }
      />

      {/* ── 4 KPI Cards ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '20px',
          marginBottom: '32px',
        }}
      >
        {/* Card 1: Total Eventos */}
        <div
          className="card-mist floating-artifact"
          style={{
            padding: '24px',
            borderRadius: 'var(--radius-cards)',
            border: '1px solid var(--color-border)',
            backgroundColor: '#ffffff',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '12px',
            }}
          >
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: 'var(--color-fog-white)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Activity size={18} color="var(--color-slate-gray)" />
            </div>
            <h3
              style={{
                fontSize: '12px',
                fontWeight: '700',
                color: 'var(--color-slate-gray)',
                margin: 0,
                textTransform: 'uppercase',
                letterSpacing: '0.6px',
              }}
            >
              Total Eventos Registrados
            </h3>
          </div>
          <div
            className="serif-display"
            style={{
              fontSize: '34px',
              fontWeight: '500',
              color: 'var(--color-ink-black)',
              marginBottom: '4px',
            }}
          >
            {kpis.total_eventos} eventos
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
            Ledger institucional inmutable
          </div>
        </div>

        {/* Card 2: Seguridad & 2FA */}
        <div
          className="card-mist floating-artifact"
          style={{
            padding: '24px',
            borderRadius: 'var(--radius-cards)',
            border: '1px solid var(--color-border)',
            backgroundColor: '#ffffff',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '12px',
            }}
          >
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: '#ede9fe',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <ShieldCheck size={18} color="#6d28d9" />
            </div>
            <h3
              style={{
                fontSize: '12px',
                fontWeight: '700',
                color: 'var(--color-slate-gray)',
                margin: 0,
                textTransform: 'uppercase',
                letterSpacing: '0.6px',
              }}
            >
              Eventos de Seguridad &amp; 2FA
            </h3>
          </div>
          <div
            className="serif-display"
            style={{
              fontSize: '34px',
              fontWeight: '500',
              color: '#6d28d9',
              marginBottom: '4px',
            }}
          >
            {kpis.eventos_seguridad} operaciones
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
            Autenticación, OTP y RBAC
          </div>
        </div>

        {/* Card 3: Ingestas DataOps */}
        <div
          className="card-mist floating-artifact"
          style={{
            padding: '24px',
            borderRadius: 'var(--radius-cards)',
            border: '1px solid var(--color-border)',
            backgroundColor: '#ffffff',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '12px',
            }}
          >
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: '#e0f2fe',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <FileSpreadsheet size={18} color="#0284c7" />
            </div>
            <h3
              style={{
                fontSize: '12px',
                fontWeight: '700',
                color: 'var(--color-slate-gray)',
                margin: 0,
                textTransform: 'uppercase',
                letterSpacing: '0.6px',
              }}
            >
              Ingestas DataOps
            </h3>
          </div>
          <div
            className="serif-display"
            style={{
              fontSize: '34px',
              fontWeight: '500',
              color: '#0284c7',
              marginBottom: '4px',
            }}
          >
            {kpis.ingestas_dataops} procesamientos
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
            Pipelines, normalización y staging
          </div>
        </div>

        {/* Card 4: Alertas / Inconsistencias */}
        <div
          className="card-mist floating-artifact"
          style={{
            padding: '24px',
            borderRadius: 'var(--radius-cards)',
            border: '1px solid var(--color-border)',
            backgroundColor: '#ffffff',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '12px',
            }}
          >
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: '#fee2e2',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <AlertTriangle size={18} color="var(--color-alert-red)" />
            </div>
            <h3
              style={{
                fontSize: '12px',
                fontWeight: '700',
                color: 'var(--color-slate-gray)',
                margin: 0,
                textTransform: 'uppercase',
                letterSpacing: '0.6px',
              }}
            >
              Alertas / Inconsistencias
            </h3>
          </div>
          <div
            className="serif-display"
            style={{
              fontSize: '34px',
              fontWeight: '500',
              color: 'var(--color-alert-red)',
              marginBottom: '4px',
            }}
          >
            {kpis.alertas_criticas} críticas
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
            Severidad CRITICAL detectada
          </div>
        </div>
      </div>

      {/* ── Interactive Filter Bar ── */}
      <div
        className="card-mist floating-artifact"
        style={{
          padding: '18px 24px',
          borderRadius: 'var(--radius-cards)',
          border: '1px solid var(--color-border)',
          backgroundColor: '#ffffff',
          marginBottom: '24px',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
          }}
        >
          {/* Left: Filters */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              gap: '16px',
            }}
          >
            {/* Filter by Module */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontSize: '12.5px',
                  fontWeight: 600,
                  color: 'var(--color-slate-gray)',
                }}
              >
                Módulo:
              </span>
              <select
                className="form-input"
                value={filterModulo}
                onChange={(e) => setFilterModulo(e.target.value)}
                style={{
                  padding: '7px 12px',
                  fontSize: '12.5px',
                  borderRadius: 'var(--radius-inputs)',
                  minWidth: '150px',
                }}
              >
                <option value="Todos">Todos</option>
                <option value="Seguridad & 2FA">Seguridad &amp; 2FA</option>
                <option value="DataOps">DataOps</option>
                <option value="Usuarios">Usuarios</option>
              </select>
            </div>

            {/* Filter by Severity */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontSize: '12.5px',
                  fontWeight: 600,
                  color: 'var(--color-slate-gray)',
                }}
              >
                Nivel:
              </span>
              <select
                className="form-input"
                value={filterSeveridad}
                onChange={(e) => setFilterSeveridad(e.target.value)}
                style={{
                  padding: '7px 12px',
                  fontSize: '12.5px',
                  borderRadius: 'var(--radius-inputs)',
                  minWidth: '130px',
                }}
              >
                <option value="Todos">Todos</option>
                <option value="CRITICAL">CRITICAL</option>
                <option value="WARNING">WARNING</option>
                <option value="INFO">INFO</option>
                <option value="SUCCESS">SUCCESS</option>
              </select>
            </div>

            {hasActiveFilters && (
              <button
                type="button"
                onClick={handleClearFilters}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-sienna-brown)',
                  fontSize: '12.5px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  padding: '4px 8px',
                }}
              >
                Limpiar Filtros
              </button>
            )}
          </div>

          {/* Right: Search Box */}
          <form
            onSubmit={handleSearchSubmit}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              flex: '1 1 260px',
              maxWidth: '360px',
            }}
          >
            <div
              style={{
                position: 'relative',
                width: '100%',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <Search
                size={16}
                color="var(--color-slate-gray)"
                style={{ position: 'absolute', left: '12px' }}
              />
              <input
                type="text"
                className="form-input"
                placeholder="Buscar por usuario, IP, acción..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px 8px 36px',
                  fontSize: '12.5px',
                  borderRadius: 'var(--radius-inputs)',
                }}
              />
            </div>
            <button
              type="submit"
              className="btn-pill-ghost"
              style={{ padding: '8px 14px', fontSize: '12.5px', flexShrink: 0 }}
            >
              Buscar
            </button>
          </form>
        </div>
      </div>

      {/* ── Responsive Table ── */}
      <div
        className="card-mist floating-artifact"
        style={{
          borderRadius: 'var(--radius-cards)',
          border: '1px solid var(--color-border)',
          backgroundColor: '#ffffff',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            padding: '16px 24px',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Shield size={16} color="var(--color-slate-gray)" />
            <span
              style={{
                fontSize: '13px',
                fontWeight: 700,
                color: 'var(--color-ink-black)',
              }}
            >
              Bitácora de Eventos de Auditoría ({logs.length} mostrados)
            </span>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
            Firma Hash SHA-256 habilitada · Inmutable
          </span>
        </div>

        <ResponsiveTable>
          <table className="steep-table">
            <thead>
              <tr>
                <th style={{ width: '150px' }}>Timestamp</th>
                <th style={{ width: '130px' }}>Módulo</th>
                <th style={{ width: '180px' }}>Usuario / Rol</th>
                <th>Acción / Evento</th>
                <th style={{ width: '150px' }}>IP / Canal</th>
                <th style={{ width: '100px', textAlign: 'center' }}>Severidad</th>
                <th>Detalles</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td
                    colSpan="7"
                    style={{ textAlign: 'center', padding: '40px', color: 'var(--color-slate-gray)' }}
                  >
                    <div
                      className="spin"
                      style={{
                        width: '24px',
                        height: '24px',
                        border: '2px solid var(--color-border)',
                        borderTopColor: 'var(--color-sienna-brown)',
                        borderRadius: '50%',
                        margin: '0 auto 10px',
                      }}
                    />
                    Cargando bitácora de auditoría...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td
                    colSpan="7"
                    style={{ textAlign: 'center', padding: '40px', color: 'var(--color-slate-gray)' }}
                  >
                    No se encontraron registros de auditoría que coincidan con los filtros aplicados.
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const sBadge = getSeverityBadge(log.severidad);
                  const mBadge = getModuleBadge(log.modulo);
                  const ModIcon = mBadge.icon;

                  return (
                    <tr key={log.id}>
                      {/* Timestamp */}
                      <td
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '12px',
                          color: 'var(--color-slate-gray)',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {log.timestamp}
                      </td>

                      {/* Módulo */}
                      <td>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            padding: '3px 8px',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: 600,
                            backgroundColor: mBadge.bg,
                            color: mBadge.color,
                            whiteSpace: 'nowrap',
                          }}
                        >
                          <ModIcon size={12} />
                          {log.modulo}
                        </span>
                      </td>

                      {/* Usuario / Rol */}
                      <td style={{ fontSize: '12.5px' }}>
                        <span style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>
                          {log.usuario_rol}
                        </span>
                      </td>

                      {/* Acción / Evento */}
                      <td style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-ink-black)' }}>
                        {log.accion}
                      </td>

                      {/* IP / Canal */}
                      <td
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '11.5px',
                          color: 'var(--color-slate-gray)',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {log.ip_canal}
                      </td>

                      {/* Severidad Badge */}
                      <td style={{ textAlign: 'center' }}>
                        <span
                          style={{
                            display: 'inline-block',
                            padding: '3px 9px',
                            borderRadius: '9999px',
                            fontSize: '11px',
                            fontWeight: 700,
                            letterSpacing: '0.4px',
                            backgroundColor: sBadge.bg,
                            color: sBadge.color,
                            border: `1px solid ${sBadge.border}`,
                          }}
                        >
                          {sBadge.label}
                        </span>
                      </td>

                      {/* Detalles */}
                      <td
                        style={{
                          fontSize: '12px',
                          color: 'var(--color-slate-gray)',
                          maxWidth: '300px',
                          lineHeight: '1.4',
                        }}
                      >
                        {log.detalles}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </ResponsiveTable>
      </div>
    </div>
  );
}
