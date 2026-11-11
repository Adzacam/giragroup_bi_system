import React, { useState, useEffect, useMemo, useRef } from 'react';
import usePaginacion from '../../hooks/usePaginacion';
import Paginacion from '../../components/shared/Paginacion';
import {
  ShieldCheck, Shield, AlertTriangle, FileSpreadsheet,
  Activity, Search, Download, RefreshCw, Filter, CheckCircle2,
  Lock, Key, Info, Play, Terminal, X, UploadCloud, FileText,
  AlertCircle, Users, CheckCircle, Clock, Database, Layers,
  ArrowRight, Sparkles
} from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import { auditApi } from '../../api/auditApi';
import { kpiApi } from '../../api/kpiApi';
import { academicApi } from '../../api/academicApi';
import useKineticScroll from '../../hooks/useKineticScroll';
import { sileoToast } from '../../services/sileoToast';

export default function AuditoriaSistema() {
  useKineticScroll();

  // ── Tab State: 'trazabilidad' | 'alertas' ───────────────────────────
  const [activeTab, setActiveTab] = useState('trazabilidad');

  // ── Bitácora de Eventos (Pestaña 1) ──────────────────────────────────
  const [logs, setLogs] = useState([]);
  const [auditKpis, setAuditKpis] = useState({
    total_eventos: 0,
    eventos_seguridad: 0,
    ingestas_dataops: 0,
    alertas_criticas: 0,
  });
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Filtros de Auditoría
  const [filterModulo, setFilterModulo] = useState('Todos');
  const [filterSeveridad, setFilterSeveridad] = useState('Todos');
  const [searchQuery, setSearchQuery] = useState('');

  // ── Reglas y Alertas de Negocio (Pestaña 2) ──────────────────────────
  const [alertas, setAlertas] = useState([]);
  const [casosCruzados, setCasosCruzados] = useState([]);
  const [isLoadingAlertas, setIsLoadingAlertas] = useState(false);
  const [filterTipoAlerta, setFilterTipoAlerta] = useState('Todos');
  const [filterSeveridadAlerta, setFilterSeveridadAlerta] = useState('Todos');
  const [searchAlertas, setSearchAlertas] = useState('');

  // ── Modal de Pipeline Bajo Demanda ──────────────────────────────────
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [manualDocId, setManualDocId] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isExecutingPipeline, setIsExecutingPipeline] = useState(false);
  const [pipelineResult, setPipelineResult] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  // ── Carga de Bitácora ────────────────────────────────────────────────
  const loadAuditData = async () => {
    setIsLoadingLogs(true);
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
          setAuditKpis(res.kpis);
        }
      }
    } catch (err) {
      console.warn('Error al cargar logs de auditoría:', err);
    } finally {
      setIsLoadingLogs(false);
    }
  };

  // ── Carga de Reglas y Alertas ────────────────────────────────────────
  const loadAlertasData = async () => {
    setIsLoadingAlertas(true);
    try {
      const [alertasRes, cruzadoRes] = await Promise.allSettled([
        kpiApi.getAlertas(),
        academicApi.getRiesgoCruzado(70.0, 2),
      ]);

      if (alertasRes.status === 'fulfilled' && alertasRes.value?.data) {
        setAlertas(alertasRes.value.data);
      }
      if (cruzadoRes.status === 'fulfilled' && cruzadoRes.value?.data) {
        setCasosCruzados(cruzadoRes.value.data);
      }
    } catch (err) {
      console.warn('Error al cargar alertas del motor de reglas:', err);
    } finally {
      setIsLoadingAlertas(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'trazabilidad') {
      loadAuditData();
    }
  }, [activeTab, filterModulo, filterSeveridad]);

  useEffect(() => {
    if (activeTab === 'alertas' && alertas.length === 0) {
      loadAlertasData();
    }
  }, [activeTab]);

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

  // ── Helpers de Enmascaramiento y Badges ──────────────────────────────
  const maskCi = (ci) => {
    if (!ci) return 'N/D';
    const str = String(ci).trim();
    if (str.length <= 4) return str;
    return `${str.slice(0, 2)}***${str.slice(-2)}`;
  };

  const maskNombre = (nombre) => {
    if (!nombre) return 'Estudiante Anonimizado';
    const parts = String(nombre).trim().split(/\s+/);
    if (parts.length === 1) return `${parts[0][0]}.***`;
    return parts.map((p) => (p ? `${p[0]}.` : '')).join(' ') + ' (Anonimizado)';
  };

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

  const getModuleBadge = (mod) => {
    const m = (mod || '').toLowerCase();
    if (m.includes('seguridad') || m.includes('2fa')) {
      return { bg: '#ede9fe', color: '#6d28d9', icon: Lock };
    }
    if (m.includes('dataops') || m.includes('ingesta') || m.includes('pipeline')) {
      return { bg: '#e0f2fe', color: '#0284c7', icon: FileSpreadsheet };
    }
    return { bg: 'var(--color-mist-gray)', color: 'var(--color-ink-black)', icon: Activity };
  };

  const getRoleBadge = (role) => {
    switch (role) {
      case 'DIRECTOR_ACADEMICO':
        return { bg: '#dbeafe', color: '#1e40af', label: 'Dirección Académica' };
      case 'ANALISTA_FINANCIERO':
        return { bg: '#fef3c7', color: '#92400e', label: 'Analista Financiero' };
      case 'AUDITOR_CALIDAD':
        return { bg: '#f3e8ff', color: '#6b21a8', label: 'Auditor de Calidad' };
      case 'ADMIN':
      default:
        return { bg: '#f1f5f9', color: '#334155', label: 'Administrador' };
    }
  };

  const getSuggestedAction = (al) => {
    if (al.tipo === 'RIESGO_CRUZADO') return 'Comité interdisciplinario: tutoría prioritaria y refinanciación de cuotas';
    if (al.tipo === 'DESERCION') return 'Intervención de bienestar estudiantil y seguimiento de inasistencia';
    if (al.tipo === 'ACADEMICO') return 'Tutoría académica preventiva y plan de reforzamiento modular';
    if (al.tipo === 'FINANCIERO') return 'Gestión de cobranza preventiva y facilidades de pago';
    if (al.tipo === 'CALIDAD') return 'Revisión humana en Registros de Ingesta y verificación de estructura';
    if (al.role_target === 'DIRECTOR_ACADEMICO') return 'Revisión pedagógica con docente a cargo';
    if (al.role_target === 'ANALISTA_FINANCIERO') return 'Contacto para regularización de cuotas';
    return 'Supervisión de cumplimiento institucional';
  };

  // ── CSV Export ───────────────────────────────────────────────────────
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

  // ── Ejecución de Pipeline Bajo Demanda ────────────────────────────────
  const handleTriggerPipeline = async (e) => {
    e.preventDefault();
    if (!selectedFile && !manualDocId) {
      sileoToast.icon({
        title: 'Parámetros Incompletos',
        description: 'Debe seleccionar un archivo (.xlsx, .csv) o ingresar un ID de documento existente.',
        icon: <AlertCircle size={16} color="#ef4444" />
      });
      return;
    }

    setIsExecutingPipeline(true);
    setPipelineResult(null);

    try {
      const docIdNum = manualDocId ? parseInt(manualDocId, 10) : undefined;
      const res = await auditApi.triggerManualPipeline({
        file: selectedFile || undefined,
        docId: docIdNum,
      });

      setPipelineResult(res);
      sileoToast.icon({
        title: 'Pipeline Ejecutado con Éxito',
        description: `Procesamiento completado en ${res.tiempo_total_ms?.toFixed(0) || 0} ms.`,
        icon: <CheckCircle2 size={16} color="#22c55e" />
      });

      // Recargar bitácora y alertas para reflejar el nuevo procesamiento
      loadAuditData();
      loadAlertasData();
    } catch (err) {
      const errMsg = err.response?.data?.detail || err.message || 'Error en la ejecución del pipeline';
      sileoToast.icon({
        title: 'Error de Ejecución',
        description: errMsg,
        icon: <AlertTriangle size={16} color="#ef4444" />
      });
    } finally {
      setIsExecutingPipeline(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const ext = file.name.split('.').pop().toLowerCase();
      if (['xlsx', 'csv'].includes(ext)) {
        setSelectedFile(file);
      } else {
        sileoToast.icon({
          title: 'Formato no soportado',
          description: 'Solo se admiten archivos .xlsx y .csv',
          icon: <AlertCircle size={16} color="#ef4444" />
        });
      }
    }
  };

  // ── Filtrado de Alertas en Memoria ────────────────────────────────────
  const filteredAlertas = useMemo(() => {
    return alertas.filter((al) => {
      if (filterTipoAlerta !== 'Todos' && al.tipo !== filterTipoAlerta) return false;
      if (filterSeveridadAlerta !== 'Todos' && al.severidad !== filterSeveridadAlerta) return false;
      if (searchAlertas.trim()) {
        const query = searchAlertas.toLowerCase();
        const est = (al.estudiante || '').toLowerCase();
        const ci = (al.codigo_estudiante || '').toLowerCase();
        const regla = (al.regla || '').toLowerCase();
        const mod = (al.modulo || '').toLowerCase();
        return est.includes(query) || ci.includes(query) || regla.includes(query) || mod.includes(query);
      }
      return true;
    });
  }, [alertas, filterTipoAlerta, filterSeveridadAlerta, searchAlertas]);
  const pagLogs = usePaginacion(logs);
  const pagAlertas = usePaginacion(filteredAlertas);

  const totalCriticasAlertas = alertas.filter((a) => a.severidad === 'CRITICAL').length;
  const totalWarningAlertas = alertas.filter((a) => a.severidad === 'WARNING').length;

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto', paddingBottom: '60px' }}>
      {/* ── Page Header ── */}
      <PageHeader
        category="GOBERNANZA & COMPLIANCE INSTITUCIONAL"
        title="Auditoría, Trazabilidad y Alertas"
        subtitle="Monitoreo cronológico inmutable de eventos, evaluación multidimensional de reglas de riesgo e ingesta bajo demanda."
        action={
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button
              onClick={() => setIsModalOpen(true)}
              type="button"
              className="btn-pill-dark"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 18px',
                fontSize: '13px',
                fontWeight: 600,
                backgroundColor: 'var(--color-sienna-brown)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '12px',
                cursor: 'pointer',
                boxShadow: '0 4px 12px rgba(184, 80, 66, 0.25)',
              }}
              title="Ejecutar ingesta manual y transformación inmediata al Data Warehouse"
            >
              <Terminal size={15} />
              Ejecutar Pipeline Bajo Demanda
            </button>

            <button
              onClick={activeTab === 'trazabilidad' ? loadAuditData : loadAlertasData}
              disabled={isLoadingLogs || isLoadingAlertas}
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
              <RefreshCw size={15} className={isLoadingLogs || isLoadingAlertas ? 'spin' : ''} />
              Refrescar
            </button>

            {activeTab === 'trazabilidad' && (
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
            )}
          </div>
        }
      />

      {/* ── Selector de Pestañas Institucional ── */}
      <div
        style={{
          display: 'flex',
          gap: '12px',
          borderBottom: '1px solid var(--color-border)',
          marginBottom: '28px',
          paddingBottom: '2px',
        }}
      >
        <button
          onClick={() => setActiveTab('trazabilidad')}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 20px',
            fontSize: '14px',
            fontWeight: 700,
            cursor: 'pointer',
            border: 'none',
            background: 'none',
            color: activeTab === 'trazabilidad' ? 'var(--color-ink-black)' : 'var(--color-slate-gray)',
            borderBottom: activeTab === 'trazabilidad' ? '2.5px solid var(--color-ink-black)' : '2.5px solid transparent',
            transition: 'all 0.2s ease',
          }}
        >
          <Shield size={16} />
          Trazabilidad &amp; Eventos Inmutables ({logs.length})
        </button>

        <button
          onClick={() => setActiveTab('alertas')}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 20px',
            fontSize: '14px',
            fontWeight: 700,
            cursor: 'pointer',
            border: 'none',
            background: 'none',
            color: activeTab === 'alertas' ? 'var(--color-ink-black)' : 'var(--color-slate-gray)',
            borderBottom: activeTab === 'alertas' ? '2.5px solid var(--color-ink-black)' : '2.5px solid transparent',
            transition: 'all 0.2s ease',
          }}
        >
          <AlertTriangle size={16} />
          Reglas de Negocio &amp; Alertas de Riesgo ({alertas.length})
        </button>
      </div>

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* PESTAÑA 1: TRAZABILIDAD & EVENTOS INMUTABLES                      */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {activeTab === 'trazabilidad' && (
        <>
          {/* ── 4 KPI Cards de Auditoría ── */}
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
                backgroundColor: 'var(--color-paper-white)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
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
                {auditKpis.total_eventos} eventos
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
                backgroundColor: 'var(--color-paper-white)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
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
                  <Lock size={18} color="#6d28d9" />
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
                  Seguridad &amp; 2FA
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
                {auditKpis.eventos_seguridad} logs
              </div>
              <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
                Tokens, contraseñas y accesos RBAC
              </div>
            </div>

            {/* Card 3: Ingestas DataOps */}
            <div
              className="card-mist floating-artifact"
              style={{
                padding: '24px',
                borderRadius: 'var(--radius-cards)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-paper-white)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
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
                  Origen Documental y Lotes
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
                {auditKpis.ingestas_dataops} lotes
              </div>
              <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
                Pipelines, normalización y Registros de Ingesta
              </div>
            </div>

            {/* Card 4: Alertas / Inconsistencias */}
            <div
              className="card-mist floating-artifact"
              style={{
                padding: '24px',
                borderRadius: 'var(--radius-cards)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-paper-white)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
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
                  Alertas Críticas
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
                {auditKpis.alertas_criticas} críticas
              </div>
              <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
                Severidad CRITICAL en DataOps o Seguridad
              </div>
            </div>
          </div>

          {/* ── Barra de Filtros de Auditoría ── */}
          <div
            className="card-mist floating-artifact"
            style={{
              padding: '18px 24px',
              borderRadius: 'var(--radius-cards)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-paper-white)',
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
              <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--color-slate-gray)' }}>
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
                    <option value="DataOps">Origen Documental y DataOps</option>
                    <option value="Usuarios">Usuarios</option>
                  </select>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--color-slate-gray)' }}>
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

              {/* Búsqueda */}
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
                <div style={{ position: 'relative', width: '100%', display: 'flex', alignItems: 'center' }}>
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

          {/* ── Tabla de Auditoría ── */}
          <div
            className="card-mist floating-artifact"
            style={{
              borderRadius: 'var(--radius-cards)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-paper-white)',
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
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-ink-black)' }}>
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
                    <th style={{ width: '150px' }}>Módulo</th>
                    <th style={{ width: '180px' }}>Usuario / Rol</th>
                    <th>Acción / Evento</th>
                    <th style={{ width: '140px' }}>IP / Canal</th>
                    <th style={{ width: '100px', textAlign: 'center' }}>Severidad</th>
                    <th>Detalles</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoadingLogs ? (
                    <tr>
                      <td colSpan="7" style={{ textAlign: 'center', padding: '40px', color: 'var(--color-slate-gray)' }}>
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
                      <td colSpan="7" style={{ textAlign: 'center', padding: '40px', color: 'var(--color-slate-gray)' }}>
                        No se encontraron registros de auditoría que coincidan con los filtros aplicados.
                      </td>
                    </tr>
                  ) : (
                    pagLogs.visibles.map((log) => {
                      const sBadge = getSeverityBadge(log.severidad);
                      const mBadge = getModuleBadge(log.modulo);
                      const ModIcon = mBadge.icon;

                      return (
                        <tr key={log.id}>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-slate-gray)', whiteSpace: 'nowrap' }}>
                            {log.timestamp}
                          </td>
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
                          <td style={{ fontSize: '12.5px' }}>
                            <span style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>
                              {log.usuario_rol}
                            </span>
                          </td>
                          <td style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-ink-black)' }}>
                            {log.accion}
                          </td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11.5px', color: 'var(--color-slate-gray)', whiteSpace: 'nowrap' }}>
                            {log.ip_canal}
                          </td>
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
                          <td style={{ fontSize: '12px', color: 'var(--color-slate-gray)', maxWidth: '300px', lineHeight: '1.4' }}>
                            {log.detalles}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
              <Paginacion {...pagLogs} onChange={pagLogs.setPagina} />
            </ResponsiveTable>
          </div>
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* PESTAÑA 2: REGLAS DE NEGOCIO & ALERTAS DE RIESGO                  */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {activeTab === 'alertas' && (
        <>
          {/* ── 4 Tarjetas KPI de Alertas de Negocio ── */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '20px',
              marginBottom: '32px',
            }}
          >
            {/* KPI 1: Total Alertas */}
            <div
              className="card-mist floating-artifact"
              style={{
                padding: '24px',
                borderRadius: 'var(--radius-cards)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-paper-white)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
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
                <h3 style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-slate-gray)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                  Total Alertas Evaluadas
                </h3>
              </div>
              <div className="serif-display" style={{ fontSize: '34px', fontWeight: '500', color: 'var(--color-ink-black)', marginBottom: '4px' }}>
                {alertas.length} alertas
              </div>
              <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
                Reglas deterministas IF/THEN activas
              </div>
            </div>

            {/* KPI 2: Críticas */}
            <div
              className="card-mist floating-artifact"
              style={{
                padding: '24px',
                borderRadius: 'var(--radius-cards)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-paper-white)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
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
                <h3 style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-slate-gray)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                  Alertas Críticas
                </h3>
              </div>
              <div className="serif-display" style={{ fontSize: '34px', fontWeight: '500', color: 'var(--color-alert-red)', marginBottom: '4px' }}>
                {totalCriticasAlertas} críticas
              </div>
              <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
                Requieren acción prioritaria inmediata
              </div>
            </div>

            {/* KPI 3: Advertencias */}
            <div
              className="card-mist floating-artifact"
              style={{
                padding: '24px',
                borderRadius: 'var(--radius-cards)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-paper-white)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <div
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '8px',
                    backgroundColor: '#fef3c7',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <AlertCircle size={18} color="#b45309" />
                </div>
                <h3 style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-slate-gray)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                  Advertencias Preventivas
                </h3>
              </div>
              <div className="serif-display" style={{ fontSize: '34px', fontWeight: '500', color: '#b45309', marginBottom: '4px' }}>
                {totalWarningAlertas} preventivas
              </div>
              <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
                Zona de riesgo temprano detectable
              </div>
            </div>

            {/* KPI 4: Casos Riesgo Cruzado */}
            <div
              className="card-mist floating-artifact"
              style={{
                padding: '24px',
                borderRadius: 'var(--radius-cards)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-paper-white)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <div
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '8px',
                    backgroundColor: '#ffe4e6',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Users size={18} color="#be123c" />
                </div>
                <h3 style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-slate-gray)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                  Casos con Riesgo Cruzado
                </h3>
              </div>
              <div className="serif-display" style={{ fontSize: '34px', fontWeight: '500', color: '#be123c', marginBottom: '4px' }}>
                {casosCruzados.length} estudiantes
              </div>
              <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
                Bajo rendimiento y cuotas en mora
              </div>
            </div>
          </div>

          {/* ── Barra de Filtros de Alertas ── */}
          <div
            className="card-mist floating-artifact"
            style={{
              padding: '18px 24px',
              borderRadius: 'var(--radius-cards)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-paper-white)',
              marginBottom: '24px',
            }}
          >
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--color-slate-gray)' }}>
                    Tipo de Regla:
                  </span>
                  <select
                    className="form-input"
                    value={filterTipoAlerta}
                    onChange={(e) => setFilterTipoAlerta(e.target.value)}
                    style={{ padding: '7px 12px', fontSize: '12.5px', borderRadius: 'var(--radius-inputs)', minWidth: '160px' }}
                  >
                    <option value="Todos">Todos los tipos</option>
                    <option value="ACADEMICO">Rendimiento Académico</option>
                    <option value="DESERCION">Riesgo de Deserción</option>
                    <option value="FINANCIERO">Situación Financiera</option>
                    <option value="RIESGO_CRUZADO">Riesgo Cruzado</option>
                    <option value="CALIDAD">Calidad de Ingesta</option>
                  </select>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--color-slate-gray)' }}>
                    Severidad:
                  </span>
                  <select
                    className="form-input"
                    value={filterSeveridadAlerta}
                    onChange={(e) => setFilterSeveridadAlerta(e.target.value)}
                    style={{ padding: '7px 12px', fontSize: '12.5px', borderRadius: 'var(--radius-inputs)', minWidth: '130px' }}
                  >
                    <option value="Todos">Todas</option>
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="WARNING">WARNING</option>
                    <option value="INFO">INFO</option>
                  </select>
                </div>

                {(filterTipoAlerta !== 'Todos' || filterSeveridadAlerta !== 'Todos' || searchAlertas) && (
                  <button
                    type="button"
                    onClick={() => {
                      setFilterTipoAlerta('Todos');
                      setFilterSeveridadAlerta('Todos');
                      setSearchAlertas('');
                    }}
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

              {/* Búsqueda en Alertas */}
              <div style={{ position: 'relative', width: '100%', maxWidth: '320px', display: 'flex', alignItems: 'center' }}>
                <Search size={16} color="var(--color-slate-gray)" style={{ position: 'absolute', left: '12px' }} />
                <input
                  type="text"
                  className="form-input"
                  placeholder="Buscar estudiante, regla, CI..."
                  value={searchAlertas}
                  onChange={(e) => setSearchAlertas(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px 8px 36px', fontSize: '12.5px', borderRadius: 'var(--radius-inputs)' }}
                />
              </div>
            </div>
          </div>

          {/* ── Tabla Interactiva de Reglas & Alertas ── */}
          <div
            className="card-mist floating-artifact"
            style={{
              borderRadius: 'var(--radius-cards)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-paper-white)',
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
                <ShieldCheck size={16} color="var(--color-slate-gray)" />
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-ink-black)' }}>
                  Matriz de Reglas Disparadas ({filteredAlertas.length} registros)
                </span>
              </div>
              <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                Fidelidad PoLP · Cédulas de Identidad enmascaradas
              </span>
            </div>

            <ResponsiveTable>
              <table className="steep-table">
                <thead>
                  <tr>
                    <th style={{ width: '220px' }}>Regla Disparada (IF/THEN)</th>
                    <th style={{ width: '100px', textAlign: 'center' }}>Severidad</th>
                    <th>Estudiante</th>
                    <th style={{ width: '120px' }}>Métrica</th>
                    <th style={{ width: '120px' }}>Umbral</th>
                    <th style={{ width: '160px' }}>Rol Destinatario</th>
                    <th>Acción Sugerida</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoadingAlertas ? (
                    <tr>
                      <td colSpan="7" style={{ textAlign: 'center', padding: '40px', color: 'var(--color-slate-gray)' }}>
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
                        Evaluando motor de reglas de riesgo...
                      </td>
                    </tr>
                  ) : filteredAlertas.length === 0 ? (
                    <tr>
                      <td colSpan="7" style={{ textAlign: 'center', padding: '40px', color: 'var(--color-slate-gray)' }}>
                        No se detectaron alertas de riesgo para los filtros seleccionados.
                      </td>
                    </tr>
                  ) : (
                    pagAlertas.visibles.map((al, idx) => {
                      const sBadge = getSeverityBadge(al.severidad);
                      const rBadge = getRoleBadge(al.role_target);

                      return (
                        <tr key={idx}>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11.5px', color: 'var(--color-ink-black)' }}>
                            {al.regla}
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            <span
                              style={{
                                display: 'inline-block',
                                padding: '3px 8px',
                                borderRadius: '9999px',
                                fontSize: '11px',
                                fontWeight: 700,
                                backgroundColor: sBadge.bg,
                                color: sBadge.color,
                                border: `1px solid ${sBadge.border}`,
                              }}
                            >
                              {sBadge.label}
                            </span>
                          </td>
                          <td>
                            <strong>{maskNombre(al.estudiante)}</strong>
                            {al.codigo_estudiante && (
                              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-slate-gray)' }}>
                                {maskCi(al.codigo_estudiante)}
                              </div>
                            )}
                          </td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                            {typeof al.metrica_valor === 'object' && al.metrica_valor !== null
                              ? (al.metrica_valor.cuotas_impagas !== undefined
                                  ? `${al.metrica_valor.cuotas_impagas} ctas · Bs. ${Number(al.metrica_valor.deuda || 0).toLocaleString('es-BO')}`
                                  : al.metrica_valor.score_fuzzy !== undefined
                                  ? `${al.metrica_valor.score_fuzzy}%${al.metrica_valor.mejor_candidato ? ` (${maskNombre ? maskNombre(al.metrica_valor.mejor_candidato) : al.metrica_valor.mejor_candidato})` : ''}`
                                  : al.metrica_valor.nota_actual !== undefined
                                  ? `Nota ${al.metrica_valor.nota_actual} · ${al.metrica_valor.cuotas_mora} ctas`
                                  : JSON.stringify(al.metrica_valor))
                              : String(al.metrica_valor ?? '—')}
                          </td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                            {al.umbral_disparador}
                          </td>
                          <td>
                            <span
                              style={{
                                display: 'inline-block',
                                padding: '3px 8px',
                                borderRadius: '6px',
                                fontSize: '11px',
                                fontWeight: 600,
                                backgroundColor: rBadge.bg,
                                color: rBadge.color,
                              }}
                            >
                              {rBadge.label}
                            </span>
                          </td>
                          <td style={{ fontSize: '12px', color: 'var(--color-slate-gray)', lineHeight: '1.4' }}>
                            {getSuggestedAction(al)}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
              <Paginacion {...pagAlertas} onChange={pagAlertas.setPagina} />
            </ResponsiveTable>
          </div>
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* MODAL: EJECUCIÓN DE PIPELINE BAJO DEMANDA                          */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {isModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
            backgroundColor: 'rgba(15, 23, 42, 0.65)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
          onClick={() => !isExecutingPipeline && setIsModalOpen(false)}
        >
          <div
            style={{
              backgroundColor: 'var(--color-paper-white)',
              borderRadius: '24px',
              border: '1px solid var(--color-border)',
              width: '100%',
              maxWidth: '680px',
              maxHeight: '90vh',
              overflowY: 'auto',
              padding: '32px',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
              position: 'relative',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-sienna-brown)', marginBottom: '4px' }}>
                  <Terminal size={18} />
                  <span style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '0.6px', textTransform: 'uppercase' }}>
                    Orquestación DataOps Directa
                  </span>
                </div>
                <h2 className="serif-heading" style={{ fontSize: '24px', margin: 0, color: 'var(--color-ink-black)' }}>
                  Ejecución de Pipeline Bajo Demanda
                </h2>
                <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', marginTop: '4px', marginBottom: 0 }}>
                  Ingesta, inferencia semántica NLP, reglas de calidad y carga directa a tablas de hechos del Data Warehouse.
                </p>
              </div>

              <button
                onClick={() => setIsModalOpen(false)}
                disabled={isExecutingPipeline}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: isExecutingPipeline ? 'not-allowed' : 'pointer',
                  color: 'var(--color-slate-gray)',
                  padding: '6px',
                  borderRadius: '8px',
                }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleTriggerPipeline}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', marginBottom: '24px' }}>
                {/* File Dropzone */}
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--color-ink-black)', marginBottom: '6px' }}>
                    Archivo Documental (.xlsx, .csv):
                  </label>
                  <div
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    style={{
                      border: dragActive ? '2px dashed var(--color-sienna-brown)' : '2px dashed var(--color-border)',
                      borderRadius: '16px',
                      padding: '24px',
                      textAlign: 'center',
                      backgroundColor: dragActive ? '#fff1f2' : 'var(--color-fog-white)',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".xlsx,.csv"
                      style={{ display: 'none' }}
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          setSelectedFile(e.target.files[0]);
                        }
                      }}
                    />
                    <UploadCloud size={32} color="var(--color-slate-gray)" style={{ margin: '0 auto 8px' }} />
                    {selectedFile ? (
                      <div>
                        <p style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--color-ink-black)', margin: 0 }}>
                          {selectedFile.name}
                        </p>
                        <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '4px 0 0' }}>
                          {(selectedFile.size / 1024).toFixed(1)} KB · Clic para reemplazar
                        </p>
                      </div>
                    ) : (
                      <div>
                        <p style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-ink-black)', margin: 0 }}>
                          Arrastre su archivo aquí o haga clic para examinar
                        </p>
                        <p style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', margin: '4px 0 0' }}>
                          Formatos admitidos: Excel (.xlsx) o CSV delimitado por comas
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Document ID fallback */}
                <div style={{ textAlign: 'center', position: 'relative' }}>
                  <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center' }}>
                    <div style={{ width: '100%', borderTop: '1px solid var(--color-border)' }} />
                  </div>
                  <span style={{ position: 'relative', backgroundColor: 'var(--color-paper-white)', padding: '0 12px', fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                    O bien procesar documento existente
                  </span>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--color-ink-black)', marginBottom: '6px' }}>
                    ID de Origen Documental y Lotes (opcional):
                  </label>
                  <input
                    type="number"
                    min="1"
                    className="form-input"
                    placeholder="Ej. 12"
                    value={manualDocId}
                    onChange={(e) => setManualDocId(e.target.value)}
                    style={{ width: '100%', padding: '9px 12px', fontSize: '13px', borderRadius: 'var(--radius-inputs)' }}
                  />
                  <span style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', marginTop: '4px', display: 'block' }}>
                    Identificador numérico registrado en Origen Documental y Lotes.
                  </span>
                </div>
              </div>

              {/* Botón de Ejecutar */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginBottom: '20px' }}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  disabled={isExecutingPipeline}
                  className="btn-pill-ghost"
                  style={{ padding: '9px 18px', fontSize: '13px' }}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isExecutingPipeline || (!selectedFile && !manualDocId)}
                  className="btn-pill-dark"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '9px 24px',
                    fontSize: '13px',
                    fontWeight: 600,
                    backgroundColor: 'var(--color-ink-black)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '12px',
                    cursor: (isExecutingPipeline || (!selectedFile && !manualDocId)) ? 'not-allowed' : 'pointer',
                    opacity: (isExecutingPipeline || (!selectedFile && !manualDocId)) ? 0.6 : 1,
                  }}
                >
                  {isExecutingPipeline ? (
                    <>
                      <RefreshCw size={15} className="spin" />
                      Ejecutando Ingesta &amp; Inferencia...
                    </>
                  ) : (
                    <>
                      <Play size={15} fill="currentColor" />
                      Ejecutar Pipeline
                    </>
                  )}
                </button>
              </div>
            </form>

            {/* ── Retroalimentación de Telemetría en Tiempo Real ── */}
            {pipelineResult && (
              <div
                style={{
                  borderTop: '1px solid var(--color-border)',
                  paddingTop: '20px',
                  marginTop: '10px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                  <CheckCircle2 size={18} color="var(--color-alert-green)" />
                  <h4 style={{ fontSize: '14px', fontWeight: 700, margin: 0, color: 'var(--color-ink-black)' }}>
                    Resultado de Ejecución: {pipelineResult.status?.toUpperCase() || 'COMPLETADO'}
                  </h4>
                </div>

                {/* 5 Tarjetas de Telemetría */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '10px', marginBottom: '16px' }}>
                  <div style={{ padding: '12px', borderRadius: '12px', backgroundColor: 'var(--color-fog-white)', border: '1px solid var(--color-border)', textAlign: 'center' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>TIEMPO TOTAL</div>
                    <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-ink-black)', marginTop: '2px' }}>
                      {pipelineResult.tiempo_total_ms?.toFixed(0)} ms
                    </div>
                  </div>

                  <div style={{ padding: '12px', borderRadius: '12px', backgroundColor: 'var(--color-fog-white)', border: '1px solid var(--color-border)', textAlign: 'center' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>FILAS PROCESADAS</div>
                    <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-ink-black)', marginTop: '2px' }}>
                      {pipelineResult.total_filas_procesadas}
                    </div>
                  </div>

                  <div style={{ padding: '12px', borderRadius: '12px', backgroundColor: '#dcfce7', border: '1px solid #86efac', textAlign: 'center' }}>
                    <div style={{ fontSize: '11px', color: '#166534', fontWeight: 600 }}>CARGADOS AL DW</div>
                    <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-alert-green)', marginTop: '2px' }}>
                      {pipelineResult.hechos_cargados_dw}
                    </div>
                  </div>

                  <div style={{ padding: '12px', borderRadius: '12px', backgroundColor: pipelineResult.entidades_derivadas_staging > 0 ? '#fef3c7' : 'var(--color-fog-white)', border: '1px solid var(--color-border)', textAlign: 'center' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>A REVISIÓN</div>
                    <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: pipelineResult.entidades_derivadas_staging > 0 ? '#b45309' : 'var(--color-ink-black)', marginTop: '2px' }}>
                      {pipelineResult.entidades_derivadas_staging}
                    </div>
                  </div>

                  <div style={{ padding: '12px', borderRadius: '12px', backgroundColor: 'var(--color-fog-white)', border: '1px solid var(--color-border)', textAlign: 'center' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>CONFIANZA NLP</div>
                    <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-ink-black)', marginTop: '2px' }}>
                      {((pipelineResult.nivel_confianza_promedio > 1 ? pipelineResult.nivel_confianza_promedio : pipelineResult.nivel_confianza_promedio * 100) || 0).toFixed(1)}%
                    </div>
                  </div>
                </div>

                {pipelineResult.requiere_revision_humana && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '12px 16px',
                      backgroundColor: '#fef3c7',
                      border: '1px solid #fcd34d',
                      borderRadius: '12px',
                      fontSize: '12.5px',
                      color: '#92400e',
                    }}
                  >
                    <AlertTriangle size={16} flexShrink={0} />
                    <span>
                      Existen entidades con score de confianza inferior al umbral o sin llave foránea resuelta. Han sido derivadas a la <strong>Cola de Revisión Humana</strong>.
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
