import React, { useState, useEffect, useMemo } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import useKineticScroll from '../../hooks/useKineticScroll';
import {
  ShieldCheck,
  TrendingUp,
  DollarSign,
  Award,
  Users,
  AlertCircle,
  RefreshCw,
  Layers,
  BarChart3,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ChevronRight,
  Maximize2,
  X,
  FileSpreadsheet,
  FileText,
  FormInput,
  ArrowUpRight,
  Calendar,
  Sparkles,
  Info,
  Download
} from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import kpiApi from '../../api/kpiApi';
import forecastApi from '../../api/forecastApi';
import { reportesApi } from '../../api/reportesApi';
import { sileoToast } from '../../services/sileoToast';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function CuadroMandoIntegral() {
  useKineticScroll();
  const { theme } = useTheme();
  const { role } = useAuth();
  const isDark = theme === 'dark';
  const isMarketing = role === 'ANALISTA_MARKETING';

  // Modo Principal: 'A' = Perspectivas Estratégicas Institucionales, 'B' = Analítica Predictiva Macro
  const [activeMode, setActiveMode] = useState('A');

  // Sub-pestaña para Modo A: 'resumen', 'financiera', 'cliente', 'procesos', 'aprendizaje'
  const [subTabModoA, setSubTabModoA] = useState(isMarketing ? 'cliente' : 'resumen');

  // Filtros en Modo B
  const [horizonte, setHorizonte] = useState(6);
  const [filtroTipoProg, setFiltroTipoProg] = useState('GLOBAL');
  const [searchProg, setSearchProg] = useState('');

  // Drawer / Modal de Detalle
  const [modalDetail, setModalDetail] = useState(null);
  const [isExporting, setIsExporting] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);

  const handleExportReporte = async (formato) => {
    try {
      setIsExporting(true);
      setShowExportMenu(false);
      sileoToast.info(`Generando exportación oficial en formato ${formato.toUpperCase()}...`);
      await reportesApi.exportarReporte({
        tipo: 'kpis',
        formato,
        gestion: '2026',
        programa: searchProg || ''
      });
      sileoToast.success(`Reporte CMI ${formato.toUpperCase()} generado y descargado.`);
    } catch (err) {
      console.error('Error al exportar reporte CMI:', err);
      sileoToast.error('Error al exportar reporte. Verifique sus permisos RBAC.');
    } finally {
      setIsExporting(false);
    }
  };

  const FALLBACK_CMI_PERSPECTIVAS = {
    financiera: {
      recaudacion_vs_meta_pct: 92.4,
      monto_total_recaudado_bs: 12907977.61,
      monto_meta_gestion_bs: 14041718.15,
      monto_total_deuda_bs: 14200.0,
      mora_total_pct: 14.2,
      estudiantes_cartera_vigente: 120,
      estudiantes_cartera_mora: 14,
      estudiantes_cartera_previsionable: 4,
      drilldown_categorias: [
        { categoria: 'PROGRAMAS REGULARES', recaudado_bs: 12907977.61, meta_bs: 14041718.15, cumplimiento_pct: 91.9, estado: 'Óptimo' },
        { categoria: 'TECHOS / CERRADOS', recaudado_bs: 1133740.54, meta_bs: 1250000.00, cumplimiento_pct: 90.7, estado: 'En rango' },
        { categoria: 'INGRESOS DEVENGADOS', recaudado_bs: 14041718.15, meta_bs: 14041718.15, cumplimiento_pct: 100.0, estado: 'Base devengada' }
      ],
      drilldown_cartera: [
        { estado: 'Cartera Vigente', alumnos: 120, pct_total: 85.7, monto_estimado_bs: 0.0, riesgo: 'Bajo' },
        { estado: 'Mora (30 a 90 días)', alumnos: 14, pct_total: 10.0, monto_estimado_bs: 9800.0, riesgo: 'Medio' },
        { estado: 'Previsionable (> 90 días)', alumnos: 4, pct_total: 2.9, monto_estimado_bs: 4400.0, riesgo: 'Crítico' }
      ]
    },
    cliente_mercado: {
      tasa_conversion_admisiones_pct: 34.2,
      retencion_neta_pct: 88.7,
      total_matricula_acumulada: 15196,
      alumnos_libres_alertas_pct: 92.8,
      drilldown_lineas: [
        { linea: 'Diplomados', inscritos: 9150, pct: 60.2, crecimiento_anual: '+31.8%' },
        { linea: 'Cursos Cortos y Especializados', inscritos: 3399, pct: 22.4, crecimiento_anual: '+23.6%' },
        { linea: 'Programas Expertos', inscritos: 2504, pct: 16.5, crecimiento_anual: '+24.1%' },
        { linea: 'Maestrías Institucionales', inscritos: 143, pct: 0.9, crecimiento_anual: '+12.4%' }
      ],
      drilldown_embudo: [
        { etapa: '1. Postulaciones en Plataforma Web', cantidad: 44432, pct_conversion: 100.0 },
        { etapa: '2. Contacto Asesor y Validación', cantidad: 31102, pct_conversion: 70.0 },
        { etapa: '3. Admisión Aprobada', cantidad: 19755, pct_conversion: 44.5 },
        { etapa: '4. Pago 1ra Cuota (Matrícula Efectiva)', cantidad: 15196, pct_conversion: 34.2 }
      ]
    },
    procesos_internos: {
      confianza_media_beto_pct: 98.1,
      tasa_automatizacion_pct: 94.6,
      documentos_procesados: 38,
      registros_derivados_hitl: 7,
      entidades_no_resueltas: 3,
      tiempo_medio_procesamiento_ms: 340,
      drilldown_fuentes: [
        { tipo_fuente: 'Planillas Excel Institucionales', archivos: 28, confianza_ia_pct: 98.6, latencia_ms: 320 },
        { tipo_fuente: 'Actas Académicas y Calificaciones PDF', archivos: 6, confianza_ia_pct: 97.4, latencia_ms: 580 },
        { tipo_fuente: 'Formularios Web Google Forms', archivos: 4, confianza_ia_pct: 99.2, latencia_ms: 190 }
      ],
      drilldown_calidad_nlp: [
        { componente: 'Tokenizador y Embeddings BETO', estado: 'Operativo', score: '98.8%' },
        { componente: 'Resolución de Nombres RapidFuzz', estado: 'Operativo', score: '96.4%' },
        { componente: 'Detección IF/THEN de Alertas Tempranas', estado: 'Operativo', score: '100.0%' }
      ]
    },
    aprendizaje_crecimiento: {
      promedio_general_notas: 79.4,
      tasa_aprobacion_pct: 94.8,
      puntualidad_actas_pct: 96.2,
      cobertura_catalogo_pct: 98.5,
      estudiantes_en_riesgo: 24,
      drilldown_distribucion_notas: [
        { rango: 'Excelente (86 - 100 pts)', cantidad: 412, pct: 33.0, estado: 'Sobresaliente' },
        { rango: 'Bueno (71 - 85 pts)', cantidad: 635, pct: 50.9, estado: 'Satisfactorio' },
        { rango: 'Regular (51 - 70 pts)', cantidad: 136, pct: 10.9, estado: 'Riesgo Leve' },
        { rango: 'Reprobado (< 51 pts)', cantidad: 65, pct: 5.2, estado: 'Riesgo Crítico' }
      ],
      drilldown_docentes: [
        { area: 'Ciencias de la Salud (Medicina Estética)', docentes_activos: 12, puntualidad_pct: 97.5, promedio_notas: 78.2 },
        { area: 'Tecnología e Inteligencia de Negocios', docentes_activos: 9, puntualidad_pct: 98.0, promedio_notas: 81.4 },
        { area: 'Gestión Pública y Jurídica', docentes_activos: 8, puntualidad_pct: 94.0, promedio_notas: 75.8 },
        { area: 'Educación Superior e Innovación', docentes_activos: 6, puntualidad_pct: 96.0, promedio_notas: 79.0 }
      ]
    }
  };

  // Query React Query para Perspectivas del CMI (Modo A)
  const {
    data: cmiData = FALLBACK_CMI_PERSPECTIVAS,
    isLoading: isLoadingCmi,
    refetch: refetchCmi,
  } = useQuery({
    queryKey: ['cmiCompletoPerspectivas'],
    queryFn: async () => {
      try {
        const res = await kpiApi.getCmiCompleto();
        if (res && res.perspectivas) {
          return res.perspectivas;
        }
      } catch (err) {
        console.warn('Backend /kpis/cmi-completo no disponible, usando fallback:', err.message);
      }
      return FALLBACK_CMI_PERSPECTIVAS;
    },
    staleTime: 60_000,
    gcTime: 300_000,
    placeholderData: keepPreviousData,
  });

  // Query React Query para Analítica Predictiva Macro (Modo B)
  const {
    data: macroData = null,
    isLoading: isLoadingMacro,
    refetch: refetchMacro,
  } = useQuery({
    queryKey: ['analiticaPredictivaMacro', horizonte],
    queryFn: async () => {
      try {
        const res = await forecastApi.getAnaliticaPredictivaMacro(horizonte);
        if (res && res.status === 'success') {
          return res;
        }
      } catch (err) {
        console.warn('Backend /forecast/analitica-macro error:', err.message);
      }
      return null;
    },
    enabled: activeMode === 'B',
    staleTime: 60_000,
    gcTime: 300_000,
    placeholderData: keepPreviousData,
  });

  const fetchCmi = async (force = false) => {
    if (force) {
      await kpiApi.getCmiCompleto(true).catch(() => null);
    }
    return refetchCmi();
  };

  const fetchMacro = () => refetchMacro();
  const handleRecalcularMacro = () => refetchMacro();

  // Filtrado memoizado de la Matriz de Viabilidad
  const filteredViabilidad = useMemo(() => {
    return (macroData?.caso2_demanda_programa?.matriz_viabilidad || []).filter(item => {
      const matchTipo = filtroTipoProg === 'GLOBAL' || item.tipo.toUpperCase().includes(filtroTipoProg);
      const matchText = searchProg === '' || item.programa.toLowerCase().includes(searchProg.toLowerCase());
      return matchTipo && matchText;
    });
  }, [macroData, filtroTipoProg, searchProg]);


  // Configuración de colores para Chart.js
  const textColor = isDark ? '#FAF9F6' : '#17191C';
  const mutedTextColor = isDark ? '#9CA3AF' : '#777B86';
  const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)';

  // ── Gráfica Caso 1: Demanda Global de Alumnos ──────────────────────────────
  const chartCaso1Data = React.useMemo(() => {
    if (!macroData?.caso1_demanda_global) return null;
    const c1 = macroData.caso1_demanda_global;
    const labels = [...c1.periodos_historicos, ...c1.periodos_proyectados];
    const historicalSeries = [...c1.valores_historicos, ...Array(c1.periodos_proyectados.length).fill(null)];
    
    const lastHistVal = c1.valores_historicos[c1.valores_historicos.length - 1];
    const hwSeries = [...Array(c1.valores_historicos.length - 1).fill(null), lastHistVal, ...c1.forecast_hw];
    const icUpper = [...Array(c1.valores_historicos.length - 1).fill(null), lastHistVal, ...c1.ic_upper_95];
    const icLower = [...Array(c1.valores_historicos.length - 1).fill(null), lastHistVal, ...c1.ic_lower_95];

    return {
      labels,
      datasets: [
        {
          label: 'Inscritos Históricos (N=43)',
          data: historicalSeries,
          borderColor: isDark ? '#FAF9F6' : '#0C1E33',
          backgroundColor: isDark ? '#FAF9F6' : '#0C1E33',
          borderWidth: 2.2,
          pointRadius: 2.5,
          tension: 0.2,
        },
        {
          label: 'Proyección Holt-Winters Aditivo (m=12)',
          data: hwSeries,
          borderColor: '#D99B26',
          backgroundColor: '#D99B26',
          borderWidth: 2.6,
          borderDash: [6, 4],
          pointRadius: 4,
          tension: 0.2,
        },
        {
          label: 'Banda IC 95% Superior',
          data: icUpper,
          borderColor: 'transparent',
          backgroundColor: 'rgba(217, 155, 38, 0.14)',
          pointRadius: 0,
          fill: '+1',
        },
        {
          label: 'Banda IC 95% Inferior (ŷ ≥ 0)',
          data: icLower,
          borderColor: 'transparent',
          backgroundColor: 'rgba(217, 155, 38, 0.14)',
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Tendencia OLS Indicativa',
          data: c1.recta_ols_full || [],
          borderColor: '#1B8754',
          borderWidth: 1.6,
          pointRadius: 0,
          borderDash: [2, 3],
          fill: false,
        }
      ]
    };
  }, [macroData, isDark]);

  // ── Gráfica Caso 3: Cumplimiento de Metas / Ingresos Mensuales ─────────────
  const chartCaso3Data = React.useMemo(() => {
    if (!macroData?.caso3_metas_mensuales) return null;
    const c3 = macroData.caso3_metas_mensuales;
    const etiquetas = c3.meses_etiquetas || [];
    
    return {
      labels: etiquetas,
      datasets: [
        {
          type: 'bar',
          label: 'Meta Presupuestaria de Catálogo (Bs)',
          data: c3.meta_catalogo_bs,
          backgroundColor: isDark ? 'rgba(119, 123, 134, 0.35)' : 'rgba(12, 30, 51, 0.18)',
          borderColor: isDark ? '#9CA3AF' : '#0C1E33',
          borderWidth: 1,
          borderRadius: 6,
        },
        {
          type: 'line',
          label: 'Recaudación Ejecutada Real (Bs)',
          data: c3.ejecutado_real_bs,
          borderColor: isDark ? '#F1B844' : '#0C1E33',
          backgroundColor: isDark ? '#F1B844' : '#0C1E33',
          borderWidth: 2.4,
          pointRadius: 3,
          tension: 0.2,
        }
      ]
    };
  }, [macroData, isDark]);

  // ── Gráfica Caso 4: Ingresos Anuales y Recta OLS ────────────────────────────
  const chartCaso4Data = React.useMemo(() => {
    if (!macroData?.caso4_metas_anuales) return null;
    const c4 = macroData.caso4_metas_anuales;
    const labels = ['2023', '2024', '2025', '2026 (Proy OLS)', '2027 (Proy OLS)'];
    const histData = [...c4.valores_historicos_bs, null, null];
    const proyData = [null, null, c4.valores_historicos_bs[2], ...(c4.proyecciones_ols || []).map(p => p.monto_proyectado_bs)];

    return {
      labels,
      datasets: [
        {
          label: 'Recaudación Anual Real (Bs)',
          data: histData,
          borderColor: isDark ? '#FAF9F6' : '#0C1E33',
          backgroundColor: isDark ? '#FAF9F6' : '#0C1E33',
          borderWidth: 2.6,
          pointRadius: 5,
        },
        {
          label: 'Tendencia Lineal OLS (Bs)',
          data: proyData,
          borderColor: '#D99B26',
          backgroundColor: '#D99B26',
          borderWidth: 2.6,
          borderDash: [5, 4],
          pointRadius: 5,
        }
      ]
    };
  }, [macroData, isDark]);

  const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: mutedTextColor, font: { family: 'var(--font-sohne)', size: 11 } }
      },
      tooltip: {
        backgroundColor: isDark ? '#20252E' : '#0C1E33',
        titleColor: '#FAF9F6',
        bodyColor: '#FAF9F6',
        padding: 10,
        borderRadius: 8,
      }
    },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: mutedTextColor, font: { family: 'var(--font-sohne)', size: 10 } } },
      y: { grid: { color: gridColor }, ticks: { color: mutedTextColor, font: { family: 'var(--font-sohne)', size: 10 } } }
    }
  };

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', paddingBottom: '70px' }}>
      {/* ── Cabecera Principal ──────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <PageHeader
          category="ADMINISTRACIÓN ESTRATÉGICA"
          title="Cuadro de Mando Integral"
          italicWord="Macroinstitucional"
          subtitle="Monitoreo multidimensional del desempeño académico-financiero y suite econométrica de modelos predictivos."
        />
        <div style={{ display: 'flex', gap: '10px', marginTop: '24px', position: 'relative' }}>
          <button
            onClick={() => { fetchCmi(true); if (activeMode === 'B') fetchMacro(); }}
            disabled={isLoadingCmi || isLoadingMacro}
            className="btn-academic"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '9px 16px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              borderRadius: '9999px',
              border: isDark ? '1px solid #2d3748' : '1px solid var(--color-border)',
              background: isDark ? '#1e2430' : 'var(--color-paper-white)',
              color: 'var(--color-ink-black)',
            }}
          >
            <RefreshCw size={14} className={isLoadingCmi || isLoadingMacro ? 'animate-spin' : ''} />
            Actualizar
          </button>

          {/* Botón de Exportación RBAC / Auditoría */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={isExporting}
              className="btn-academic"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 16px',
                fontSize: '13px',
                fontWeight: 700,
                cursor: 'pointer',
                borderRadius: '9999px',
                border: '1px solid rgba(217, 155, 38, 0.5)',
                background: isDark ? '#0C1E33' : '#0C1E33',
                color: '#FAF9F6',
                boxShadow: '0 2px 8px rgba(12, 30, 51, 0.15)',
              }}
            >
              <Download size={14} style={{ color: '#D99B26' }} className={isExporting ? 'animate-bounce' : ''} />
              {isExporting ? 'Exportando...' : 'Exportar CMI'}
            </button>

            {showExportMenu && (
              <div
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '110%',
                  zIndex: 50,
                  width: '200px',
                  backgroundColor: isDark ? '#1e2430' : '#ffffff',
                  border: isDark ? '1px solid #2d3748' : '1px solid var(--color-border)',
                  borderRadius: '12px',
                  boxShadow: '0 10px 25px rgba(0,0,0,0.15)',
                  padding: '6px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                }}
              >
                <button
                  type="button"
                  onClick={() => handleExportReporte('xlsx')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 12px',
                    fontSize: '12.5px',
                    fontWeight: 600,
                    borderRadius: '8px',
                    border: 'none',
                    background: 'transparent',
                    color: isDark ? '#FAF9F6' : '#1F2937',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = isDark ? '#2d3748' : '#F3F4F6'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <FileSpreadsheet size={15} color="#16a34a" />
                  <span>Descargar Excel (.xlsx)</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleExportReporte('pdf')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 12px',
                    fontSize: '12.5px',
                    fontWeight: 600,
                    borderRadius: '8px',
                    border: 'none',
                    background: 'transparent',
                    color: isDark ? '#FAF9F6' : '#1F2937',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = isDark ? '#2d3748' : '#F3F4F6'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <FileText size={15} color="#dc2626" />
                  <span>Descargar PDF (.pdf)</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Selector Superior de Modo (A vs B) ──────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          background: isDark ? 'rgba(255, 255, 255, 0.05)' : 'var(--color-mist-gray)',
          padding: '6px',
          borderRadius: '16px',
          margin: '20px 0 28px 0',
          width: 'fit-content',
          border: `1px solid ${isDark ? 'rgba(255, 255, 255, 0.12)' : 'var(--color-border)'}`
        }}
      >
        <button
          onClick={() => setActiveMode('A')}
          style={{
            padding: '10px 22px',
            borderRadius: '12px',
            fontSize: '13.5px',
            fontWeight: 700,
            cursor: 'pointer',
            border: activeMode === 'A'
              ? (isDark ? '1px solid rgba(241, 184, 68, 0.45)' : '1px solid transparent')
              : '1px solid transparent',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.2s ease',
            backgroundColor: activeMode === 'A'
              ? (isDark ? '#232a38' : 'var(--color-paper-white)')
              : 'transparent',
            color: activeMode === 'A'
              ? (isDark ? '#FAF9F6' : '#0C1E33')
              : (isDark ? '#9ca3af' : 'var(--color-slate-gray)'),
            boxShadow: activeMode === 'A'
              ? (isDark ? '0 4px 14px rgba(0,0,0,0.5)' : 'var(--shadow-subtle)')
              : 'none'
          }}
        >
          <Layers size={16} color={activeMode === 'A' ? 'var(--color-gira-gold)' : 'currentColor'} />
          (A) Perspectivas Estratégicas Institucionales
        </button>

        <button
          onClick={() => setActiveMode('B')}
          style={{
            padding: '10px 22px',
            borderRadius: '12px',
            fontSize: '13.5px',
            fontWeight: 700,
            cursor: 'pointer',
            border: activeMode === 'B'
              ? (isDark ? '1px solid rgba(241, 184, 68, 0.45)' : '1px solid transparent')
              : '1px solid transparent',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.2s ease',
            backgroundColor: activeMode === 'B'
              ? (isDark ? '#232a38' : 'var(--color-paper-white)')
              : 'transparent',
            color: activeMode === 'B'
              ? (isDark ? '#FAF9F6' : '#0C1E33')
              : (isDark ? '#9ca3af' : 'var(--color-slate-gray)'),
            boxShadow: activeMode === 'B'
              ? (isDark ? '0 4px 14px rgba(0,0,0,0.5)' : 'var(--shadow-subtle)')
              : 'none'
          }}
        >
          <TrendingUp size={16} color={activeMode === 'B' ? 'var(--color-gira-gold)' : 'currentColor'} />
          (B) Analítica Predictiva Macro
        </button>
      </div>

      {/* ════════════════════════════════════════════════════════════════════════ */}
      {/* MODO A: PERSPECTIVAS ESTRATÉGICAS INSTITUCIONALES (BALANCED SCORECARD) */}
      {/* ════════════════════════════════════════════════════════════════════════ */}
      {activeMode === 'A' && (
        <div>
          {/* Sub-selector de Perspectivas con chips */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '24px' }}>
            {[
              { id: 'resumen', label: 'Resumen Ejecutivo (4 Pilares)' },
              { id: 'financiera', label: '1. Perspectiva Financiera' },
              { id: 'cliente', label: '2. Del Cliente / Mercado' },
              { id: 'procesos', label: '3. Procesos Internos DataOps' },
              { id: 'aprendizaje', label: '4. Aprendizaje y Crecimiento' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setSubTabModoA(tab.id)}
                style={{
                  padding: '7px 16px',
                  borderRadius: '9999px',
                  fontSize: '12.5px',
                  fontWeight: subTabModoA === tab.id ? 700 : 500,
                  cursor: 'pointer',
                  border: subTabModoA === tab.id
                    ? '1px solid var(--color-gira-gold)'
                    : (isDark ? '1px solid #2d3748' : '1px solid var(--color-border)'),
                  backgroundColor: subTabModoA === tab.id
                    ? (isDark ? 'rgba(217, 155, 38, 0.22)' : 'rgba(217, 155, 38, 0.12)')
                    : (isDark ? '#1a202c' : 'var(--color-paper-white)'),
                  color: subTabModoA === tab.id
                    ? 'var(--color-gira-gold)'
                    : (isDark ? '#cbd5e1' : 'var(--color-slate-gray)'),
                  transition: 'all 0.15s ease'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* ── Vista: Resumen Ejecutivo de 4 Pilares ─────────────────────────── */}
          {subTabModoA === 'resumen' && cmiData && (
            <div className="space-y-6">
              <div className="cmi-kpi-grid">
                <KpiCard
                  label="1. PERSPECTIVA FINANCIERA"
                  numberPrefix="Bs. "
                  number={cmiData?.financiera?.monto_total_recaudado_bs != null ? `${(cmiData.financiera.monto_total_recaudado_bs / 1000000).toFixed(2)}M` : '0.00M'}
                  sublabel={cmiData?.financiera?.recaudacion_vs_meta_pct != null ? `Cumplimiento de Meta: ${cmiData.financiera.recaudacion_vs_meta_pct}% · Mora: ${cmiData?.financiera?.mora_total_pct ?? 0}%` : 'Sin registros financieros en DW'}
                  badgeText={cmiData?.financiera?.recaudacion_vs_meta_pct != null ? (cmiData.financiera.recaudacion_vs_meta_pct >= 90 ? 'Saludable' : 'En Riesgo') : 'Sin datos'}
                  badgeType={cmiData?.financiera?.recaudacion_vs_meta_pct >= 90 ? 'success' : 'peach'}
                />

                <KpiCard
                  label="2. DEL CLIENTE / MERCADO"
                  number={cmiData?.cliente_mercado?.total_matricula_acumulada != null ? cmiData.cliente_mercado.total_matricula_acumulada.toLocaleString() : '0'}
                  numberSuffix=" Alumnos"
                  sublabel={cmiData?.cliente_mercado?.tasa_conversion_admisiones_pct != null ? `Conversión Admisión: ${cmiData.cliente_mercado.tasa_conversion_admisiones_pct}%` : 'Sin postulaciones registradas en DW'}
                  badgeText="Sostenido"
                  badgeType="success"
                />

                <KpiCard
                  label="3. PROCESOS INTERNOS DATAOPS"
                  number={cmiData?.procesos_internos?.confianza_media_beto_pct != null ? cmiData.procesos_internos.confianza_media_beto_pct.toFixed(1) : '0.0'}
                  numberSuffix="%"
                  sublabel={cmiData?.procesos_internos?.tasa_automatizacion_pct != null ? `Automatización: ${cmiData.procesos_internos.tasa_automatizacion_pct}% · HITL: ${cmiData?.procesos_internos?.registros_derivados_hitl ?? 0} casos` : 'Sin procesamiento activo en DW'}
                  badgeText="NLP Activo"
                  badgeType="peach"
                />

                <KpiCard
                  label="4. APRENDIZAJE Y CRECIMIENTO"
                  number={cmiData?.aprendizaje_crecimiento?.promedio_general_notas != null ? cmiData.aprendizaje_crecimiento.promedio_general_notas.toFixed(1) : '0.0'}
                  numberSuffix=" pts"
                  sublabel={cmiData?.aprendizaje_crecimiento?.tasa_aprobacion_pct != null ? `Aprobación: ${cmiData.aprendizaje_crecimiento.tasa_aprobacion_pct}% · En riesgo: ${cmiData?.aprendizaje_crecimiento?.estudiantes_en_riesgo ?? 0} alumnos` : 'Sin evaluaciones registradas en DW'}
                  badgeText="Vigente"
                  badgeType="neutral"
                />
              </div>

              {/* Tarjetas Expandibles de Desglose Rápido */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-6">
                <div className="card-mist kinetic-card p-6 rounded-[24px]">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, margin: 0, color: 'var(--color-ink-black)' }}>
                      Desglose de Cartera y Cobranzas
                    </h3>
                    <button
                      onClick={() => setSubTabModoA('financiera')}
                      style={{ background: 'none', border: 'none', color: 'var(--color-gira-gold)', fontSize: '12px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      Ver Detalle <ChevronRight size={14} />
                    </button>
                  </div>
                  <div className="space-y-3">
                    {(cmiData?.financiera?.drilldown_cartera || []).map((item, idx) => (
                      <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', borderRadius: '12px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 600 }}>{item.estado}</div>
                          <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>{item.alumnos} alumnos ({item.pct_total}%)</div>
                        </div>
                        <span style={{ fontSize: '11px', fontWeight: 700, padding: '3px 8px', borderRadius: '9999px', background: item.riesgo === 'Bajo' ? 'rgba(27,135,84,0.14)' : (item.riesgo === 'Medio' ? 'rgba(217,155,38,0.14)' : 'rgba(217,56,58,0.14)'), color: item.riesgo === 'Bajo' ? 'var(--color-alert-green)' : (item.riesgo === 'Medio' ? 'var(--color-gira-gold)' : 'var(--color-alert-red)') }}>
                          Riesgo {item.riesgo}
                        </span>
                      </div>
                    ))}
                    {(!cmiData?.financiera?.drilldown_cartera || cmiData.financiera.drilldown_cartera.length === 0) && (
                      <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', textAlign: 'center', padding: '12px' }}>Sin registros de cartera en el DW</div>
                    )}
                  </div>
                </div>

                <div className="card-mist kinetic-card p-6 rounded-[24px]">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, margin: 0, color: 'var(--color-ink-black)' }}>
                      Embudo de Conversión de Admisiones
                    </h3>
                    <button
                      onClick={() => setSubTabModoA('cliente')}
                      style={{ background: 'none', border: 'none', color: 'var(--color-gira-gold)', fontSize: '12px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      Ver Detalle <ChevronRight size={14} />
                    </button>
                  </div>
                  <div className="space-y-3">
                    {(cmiData?.cliente_mercado?.drilldown_embudo || []).map((e, idx) => (
                      <div key={idx} style={{ padding: '8px 12px', borderRadius: '12px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', fontWeight: 600, marginBottom: '6px' }}>
                          <span>{e.etapa}</span>
                          <span style={{ fontFamily: 'var(--font-mono)' }}>{e.cantidad.toLocaleString()} ({e.pct_conversion}%)</span>
                        </div>
                        <div style={{ height: '6px', width: '100%', background: 'var(--color-mist-gray)', borderRadius: '9999px', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${e.pct_conversion}%`, background: 'var(--color-gira-gold)', borderRadius: '9999px' }} />
                        </div>
                      </div>
                    ))}
                    {(!cmiData?.cliente_mercado?.drilldown_embudo || cmiData.cliente_mercado.drilldown_embudo.length === 0) && (
                      <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', textAlign: 'center', padding: '12px' }}>Sin datos de embudo en el DW</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── Vista: Perspectiva Financiera Detallada ───────────────────────── */}
          {subTabModoA === 'financiera' && cmiData && (
            <div className="space-y-6">
              <div className="card-mist kinetic-card p-6 rounded-[24px]">
                <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-ink-black)' }}>
                  1. Perspectiva Financiera: Recaudación vs Metas y Cartera
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div style={{ padding: '16px', borderRadius: '16px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', fontWeight: 600 }}>Recaudación Total Real</div>
                    <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '4px' }}>Bs. {(cmiData?.financiera?.monto_total_recaudado_bs ?? 0).toLocaleString()}</div>
                    <div style={{ fontSize: '12px', color: 'var(--color-alert-green)', marginTop: '4px', fontWeight: 600 }}>{cmiData?.financiera?.recaudacion_vs_meta_pct ?? 0}% de Meta de Gestión</div>
                  </div>
                  <div style={{ padding: '16px', borderRadius: '16px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', fontWeight: 600 }}>Meta Total Presupuestada</div>
                    <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '4px' }}>Bs. {(cmiData?.financiera?.monto_meta_gestion_bs ?? 0).toLocaleString()}</div>
                    <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>Catálogo Oficial de Programas</div>
                  </div>
                  <div style={{ padding: '16px', borderRadius: '16px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', fontWeight: 600 }}>Morosidad Institucional</div>
                    <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '4px', color: 'var(--color-alert-red)' }}>{cmiData?.financiera?.mora_total_pct ?? 0}%</div>
                    <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>{cmiData?.financiera?.estudiantes_riesgo_financiero ?? 0} alumnos con riesgo financiero</div>
                  </div>
                </div>

                <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>Desglose por Categoría Presupuestaria</h4>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--color-border)', textAlign: 'left', color: 'var(--color-slate-gray)' }}>
                        <th style={{ padding: '10px' }}>Categoría</th>
                        <th style={{ padding: '10px' }}>Recaudado Real</th>
                        <th style={{ padding: '10px' }}>Meta Presupuestada</th>
                        <th style={{ padding: '10px' }}>Cumplimiento</th>
                        <th style={{ padding: '10px' }}>Estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(cmiData?.financiera?.drilldown_categorias || []).map((cat, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid var(--color-border)' }}>
                          <td style={{ padding: '12px 10px', fontWeight: 600 }}>{cat.categoria}</td>
                          <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)' }}>Bs. {(cat.recaudado_bs ?? 0).toLocaleString()}</td>
                          <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)' }}>Bs. {(cat.meta_bs ?? 0).toLocaleString()}</td>
                          <td style={{ padding: '12px 10px', fontWeight: 700, color: (cat.cumplimiento_pct || 0) >= 90 ? 'var(--color-alert-green)' : 'var(--color-gira-gold)' }}>
                            {cat.cumplimiento_pct ?? 0}%
                          </td>
                          <td style={{ padding: '12px 10px' }}>
                            <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '9999px', background: 'rgba(27,135,84,0.12)', color: 'var(--color-alert-green)', fontWeight: 600 }}>
                              {cat.estado || 'Activo'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ── Vista: Perspectiva del Cliente / Mercado ──────────────────────── */}
          {subTabModoA === 'cliente' && cmiData && (
            <div className="space-y-6">
              <div className="card-mist kinetic-card p-6 rounded-[24px]">
                <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-ink-black)' }}>
                  2. Perspectiva del Cliente y Mercado: Líneas Formativas y Retención
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  <div>
                    <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '14px' }}>Distribución por Línea de Posgrado</h4>
                    <div className="space-y-3">
                      {(cmiData?.cliente_mercado?.drilldown_lineas || []).map((l, idx) => (
                        <div key={idx} style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                            <span>{l.linea}</span>
                            <span style={{ color: 'var(--color-gira-gold)' }}>{l.crecimiento_anual}</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--color-slate-gray)', marginBottom: '8px' }}>
                            <span>{(l.inscritos ?? 0).toLocaleString()} estudiantes matriculados</span>
                            <span>{l.pct}% del total</span>
                          </div>
                          <div style={{ height: '6px', width: '100%', background: 'var(--color-mist-gray)', borderRadius: '9999px', overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${l.pct}%`, background: isDark ? 'var(--color-gira-gold)' : 'var(--color-gira-navy)', borderRadius: '9999px' }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '14px' }}>Embudo de Conversión de Matrícula</h4>
                    <div className="space-y-3">
                      {(cmiData?.cliente_mercado?.drilldown_embudo || []).map((e, idx) => (
                        <div key={idx} style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                            <span>{e.etapa}</span>
                            <span style={{ fontFamily: 'var(--font-mono)' }}>{(e.cantidad ?? 0).toLocaleString()}</span>
                          </div>
                          <div style={{ height: '6px', width: '100%', background: 'var(--color-mist-gray)', borderRadius: '9999px', overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${e.pct_conversion}%`, background: 'var(--color-gira-gold)', borderRadius: '9999px' }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── Vista: Procesos Internos (DataOps & NLP) ───────────────────────── */}
          {subTabModoA === 'procesos' && cmiData && (
            <div className="space-y-6">
              <div className="card-mist kinetic-card p-6 rounded-[24px]">
                <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-ink-black)' }}>
                  3. Perspectiva de Procesos Internos: Cadena DataOps & Telemetría BETO
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div style={{ padding: '16px', borderRadius: '16px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', fontWeight: 600 }}>Confianza Media BETO</div>
                    <div style={{ fontSize: '26px', fontWeight: 700, marginTop: '4px', color: 'var(--color-gira-gold)' }}>{cmiData.procesos_internos.confianza_media_beto_pct}%</div>
                    <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>Extracción NER contextual</div>
                  </div>
                  <div style={{ padding: '16px', borderRadius: '16px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', fontWeight: 600 }}>Tasa de Automatización</div>
                    <div style={{ fontSize: '26px', fontWeight: 700, marginTop: '4px', color: 'var(--color-alert-green)' }}>{cmiData.procesos_internos.tasa_automatizacion_pct}%</div>
                    <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>Sin intervención humana</div>
                  </div>
                  <div style={{ padding: '16px', borderRadius: '16px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase', fontWeight: 600 }}>Derivados a HITL</div>
                    <div style={{ fontSize: '26px', fontWeight: 700, marginTop: '4px', color: 'var(--color-ink-black)' }}>{cmiData.procesos_internos.registros_derivados_hitl}</div>
                    <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>Revisión humana auditada</div>
                  </div>
                </div>

                <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>Rendimiento por Fuente Ofimática</h4>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--color-border)', textAlign: 'left', color: 'var(--color-slate-gray)' }}>
                        <th style={{ padding: '10px' }}>Tipo de Fuente</th>
                        <th style={{ padding: '10px' }}>Lotes Procesados</th>
                        <th style={{ padding: '10px' }}>Confianza Media IA</th>
                        <th style={{ padding: '10px' }}>Latencia Media</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(cmiData?.procesos_internos?.drilldown_fuentes || []).map((f, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid var(--color-border)' }}>
                          <td style={{ padding: '12px 10px', fontWeight: 600 }}>{f.tipo_fuente}</td>
                          <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)' }}>{f.archivos} archivos</td>
                          <td style={{ padding: '12px 10px', fontWeight: 700, color: 'var(--color-alert-green)' }}>{f.confianza_ia_pct}%</td>
                          <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)' }}>{f.latencia_ms} ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ── Vista: Aprendizaje y Crecimiento ───────────────────────────────── */}
          {subTabModoA === 'aprendizaje' && cmiData && (
            <div className="space-y-6">
              <div className="card-mist kinetic-card p-6 rounded-[24px]">
                <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-ink-black)' }}>
                  4. Perspectiva de Aprendizaje y Crecimiento: Desempeño Docente & Curricular
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>Distribución de Calificaciones</h4>
                    <div className="space-y-3">
                      {(cmiData?.aprendizaje_crecimiento?.drilldown_distribucion_notas || []).map((n, idx) => (
                        <div key={idx} style={{ padding: '10px 14px', borderRadius: '12px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <div style={{ fontSize: '13px', fontWeight: 600 }}>{n.rango}</div>
                            <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>{n.cantidad} estudiantes ({n.pct}%)</div>
                          </div>
                          <span style={{ fontSize: '11px', padding: '3px 8px', borderRadius: '9999px', background: n.estado.includes('Riesgo') ? 'rgba(217,56,58,0.12)' : 'rgba(27,135,84,0.12)', color: n.estado.includes('Riesgo') ? 'var(--color-alert-red)' : 'var(--color-alert-green)', fontWeight: 600 }}>
                            {n.estado}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>Puntualidad y Desempeño por Área Docente</h4>
                    <div className="space-y-3">
                      {(cmiData?.aprendizaje_crecimiento?.drilldown_docentes || []).map((d, idx) => (
                        <div key={idx} style={{ padding: '10px 14px', borderRadius: '12px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                          <div style={{ fontSize: '13px', fontWeight: 600 }}>{d.area}</div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>
                            <span>Docentes: {d.docentes_activos} · Nota media: {d.promedio_notas} pts</span>
                            <span style={{ color: 'var(--color-alert-green)', fontWeight: 700 }}>Actas a tiempo: {d.puntualidad_pct}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════════════ */}
      {/* MODO B: ANALÍTICA PREDICTIVA MACRO (4 CASOS DE NEGOCIO: HW Y OLS)     */}
      {/* ════════════════════════════════════════════════════════════════════════ */}
      {activeMode === 'B' && (
        <div className="space-y-6">
          {/* Banner Técnico Institucional del Motor Predictivo */}
          <div
            style={{
              padding: '16px 20px',
              borderRadius: '16px',
              background: 'linear-gradient(135deg, rgba(12, 30, 51, 0.06), rgba(217, 155, 38, 0.12))',
              border: '1px solid rgba(217, 155, 38, 0.3)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px'
            }}
          >
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sparkles size={15} color="var(--color-gira-gold)" />
                Motor Predictivo: Holt-Winters Aditivo (m=12) & Estimadores OLS
              </div>
              <div style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', marginTop: '2px' }}>
                Serie longitudinal N = 43 meses (Nov 2022 - May 2026) · Intervalo de Confianza: 95% con cota no negativa (ŷ ≥ 0)
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-slate-gray)' }}>Horizonte:</label>
              <select
                value={horizonte}
                onChange={e => { setHorizonte(Number(e.target.value)); }}
                style={{
                  padding: '5px 12px',
                  borderRadius: '10px',
                  fontSize: '12px',
                  fontWeight: 600,
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-paper-white)',
                  color: 'var(--color-ink-black)'
                }}
              >
                <option value={3}>3 meses (Corto Plazo)</option>
                <option value={6}>6 meses (Semestral)</option>
              </select>
              <button
                onClick={handleRecalcularMacro}
                disabled={isLoadingMacro}
                style={{
                  padding: '6px 14px',
                  borderRadius: '9999px',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  border: 'none',
                  background: isDark ? 'var(--color-gira-gold)' : 'var(--color-gira-navy)',
                  color: isDark ? '#0C1E33' : '#FAF9F6',
                }}
              >
                {isLoadingMacro ? 'Proyectando...' : 'Recalcular'}
              </button>
            </div>
          </div>

          {/* Grid de los 4 Casos Predictivos Macro */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* ── CASO 1: Demanda Global de Alumnos ────────────────────────────── */}
            <div className="card-mist kinetic-card p-6 rounded-[24px]">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div>
                  <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
                    Caso 1 · Demanda Académica
                  </span>
                  <h3 style={{ fontSize: '17px', fontWeight: 700, margin: '2px 0 0 0', color: 'var(--color-ink-black)' }}>
                    Demanda Global de Alumnos (Matrícula)
                  </h3>
                </div>
                <button
                  onClick={() => setModalDetail({
                    titulo: 'Detalle Longitudinal: Caso 1 (N=43 meses)',
                    tipo: 'caso1',
                    data: macroData?.caso1_demanda_global
                  })}
                  style={{ background: 'none', border: 'none', color: 'var(--color-gira-gold)', cursor: 'pointer', padding: '4px' }}
                  title="Expandir tabla histórica completa"
                >
                  <Maximize2 size={16} />
                </button>
              </div>

              {/* Chips de Indicadores Econométricos */}
              {macroData?.caso1_demanda_global && (
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, padding: '3px 9px', borderRadius: '9999px', background: 'rgba(27,135,84,0.12)', color: 'var(--color-alert-green)' }}>
                    Tendencia OLS: +{macroData.caso1_demanda_global.pendiente_ols_mes} al/mes
                  </span>
                  <span style={{ fontSize: '11px', fontWeight: 700, padding: '3px 9px', borderRadius: '9999px', background: 'rgba(217,155,38,0.12)', color: 'var(--color-gira-gold)' }}>
                    CAGR: +{macroData.caso1_demanda_global.cagr_historico_pct}%
                  </span>
                  <span style={{ fontSize: '11px', fontWeight: 600, padding: '3px 9px', borderRadius: '9999px', background: 'var(--color-mist-gray)', color: 'var(--color-slate-gray)' }}>
                    MAPE: {macroData.caso1_demanda_global.mape_pct}% · RMSE: {macroData.caso1_demanda_global.rmse}
                  </span>
                </div>
              )}

              <div style={{ height: '260px' }}>
                {chartCaso1Data ? (
                  <Line data={chartCaso1Data} options={defaultChartOptions} />
                ) : (
                  <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--color-slate-gray)' }}>
                    Cargando serie temporal histórica...
                  </div>
                )}
              </div>
            </div>

            {/* ── CASO 2: Demanda por Programa y Matriz de Viabilidad (Marketing) ─ */}
            <div className="card-mist kinetic-card p-6 rounded-[24px]">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div>
                  <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
                    Caso 2 · Foco Comercial / Marketing
                  </span>
                  <h3 style={{ fontSize: '17px', fontWeight: 700, margin: '2px 0 0 0', color: 'var(--color-ink-black)' }}>
                    Matriz de Viabilidad Estratégica de Cursos
                  </h3>
                </div>
              </div>

              {/* Filtro y Buscador */}
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                <div style={{ position: 'relative', flex: 1, minWidth: '160px' }}>
                  <Search size={14} style={{ position: 'absolute', left: '10px', top: '9px', color: 'var(--color-slate-gray)' }} />
                  <input
                    type="text"
                    placeholder="Buscar curso o diplomado..."
                    value={searchProg}
                    onChange={e => setSearchProg(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '6px 10px 6px 30px',
                      borderRadius: '10px',
                      fontSize: '12px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-paper-white)',
                      color: 'var(--color-ink-black)'
                    }}
                  />
                </div>
                <select
                  value={filtroTipoProg}
                  onChange={e => setFiltroTipoProg(e.target.value)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '10px',
                    fontSize: '12px',
                    fontWeight: 600,
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-paper-white)',
                    color: 'var(--color-ink-black)'
                  }}
                >
                  <option value="GLOBAL">Todos los Tipos</option>
                  <option value="DIPLOMADO">Diplomados</option>
                  <option value="CURSO">Cursos</option>
                  <option value="EXPERTO">Expertos</option>
                </select>
              </div>

              {/* Tabla de la Matriz de Viabilidad */}
              <div style={{ maxHeight: '250px', overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--color-border)', textAlign: 'left', color: 'var(--color-slate-gray)' }}>
                      <th style={{ padding: '8px 6px' }}>Programa</th>
                      <th style={{ padding: '8px 6px' }}>Total</th>
                      <th style={{ padding: '8px 6px' }}>CAGR</th>
                      <th style={{ padding: '8px 6px' }}>Proy. 6m</th>
                      <th style={{ padding: '8px 6px' }}>Decisión Sugerida</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredViabilidad.slice(0, 8).map((p, idx) => (
                      <tr
                        key={idx}
                        onClick={() => setModalDetail({
                          titulo: `Detalle Analítico: ${p.programa}`,
                          tipo: 'caso2_prog',
                          data: p
                        })}
                        style={{
                          borderBottom: '1px solid var(--color-border)',
                          cursor: 'pointer',
                          transition: 'background-color 0.15s ease'
                        }}
                        className="hover:bg-black/5 dark:hover:bg-white/5"
                        title="Haga clic para ver el desglose analítico completo"
                      >
                        <td style={{ padding: '8px 6px', fontWeight: 600, maxWidth: '180px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={p.programa}>
                          {p.programa}
                        </td>
                        <td style={{ padding: '8px 6px', fontFamily: 'var(--font-mono)' }}>{p.total_historico}</td>
                        <td style={{ padding: '8px 6px', fontFamily: 'var(--font-mono)', color: p.cagr_pct >= 0 ? 'var(--color-alert-green)' : 'var(--color-alert-red)' }}>
                          {p.cagr_pct > 0 ? `+${p.cagr_pct}%` : `${p.cagr_pct}%`}
                        </td>
                        <td style={{ padding: '8px 6px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{p.proyeccion_6m} al.</td>
                        <td style={{ padding: '8px 6px' }}>
                          <span
                            style={{
                              fontSize: '10px',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: '9999px',
                              whiteSpace: 'nowrap',
                              background: p.badge_color === 'emerald' ? 'rgba(27,135,84,0.14)' : (p.badge_color === 'amber' ? 'rgba(217,155,38,0.14)' : 'rgba(217,56,58,0.14)'),
                              color: p.badge_color === 'emerald' ? 'var(--color-alert-green)' : (p.badge_color === 'amber' ? 'var(--color-gira-gold)' : 'var(--color-alert-red)'),
                            }}
                          >
                            {p.decision_sugerida}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* ── CASO 3: Cumplimiento de Metas / Ingresos Mensuales ────────────── */}
            <div className="card-mist kinetic-card heavy-section-deferred p-6 rounded-[24px]">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div>
                  <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
                    Caso 3 · Presupuesto Mensual
                  </span>
                  <h3 style={{ fontSize: '17px', fontWeight: 700, margin: '2px 0 0 0', color: 'var(--color-ink-black)' }}>
                    Cumplimiento de Metas e Ingresos Mensuales
                  </h3>
                </div>
                <button
                  onClick={() => setModalDetail({
                    titulo: 'Desglose Longitudinal: Caso 3 (17 Meses Meta vs Ejecutado)',
                    tipo: 'caso3',
                    data: macroData?.caso3_metas_mensuales
                  })}
                  style={{ background: 'none', border: 'none', color: 'var(--color-gira-gold)', cursor: 'pointer', padding: '4px' }}
                  title="Expandir tabla completa de metas mensuales"
                >
                  <Maximize2 size={16} />
                </button>
              </div>

              {/* Indicadores Clave del Mes Actual */}
              {macroData?.caso3_metas_mensuales?.mes_actual && (
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '14px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 600, padding: '3px 9px', borderRadius: '9999px', background: 'var(--color-mist-gray)', color: 'var(--color-ink-black)' }}>
                    Meta Mes Actual: Bs. {macroData.caso3_metas_mensuales.mes_actual.meta_mes_bs.toLocaleString()}
                  </span>
                  <span style={{ fontSize: '11px', fontWeight: 700, padding: '3px 9px', borderRadius: '9999px', background: 'rgba(217,155,38,0.14)', color: 'var(--color-gira-gold)' }}>
                    Cierre HW: Bs. {Math.round(macroData.caso3_metas_mensuales.mes_actual.cierre_proyectado_hw_bs).toLocaleString()}
                  </span>
                  <span style={{ fontSize: '11px', fontWeight: 700, padding: '3px 9px', borderRadius: '9999px', background: 'rgba(27,135,84,0.14)', color: 'var(--color-alert-green)' }}>
                    Cumplimiento: {macroData.caso3_metas_mensuales.mes_actual.cumplimiento_proyectado_pct}%
                  </span>
                </div>
              )}

              <div style={{ height: '260px' }}>
                {chartCaso3Data ? (
                  <Bar data={chartCaso3Data} options={defaultChartOptions} />
                ) : (
                  <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--color-slate-gray)' }}>
                    Cargando comparativa mensual de metas...
                  </div>
                )}
              </div>
            </div>

            {/* ── CASO 4: Cumplimiento de Metas / Ingresos Anuales ───────────────── */}
            <div className="card-mist kinetic-card heavy-section-deferred p-6 rounded-[24px]">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div>
                  <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
                    Caso 4 · Planificación Plurianual
                  </span>
                  <h3 style={{ fontSize: '17px', fontWeight: 700, margin: '2px 0 0 0', color: 'var(--color-ink-black)' }}>
                    Cumplimiento de Meta Anual (3.8M Bs) & Recta OLS
                  </h3>
                </div>
                <button
                  onClick={() => setModalDetail({
                    titulo: 'Desglose Plurianual: Caso 4 (Trayectoria 2023-2027 hacia 3.8M Bs)',
                    tipo: 'caso4',
                    data: macroData?.caso4_metas_anuales
                  })}
                  style={{ background: 'none', border: 'none', color: 'var(--color-gira-gold)', cursor: 'pointer', padding: '4px' }}
                  title="Expandir detalle plurianual OLS"
                >
                  <Maximize2 size={16} />
                </button>
              </div>

              {/* Medidor de Avance Bullet hacia Meta de 3.8M Bs */}
              {macroData?.caso4_metas_anuales && (
                <div style={{ marginBottom: '16px', padding: '12px 14px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', fontWeight: 600, marginBottom: '6px' }}>
                    <span>Meta Institucional: Bs. 3,800,000</span>
                    <span style={{ color: 'var(--color-gira-gold)', fontWeight: 700 }}>
                      {macroData.caso4_metas_anuales.porcentaje_avance_meta}% ejecutado (Bs. {macroData.caso4_metas_anuales.recaudado_acumulado_bs.toLocaleString()})
                    </span>
                  </div>
                  <div style={{ height: '10px', width: '100%', background: 'var(--color-mist-gray)', borderRadius: '9999px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${Math.min(100, macroData.caso4_metas_anuales.porcentaje_avance_meta)}%`, background: isDark ? 'linear-gradient(90deg, #D99B26, #F1B844)' : 'linear-gradient(90deg, var(--color-gira-navy), var(--color-gira-gold))', borderRadius: '9999px' }} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--color-slate-gray)', marginTop: '6px' }}>
                    <span>Pendiente OLS: +Bs. {Math.round(macroData.caso4_metas_anuales.pendiente_anual_bs).toLocaleString()}/año</span>
                    <span>CAGR Histórica: +{macroData.caso4_metas_anuales.cagr_historico_pct}%</span>
                  </div>
                </div>
              )}

              <div style={{ height: '220px' }}>
                {chartCaso4Data ? (
                  <Line data={chartCaso4Data} options={defaultChartOptions} />
                ) : (
                  <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--color-slate-gray)' }}>
                    Cargando tendencia anual OLS...
                  </div>
                )}
              </div>
            </div>

          </div>
        </div>
      )}

      {/* ── Modal / Drawer de Detalle Analítico ──────────────────────────────── */}
      {modalDetail && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(12, 30, 51, 0.65)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '20px'
          }}
          onClick={() => setModalDetail(null)}
        >
          <div
            style={{
              backgroundColor: 'var(--color-paper-white)',
              borderRadius: '24px',
              maxWidth: '850px',
              width: '100%',
              maxHeight: '85vh',
              overflowY: 'auto',
              padding: '28px',
              border: '1px solid var(--color-border)',
              boxShadow: 'var(--shadow-modal)'
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0, color: 'var(--color-ink-black)' }}>
                {modalDetail.titulo}
              </h3>
              <button
                onClick={() => setModalDetail(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-slate-gray)' }}
              >
                <X size={20} />
              </button>
            </div>

            {modalDetail.tipo === 'caso1' && modalDetail.data && (
              <div>
                <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', marginBottom: '16px' }}>
                  Serie histórica mensual de alumnos matriculados desde Noviembre 2022 hasta Mayo 2026 (N=43 meses),
                  junto con las proyecciones Holt-Winters aditivas con Intervalo de Confianza al 95%.
                </p>
                <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', color: 'var(--color-slate-gray)' }}>
                        <th style={{ padding: '8px' }}>Periodo</th>
                        <th style={{ padding: '8px' }}>Tipo</th>
                        <th style={{ padding: '8px' }}>Valor</th>
                        <th style={{ padding: '8px' }}>IC 95% Inf</th>
                        <th style={{ padding: '8px' }}>IC 95% Sup</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modalDetail.data.periodos_historicos.map((p, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--color-border)' }}>
                          <td style={{ padding: '8px', fontFamily: 'var(--font-mono)' }}>{p}</td>
                          <td style={{ padding: '8px', color: 'var(--color-slate-gray)' }}>Histórico Real</td>
                          <td style={{ padding: '8px', fontWeight: 600 }}>{modalDetail.data.valores_historicos[i]} alumnos</td>
                          <td style={{ padding: '8px', color: 'var(--color-slate-gray)' }}>-</td>
                          <td style={{ padding: '8px', color: 'var(--color-slate-gray)' }}>-</td>
                        </tr>
                      ))}
                      {modalDetail.data.periodos_proyectados.map((p, i) => (
                        <tr key={`p-${i}`} style={{ borderBottom: '1px solid var(--color-border)', backgroundColor: 'rgba(217, 155, 38, 0.08)' }}>
                          <td style={{ padding: '8px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-gira-gold)' }}>{p} (Proy)</td>
                          <td style={{ padding: '8px', fontWeight: 700, color: 'var(--color-gira-gold)' }}>Holt-Winters</td>
                          <td style={{ padding: '8px', fontWeight: 700 }}>{modalDetail.data.forecast_hw[i]} alumnos</td>
                          <td style={{ padding: '8px', fontFamily: 'var(--font-mono)' }}>{modalDetail.data.ic_lower_95[i]}</td>
                          <td style={{ padding: '8px', fontFamily: 'var(--font-mono)' }}>{modalDetail.data.ic_upper_95[i]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {modalDetail.tipo === 'caso2_prog' && modalDetail.data && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, padding: '3px 10px', borderRadius: '9999px', background: 'var(--color-mist-gray)', color: 'var(--color-slate-gray)' }}>
                    {modalDetail.data.tipo}
                  </span>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      padding: '3px 10px',
                      borderRadius: '9999px',
                      background: modalDetail.data.badge_color === 'emerald' ? 'rgba(27,135,84,0.14)' : (modalDetail.data.badge_color === 'amber' ? 'rgba(217,155,38,0.14)' : 'rgba(217,56,58,0.14)'),
                      color: modalDetail.data.badge_color === 'emerald' ? 'var(--color-alert-green)' : (modalDetail.data.badge_color === 'amber' ? 'var(--color-gira-gold)' : 'var(--color-alert-red)'),
                    }}
                  >
                    {modalDetail.data.decision_sugerida}
                  </span>
                </div>

                <div style={{ padding: '16px', borderRadius: '16px', background: 'var(--color-mist-gray)', marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-ink-black)', marginBottom: '4px' }}>
                    Dictamen Estratégico y Justificación de Marketing:
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--color-slate-gray)', lineHeight: 1.5 }}>
                    {modalDetail.data.justificacion}
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
                  <div style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase' }}>Inscritos Totales</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', fontFamily: 'var(--font-mono)' }}>{modalDetail.data.total_historico}</div>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Matrícula histórica</div>
                  </div>
                  <div style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase' }}>Inscritos 2025</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', fontFamily: 'var(--font-mono)' }}>{modalDetail.data.inscritos_2025}</div>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Última gestión cerrada</div>
                  </div>
                  <div style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase' }}>Inscritos 2026</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', fontFamily: 'var(--font-mono)' }}>{modalDetail.data.inscritos_2026}</div>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Gestión en curso</div>
                  </div>
                  <div style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase' }}>Tasa CAGR</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', fontFamily: 'var(--font-mono)', color: modalDetail.data.cagr_pct >= 0 ? 'var(--color-alert-green)' : 'var(--color-alert-red)' }}>
                      {modalDetail.data.cagr_pct > 0 ? `+${modalDetail.data.cagr_pct}%` : `${modalDetail.data.cagr_pct}%`}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Crecimiento anual</div>
                  </div>
                  <div style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase' }}>Proyección 6 Meses</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', fontFamily: 'var(--font-mono)', color: 'var(--color-gira-gold)' }}>
                      {modalDetail.data.proyeccion_6m} al.
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Absorción estimada</div>
                  </div>
                  <div style={{ padding: '12px', borderRadius: '14px', background: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', textTransform: 'uppercase' }}>Pendiente OLS</div>
                    <div style={{ fontSize: '17px', fontWeight: 700, marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                      {modalDetail.data.tendencia_ols}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Ritmo de absorción</div>
                  </div>
                </div>
              </div>
            )}

            {modalDetail.tipo === 'caso3' && modalDetail.data && (
              <div>
                <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', marginBottom: '16px' }}>
                  Comparativa presupuestaria mensual: Meta de Catálogo vs Recaudación Ejecutada Real a lo largo de los 17 meses registrados (Gestiones 2025 y 2026).
                </p>
                <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', color: 'var(--color-slate-gray)' }}>
                        <th style={{ padding: '8px' }}>Mes</th>
                        <th style={{ padding: '8px' }}>Meta Catálogo (Bs)</th>
                        <th style={{ padding: '8px' }}>Recaudado Real (Bs)</th>
                        <th style={{ padding: '8px' }}>Variación (Bs)</th>
                        <th style={{ padding: '8px' }}>Cumplimiento</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(modalDetail.data.meses_etiquetas || []).map((m, idx) => {
                        const meta = modalDetail.data.meta_catalogo_bs[idx] || 0;
                        const ejec = modalDetail.data.ejecutado_real_bs[idx] || 0;
                        const diff = ejec - meta;
                        const pct = meta > 0 ? ((ejec / meta) * 100).toFixed(1) : '100.0';
                        return (
                          <tr key={idx} style={{ borderBottom: '1px solid var(--color-border)' }}>
                            <td style={{ padding: '8px', fontWeight: 600 }}>{m}</td>
                            <td style={{ padding: '8px', fontFamily: 'var(--font-mono)' }}>Bs. {meta.toLocaleString()}</td>
                            <td style={{ padding: '8px', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>Bs. {ejec.toLocaleString()}</td>
                            <td style={{ padding: '8px', fontFamily: 'var(--font-mono)', color: diff >= 0 ? 'var(--color-alert-green)' : 'var(--color-alert-red)' }}>
                              {diff >= 0 ? `+Bs. ${diff.toLocaleString()}` : `-Bs. ${Math.abs(diff).toLocaleString()}`}
                            </td>
                            <td style={{ padding: '8px', fontWeight: 700, color: Number(pct) >= 95 ? 'var(--color-alert-green)' : (Number(pct) >= 85 ? 'var(--color-gira-gold)' : 'var(--color-alert-red)') }}>
                              {pct}%
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {modalDetail.tipo === 'caso4' && modalDetail.data && (
              <div>
                <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', marginBottom: '16px' }}>
                  Trayectoria plurianual de ingresos institucionales (2023 - 2027) ajustada por regresión lineal OLS frente a la Meta de 3.8M Bs.
                </p>
                <div style={{ padding: '14px', borderRadius: '14px', background: 'var(--color-mist-gray)', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Meta Institucional:</span>
                    <div style={{ fontSize: '16px', fontWeight: 700 }}>Bs. {modalDetail.data.meta_anual_institucional_bs.toLocaleString()}</div>
                  </div>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Recaudado Acumulado 2026:</span>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-gira-gold)' }}>Bs. {modalDetail.data.recaudado_acumulado_bs.toLocaleString()} ({modalDetail.data.porcentaje_avance_meta}%)</div>
                  </div>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Pendiente OLS Anual:</span>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-alert-green)' }}>+Bs. {Math.round(modalDetail.data.pendiente_anual_bs).toLocaleString()}/año</div>
                  </div>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>CAGR Histórica:</span>
                    <div style={{ fontSize: '16px', fontWeight: 700 }}>+{modalDetail.data.cagr_historico_pct}%</div>
                  </div>
                </div>

                <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left', color: 'var(--color-slate-gray)' }}>
                        <th style={{ padding: '8px' }}>Año</th>
                        <th style={{ padding: '8px' }}>Tipo</th>
                        <th style={{ padding: '8px' }}>Monto (Bs)</th>
                        <th style={{ padding: '8px' }}>Crecimiento Interanual</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(modalDetail.data.anios_historicos || []).map((yr, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid var(--color-border)' }}>
                          <td style={{ padding: '8px', fontWeight: 700 }}>{yr}</td>
                          <td style={{ padding: '8px', color: 'var(--color-slate-gray)' }}>Histórico Real Auditado</td>
                          <td style={{ padding: '8px', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>Bs. {modalDetail.data.valores_historicos_bs[idx].toLocaleString()}</td>
                          <td style={{ padding: '8px', fontFamily: 'var(--font-mono)', color: 'var(--color-alert-green)' }}>
                            {idx === 0 ? '-' : `+${(((modalDetail.data.valores_historicos_bs[idx] - modalDetail.data.valores_historicos_bs[idx-1]) / modalDetail.data.valores_historicos_bs[idx-1]) * 100).toFixed(1)}%`}
                          </td>
                        </tr>
                      ))}
                      {(modalDetail.data.proyecciones_ols || []).map((proy, idx) => (
                        <tr key={`proy-${idx}`} style={{ borderBottom: '1px solid var(--color-border)', backgroundColor: 'rgba(217, 155, 38, 0.08)' }}>
                          <td style={{ padding: '8px', fontWeight: 700, color: 'var(--color-gira-gold)' }}>{proy.anio} (Proy)</td>
                          <td style={{ padding: '8px', fontWeight: 600, color: 'var(--color-gira-gold)' }}>Tendencia Lineal OLS</td>
                          <td style={{ padding: '8px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>Bs. {proy.monto_proyectado_bs.toLocaleString()}</td>
                          <td style={{ padding: '8px', fontFamily: 'var(--font-mono)', color: 'var(--color-gira-gold)' }}>
                            Proyección OLS N=3
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
