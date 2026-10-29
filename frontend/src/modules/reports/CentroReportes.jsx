import React, { useState, useEffect } from 'react';
import {
  FileSpreadsheet, FileText, Download, Shield, ShieldAlert,
  Clock, CheckCircle2, AlertTriangle, Filter, RefreshCw,
  Building2, Layers, UserCheck, Sparkles, Database
} from 'lucide-react';
import { sileoToast } from '../../services/sileoToast';
import { useAuth } from '../../context/AuthContext';
import { reportesApi } from '../../api/reportesApi';

const TIPOS_REPORTE = [
  {
    id: 'kpis',
    titulo: 'Cuadro de Mando Integral (CMI)',
    subtitulo: 'Indicadores estratégicos de las 4 perspectivas según alcance RBAC',
    icono: Layers,
    color: '#2563EB',
    badge: 'ESTRATÉGICO',
  },
  {
    id: 'alertas',
    titulo: 'Alertas Tempranas',
    subtitulo: 'Casos estudiantiles con umbrales críticos de notas y asistencia',
    icono: AlertTriangle,
    color: '#D97706',
    badge: 'OPERATIVO',
  },
  {
    id: 'cierre',
    titulo: 'Cierre de Gestión y Rendimiento',
    subtitulo: 'Matrícula consolidada, recaudación y ticket promedio por programa',
    icono: Building2,
    color: '#059669',
    badge: 'CONSOLIDADO',
  },
];

const FORMATOS = [
  {
    id: 'xlsx',
    nombre: 'Microsoft Excel (.xlsx)',
    descripcion: 'Libro de cálculo estructurado con estilos y cabeceras oficiales',
    icono: FileSpreadsheet,
    color: '#16A34A',
  },
  {
    id: 'pdf',
    nombre: 'Documento PDF (.pdf)',
    descripcion: 'Reporte ejecutivo formal para impresión y presentación directiva',
    icono: FileText,
    color: '#DC2626',
  },
];

const GESTIONES = ['Todas', '2026', '2025', '2024'];

const PROGRAMAS_DEFAULT = [
  'Todos',
  'Diplomado en Inteligencia de Negocios',
  'Maestría en Data Science',
  'Especialidad en Gestión Tributaria',
  'Diplomado en Educación Superior',
  'Maestría en Finanzas Corporativas',
];

