import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ShieldAlert,
  RefreshCw,
  Search,
  Filter,
  Download,
  FileSpreadsheet,
  Eye,
  EyeOff,
  X,
  CheckCircle2,
  BookOpen,
  CreditCard,
  ShieldCheck,
  Layers,
  UserCheck,
  Hash,
} from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import { academicApi } from '../../api/academicApi';
import { useAuth } from '../../context/AuthContext';

export default function RendimientoAlertas() {
  const { role } = useAuth();
  const canRevealPii = ['ADMIN', 'DIRECTOR_ACADEMICO', 'ANALISTA_FINANCIERO', 'AUDITOR_CALIDAD'].includes(role);

  const [revealCi, setRevealCi] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Filtros multi-criterio (sin forzar 2026-II fijo; por defecto TODOS)
  const [periodo, setPeriodo] = useState('TODOS');
  const [programa, setPrograma] = useState('TODOS');
  const [modulo, setModulo] = useState('TODOS');
  const [docente, setDocente] = useState('TODOS');
  const [reglaFiltro, setReglaFiltro] = useState('TODOS');
  const [busqueda, setBusqueda] = useState('');

  // Estado devuelto por el motor determinístico IF/THEN del backend
  const [datosAlertas, setDatosAlertas] = useState({
    motor_reglas: 'DETERMINISTICO_IF_THEN_ESTRICTO',
    total_matricula_activa: 0,
    tarjetas: {
      riesgo_academico: {
        codigo: 'ACADEMICO',
        titulo: 'RIESGO ACADÉM.',
        regla_texto: 'Regla: Promedio <= 70',
        severidad: 'ROJO',
        total_alumnos: 0,
        porcentaje_matricula: 0,
        subtitulo_secundario: '0.0% de matrícula',
      },
      riesgo_desercion: {
        codigo: 'DESERCION',
        titulo: 'RIESGO DESERC.',
        regla_texto: 'Regla: Incumpl. > 30%',
        severidad: 'ROJO',
        total_alumnos: 0,
        porcentaje_matricula: 0,
        subtitulo_secundario: '0.0% de matrícula',
      },
      riesgo_financiero: {
        codigo: 'FINANCIERO',
        titulo: 'RIESGO FINANC.',
        regla_texto: 'Regla: Mora >= 2 Cuot.',
        severidad: 'AMBAR',
        total_alumnos: 0,
        porcentaje_matricula: 0,
        monto_mora_bs: 0,
        subtitulo_secundario: '0 Bs en mora',
      },
      alerta_critica: {
        codigo: 'CRITICA',
        titulo: 'ALERTA CRÍTICA',
        regla_texto: '(2 o + Reglas)',
        severidad: 'CRITICO',
        total_alumnos: 0,
        porcentaje_matricula: 0,
        subtitulo_secundario: 'Prioridad Alta',
      },
    },
    matriz_interseccion: [
      { codigo: 'A+D', etiqueta: 'Académico + Deserción (A+D)', total_alumnos: 0 },
      { codigo: 'D+F', etiqueta: 'Deserción + Financiero (D+F)', total_alumnos: 0 },
      { codigo: 'A+F', etiqueta: 'Académico + Financiero (A+F)', total_alumnos: 0 },
      { codigo: 'A+D+F', etiqueta: 'Triple Alerta (A+D+F)', total_alumnos: 0 },
    ],
    top_programas: [],
    filtros_disponibles: {
      periodos: [],
      programas: [],
      modulos: [],
      docentes: [],
    },
    total_estudiantes_filtrados: 0,
    estudiantes: [],
  });

  // Selección de alumno y Modal de Ficha Cruzada Académico-Financiera
  const [selectedStudentId, setSelectedStudentId] = useState(null);
  const [fichaModalOpen, setFichaModalOpen] = useState(false);
  const [fichaLoading, setFichaLoading] = useState(false);
  const [fichaData, setFichaData] = useState(null);

  const maskCi = (ci) => {
    if (!ci || ci === 'S/C') return 'S/C';
    const str = String(ci).trim();
    if (revealCi && canRevealPii) return str;
    if (str.length <= 4) return str;
    return `${str.slice(0, 3)}***${str.slice(-2)}`;
  };

  const cargarAlertas = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg('');
    try {
      const res = await academicApi.getAlertasTempranas({
        periodo,
        programa,
        modulo,
        docente,
        regla_filtro: reglaFiltro,
        busqueda: busqueda.trim() || undefined,
      });
      if (res && res.status === 'success') {
        setDatosAlertas(res);
        if (res.estudiantes?.length > 0 && !selectedStudentId) {
          setSelectedStudentId(res.estudiantes[0].id_estudiante);
        }
      }
    } catch (err) {
      console.error('Error al consultar el motor determinístico de alertas tempranas:', err);
      setErrorMsg('No se pudo sincronizar con el motor determinístico de alertas tempranas.');
    } finally {
      setIsLoading(false);
    }
  }, [periodo, programa, modulo, docente, reglaFiltro, busqueda, selectedStudentId]);

  useEffect(() => {
    cargarAlertas();
  }, [cargarAlertas]);

  const handleToggleRegla = (codigo) => {
    setReglaFiltro((prev) => (prev === codigo ? 'TODOS' : codigo));
  };

  const handleResetFiltros = () => {
    setPeriodo('TODOS');
    setPrograma('TODOS');
    setModulo('TODOS');
    setDocente('TODOS');
    setReglaFiltro('TODOS');
    setBusqueda('');
  };

  const handleOpenFicha = async (idEst) => {
    const targetId = idEst || selectedStudentId || datosAlertas.estudiantes?.[0]?.id_estudiante;
    if (!targetId) return;
    setSelectedStudentId(targetId);
    setFichaModalOpen(true);
    setFichaLoading(true);
    try {
      const res = await academicApi.getFichaCruzadaEstudiante(targetId);
      setFichaData(res);
    } catch (err) {
      console.error('Error al obtener la ficha cruzada del estudiante:', err);
      setFichaData(null);
    } finally {
      setFichaLoading(false);
    }
  };

  const handleExportarCsv = () => {
    const filas = datosAlertas.estudiantes || [];
    if (filas.length === 0) return;

    const cabeceras = [
      'ID_ESTUDIANTE',
      'CI',
      'ESTUDIANTE',
      'PROGRAMA',
      'MODULO',
      'DOCENTE',
      'PERIODO',
      'PROMEDIO_NOTAS',
      'INCUMPLIMIENTO_PCT',
      'CUOTAS_MORA',
      'DEUDA_MORA_BS',
      'TAG_REGLAS',
      'PRIORIDAD',
    ];

    const escapar = (val) => {
      const s = String(val ?? '').replace(/"/g, '""');
      return `"${s}"`;
    };

    const lineas = [
      cabeceras.join(','),
      ...filas.map((est) =>
        [
          est.id_estudiante,
          maskCi(est.ci),
          est.nombre_completo,
          est.programa,
          est.modulo,
          est.docente,
          est.periodo,
          est.promedio_notas !== null && est.promedio_notas !== undefined ? est.promedio_notas.toFixed(1) : 'N/D',
          Number(est.incumplimiento_pct || 0).toFixed(1),
          est.cuotas_mora || 0,
          Number(est.deuda_mora_bs || 0).toFixed(2),
          est.tag,
          est.prioridad,
        ]
          .map(escapar)
          .join(',')
      ),
    ];

    const blob = new Blob(['\uFEFF' + lineas.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `alertas_tempranas_if_then_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const tarjetas = datosAlertas.tarjetas || {};
  const cardList = [
    {
      key: 'riesgo_academico',
      data: tarjetas.riesgo_academico || {},
      badgeText: '[ROJO] RIESGO ACADÉM.',
      accentColor: '#D9383A',
      bgTint: 'rgba(217, 56, 58, 0.08)',
      icon: AlertCircle,
    },
    {
      key: 'riesgo_desercion',
      data: tarjetas.riesgo_desercion || {},
      badgeText: '[ROJO] RIESGO DESERC.',
      accentColor: '#D9383A',
      bgTint: 'rgba(217, 56, 58, 0.08)',
      icon: AlertTriangle,
    },
    {
      key: 'riesgo_financiero',
      data: tarjetas.riesgo_financiero || {},
      badgeText: '[ÁMBAR] RIESGO FINANC.',
      accentColor: '#D99B26',
      bgTint: 'rgba(217, 155, 38, 0.10)',
      icon: CreditCard,
    },
    {
      key: 'alerta_critica',
      data: tarjetas.alerta_critica || {},
      badgeText: 'ALERTA CRÍTICA',
      accentColor: '#991B1B',
      bgTint: 'rgba(153, 27, 27, 0.10)',
      icon: ShieldAlert,
    },
  ];

  const getTagStyle = (tag) => {
    if (tag?.includes('+')) {
      return {
        backgroundColor: 'rgba(217, 56, 58, 0.14)',
        color: '#D9383A',
        border: '1px solid rgba(217, 56, 58, 0.38)',
      };
    }
    if (tag === 'F') {
      return {
        backgroundColor: 'rgba(217, 155, 38, 0.15)',
        color: '#D99B26',
        border: '1px solid rgba(217, 155, 38, 0.4)',
      };
    }
    return {
      backgroundColor: 'rgba(217, 56, 58, 0.10)',
      color: '#D9383A',
      border: '1px solid rgba(217, 56, 58, 0.28)',
    };
  };

  return (
    <div className="module-container" style={{ maxWidth: '1400px', margin: '0 auto', paddingBottom: '64px' }}>
      {/* ── Encabezado Institucional ── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: '18px',
        }}
      >
        <PageHeader
          category="DIRECCIÓN ACADÉMICA & FINANCIERA · VISTA 3"
          title="Monitoreo de Reglas de Umbral y"
          italicWord="Alertas Tempranas"
          subtitle="Auditoría determinística estricta (IF/THEN) sobre tablas de hechos consolidadas (fact_rendimiento_academico y fact_situacion_financiera) sin incertidumbre estadística individual."
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '16px', flexWrap: 'wrap' }}>
          {canRevealPii && (
            <button
              type="button"
              onClick={() => setRevealCi((prev) => !prev)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '7px',
                padding: '8px 13px',
                fontSize: '12.5px',
                fontWeight: 600,
                borderRadius: '10px',
                border: '1px solid var(--color-border)',
                background: 'var(--color-paper-white)',
                color: 'var(--color-ink-black)',
                cursor: 'pointer',
              }}
              title="Conmutar visualización de Cédula de Identidad"
            >
              {revealCi ? <EyeOff size={14} /> : <Eye size={14} />}
              {revealCi ? 'Ocultar CI' : 'Revelar CI'}
            </button>
          )}
          <button
            type="button"
            onClick={cargarAlertas}
            disabled={isLoading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 14px',
              fontSize: '12.5px',
              fontWeight: 700,
              borderRadius: '10px',
              border: '1px solid rgba(217, 155, 38, 0.45)',
              background: '#0C1E33',
              color: '#FAF9F6',
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} style={{ color: '#D99B26' }} />
            Evaluar Reglas IF/THEN
          </button>
        </div>
      </div>

      {/* ── BANNER DE GOBERNANZA Y FILTROS MULTI-CRITERIO ── */}
      <div
        style={{
          background: 'var(--color-paper-white)',
          border: '1px solid var(--color-border)',
          borderRadius: '18px',
          padding: '16px 20px',
          marginBottom: '22px',
          boxShadow: '0 4px 16px rgba(12, 30, 51, 0.04)',
        }}
      >
        {/* Banner superior de gobernanza */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
            paddingBottom: '14px',
            marginBottom: '14px',
            borderBottom: '1px solid var(--color-border)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                borderRadius: '999px',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                backgroundColor: 'rgba(12, 30, 51, 0.9)',
                color: '#D99B26',
                border: '1px solid rgba(217, 155, 38, 0.35)',
              }}
            >
              <ShieldCheck size={13} />
              BANNER DE GOBERNANZA
            </span>
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-ink-black)' }}>
              Motor Determinístico de Reglas Fijas (IF/THEN) — Sin inferencia ML individual
            </span>
          </div>
          <div
            style={{
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-slate-gray)',
            }}
          >
            Matrícula Activa Auditada:{' '}
            <strong style={{ color: 'var(--color-ink-black)' }}>
              {Number(datosAlertas.total_matricula_activa || 0).toLocaleString()} alumnos
            </strong>
          </div>
        </div>

        {/* Barra de Filtros Multi-Criterio */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '12px',
            alignItems: 'end',
          }}
        >
          <div>
            <label
              style={{
                display: 'block',
                fontSize: '11px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                color: 'var(--color-slate-gray)',
                marginBottom: '5px',
              }}
            >
              Periodo (Multi-Semestre)
            </label>
            <select
              value={periodo}
              onChange={(e) => setPeriodo(e.target.value)}
              className="form-input"
              style={{ width: '100%', padding: '8px 12px', fontSize: '12.5px' }}
            >
              <option value="TODOS">Todos los periodos</option>
              {(datosAlertas.filtros_disponibles?.periodos || []).map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              style={{
                display: 'block',
                fontSize: '11px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                color: 'var(--color-slate-gray)',
                marginBottom: '5px',
              }}
            >
              Programa Académico
            </label>
            <select
              value={programa}
              onChange={(e) => setPrograma(e.target.value)}
              className="form-input"
              style={{ width: '100%', padding: '8px 12px', fontSize: '12.5px' }}
            >
              <option value="TODOS">Todos los programas</option>
              {(datosAlertas.filtros_disponibles?.programas || []).map((prog) => (
                <option key={prog} value={prog}>
                  {prog}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              style={{
                display: 'block',
                fontSize: '11px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                color: 'var(--color-slate-gray)',
                marginBottom: '5px',
              }}
            >
              Módulo Curricular
            </label>
            <select
              value={modulo}
              onChange={(e) => setModulo(e.target.value)}
              className="form-input"
              style={{ width: '100%', padding: '8px 12px', fontSize: '12.5px' }}
            >
              <option value="TODOS">Todos los módulos</option>
              {(datosAlertas.filtros_disponibles?.modulos || []).map((mod) => (
                <option key={mod} value={mod}>
                  {mod}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              style={{
                display: 'block',
                fontSize: '11px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                color: 'var(--color-slate-gray)',
                marginBottom: '5px',
              }}
            >
              Docente
            </label>
            <select
              value={docente}
              onChange={(e) => setDocente(e.target.value)}
              className="form-input"
              style={{ width: '100%', padding: '8px 12px', fontSize: '12.5px' }}
            >
              <option value="TODOS">Todos los docentes</option>
              {(datosAlertas.filtros_disponibles?.docentes || []).map((doc) => (
                <option key={doc} value={doc}>
                  {doc}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              style={{
                display: 'block',
                fontSize: '11px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                color: 'var(--color-slate-gray)',
                marginBottom: '5px',
              }}
            >
              Búsqueda Nominal (CI / Alumno)
            </label>
            <div style={{ position: 'relative' }}>
              <Search
                size={14}
                style={{
                  position: 'absolute',
                  left: '11px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--color-slate-gray)',
                }}
              />
              <input
                type="text"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder="CI o apellido..."
                className="form-input"
                style={{ width: '100%', padding: '8px 12px 8px 32px', fontSize: '12.5px' }}
              />
            </div>
          </div>
        </div>

        {(periodo !== 'TODOS' ||
          programa !== 'TODOS' ||
          modulo !== 'TODOS' ||
          docente !== 'TODOS' ||
          reglaFiltro !== 'TODOS' ||
          busqueda.trim() !== '') && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: '12px',
              paddingTop: '10px',
              borderTop: '1px dashed var(--color-border)',
              fontSize: '12px',
            }}
          >
            <span style={{ color: 'var(--color-slate-gray)' }}>
              Filtro de Regla Activo:{' '}
              <strong style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-ink-black)' }}>
                {reglaFiltro}
              </strong>
            </span>
            <button
              type="button"
              onClick={handleResetFiltros}
              style={{
                background: 'none',
                border: 'none',
                color: '#D99B26',
                fontWeight: 700,
                fontSize: '12px',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
            >
              Restablecer todos los filtros
            </button>
          </div>
        )}
      </div>

      {errorMsg && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '12px',
            backgroundColor: 'rgba(217, 56, 58, 0.1)',
            border: '1px solid rgba(217, 56, 58, 0.35)',
            color: '#D9383A',
            fontSize: '13px',
            marginBottom: '20px',
          }}
        >
          {errorMsg}
        </div>
      )}

      {/* ── SECCIÓN TARJETAS SEMAFÓRICAS DE REGLAS DETERMINÍSTICAS (Click para filtrar) ── */}
      <div style={{ marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span
          style={{
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.6px',
            color: 'var(--color-slate-gray)',
          }}
        >
          TARJETAS SEMAFÓRICAS DE REGLAS DETERMINÍSTICAS (Click para filtrar tabla nominal)
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        {cardList.map(({ key, data, badgeText, accentColor, bgTint, icon: Icon }) => {
          const isSelected = reglaFiltro === data.codigo;
          return (
            <button
              key={key}
              type="button"
              onClick={() => handleToggleRegla(data.codigo)}
              style={{
                textAlign: 'left',
                padding: '18px 20px',
                borderRadius: '18px',
                background: 'var(--color-paper-white)',
                border: isSelected ? `2px solid ${accentColor}` : '1px solid var(--color-border)',
                boxShadow: isSelected
                  ? `0 8px 24px ${bgTint}`
                  : '0 2px 10px rgba(12, 30, 51, 0.04)',
                cursor: 'pointer',
                transition: 'all 0.18s ease',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '8px',
                }}
              >
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '3px 9px',
                    borderRadius: '6px',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 800,
                    backgroundColor: bgTint,
                    color: accentColor,
                  }}
                >
                  <Icon size={13} />
                  {badgeText}
                </span>
                {isSelected && (
                  <span
                    style={{
                      fontSize: '10px',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      color: accentColor,
                    }}
                  >
                    ● FILTRO ACTIVO
                  </span>
                )}
              </div>

              <div
                style={{
                  fontSize: '12px',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  color: 'var(--color-slate-gray)',
                  marginBottom: '10px',
                }}
              >
                {data.regla_texto}
              </div>

              <div
                className="serif-display"
                style={{
                  fontSize: '30px',
                  fontWeight: 700,
                  color: 'var(--color-ink-black)',
                  lineHeight: 1.1,
                }}
              >
                {Number(data.total_alumnos || 0).toLocaleString()}{' '}
                <span style={{ fontSize: '15px', fontWeight: 500, color: 'var(--color-slate-gray)' }}>
                  Alumnos
                </span>
              </div>

              <div
                style={{
                  marginTop: '8px',
                  fontSize: '12px',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  color: accentColor,
                }}
              >
                {data.subtitulo_secundario}
              </div>
            </button>
          );
        })}
      </div>

      {/* ── GRILLA PRINCIPAL 4 COL (MATRIZ DE INTERSECCIÓN) + 8 COL (TABLA NOMINAL) ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(12, minmax(0, 1fr))',
          gap: '20px',
          alignItems: 'start',
        }}
      >
        {/* Panel Izquierdo: Matriz de Intersección de Riesgos y Top Programas (4 Col en Desktop, 12 en Móvil) */}
        <div
          style={{
            gridColumn: 'span 12',
          }}
          className="vista3-left-col"
        >
          <div
            style={{
              background: 'var(--color-paper-white)',
              border: '1px solid var(--color-border)',
              borderRadius: '18px',
              padding: '20px',
              boxShadow: '0 4px 16px rgba(12, 30, 51, 0.04)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <Layers size={16} style={{ color: '#D99B26' }} />
              <h3
                style={{
                  fontSize: '13.5px',
                  fontWeight: 800,
                  textTransform: 'uppercase',
                  letterSpacing: '0.4px',
                  color: 'var(--color-ink-black)',
                  margin: 0,
                }}
              >
                Matriz de Intersección de Riesgos
              </h3>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginBottom: '14px' }}>
              Desglose de Co-ocurrencia determinística (Click para aislar casos):
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '22px' }}>
              {(datosAlertas.matriz_interseccion || []).map((item) => {
                const active = reglaFiltro === item.codigo;
                const isTriple = item.codigo === 'A+D+F';
                return (
                  <button
                    key={item.codigo}
                    type="button"
                    onClick={() => handleToggleRegla(item.codigo)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 12px',
                      borderRadius: '10px',
                      border: active
                        ? '1.5px solid #D9383A'
                        : '1px solid var(--color-border)',
                      background: active
                        ? 'rgba(217, 56, 58, 0.10)'
                        : 'var(--color-fog-white)',
                      color: 'var(--color-ink-black)',
                      cursor: 'pointer',
                      textAlign: 'left',
                    }}
                  >
                    <span style={{ fontSize: '12.5px', fontWeight: isTriple ? 700 : 600 }}>
                      • {item.etiqueta}
                    </span>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '12px',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '999px',
                        backgroundColor:
                          item.total_alumnos > 0
                            ? 'rgba(217, 56, 58, 0.14)'
                            : 'rgba(119, 123, 134, 0.12)',
                        color: item.total_alumnos > 0 ? '#D9383A' : 'var(--color-slate-gray)',
                      }}
                    >
                      {item.total_alumnos} casos
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Top Programas con Mayor Riesgo */}
            <div
              style={{
                borderTop: '1px solid var(--color-border)',
                paddingTop: '16px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <BookOpen size={15} style={{ color: '#D99B26' }} />
                <h4
                  style={{
                    fontSize: '12.5px',
                    fontWeight: 800,
                    textTransform: 'uppercase',
                    letterSpacing: '0.4px',
                    color: 'var(--color-ink-black)',
                    margin: 0,
                  }}
                >
                  Top Programas con Mayor Riesgo
                </h4>
              </div>

              {(datosAlertas.top_programas || []).length === 0 ? (
                <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', padding: '8px 0' }}>
                  Sin programas afectados bajo los filtros actuales.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {datosAlertas.top_programas.map((tp, idx) => {
                    const maxAf = Math.max(1, datosAlertas.top_programas[0]?.total_afectados || 1);
                    const pctBar = Math.min(100, Math.round((tp.total_afectados / maxAf) * 100));
                    return (
                      <div
                        key={tp.programa}
                        onClick={() => setPrograma((prev) => (prev === tp.programa ? 'TODOS' : tp.programa))}
                        style={{
                          padding: '8px 10px',
                          borderRadius: '10px',
                          border:
                            programa === tp.programa
                              ? '1px solid #D99B26'
                              : '1px solid var(--color-border)',
                          background: 'var(--color-fog-white)',
                          cursor: 'pointer',
                        }}
                        title={`Filtrar por ${tp.programa}`}
                      >
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            gap: '8px',
                            fontSize: '12px',
                            marginBottom: '5px',
                          }}
                        >
                          <span
                            style={{
                              fontWeight: 600,
                              color: 'var(--color-ink-black)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {idx + 1}. {tp.codigo_programa}: {tp.programa}
                          </span>
                          <span
                            style={{
                              fontFamily: 'var(--font-mono)',
                              fontSize: '11.5px',
                              fontWeight: 700,
                              color: '#D99B26',
                              flexShrink: 0,
                            }}
                          >
                            ({tp.total_afectados} afectados)
                          </span>
                        </div>
                        <div
                          style={{
                            height: '5px',
                            borderRadius: '999px',
                            backgroundColor: 'rgba(119, 123, 134, 0.16)',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              width: `${pctBar}%`,
                              height: '100%',
                              backgroundColor: idx === 0 ? '#D9383A' : '#D99B26',
                              borderRadius: '999px',
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Panel Derecho: Tabla Nominal de Intervención (8 Col en Desktop, 12 en Móvil) */}
        <div
          style={{
            gridColumn: 'span 12',
          }}
          className="vista3-right-col"
        >
          <div
            style={{
              background: 'var(--color-paper-white)',
              border: '1px solid var(--color-border)',
              borderRadius: '18px',
              padding: '20px',
              boxShadow: '0 4px 16px rgba(12, 30, 51, 0.04)',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '12px',
                marginBottom: '16px',
              }}
            >
              <div>
                <h3
                  style={{
                    fontSize: '14px',
                    fontWeight: 800,
                    textTransform: 'uppercase',
                    letterSpacing: '0.4px',
                    color: 'var(--color-ink-black)',
                    margin: 0,
                  }}
                >
                  Tabla Nominal de Intervención (Estudiantes en Alerta)
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '3px 0 0' }}>
                  Valores entre corchetes{' '}
                  <code style={{ fontFamily: 'var(--font-mono)', color: '#D9383A', fontWeight: 700 }}>
                    [valor]
                  </code>{' '}
                  indican la condición exacta que activó el umbral determinístico IF/THEN.
                </p>
              </div>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  fontWeight: 700,
                  padding: '4px 10px',
                  borderRadius: '999px',
                  backgroundColor: 'rgba(12, 30, 51, 0.08)',
                  color: 'var(--color-ink-black)',
                  border: '1px solid var(--color-border)',
                }}
              >
                {datosAlertas.total_estudiantes_filtrados || 0} registros en alerta
              </span>
            </div>

            <ResponsiveTable>
              <table className="steep-table">
                <thead>
                  <tr>
                    <th>CI</th>
                    <th>Estudiante</th>
                    <th>Programa / Módulo</th>
                    <th style={{ textAlign: 'center' }}>Prom. Notas</th>
                    <th style={{ textAlign: 'center' }}>% Incumpl.</th>
                    <th style={{ textAlign: 'center' }}>Mora</th>
                    <th style={{ textAlign: 'center' }}>Tag</th>
                    <th style={{ textAlign: 'right' }}>Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {(datosAlertas.estudiantes || []).length === 0 ? (
                    <tr>
                      <td
                        colSpan="8"
                        style={{
                          textAlign: 'center',
                          padding: '42px 20px',
                          color: 'var(--color-slate-gray)',
                        }}
                      >
                        No se encontraron estudiantes que disparen las reglas determinísticas con los filtros seleccionados.
                      </td>
                    </tr>
                  ) : (
                    datosAlertas.estudiantes.map((est) => {
                      const isRowSelected = selectedStudentId === est.id_estudiante;
                      const promStr =
                        est.promedio_notas !== null && est.promedio_notas !== undefined
                          ? Number(est.promedio_notas).toFixed(1)
                          : 'N/D';
                      const incStr = `${Number(est.incumplimiento_pct || 0).toFixed(1)}%`;
                      const moraStr = String(est.cuotas_mora || 0);

                      return (
                        <tr
                          key={est.id_estudiante}
                          onClick={() => setSelectedStudentId(est.id_estudiante)}
                          style={{
                            cursor: 'pointer',
                            backgroundColor: isRowSelected ? 'rgba(217, 155, 38, 0.08)' : undefined,
                          }}
                        >
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600 }}>
                            {maskCi(est.ci)}
                          </td>
                          <td>
                            <div style={{ fontWeight: 700, color: 'var(--color-ink-black)', fontSize: '13px' }}>
                              {est.nombre_completo}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>
                              Periodo: {est.periodo} · Docente: {est.docente}
                            </div>
                          </td>
                          <td>
                            <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
                              {est.programa}
                            </div>
                            <div style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)' }}>
                              {est.modulo}
                            </div>
                          </td>
                          <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '12.5px' }}>
                            {est.regla_academico ? (
                              <span
                                style={{
                                  padding: '3px 7px',
                                  borderRadius: '6px',
                                  fontWeight: 800,
                                  backgroundColor: 'rgba(217, 56, 58, 0.14)',
                                  color: '#D9383A',
                                  border: '1px solid rgba(217, 56, 58, 0.35)',
                                }}
                              >
                                [{promStr}]
                              </span>
                            ) : (
                              <span style={{ color: 'var(--color-ink-black)' }}>{promStr}</span>
                            )}
                          </td>
                          <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '12.5px' }}>
                            {est.regla_desercion ? (
                              <span
                                style={{
                                  padding: '3px 7px',
                                  borderRadius: '6px',
                                  fontWeight: 800,
                                  backgroundColor: 'rgba(217, 56, 58, 0.14)',
                                  color: '#D9383A',
                                  border: '1px solid rgba(217, 56, 58, 0.35)',
                                }}
                              >
                                [{incStr}]
                              </span>
                            ) : (
                              <span style={{ color: 'var(--color-slate-gray)' }}>{incStr}</span>
                            )}
                          </td>
                          <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '12.5px' }}>
                            {est.regla_financiero ? (
                              <span
                                style={{
                                  padding: '3px 7px',
                                  borderRadius: '6px',
                                  fontWeight: 800,
                                  backgroundColor: 'rgba(217, 155, 38, 0.16)',
                                  color: '#D99B26',
                                  border: '1px solid rgba(217, 155, 38, 0.45)',
                                }}
                              >
                                [{moraStr}]
                              </span>
                            ) : (
                              <span style={{ color: 'var(--color-slate-gray)' }}>{moraStr}</span>
                            )}
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            <span
                              style={{
                                display: 'inline-block',
                                fontFamily: 'var(--font-mono)',
                                fontSize: '11px',
                                fontWeight: 800,
                                padding: '3px 8px',
                                borderRadius: '6px',
                                ...getTagStyle(est.tag),
                              }}
                            >
                              {est.tag}
                            </span>
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenFicha(est.id_estudiante);
                              }}
                              style={{
                                padding: '5px 10px',
                                fontSize: '11.5px',
                                fontWeight: 700,
                                borderRadius: '8px',
                                border: '1px solid var(--color-border)',
                                background: 'var(--color-fog-white)',
                                color: 'var(--color-ink-black)',
                                cursor: 'pointer',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              Ver Ficha
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </ResponsiveTable>

            {/* Barra de acciones al pie de la Tabla Nominal */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '12px',
                marginTop: '18px',
                paddingTop: '16px',
                borderTop: '1px solid var(--color-border)',
              }}
            >
              <button
                type="button"
                onClick={() => handleOpenFicha(selectedStudentId)}
                disabled={(datosAlertas.estudiantes || []).length === 0}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '9px 16px',
                  borderRadius: '10px',
                  fontSize: '12.5px',
                  fontWeight: 700,
                  border: '1px solid rgba(217, 155, 38, 0.45)',
                  background: '#0C1E33',
                  color: '#FAF9F6',
                  cursor: (datosAlertas.estudiantes || []).length === 0 ? 'not-allowed' : 'pointer',
                  opacity: (datosAlertas.estudiantes || []).length === 0 ? 0.5 : 1,
                }}
              >
                <UserCheck size={15} style={{ color: '#D99B26' }} />
                [Ver Ficha Cruzada Académico-Financiera]
              </button>

              <button
                type="button"
                onClick={handleExportarCsv}
                disabled={(datosAlertas.estudiantes || []).length === 0}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '9px 16px',
                  borderRadius: '10px',
                  fontSize: '12.5px',
                  fontWeight: 700,
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-paper-white)',
                  color: 'var(--color-ink-black)',
                  cursor: (datosAlertas.estudiantes || []).length === 0 ? 'not-allowed' : 'pointer',
                  opacity: (datosAlertas.estudiantes || []).length === 0 ? 0.5 : 1,
                }}
              >
                <Download size={15} />
                [Exportar CSV]
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Responsive CSS para las 4 + 8 columnas en escritorio (>= 1024px) */}
      <style>{`
        @media (min-width: 1024px) {
          .vista3-left-col {
            grid-column: span 4 !important;
          }
          .vista3-right-col {
            grid-column: span 8 !important;
          }
        }
      `}</style>

      {/* ── MODAL: FICHA CRUZADA ACADÉMICO-FINANCIERA DEL ESTUDIANTE ── */}
      {fichaModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Ficha Cruzada Académico-Financiera del Estudiante"
          onClick={() => setFichaModalOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            backgroundColor: 'rgba(12, 30, 51, 0.68)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: '980px',
              maxHeight: '88vh',
              overflowY: 'auto',
              background: 'var(--color-paper-white)',
              border: '1px solid var(--color-border)',
              borderRadius: '20px',
              padding: '24px',
              boxShadow: '0 24px 48px rgba(0, 0, 0, 0.32)',
            }}
          >
            {/* Cabecera del Modal */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                gap: '16px',
                paddingBottom: '16px',
                borderBottom: '1px solid var(--color-border)',
                marginBottom: '18px',
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                    color: '#D99B26',
                    textTransform: 'uppercase',
                    letterSpacing: '0.6px',
                  }}
                >
                  EXPEDIENTE UNIFICADO · ESQUEMA CONSTELACIÓN
                </div>
                <h2
                  className="serif-display"
                  style={{
                    fontSize: '24px',
                    fontWeight: 700,
                    color: 'var(--color-ink-black)',
                    margin: '4px 0',
                  }}
                >
                  {fichaData?.nombre_completo || 'Cargando Ficha Cruzada...'}
                </h2>
                {fichaData && (
                  <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)', display: 'flex', gap: '14px', flexWrap: 'wrap' }}>
                    <span>
                      CI: <strong style={{ fontFamily: 'var(--font-mono)' }}>{maskCi(fichaData.ci)}</strong>
                    </span>
                    <span>
                      Programa Origen: <strong>{fichaData.programa_origen}</strong>
                    </span>
                    <span>
                      Sede/Ciudad: <strong>{fichaData.ciudad}</strong>
                    </span>
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={() => setFichaModalOpen(false)}
                style={{
                  padding: '8px',
                  borderRadius: '10px',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-fog-white)',
                  color: 'var(--color-ink-black)',
                  cursor: 'pointer',
                }}
                aria-label="Cerrar Ficha Cruzada"
              >
                <X size={18} />
              </button>
            </div>

            {fichaLoading ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-slate-gray)' }}>
                Consultando tablas de hechos consolidadas...
              </div>
            ) : !fichaData ? (
              <div style={{ padding: '40px', textAlign: 'center', color: '#D9383A' }}>
                No se pudo cargar la información del estudiante.
              </div>
            ) : (
              <>
                {/* Resumen de evaluación determinística del alumno */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: '12px',
                    marginBottom: '22px',
                  }}
                >
                  <div
                    style={{
                      padding: '12px 14px',
                      borderRadius: '12px',
                      background: 'var(--color-fog-white)',
                      border: '1px solid var(--color-border)',
                    }}
                  >
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Promedio de Notas</div>
                    <div
                      style={{
                        fontSize: '20px',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 800,
                        color: fichaData.resumen_reglas?.regla_academico ? '#D9383A' : '#1B8754',
                      }}
                    >
                      {fichaData.resumen_reglas?.promedio_notas ?? 'N/D'} pts
                    </div>
                  </div>

                  <div
                    style={{
                      padding: '12px 14px',
                      borderRadius: '12px',
                      background: 'var(--color-fog-white)',
                      border: '1px solid var(--color-border)',
                    }}
                  >
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>% Incumplimiento Máx.</div>
                    <div
                      style={{
                        fontSize: '20px',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 800,
                        color: fichaData.resumen_reglas?.regla_desercion ? '#D9383A' : 'var(--color-ink-black)',
                      }}
                    >
                      {Number(fichaData.resumen_reglas?.incumplimiento_max_pct || 0).toFixed(1)}%
                    </div>
                  </div>

                  <div
                    style={{
                      padding: '12px 14px',
                      borderRadius: '12px',
                      background: 'var(--color-fog-white)',
                      border: '1px solid var(--color-border)',
                    }}
                  >
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Cuotas Impagas (Mora)</div>
                    <div
                      style={{
                        fontSize: '20px',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 800,
                        color: fichaData.resumen_reglas?.regla_financiero ? '#D99B26' : 'var(--color-ink-black)',
                      }}
                    >
                      {fichaData.resumen_reglas?.cuotas_mora_total || 0} cuotas
                    </div>
                  </div>

                  <div
                    style={{
                      padding: '12px 14px',
                      borderRadius: '12px',
                      background: 'var(--color-fog-white)',
                      border: '1px solid var(--color-border)',
                    }}
                  >
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Deuda Total Exigible</div>
                    <div
                      style={{
                        fontSize: '20px',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 800,
                        color: 'var(--color-ink-black)',
                      }}
                    >
                      Bs. {Number(fichaData.resumen_reglas?.deuda_total_bs || 0).toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* Hechos Académicos */}
                <h4
                  style={{
                    fontSize: '13px',
                    fontWeight: 800,
                    textTransform: 'uppercase',
                    letterSpacing: '0.4px',
                    color: 'var(--color-ink-black)',
                    marginBottom: '10px',
                  }}
                >
                  1. Historial en fact_rendimiento_academico ({fichaData.historial_academico?.length || 0})
                </h4>
                <ResponsiveTable>
                  <table className="steep-table" style={{ marginBottom: '22px' }}>
                    <thead>
                      <tr>
                        <th>Periodo</th>
                        <th>Programa / Módulo</th>
                        <th>Docente</th>
                        <th>Nota Final</th>
                        <th>% Incumpl.</th>
                        <th>Regla Evaluada</th>
                        <th>Trazabilidad SHA-256</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(fichaData.historial_academico || []).length === 0 ? (
                        <tr>
                          <td colSpan="7" style={{ textAlign: 'center', padding: '18px', color: 'var(--color-slate-gray)' }}>
                            Sin registros académicos consolidados.
                          </td>
                        </tr>
                      ) : (
                        fichaData.historial_academico.map((ha) => (
                          <tr key={ha.id_hecho_aca}>
                            <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{ha.periodo}</td>
                            <td>
                              <div style={{ fontWeight: 600, fontSize: '12.5px' }}>{ha.modulo}</div>
                              <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>{ha.programa}</div>
                            </td>
                            <td style={{ fontSize: '12px' }}>{ha.docente}</td>
                            <td
                              style={{
                                fontFamily: 'var(--font-mono)',
                                fontWeight: 700,
                                color: ha.nota_final <= 70 ? '#D9383A' : '#1B8754',
                              }}
                            >
                              {ha.nota_final}
                            </td>
                            <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                              {ha.incumplimiento_pct}%
                            </td>
                            <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                              {ha.regla_disparada}
                            </td>
                            <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-slate-gray)' }}>
                              {ha.origen_archivo || 'DW Consolidado'}
                              {ha.hash_sha256 ? ` · ${ha.hash_sha256.slice(0, 10)}...` : ''}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </ResponsiveTable>

                {/* Hechos Financieros */}
                <h4
                  style={{
                    fontSize: '13px',
                    fontWeight: 800,
                    textTransform: 'uppercase',
                    letterSpacing: '0.4px',
                    color: 'var(--color-ink-black)',
                    marginBottom: '10px',
                  }}
                >
                  2. Historial en fact_situacion_financiera ({fichaData.historial_financiero?.length || 0})
                </h4>
                <ResponsiveTable>
                  <table className="steep-table">
                    <thead>
                      <tr>
                        <th>Periodo</th>
                        <th>Concepto / Módulo</th>
                        <th>Pagado (Bs)</th>
                        <th>Deuda (Bs)</th>
                        <th>Cuotas Impagas</th>
                        <th>Estado Cartera</th>
                        <th>Trazabilidad SHA-256</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(fichaData.historial_financiero || []).length === 0 ? (
                        <tr>
                          <td colSpan="7" style={{ textAlign: 'center', padding: '18px', color: 'var(--color-slate-gray)' }}>
                            Sin registros de mora o obligaciones financieras consolidadas para este estudiante.
                          </td>
                        </tr>
                      ) : (
                        fichaData.historial_financiero.map((hf) => (
                          <tr key={hf.id_hecho_fin}>
                            <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{hf.periodo}</td>
                            <td>
                              <div style={{ fontWeight: 600, fontSize: '12.5px' }}>{hf.concepto}</div>
                              {hf.modulo && (
                                <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>{hf.modulo}</div>
                              )}
                            </td>
                            <td style={{ fontFamily: 'var(--font-mono)', color: '#1B8754' }}>
                              Bs. {Number(hf.monto_pagado || 0).toLocaleString()}
                            </td>
                            <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#D9383A' }}>
                              Bs. {Number(hf.monto_deuda || 0).toLocaleString()}
                            </td>
                            <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                              {hf.cuotas_impagas}
                            </td>
                            <td>{hf.estado_cartera}</td>
                            <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-slate-gray)' }}>
                              {hf.origen_archivo || 'DW Consolidado'}
                              {hf.hash_sha256 ? ` · ${hf.hash_sha256.slice(0, 10)}...` : ''}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </ResponsiveTable>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
