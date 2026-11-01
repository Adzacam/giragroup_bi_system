import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Cpu, CheckCircle2, AlertTriangle, AlertCircle, ArrowRight, ShieldCheck,
  HelpCircle, ChevronDown, ChevronUp, Eye, EyeOff, Database,
  User, BookOpen, Award, FileText, Check, Sparkles, Search,
  GraduationCap, CreditCard, ShoppingCart, ShieldAlert, ExternalLink
} from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import { dataopsApi } from '../../api/dataopsApi';
import { sileoToast } from '../../services/sileoToast';

export default function BetoReadingFlowView() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [selectedDocId, setSelectedDocId] = useState(null);
  
  // Filtros
  const [activeArea, setActiveArea] = useState('TODAS'); // 'TODAS' | 'academica' | 'financiera' | 'comercial' | 'calidad'
  const [filterCondition, setFilterCondition] = useState('ALL'); // 'ALL' | 'BAJA_CONFIANZA' | 'CONFLICTOS' | 'CATALOGO' | 'ABANDONO'
  const [selectedFileFilter, setSelectedFileFilter] = useState('TODOS');
  const [selectedEntityType, setSelectedEntityType] = useState('TODOS');
  const [searchQuery, setSearchQuery] = useState('');
  const [tablePage, setTablePage] = useState(1);
  const tablePageSize = 10;

  // Estados de expansión y modales
  const [expandedRows, setExpandedRows] = useState({});
  const [revealedCis, setRevealedCis] = useState({});
  const [showModelDetails, setShowModelDetails] = useState(false);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [isInserting, setIsInserting] = useState(false);

  useEffect(() => {
    let isMounted = true;
    setTablePage(1);

    const run = async () => {
      try {
        setLoading(true);
        let batchIdToLoad = id || localStorage.getItem('last_active_batch_id');
        if (!batchIdToLoad) {
          if (isMounted) {
            setData(null);
            setLoading(false);
          }
          return;
        }

        const res = await dataopsApi.getLoteBetoReading(batchIdToLoad, {
          docId: selectedDocId,
          area: activeArea !== 'TODAS' ? activeArea : undefined,
          filtroGlobal: filterCondition !== 'ALL' ? filterCondition : undefined,
          tipoEntidad: selectedEntityType !== 'TODOS' ? selectedEntityType : undefined,
          pageSize: 300,
        });
        if (isMounted) {
          setData(res || null);
        }
      } catch (err) {
        if (isMounted) {
          console.warn('Error al cargar beto-reading:', err);
          setData(null);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    run();

    return () => {
      isMounted = false;
    };
  }, [id, selectedDocId, activeArea, filterCondition, selectedEntityType]);

  const loadReadingData = async (docFilter = null) => {
    try {
      setLoading(true);
      let batchIdToLoad = id || localStorage.getItem('last_active_batch_id');
      if (!batchIdToLoad) {
        setData(null);
        setLoading(false);
        return;
      }

      const res = await dataopsApi.getLoteBetoReading(batchIdToLoad, {
        docId: docFilter,
        area: activeArea !== 'TODAS' ? activeArea : undefined,
        filtroGlobal: filterCondition !== 'ALL' ? filterCondition : undefined,
        tipoEntidad: selectedEntityType !== 'TODOS' ? selectedEntityType : undefined,
        pageSize: 300,
      });
      setData(res || null);
    } catch (err) {
      console.warn('Error al cargar beto-reading:', err);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const resumen = data?.resumen_ejecutivo || {
    total_procesados: data?.registros?.length || 0,
    aceptados_automaticamente: data?.capa_a_resumen?.directo_dw || 0,
    por_revisar: data?.capa_a_resumen?.a_revision || 0,
    con_incidencias: 0,
    avance_porcentaje: data?.capa_a_resumen?.porcentaje_automatico || 0,
    estado_lote: 'Revisión en curso',
    alerta_abandono_count: 0,
    sugerencias_catalogo_count: 0
  };

  const areas = data?.areas || {
    academica: { key: 'academica', titulo: 'Académica', total: 0, auto: 0, revision: 0, incidencias: 0 },
    financiera: { key: 'financiera', titulo: 'Financiera', total: 0, auto: 0, revision: 0, incidencias: 0 },
    comercial: { key: 'comercial', titulo: 'Comercial', total: 0, auto: 0, revision: 0, incidencias: 0 },
    calidad: { key: 'calidad', titulo: 'Calidad (Capa Transversal)', total: 0, auto: 0, revision: 0, incidencias: 0 }
  };

  const allRecords = data?.registros || [];

  const toggleRowExpansion = (recId) => {
    setExpandedRows(prev => ({
      ...prev,
      [recId]: !prev[recId]
    }));
  };

  const toggleCiReveal = async (recordId) => {
    if (revealedCis[recordId]) {
      setRevealedCis(prev => {
        const copy = { ...prev };
        delete copy[recordId];
        return copy;
      });
      return;
    }

    try {
      const res = await dataopsApi.revelarCi(recordId);
      const ciRevealed = res?.ci_real || res?.ci;
      if (ciRevealed) {
        setRevealedCis(prev => ({
          ...prev,
          [recordId]: ciRevealed
        }));
      }
    } catch (err) {
      const status = err.response?.status;
      sileoToast.error({
        title: status === 403 ? 'Permiso denegado (RBAC)' : 'No se pudo revelar el CI',
        description: err.response?.data?.detail || 'Se requiere rol ADMIN o AUDITOR_CALIDAD para revelar datos personales.'
      });
    }
  };

  const handleConfirmInsertDw = async () => {
    try {
      setIsInserting(true);
      const effectiveBatchId = id || localStorage.getItem('last_active_batch_id');
      const res = await dataopsApi.confirmDwInsert({
        id_lote: effectiveBatchId ? Number(effectiveBatchId) : undefined,
        doc_id: selectedDocId ? Number(selectedDocId) : undefined
      });
      
      const totalInserted = res?.inserted_dw ?? resumen.aceptados_automaticamente;
      const desglose = res?.desglose || {
        inserted_academico: res?.inserted_academico ?? totalInserted,
        inserted_financiero: res?.inserted_financiero ?? 0
      };

      sileoToast.success({
        title: `${totalInserted} registros consolidados en Data Warehouse`,
        description: `Académicos: +${desglose.inserted_academico} · Financieros: +${desglose.inserted_financiero}`
      });
      setIsConfirmModalOpen(false);
      loadReadingData(selectedDocId);
    } catch (err) {
      console.error('Error en confirmación DW:', err);
      sileoToast.error({
        title: 'Error al consolidar en Data Warehouse',
        description: err.response?.data?.detail || err.message || 'Error en la transacción de carga.'
      });
      setIsConfirmModalOpen(false);
    } finally {
      setIsInserting(false);
    }
  };

  // Lista de archivos únicos disponibles en el lote para filtro persistente
  const availableFiles = useMemo(() => {
    const fileSet = new Set();
    allRecords.forEach(r => {
      const fName = r.archivo_origen || r.nombre_archivo;
      if (fName) fileSet.add(fName);
    });
    return Array.from(fileSet);
  }, [allRecords]);

  // Filtrado de registros
  const filteredRecords = useMemo(() => {
    return allRecords.filter(r => {
      // 1. Filtro de área de trabajo
      if (activeArea !== 'TODAS') {
        if (activeArea === 'calidad') {
          if (!r.en_calidad && r.area !== 'calidad') return false;
        } else if (r.area !== activeArea) {
          return false;
        }
      }

      // 2. Filtro global persistente de Archivo de Origen
      if (selectedFileFilter !== 'TODOS') {
        const fileMatch = (r.archivo_origen === selectedFileFilter) || (r.nombre_archivo === selectedFileFilter);
        if (!fileMatch) return false;
      }

      // 3. Filtro global persistente de Tipo de Entidad
      if (selectedEntityType !== 'TODOS') {
        const ents = r.lectura?.entidades || [];
        const hasEnt = ents.some(e => {
          const l = (e.label || '').toUpperCase();
          if (selectedEntityType === 'ESTUDIANTE') return l.includes('ESTUDIANTE') || l.includes('ALUMNO') || l.includes('CI');
          if (selectedEntityType === 'MODULO') return l.includes('MODULO') || l.includes('MÓDULO');
          if (selectedEntityType === 'DOCENTE') return l.includes('DOCENTE');
          if (selectedEntityType === 'CALIFICACION') return l.includes('CALIFICACI') || l.includes('NOTA');
          if (selectedEntityType === 'MONTO') return l.includes('MONTO') || l.includes('CONCEPTO') || l.includes('CUOTA');
          if (selectedEntityType === 'ASISTENCIA') return l.includes('ASISTENCIA');
          return false;
        });
        if (!hasEnt) return false;
      }

      // 4. Filtro de condición
      if (filterCondition === 'BAJA_CONFIANZA') {
        const score = r.indice_registro || (r.score_confianza ? r.score_confianza * 100 : 80);
        if (score >= 85) return false;
      } else if (filterCondition === 'CONFLICTOS') {
        if (r.estado !== 'INCONSISTENCIA' && r.estado !== 'REVISION') return false;
      } else if (filterCondition === 'CATALOGO') {
        if (!r.es_nuevo_catalogo) return false;
      } else if (filterCondition === 'ABANDONO') {
        if (!r.alerta_abandono && !r.cruce_multifuente) return false;
      }

      // 5. Búsqueda textual
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const estMatch = (r.estudiante || '').toLowerCase().includes(q);
        const modMatch = (r.modulo || '').toLowerCase().includes(q);
        const ciMaskMatch = (r.ci_enmascarado || '').toLowerCase().includes(q);
        const ciRevMatch = (revealedCis[r.id] && String(revealedCis[r.id]).toLowerCase().includes(q));
        const rawMatch = (r.texto_linea || '').toLowerCase().includes(q);
        if (!estMatch && !modMatch && !ciMaskMatch && !ciRevMatch && !rawMatch) return false;
      }

      return true;
    });
  }, [allRecords, activeArea, selectedFileFilter, selectedEntityType, filterCondition, searchQuery, revealedCis]);

  const totalPages = Math.ceil(filteredRecords.length / tablePageSize) || 1;
  const paginatedRows = filteredRecords.slice((tablePage - 1) * tablePageSize, tablePage * tablePageSize);

  const effectiveBatchId = id || localStorage.getItem('last_active_batch_id') || '01';

  return (
    <BatchFlowLayout
      currentStep={3}
      selectedDocId={selectedDocId}
      onSelectDocId={setSelectedDocId}
    >
      {/* ── Encabezado Principal ── */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <h2 className="serif-heading" style={{ fontSize: '24px', margin: 0, color: 'var(--color-ink-black)' }}>
                Procesamiento de entidades
              </h2>
              <span
                style={{
                  fontSize: '11.5px',
                  fontWeight: '700',
                  padding: '4px 10px',
                  borderRadius: '999px',
                  backgroundColor: resumen.estado_lote === 'Listo para consolidar' ? 'rgba(27, 135, 84, 0.12)' : 'rgba(217, 155, 38, 0.14)',
                  color: resumen.estado_lote === 'Listo para consolidar' ? '#1B8754' : '#B8801A',
                  border: `1px solid ${resumen.estado_lote === 'Listo para consolidar' ? 'rgba(27, 135, 84, 0.3)' : 'rgba(217, 155, 38, 0.35)'}`,
                }}
              >
                {resumen.estado_lote}
              </span>
            </div>
            <div style={{ fontSize: '13px', color: 'var(--color-slate-gray)', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span>Lote: <strong>LOTE-{effectiveBatchId}</strong></span>
              <span>•</span>
              <span>Modelo: <strong>BETO (Spanish BERT)</strong></span>
              <span>•</span>
              <span>Umbral de relación: <strong>0,85</strong></span>
              <button
                type="button"
                onClick={() => setShowModelDetails(!showModelDetails)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-gira-gold, #D99B26)',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: '600',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '0 4px',
                  textDecoration: 'underline'
                }}
              >
                <HelpCircle size={13} /> {showModelDetails ? 'Ocultar detalles técnicos' : 'Ver detalles técnicos del modelo'}
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              type="button"
              className="btn-pill-secondary"
              onClick={() => setIsConfirmModalOpen(true)}
              disabled={resumen.aceptados_automaticamente === 0}
            >
              <Database size={14} /> Consolidar Aceptados al DW ({resumen.aceptados_automaticamente})
            </button>
            <button
              type="button"
              className="btn-pill-gold"
              onClick={() => navigate(`/dataops/lote/${effectiveBatchId}/revision`)}
            >
              <span>Ir a Bandeja ④ Revisión ({resumen.por_revisar + resumen.con_incidencias})</span>
              <ArrowRight size={15} />
            </button>
          </div>
        </div>

        {/* Panel Desplegable: Detalles Técnicos BETO */}
        {showModelDetails && (
          <div
            className="floating-artifact"
            style={{
              marginTop: '16px',
              padding: '16px 20px',
              backgroundColor: 'var(--color-paper-white)',
              border: '1px solid var(--dataops-gold-border)',
              borderRadius: '12px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: 'var(--color-gira-gold, #D99B26)' }}>
              <Cpu size={16} />
              <strong style={{ fontSize: '13px' }}>Arquitectura y Parámetros del Modelo BETO</strong>
            </div>
            <p style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)', margin: '0 0 10px 0', lineHeight: '1.5' }}>
              {data?.modelo_info?.conll_mapping || (
                'Modelo mrm8488/bert-spanish-cased-finetuned-ner (base: dccuchile/bert-base-spanish-wwm-cased). Extrae entidades CoNLL (PER, ORG, LOC, MISC), mapeándolas determinísticamente con el Catálogo Guía institucional (POS-XXXX).'
              )}
            </p>
            <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: 'var(--color-ink-black)', flexWrap: 'wrap' }}>
              <span>• Compuerta Base: <strong>70%</strong></span>
              <span>• Umbral Corte Automático: <strong>85%</strong></span>
              <span>• Bono Catálogo: <strong>+4% a +12%</strong></span>
              <span>• Bono Frecuencia Lote: <strong>+3%</strong></span>
              <span>• Tope Bonificación: <strong>99%</strong></span>
            </div>
          </div>
        )}
      </div>

      {/* ── 4 Tarjetas de Resumen Ejecutivo (Cards Superiores) ── */}
      <div className="status-card-grid">
        {/* Card 1: Registros Procesados */}
        <div className="status-card">
          <div className="status-card-header">
            <span className="status-card-title">Registros procesados</span>
            <FileText size={18} color="var(--color-slate-gray)" />
          </div>
          <div className="status-card-value">{resumen.total_procesados}</div>
          <p className="status-card-subtext">Total analizado por BETO</p>
        </div>

        {/* Card 2: Aceptados Automáticamente (#1B8754) */}
        <div className="status-card" style={{ borderLeft: '4px solid #1B8754' }}>
          <div className="status-card-header">
            <span className="status-card-title">Aceptados automáticamente</span>
            <CheckCircle2 size={18} color="#1B8754" />
          </div>
          <div className="status-card-value" style={{ color: '#1B8754' }}>
            {resumen.aceptados_automaticamente}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="status-card-subtext">Superan umbral ≥ 85%</span>
            <span style={{ fontSize: '10.5px', fontWeight: '700', padding: '2px 6px', borderRadius: '4px', background: 'rgba(27, 135, 84, 0.1)', color: '#1B8754' }}>
              &gt; 85% índice
            </span>
          </div>
        </div>

        {/* Card 3: Por revisar (#D99B26) */}
        <div className="status-card" style={{ borderLeft: '4px solid #D99B26' }}>
          <div className="status-card-header">
            <span className="status-card-title">Por revisar</span>
            <AlertTriangle size={18} color="#D99B26" />
          </div>
          <div className="status-card-value" style={{ color: '#D99B26' }}>
            {resumen.por_revisar}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="status-card-subtext">Requieren validación humana</span>
            <span style={{ fontSize: '10.5px', fontWeight: '700', padding: '2px 6px', borderRadius: '4px', background: 'rgba(217, 155, 38, 0.1)', color: '#B8801A' }}>
              Requiere HITL
            </span>
          </div>
        </div>

        {/* Card 4: Con incidencias (#D9383A) */}
        <div className="status-card" style={{ borderLeft: '4px solid #D9383A' }}>
          <div className="status-card-header">
            <span className="status-card-title">Con incidencias</span>
            <AlertCircle size={18} color="#D9383A" />
          </div>
          <div className="status-card-value" style={{ color: '#D9383A' }}>
            {resumen.con_incidencias}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="status-card-subtext">Inconsistencias y alertas</span>
            <span style={{ fontSize: '10.5px', fontWeight: '700', padding: '2px 6px', borderRadius: '4px', background: 'rgba(217, 56, 58, 0.1)', color: '#D9383A' }}>
              Conflicto / Alerta
            </span>
          </div>
        </div>
      </div>

      {/* ── Barra de Progreso: Avance de Procesamiento ── */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px', fontSize: '12.5px' }}>
          <span style={{ fontWeight: '600', color: 'var(--color-ink-black)' }}>Avance de procesamiento</span>
          <span style={{ fontWeight: '700', color: '#1B8754' }}>{resumen.avance_porcentaje}% completado</span>
        </div>
        <div className="progress-bar-container">
          <div className="progress-bar-fill" style={{ width: `${Math.min(100, Math.max(0, resumen.avance_porcentaje))}%` }} />
        </div>
      </div>

      {/* ── 4 Tarjetas de Áreas de Trabajo con Drill-Down ── */}
      <div style={{ marginBottom: '12px' }}>
        <h3 className="serif-heading" style={{ fontSize: '16px', margin: '0 0 12px 0', color: 'var(--color-ink-black)' }}>
          Áreas de trabajo
        </h3>
        <div className="area-card-grid">
          {/* Área 1: Académica */}
          <div
            className={`area-card ${activeArea === 'academica' ? 'active' : ''}`}
            onClick={() => setActiveArea(activeArea === 'academica' ? 'TODAS' : 'academica')}
          >
            <div className="area-card-top">
              <span className="area-card-name">
                <GraduationCap size={16} color="#0C1E33" /> {areas.academica.titulo}
              </span>
              <span className="area-card-count">{areas.academica.total}</span>
            </div>
            <p style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', margin: '0 0 8px 0', lineHeight: '1.4' }}>
              Notas, módulos, asistencia y validación contra oferta curricular.
            </p>
            <div className="area-card-stats">
              <span style={{ color: '#1B8754' }}>Auto: <strong>{areas.academica.auto}</strong></span>
              <span>•</span>
              <span style={{ color: '#D99B26' }}>Rev: <strong>{areas.academica.revision}</strong></span>
              <span>•</span>
              <span style={{ color: '#D9383A' }}>Inc: <strong>{areas.academica.incidencias}</strong></span>
            </div>
          </div>

          {/* Área 2: Financiera */}
          <div
            className={`area-card ${activeArea === 'financiera' ? 'active' : ''}`}
            onClick={() => setActiveArea(activeArea === 'financiera' ? 'TODAS' : 'financiera')}
          >
            <div className="area-card-top">
              <span className="area-card-name">
                <CreditCard size={16} color="#0C1E33" /> {areas.financiera.titulo}
              </span>
              <span className="area-card-count">{areas.financiera.total}</span>
            </div>
            <p style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', margin: '0 0 8px 0', lineHeight: '1.4' }}>
              Pagos, cuotas impagas e importes conciliados con aranceles del catálogo.
            </p>
            <div className="area-card-stats">
              <span style={{ color: '#1B8754' }}>Auto: <strong>{areas.financiera.auto}</strong></span>
              <span>•</span>
              <span style={{ color: '#D99B26' }}>Rev: <strong>{areas.financiera.revision}</strong></span>
              <span>•</span>
              <span style={{ color: '#D9383A' }}>Inc: <strong>{areas.financiera.incidencias}</strong></span>
            </div>
          </div>

          {/* Área 3: Comercial */}
          <div
            className={`area-card ${activeArea === 'comercial' ? 'active' : ''}`}
            onClick={() => setActiveArea(activeArea === 'comercial' ? 'TODAS' : 'comercial')}
          >
            <div className="area-card-top">
              <span className="area-card-name">
                <ShoppingCart size={16} color="#0C1E33" /> {areas.comercial.titulo}
              </span>
              <span className="area-card-count">{areas.comercial.total}</span>
            </div>
            <p style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', margin: '0 0 8px 0', lineHeight: '1.4' }}>
              Inscripciones individuales vs demanda agregada y metas de captación.
            </p>
            <div className="area-card-stats">
              <span style={{ color: '#1B8754' }}>Auto: <strong>{areas.comercial.auto}</strong></span>
              <span>•</span>
              <span style={{ color: '#D99B26' }}>Rev: <strong>{areas.comercial.revision}</strong></span>
              <span>•</span>
              <span style={{ color: '#D9383A' }}>Inc: <strong>{areas.comercial.incidencias}</strong></span>
            </div>
          </div>

          {/* Área 4: Calidad (Capa Transversal) */}
          <div
            className={`area-card ${activeArea === 'calidad' ? 'active' : ''}`}
            onClick={() => setActiveArea(activeArea === 'calidad' ? 'TODAS' : 'calidad')}
          >
            <div className="area-card-top">
              <span className="area-card-name">
                <ShieldAlert size={16} color="#D9383A" /> Calidad Transversal
              </span>
              <span className="area-card-count" style={{ color: '#D9383A' }}>{areas.calidad.total}</span>
            </div>
            <p style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', margin: '0 0 8px 0', lineHeight: '1.4' }}>
              Duplicados, cruce de abandono y sugerencias de Catálogo Guía.
            </p>
            <div className="area-card-stats">
              <span style={{ color: '#D99B26' }}>Rev: <strong>{areas.calidad.revision}</strong></span>
              <span>•</span>
              <span style={{ color: '#D9383A' }}>Alertas: <strong>{areas.calidad.incidencias}</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Barra de Filtros Persistentes y Búsqueda ── */}
      <div
        className="floating-artifact"
        style={{
          padding: '14px 18px',
          marginBottom: '20px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '14px'
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-slate-gray)', marginRight: '4px' }}>
            Filtros:
          </span>

          {/* Pastillas de condición */}
          <button
            type="button"
            className={`pill-filter ${filterCondition === 'ALL' ? 'active' : ''}`}
            onClick={() => setFilterCondition('ALL')}
          >
            Todos ({allRecords.length})
          </button>
          <button
            type="button"
            className={`pill-filter ${filterCondition === 'BAJA_CONFIANZA' ? 'active' : ''}`}
            onClick={() => setFilterCondition('BAJA_CONFIANZA')}
          >
            Confianza &lt; 85%
          </button>
          <button
            type="button"
            className={`pill-filter ${filterCondition === 'CONFLICTOS' ? 'active' : ''}`}
            onClick={() => setFilterCondition('CONFLICTOS')}
          >
            Conflictos ({resumen.por_revisar + resumen.con_incidencias})
          </button>
          <button
            type="button"
            className={`pill-filter ${filterCondition === 'CATALOGO' ? 'active' : ''}`}
            onClick={() => setFilterCondition('CATALOGO')}
          >
            💡 Sugerencias Catálogo ({resumen.sugerencias_catalogo_count})
          </button>
          <button
            type="button"
            className={`pill-filter ${filterCondition === 'ABANDONO' ? 'active' : ''}`}
            onClick={() => setFilterCondition('ABANDONO')}
          >
            ⚠️ Alerta Abandono ({resumen.alerta_abandono_count})
          </button>

          {/* Filtro Archivo de Origen */}
          {availableFiles.length > 0 && (
            <select
              className="dataops-select"
              style={{ width: 'auto', padding: '6px 12px', fontSize: '12px', borderRadius: '999px', cursor: 'pointer' }}
              value={selectedFileFilter}
              onChange={(e) => {
                setSelectedFileFilter(e.target.value);
                setTablePage(1);
              }}
              title="Filtrar por archivo de origen"
              aria-label="Archivo de origen"
            >
              <option value="TODOS">📁 Todos los archivos ({availableFiles.length})</option>
              {availableFiles.map(f => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          )}

          {/* Filtro Tipo de Entidad */}
          <select
            className="dataops-select"
            style={{ width: 'auto', padding: '6px 12px', fontSize: '12px', borderRadius: '999px', cursor: 'pointer' }}
            value={selectedEntityType}
            onChange={(e) => {
              setSelectedEntityType(e.target.value);
              setTablePage(1);
            }}
            title="Filtrar por tipo de entidad"
            aria-label="Tipo de entidad"
          >
            <option value="TODOS">🏷️ Todas las entidades</option>
            <option value="ESTUDIANTE">Estudiante / Persona</option>
            <option value="MODULO">Módulo / Materia</option>
            <option value="DOCENTE">Docente</option>
            <option value="CALIFICACION">Calificación / Nota</option>
            <option value="MONTO">Monto / Deuda / Cuota</option>
            <option value="ASISTENCIA">Asistencia / Abandono</option>
          </select>
        </div>

        {/* Buscador */}
        <div style={{ position: 'relative', minWidth: '240px', flex: '1', maxWidth: '320px' }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-slate-gray)' }} />
          <input
            type="text"
            className="dataops-input"
            style={{ paddingLeft: '32px', fontSize: '12.5px' }}
            placeholder="Buscar por estudiante, CI o módulo..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setTablePage(1);
            }}
          />
        </div>
      </div>

      {/* ── Tabla de Registros con Drill-Down Expandible ── */}
      <div className="floating-artifact" style={{ padding: '0', overflow: 'hidden', marginBottom: '24px' }}>
        <div style={{ overflowX: 'auto' }}>
          <table className="dataops-table">
            <thead>
              <tr>
                <th style={{ width: '40px', textAlign: 'center' }}></th>
                <th>Estado</th>
                <th>Área</th>
                <th>Estudiante / Entidad</th>
                <th>Módulo / Concepto</th>
                <th>Calificación / Asist / Deuda</th>
                <th>Índice BETO</th>
                <th>Alerta / Cruce</th>
                <th style={{ textAlign: 'right' }}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {paginatedRows.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '48px 16px', color: 'var(--color-slate-gray)' }}>
                    No se encontraron registros coincidentes con los filtros aplicados.
                  </td>
                </tr>
              ) : (
                paginatedRows.map((rec) => {
                  const isExpanded = !!expandedRows[rec.id];
                  const scoreVal = rec.indice_registro || (rec.score_confianza ? Math.round(rec.score_confianza * 100) : 80);
                  const isAutomatic = rec.estado === 'AUTOMATICO';
                  const isRevision = rec.estado === 'REVISION';

                  return (
                    <React.Fragment key={rec.id}>
                      <tr
                        className={`dataops-table-row ${isExpanded ? 'selected' : ''}`}
                        onClick={() => toggleRowExpansion(rec.id)}
                      >
                        <td style={{ textAlign: 'center', color: 'var(--color-slate-gray)' }}>
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </td>
                        <td>
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontSize: '11px',
                              fontWeight: '700',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              backgroundColor: isAutomatic ? 'rgba(27, 135, 84, 0.1)' : (isRevision ? 'rgba(217, 155, 38, 0.12)' : 'rgba(217, 56, 58, 0.12)'),
                              color: isAutomatic ? '#1B8754' : (isRevision ? '#B8801A' : '#D9383A'),
                            }}
                          >
                            {isAutomatic ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                            {rec.estado || (isAutomatic ? 'AUTOMÁTICO' : 'REVISIÓN')}
                          </span>
                        </td>
                        <td>
                          <span style={{ fontSize: '12px', fontWeight: '600', textTransform: 'capitalize' }}>
                            {rec.area === 'academica' ? '🎓 Académica' : (rec.area === 'financiera' ? '💳 Financiera' : (rec.area === 'comercial' ? '🛒 Comercial' : '🛡️ Calidad'))}
                          </span>
                        </td>
                        <td>
                          <div style={{ fontWeight: '600', color: 'var(--color-ink-black)' }}>
                            {rec.estudiante || 'Registro no identificado'}
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                            <span>CI: {revealedCis[rec.id] || rec.ci_enmascarado || '••••••'}</span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleCiReveal(rec.id);
                              }}
                              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--color-slate-gray)' }}
                              title="Revelar Cédula de Identidad (Auditoría)"
                            >
                              {revealedCis[rec.id] ? <EyeOff size={12} /> : <Eye size={12} />}
                            </button>
                          </div>
                        </td>
                        <td>
                          <div style={{ fontSize: '12px', color: 'var(--color-ink-black)', maxWidth: '220px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {rec.modulo || rec.concepto || 'Módulo Académico'}
                          </div>
                        </td>
                        <td>
                          {rec.nota_normalizada !== undefined && rec.nota_normalizada !== null ? (
                            <span style={{ fontWeight: '700', color: rec.nota_normalizada >= 51 ? '#1B8754' : '#D9383A' }}>
                              Nota: {rec.nota_normalizada}/100
                            </span>
                          ) : rec.monto_deuda ? (
                            <span style={{ fontWeight: '700', color: '#D9383A' }}>
                              Deuda: Bs. {rec.monto_deuda} ({rec.cuotas_impagas || 1} ctas)
                            </span>
                          ) : (
                            <span style={{ color: 'var(--color-slate-gray)' }}>—</span>
                          )}
                        </td>
                        <td>
                          <span
                            style={{
                              fontSize: '12px',
                              fontWeight: '700',
                              color: scoreVal >= 85 ? '#1B8754' : (scoreVal >= 70 ? '#B8801A' : '#D9383A')
                            }}
                          >
                            {scoreVal}%
                          </span>
                        </td>
                        <td>
                          {rec.alerta_abandono ? (
                            <span
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontSize: '11px',
                                fontWeight: '700',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                backgroundColor: 'rgba(217, 56, 58, 0.12)',
                                color: '#D9383A'
                              }}
                            >
                              ⚠️ Alerta Abandono
                            </span>
                          ) : rec.es_nuevo_catalogo ? (
                            <span
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontSize: '11px',
                                fontWeight: '700',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                backgroundColor: 'rgba(217, 155, 38, 0.14)',
                                color: '#B8801A'
                              }}
                            >
                              💡 Nuevo Catálogo
                            </span>
                          ) : (
                            <span style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)' }}>Normal</span>
                          )}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleRowExpansion(rec.id);
                            }}
                            className="btn-pill-secondary"
                            style={{ padding: '4px 10px', fontSize: '11.5px' }}
                          >
                            {isExpanded ? 'Ocultar' : 'Detalle'}
                          </button>
                        </td>
                      </tr>

                      {/* Fila Desplegable (Drill-Down) */}
                      {isExpanded && (
                        <tr>
                          <td colSpan={9} style={{ backgroundColor: 'var(--color-mist-gray)', padding: '16px 20px', borderBottom: '2px solid var(--color-border)' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '18px' }}>
                              {/* Izquierda: Sentencia extraída y Tokens */}
                              <div>
                                <div style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--color-slate-gray)', textTransform: 'uppercase', marginBottom: '6px' }}>
                                  Línea extraída del documento original
                                </div>
                                <div
                                  style={{
                                    padding: '10px 12px',
                                    borderRadius: '8px',
                                    backgroundColor: 'var(--color-paper-white)',
                                    border: '1px solid var(--color-border)',
                                    fontFamily: 'var(--font-mono, monospace)',
                                    fontSize: '12px',
                                    color: 'var(--color-ink-black)',
                                    lineHeight: '1.5',
                                    marginBottom: '10px'
                                  }}
                                >
                                  {rec.texto_linea || 'No se dispone del texto raw de la línea'}
                                </div>

                                {/* Desglose de Tokens Reconocidos */}
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                  <span className="chip-cat chip-programa">PROG: {rec.programa || 'POS-2026'}</span>
                                  <span className="chip-cat chip-modulo">MOD: {rec.modulo || 'Módulo'}</span>
                                  <span className="chip-cat chip-origen">DOC: {rec.archivo_origen || 'Origen'}</span>
                                </div>

                                {/* Alerta Multifuente de Abandono si existe */}
                                {rec.cruce_multifuente && (
                                  <div className="multi-source-alert">
                                    <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
                                    <div>
                                      <strong>Cruce Multifuente de Abandono Detectado:</strong>
                                      <div style={{ marginTop: '3px' }}>{rec.cruce_multifuente.descripcion}</div>
                                      <div style={{ fontSize: '11.5px', opacity: 0.85, marginTop: '2px' }}>
                                        Correlación con archivo: <em>{rec.cruce_multifuente.archivo_cruzado}</em>
                                      </div>
                                    </div>
                                  </div>
                                )}
                              </div>

                              {/* Derecha: Desglose Relacional Catálogo Guía (Cero-PII) */}
                              <div>
                                <div style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--color-slate-gray)', textTransform: 'uppercase', marginBottom: '6px' }}>
                                  Conciliación Catálogo Guía (Cero-PII)
                                </div>
                                <div className="zero-pii-card">
                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                    <span style={{ color: 'var(--color-slate-gray)' }}>Código Oferta:</span>
                                    <strong>{rec.desglose_relacional?.catalogo_guia?.modulo_codigo || rec.codigo_oferta || 'POS-GEST-2026'}</strong>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                    <span style={{ color: 'var(--color-slate-gray)' }}>Módulo Canónico:</span>
                                    <span>{rec.modulo || 'Módulo Curricular'}</span>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                    <span style={{ color: 'var(--color-slate-gray)' }}>Arancel Catálogo:</span>
                                    <span>{rec.desglose_relacional?.catalogo_guia?.arancel_base || 'Bs. 1.500 por cuota/módulo'}</span>
                                  </div>
                                  <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', borderTop: '1px dashed var(--color-border)', paddingTop: '6px', marginTop: '6px' }}>
                                    🛡️ <em>Principio Cero-PII: El Catálogo Guía solo almacena entidades curriculares e institucionales, nunca identidades de personas.</em>
                                  </div>
                                </div>

                                {!isAutomatic && (
                                  <div style={{ marginTop: '12px', textAlign: 'right' }}>
                                    <button
                                      type="button"
                                      className="btn-pill-gold"
                                      style={{ padding: '8px 16px', fontSize: '12px' }}
                                      onClick={() => navigate(`/dataops/lote/${effectiveBatchId}/revision`)}
                                    >
                                      <span>Resolver en Revisión Humana</span>
                                      <ArrowRight size={13} />
                                    </button>
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        {totalPages > 1 && (
          <div
            style={{
              padding: '12px 20px',
              borderTop: '1px solid var(--color-border)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '12.5px'
            }}
          >
            <span style={{ color: 'var(--color-slate-gray)' }}>
              Mostrando {Math.min(filteredRecords.length, (tablePage - 1) * tablePageSize + 1)} - {Math.min(filteredRecords.length, tablePage * tablePageSize)} de {filteredRecords.length}
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                className="btn-pill-secondary"
                disabled={tablePage === 1}
                onClick={() => setTablePage(p => Math.max(1, p - 1))}
              >
                Anterior
              </button>
              <button
                type="button"
                className="btn-pill-secondary"
                disabled={tablePage >= totalPages}
                onClick={() => setTablePage(p => p + 1)}
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Footer de Avance a Paso 4 ── */}
      <div
        className="floating-artifact"
        style={{
          padding: '20px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px'
        }}
      >
        <div>
          <div style={{ fontWeight: '700', fontSize: '15px', color: 'var(--color-ink-black)', marginBottom: '4px' }}>
            {resumen.por_revisar + resumen.con_incidencias === 0
              ? 'Todos los registros han superado el umbral del 85%'
              : `Hay ${resumen.por_revisar + resumen.con_incidencias} casos pendientes en la Bandeja de Revisión Humana`}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>
            Consolida los registros aprobados directamente al DW o procede a la resolución manual.
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn-pill-secondary"
            onClick={() => navigate(`/dataops/lote/${effectiveBatchId}/texto`)}
          >
            ← Volver a ② Texto Plano
          </button>
          <button
            type="button"
            className="btn-pill-secondary"
            onClick={() => setIsConfirmModalOpen(true)}
            disabled={resumen.aceptados_automaticamente === 0}
          >
            <Database size={15} /> Consolidar Aprobados ({resumen.aceptados_automaticamente})
          </button>
          <button
            type="button"
            className="btn-pill-gold"
            onClick={() => navigate(`/dataops/lote/${effectiveBatchId}/revision`)}
          >
            <span>Ir a Bandeja ④ Revisión Humana y Consolidación DW ({resumen.por_revisar + resumen.con_incidencias})</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </div>

      {/* ── Modal de Confirmación DW ── */}
      {isConfirmModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(12, 30, 51, 0.65)',
            backdropFilter: 'blur(3px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '16px'
          }}
        >
          <div
            className="floating-artifact"
            style={{
              maxWidth: '480px',
              width: '100%',
              padding: '24px',
              backgroundColor: 'var(--color-paper-white)',
              borderRadius: '16px'
            }}
          >
            <h3 className="serif-heading" style={{ fontSize: '20px', margin: '0 0 10px 0', color: 'var(--color-ink-black)' }}>
              Confirmar consolidación al Data Warehouse
            </h3>
            <p style={{ fontSize: '13.5px', color: 'var(--color-slate-gray)', lineHeight: '1.5', margin: '0 0 16px 0' }}>
              Se insertarán transaccionalmente <strong>{resumen.aceptados_automaticamente}</strong> registros que superaron el umbral de relación del 85% directamente en las tablas de hechos:
            </p>
            <ul style={{ fontSize: '13px', color: 'var(--color-ink-black)', marginBottom: '20px', paddingLeft: '20px', lineHeight: '1.6' }}>
              <li><code>fact_rendimiento_academico</code> (calificaciones normalizadas a escala centesimal)</li>
              <li><code>fact_situacion_financiera</code> (cuotas impagas y cobros conciliados)</li>
            </ul>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn-pill-secondary"
                onClick={() => setIsConfirmModalOpen(false)}
                disabled={isInserting}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-pill-gold"
                onClick={handleConfirmInsertDw}
                disabled={isInserting}
              >
                {isInserting ? 'Consolidando transaccionalmente...' : 'Confirmar e Insertar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </BatchFlowLayout>
  );
}