export default function CentroReportes() {
  const { user, role } = useAuth();
  const [tipoSeleccionado, setTipoSeleccionado] = useState('kpis');
  const [formatoSeleccionado, setFormatoSeleccionado] = useState('xlsx');
  const [gestion, setGestion] = useState('Todas');
  const [programa, setPrograma] = useState('Todos');
  const [loadingExport, setLoadingExport] = useState(false);
  const [loadingHistorial, setLoadingHistorial] = useState(false);
  const [historial, setHistorial] = useState([]);

  // Cargar historial de auditoría
  const cargarHistorial = async () => {
    try {
      setLoadingHistorial(true);
      const data = await reportesApi.getHistorial(15);
      if (data && Array.isArray(data.historial)) {
        setHistorial(data.historial);
      }
    } catch (err) {
      console.warn('No se pudo cargar el historial de exportaciones:', err.message);
    } finally {
      setLoadingHistorial(false);
    }
  };

  useEffect(() => {
    cargarHistorial();
  }, []);

  // Manejo de exportación
  const handleDescargar = async () => {
    try {
      setLoadingExport(true);
      sileoToast.info({
        title: 'Generando Reporte',
        description: `Compilando reporte de ${tipoSeleccionado.toUpperCase()} en formato ${formatoSeleccionado.toUpperCase()}...`,
      });

      const res = await reportesApi.exportarReporte({
        tipo: tipoSeleccionado,
        formato: formatoSeleccionado,
        gestion: gestion === 'Todas' ? '' : gestion,
        programa: programa === 'Todos' ? '' : programa,
      });

      sileoToast.success({
        title: 'Descarga Completada',
        description: `Se descargó exitosamente: ${res.filename}`,
      });

      // Refrescar historial tras exportación exitosa
      cargarHistorial();
    } catch (err) {
      console.error('Error al exportar reporte:', err);
      sileoToast.error({
        title: 'Error de Exportación',
        description: err.response?.data?.detail || 'No se pudo generar el reporte solicitado.',
      });
    } finally {
      setLoadingExport(false);
    }
  };

  // Descripción de política PoLP por rol
  const getDescripcionPoLP = () => {
    switch (role) {
      case 'DIRECTOR_ACADEMICO':
        return {
          titulo: 'Alcance Académico & Pedagógico',
          descripcion: 'Tiene acceso a notas, promedios, alertas de riesgo y matrícula. Por Principio de Menor Privilegio (PoLP), los montos financieros en Bs. se exportan enmascarados como [RESTRINGIDO PoLP].',
          badgeColor: '#2563EB',
        };
      case 'ANALISTA_FINANCIERO':
        return {
          titulo: 'Alcance Financiero & Cartera',
          descripcion: 'Tiene acceso irrestricto a cobranzas, recaudaciones, mora de cartera y tickets promedio en Bolivianos (Bs). Los datos no financieros se limitan a agregaciones de soporte.',
          badgeColor: '#059669',
        };
      case 'AUDITOR_CALIDAD':
        return {
          titulo: 'Alcance de Calidad DataOps & Auditoría',
          descripcion: 'Tiene acceso a métricas de procesamiento ETL, confianza probabilística BETO NER, registros derivados a HITL y logs de auditoría.',
          badgeColor: '#D97706',
        };
      case 'ANALISTA_MARKETING':
        return {
          titulo: 'Alcance de Demanda & Mercado',
          descripcion: 'Tiene acceso a tasas de conversión, cohortes de captación, retención neta y demanda curricular por programa.',
          badgeColor: '#7C3AED',
        };
      case 'ADMIN':
      default:
        return {
          titulo: 'Alcance Administrativo Global',
          descripcion: 'Tiene acceso irrestricto a todas las perspectivas del CMI, alertas institucionales y cifras financieras completas sin censura.',
          badgeColor: '#D99B26',
        };
    }
  };

  const polpInfo = getDescripcionPoLP();

  return (
    <div className="fade-in" style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* ─── Encabezado Institucional ─── */}
      <div style={{ marginBottom: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  fontFamily: 'var(--font-mono)',
                  padding: '4px 10px',
                  borderRadius: '9999px',
                  backgroundColor: 'rgba(217, 155, 38, 0.15)',
                  color: 'var(--color-gira-gold)',
                  letterSpacing: '0.05em',
                }}
              >
                HU-12 · GOBERNANZA & EXPORTACIÓN
              </span>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  fontFamily: 'var(--font-mono)',
                  padding: '4px 10px',
                  borderRadius: '9999px',
                  backgroundColor: 'rgba(37, 99, 235, 0.12)',
                  color: '#2563EB',
                }}
              >
                RBAC: {role || 'INVITADO'}
              </span>
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-ink-black)', margin: '8px 0 4px 0' }}>
              Centro de Reportes y Exportación Institucional
            </h1>
            <p style={{ fontSize: '14px', color: 'var(--color-slate-gray)', margin: 0 }}>
              Generación y descarga de informes ejecutivos oficiales en XLSX y PDF con trazabilidad y auditoría estricta.
            </p>
          </div>

          <button
            onClick={cargarHistorial}
            disabled={loadingHistorial}
            className="btn btn-secondary"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 14px',
              fontSize: '13px',
              borderRadius: '8px',
              cursor: loadingHistorial ? 'wait' : 'pointer',
            }}
          >
            <RefreshCw size={15} className={loadingHistorial ? 'animate-spin' : ''} />
            Actualizar Historial
          </button>
        </div>
      </div>

      {/* ─── Card Informativa de Política PoLP ─── */}
      <div
        style={{
          backgroundColor: 'var(--color-card-bg)',
          border: '1px solid var(--color-border)',
          borderRadius: '12px',
          padding: '18px 20px',
          marginBottom: '28px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '14px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
        }}
      >
        <div
          style={{
            padding: '10px',
            borderRadius: '10px',
            backgroundColor: `${polpInfo.badgeColor}18`,
            color: polpInfo.badgeColor,
            flexShrink: 0,
          }}
        >
          <Shield size={22} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-ink-black)' }}>
              {polpInfo.titulo}
            </span>
            <span
              style={{
                fontSize: '10.5px',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '6px',
                backgroundColor: `${polpInfo.badgeColor}20`,
                color: polpInfo.badgeColor,
              }}
            >
              POLP ACTIVO
            </span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: 0, lineHeight: 1.5 }}>
            {polpInfo.descripcion} Cada exportación queda registrada en la bitácora institucional <code style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>log_pipeline_ingesta</code> con etiqueta <strong style={{ color: 'var(--color-ink-black)' }}>EXPORT</strong>.
          </p>
        </div>
      </div>

      {/* ─── Panel Principal de Configuración de Reporte ─── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '24px',
          marginBottom: '32px',
        }}
      >
        {/* Selector de Tipo de Reporte */}
        <div
          style={{
            backgroundColor: 'var(--color-card-bg)',
            border: '1px solid var(--color-border)',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
          }}
        >
          <h2 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-ink-black)', marginTop: 0, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>1. Seleccionar Tipo de Reporte</span>
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {TIPOS_REPORTE.map((tipo) => {
              const Icon = tipo.icono;
              const isSelected = tipoSeleccionado === tipo.id;
              return (
                <div
                  key={tipo.id}
                  onClick={() => setTipoSeleccionado(tipo.id)}
                  style={{
                    padding: '14px',
                    borderRadius: '10px',
                    border: `2px solid ${isSelected ? tipo.color : 'var(--color-border)'}`,
                    backgroundColor: isSelected ? `${tipo.color}08` : 'transparent',
                    cursor: 'pointer',
                    transition: 'all 0.18s ease',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                  }}
                >
                  <div
                    style={{
                      padding: '8px',
                      borderRadius: '8px',
                      backgroundColor: `${tipo.color}18`,
                      color: tipo.color,
                      flexShrink: 0,
                    }}
                  >
                    <Icon size={20} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
                        {tipo.titulo}
                      </span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 700,
                          padding: '2px 6px',
                          borderRadius: '4px',
                          backgroundColor: `${tipo.color}15`,
                          color: tipo.color,
                        }}
                      >
                        {tipo.badge}
                      </span>
                    </div>
                    <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '3px 0 0 0' }}>
                      {tipo.subtitulo}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selector de Formato & Filtros */}
        <div
          style={{
            backgroundColor: 'var(--color-card-bg)',
            border: '1px solid var(--color-border)',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <h2 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-ink-black)', marginTop: 0, marginBottom: '14px' }}>
              2. Formato de Salida
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px' }}>
              {FORMATOS.map((fmt) => {
                const Icon = fmt.icono;
                const isSelected = formatoSeleccionado === fmt.id;
                return (
                  <div
                    key={fmt.id}
                    onClick={() => setFormatoSeleccionado(fmt.id)}
                    style={{
                      padding: '14px',
                      borderRadius: '10px',
                      border: `2px solid ${isSelected ? fmt.color : 'var(--color-border)'}`,
                      backgroundColor: isSelected ? `${fmt.color}08` : 'transparent',
                      cursor: 'pointer',
                      transition: 'all 0.18s ease',
                      textAlign: 'center',
                    }}
                  >
                    <Icon size={24} style={{ color: fmt.color, margin: '0 auto 8px auto' }} />
                    <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
                      {fmt.nombre}
                    </div>
                  </div>
                );
              })}
            </div>

            <h2 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-ink-black)', marginBottom: '14px' }}>
              3. Filtros Opcionales
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-slate-gray)', display: 'block', marginBottom: '6px' }}>
                  Gestión / Periodo
                </label>
                <select
                  value={gestion}
                  onChange={(e) => setGestion(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border)',
                    backgroundColor: 'var(--color-bg-base)',
                    color: 'var(--color-ink-black)',
                    fontSize: '13px',
                  }}
                >
                  {GESTIONES.map((g) => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-slate-gray)', display: 'block', marginBottom: '6px' }}>
                  Programa Académico
                </label>
                <select
                  value={programa}
                  onChange={(e) => setPrograma(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border)',
                    backgroundColor: 'var(--color-bg-base)',
                    color: 'var(--color-ink-black)',
                    fontSize: '13px',
                  }}
                >
                  {PROGRAMAS_DEFAULT.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Botón Primario de Descarga */}
          <button
            onClick={handleDescargar}
            disabled={loadingExport}
            style={{
              width: '100%',
              padding: '12px 18px',
              borderRadius: '10px',
              backgroundColor: 'var(--color-gira-gold)',
              color: '#000000',
              fontWeight: 700,
              fontSize: '14px',
              border: 'none',
              cursor: loadingExport ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              boxShadow: '0 4px 12px rgba(217, 155, 38, 0.25)',
              transition: 'all 0.2s ease',
              opacity: loadingExport ? 0.75 : 1,
            }}
          >
            <Download size={18} className={loadingExport ? 'animate-bounce' : ''} />
            {loadingExport ? 'Generando Reporte Oficial...' : `Descargar Reporte (${formatoSeleccionado.toUpperCase()})`}
          </button>
        </div>
      </div>

      {/* ─── Tabla de Historial y Auditoría de Exportaciones (HU-12) ─── */}
      <div
        style={{
          backgroundColor: 'var(--color-card-bg)',
          border: '1px solid var(--color-border)',
          borderRadius: '12px',
          padding: '20px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-ink-black)', margin: 0 }}>
              Bitácora de Auditoría de Exportaciones Recientes
            </h2>
            <p style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
              Registros trazables en log_pipeline_ingesta (etapa=EXPORT) con telemetría de latencia y alcance PoLP.
            </p>
          </div>
          <span
            style={{
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              color: 'var(--color-slate-gray)',
            }}
          >
            {historial.length} eventos registrados
          </span>
        </div>

        {historial.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: '40px 20px',
              color: 'var(--color-slate-gray)',
              fontSize: '13px',
            }}
          >
            <Clock size={32} style={{ margin: '0 auto 10px auto', opacity: 0.5 }} />
            <div>No hay exportaciones registradas recientemente para tu cuenta.</div>
            <div style={{ fontSize: '12px', marginTop: '4px' }}>
              Genera una nueva descarga arriba para registrar el primer evento de auditoría.
            </div>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left' }}>
                  <th style={{ padding: '10px 12px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>Fecha / Hora</th>
                  <th style={{ padding: '10px 12px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>Tipo</th>
                  <th style={{ padding: '10px 12px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>Formato</th>
                  <th style={{ padding: '10px 12px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>Usuario (Rol)</th>
                  <th style={{ padding: '10px 12px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>Filas</th>
                  <th style={{ padding: '10px 12px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>Latencia</th>
                  <th style={{ padding: '10px 12px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>Estado</th>
                </tr>
              </thead>
              <tbody>
                {historial.map((item, idx) => (
                  <tr
                    key={item.id || idx}
                    style={{
                      borderBottom: '1px solid var(--color-border)',
                      backgroundColor: idx % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.015)',
                    }}
                  >
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                      {item.fecha ? new Date(item.fecha).toLocaleString() : 'N/A'}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '3px 8px',
                          borderRadius: '6px',
                          backgroundColor:
                            item.tipo === 'kpis'
                              ? 'rgba(37, 99, 235, 0.12)'
                              : item.tipo === 'alertas'
                              ? 'rgba(217, 119, 6, 0.12)'
                              : 'rgba(5, 150, 105, 0.12)',
                          color:
                            item.tipo === 'kpis'
                              ? '#2563EB'
                              : item.tipo === 'alertas'
                              ? '#D97706'
                              : '#059669',
                        }}
                      >
                        {item.tipo?.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '3px 8px',
                          borderRadius: '6px',
                          backgroundColor:
                            item.formato === 'xlsx'
                              ? 'rgba(22, 163, 74, 0.12)'
                              : 'rgba(220, 38, 38, 0.12)',
                          color: item.formato === 'xlsx' ? '#16A34A' : '#DC2626',
                        }}
                      >
                        {item.formato?.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-ink-black)', fontWeight: 500 }}>
                      {item.usuario} <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>({item.rol})</span>
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)' }}>
                      {item.filas}
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                      {item.tiempo_ms} ms
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '11.5px',
                          fontWeight: 600,
                          color: '#16A34A',
                        }}
                      >
                        <CheckCircle2 size={13} />
                        EXITOSO
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
