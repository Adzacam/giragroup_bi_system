import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  CheckSquare, GitMerge, AlertTriangle, Cpu, Terminal, ShieldAlert,
  CheckCircle, Unlink, Activity, CheckCircle2, RotateCcw, Link2, Sparkles,
  Filter, ChevronLeft, ChevronRight, Eye, EyeOff, Layers, Users, BookOpen,
  Hash, ArrowRight, UserPlus, Info, X, Database
} from 'lucide-react';

import PageHeader from '../../components/shared/PageHeader';
import DataOpsTabs from './components/DataOpsTabs';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import BetoDrawer from './BetoDrawer';
import CaseReviewDrawer from './components/CaseReviewDrawer';

import { dataopsApi } from '../../api/dataopsApi';
import { catalogApi } from '../../api/catalogApi';
import { sileoToast } from '../../services/sileoToast';
import { getSourceTableMeta, getEntityTargetTableBadge } from '../../utils/sourceLabelUtils';

export default function HumanInTheLoopView() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState('review');

  // ─── EXPEDIENTE LATERAL DE REVISIÓN (DRAWER) ───
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerItem, setDrawerItem] = useState(null);
  const [isSavingReview, setIsSavingReview] = useState(false);

  // ─── TAB 1: BANDEJA DE REVISIÓN (Score < 0.85) ───
  const [reviewItems, setReviewItems] = useState([]);
  const [selectedItemIndex, setSelectedItemIndex] = useState(0);
  const [isLoadingReview, setIsLoadingReview] = useState(true);
  const [isBetoOpen, setIsBetoOpen] = useState(false);
  const [resolutionStatus, setResolutionStatus] = useState('pending'); // 'pending' | 'resolved' | 'unlinked'
  const [showRawContext, setShowRawContext] = useState(false);

  // Campos de edición individual
  const [editingCi, setEditingCi] = useState('');
  const [editingStudent, setEditingStudent] = useState('');
  const [editingModulo, setEditingModulo] = useState('');
  const [editingNota, setEditingNota] = useState(75.0);
  const [selectedStudentSuggestion, setSelectedStudentSuggestion] = useState('');
  const [catalogStudents, setCatalogStudents] = useState([]);

  // Multi-selección y resolución masiva (Batch Resolve)
  const [selectedReviewIds, setSelectedReviewIds] = useState([]);
  const [caseFilter, setCaseFilter] = useState('ALL'); // 'ALL' | 'NEW_PROFILE' | 'SAME_STUDENT' | 'MISSING_CI'
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [batchMode, setBatchMode] = useState('PRESERVE_INDIVIDUAL'); // 'PRESERVE_INDIVIDUAL' | 'SINGLE_HOMOLOGATION'
  const [batchCi, setBatchCi] = useState('');
  const [batchStudent, setBatchStudent] = useState('');
  const [batchModulo, setBatchModulo] = useState('');
  const [batchNota, setBatchNota] = useState(80.0);

  // Inserción deliberada en Data Warehouse (Observación 13)
  const [isConfirmDwOpen, setIsConfirmDwOpen] = useState(false);
  const [isExecutingDw, setIsExecutingDw] = useState(false);

  // ─── TAB 2: ENTIDADES NO RESUELTAS ───
  const [entities, setEntities] = useState([]);
  const [entityFilter, setEntityFilter] = useState('ALL'); // 'ALL' | 'PENDING' | 'LINKED'

  // ─── TAB 3: INCONSISTENCIAS ───
  const [inconsistenciasFilter, setInconsistenciasFilter] = useState('ALL');

  // ─── TAB 4: TELEMETRÍA ───
  const [telemetry, setTelemetry] = useState(null);

  // Cargar datos de revisión desde el backend
  const loadReviewTray = async () => {
    setIsLoadingReview(true);
    try {
      const res = await dataopsApi.getReviewTray();
      const items = res?.data || [];
      setReviewItems(items);
      setSelectedReviewIds([]);

      // Si viene docId en searchParams, enfocar el caso correspondiente
      const docIdParam = searchParams.get('docId');
      if (docIdParam && items.length > 0) {
        const foundIdx = items.findIndex(it => String(it.id_documento) === String(docIdParam));
        if (foundIdx !== -1) {
          setSelectedItemIndex(foundIdx);
        }
      }
    } catch (err) {
      console.warn('Error loading review tray:', err);
    } finally {
      setIsLoadingReview(false);
    }
  };

  // Cargar entidades no resueltas
  const loadEntities = async () => {
    try {
      const res = await dataopsApi.getUnresolvedEntities();
      setEntities(res?.data || []);
    } catch (err) {
      console.warn(err);
    }
  };

  // Cargar telemetría
  const loadTelemetry = async () => {
    try {
      const res = await dataopsApi.getTelemetrySummary();
      setTelemetry(res);
    } catch (err) {
      console.warn(err);
    }
  };

  // Cargar estudiantes del catálogo maestro
  const loadCatalogData = async () => {
    try {
      const res = await catalogApi.getEstudiantes({ limit: 15 });
      setCatalogStudents(res?.data || []);
    } catch (err) {
      console.warn(err);
    }
  };

  useEffect(() => {
    loadReviewTray();
    loadEntities();
    loadTelemetry();
    loadCatalogData();
  }, []);

  // Nombres de alumnos más frecuentes para el filtro rápido
  const studentFrequency = useMemo(() => {
    const counts = {};
    reviewItems.forEach(item => {
      if (item.estudiante && item.estudiante !== 'Entidad no resuelta') {
        counts[item.estudiante] = (counts[item.estudiante] || 0) + 1;
      }
    });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [reviewItems]);

  // Conteo de incidencias por categoría para las pestañas de filtro (Punto 11 & Loop 5)
  const missingCiCount = useMemo(() => {
    return reviewItems.filter(item => !item.ci_raw || item.ci_raw === 'No especificado' || item.ci_raw.includes('?')).length;
  }, [reviewItems]);

  const notFoundCount = useMemo(() => {
    return reviewItems.filter(item => item.es_perfil_nuevo || !item.sugerencia_catalogo).length;
  }, [reviewItems]);

  const fuzzyMatchCount = useMemo(() => {
    return reviewItems.filter(item => item.rapidfuzz_cross && item.rapidfuzz_cross < 85 && !item.es_perfil_nuevo).length;
  }, [reviewItems]);

  const duplicatesCount = useMemo(() => {
    return reviewItems.filter(item =>
      item.motivos_penalizacion?.some(m => m.tag?.toLowerCase().includes('homonimia') || m.tag?.toLowerCase().includes('duplicado')) ||
      item.tipo_incidencia === 'DUPLICADO' ||
      item.tipo_incidencia === 'HOMONIMIA'
    ).length;
  }, [reviewItems]);

  const unmappedConceptCount = useMemo(() => {
    return reviewItems.filter(item =>
      item.es_concepto_no_homologado ||
      item.tipo_incidencia === 'CONCEPTO_NO_HOMOLOGADO' ||
      item.motivos_penalizacion?.some(m => m.tag?.toLowerCase().includes('concepto') || m.tag?.toLowerCase().includes('financier')) ||
      (item.fuente_1 && item.fuente_1.toLowerCase().includes('egreso')) ||
      (item.fuente_1 && item.fuente_1.toLowerCase().includes('cobranza') && item.score_fuzzy && item.score_fuzzy < 90)
    ).length;
  }, [reviewItems]);

  const portfolioRiskCount = useMemo(() => {
    return reviewItems.filter(item =>
      item.es_riesgo_cartera ||
      item.tipo_incidencia === 'RIESGO_CARTERA' ||
      (item.cuotas_impagas !== undefined && item.cuotas_impagas >= 2) ||
      item.motivos_penalizacion?.some(m => m.tag?.toLowerCase().includes('mora') || m.tag?.toLowerCase().includes('cartera') || m.tag?.toLowerCase().includes('deuda')) ||
      (item.fuente_1 && item.fuente_1.toLowerCase().includes('cartera'))
    ).length;
  }, [reviewItems]);

  // Filtrado de casos en la bandeja de trabajo (Punto 11 & Loop 5)
  const filteredReviewItems = useMemo(() => {
    if (caseFilter === 'NOT_FOUND' || caseFilter === 'NEW_PROFILE') {
      return reviewItems.filter(item => item.es_perfil_nuevo || !item.sugerencia_catalogo);
    }
    if (caseFilter === 'MISSING_CI') {
      return reviewItems.filter(item => !item.ci_raw || item.ci_raw === 'No especificado' || item.ci_raw.includes('?'));
    }
    if (caseFilter === 'FUZZY_MATCH') {
      return reviewItems.filter(item => item.rapidfuzz_cross && item.rapidfuzz_cross < 85 && !item.es_perfil_nuevo);
    }
    if (caseFilter === 'DUPLICATES') {
      return reviewItems.filter(item =>
        item.motivos_penalizacion?.some(m => m.tag?.toLowerCase().includes('homonimia') || m.tag?.toLowerCase().includes('duplicado')) ||
        item.tipo_incidencia === 'DUPLICADO' ||
        item.tipo_incidencia === 'HOMONIMIA'
      );
    }
    if (caseFilter === 'UNMAPPED_CONCEPT') {
      return reviewItems.filter(item =>
        item.es_concepto_no_homologado ||
        item.tipo_incidencia === 'CONCEPTO_NO_HOMOLOGADO' ||
        item.motivos_penalizacion?.some(m => m.tag?.toLowerCase().includes('concepto') || m.tag?.toLowerCase().includes('financier')) ||
        (item.fuente_1 && item.fuente_1.toLowerCase().includes('egreso')) ||
        (item.fuente_1 && item.fuente_1.toLowerCase().includes('cobranza') && item.score_fuzzy && item.score_fuzzy < 90)
      );
    }
    if (caseFilter === 'PORTFOLIO_RISK') {
      return reviewItems.filter(item =>
        item.es_riesgo_cartera ||
        item.tipo_incidencia === 'RIESGO_CARTERA' ||
        (item.cuotas_impagas !== undefined && item.cuotas_impagas >= 2) ||
        item.motivos_penalizacion?.some(m => m.tag?.toLowerCase().includes('mora') || m.tag?.toLowerCase().includes('cartera') || m.tag?.toLowerCase().includes('deuda')) ||
        (item.fuente_1 && item.fuente_1.toLowerCase().includes('cartera'))
      );
    }
    if (caseFilter.startsWith('STUDENT:')) {
      const targetStudent = caseFilter.replace('STUDENT:', '');
      return reviewItems.filter(item => item.estudiante === targetStudent);
    }
    return reviewItems;
  }, [reviewItems, caseFilter, studentFrequency]);

  // Resetear página al cambiar filtros
  useEffect(() => {
    setCurrentPage(1);
  }, [caseFilter]);

  // Paginación ergonómica
  const totalPages = Math.ceil(filteredReviewItems.length / pageSize) || 1;
  const paginatedReviewItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredReviewItems.slice(start, start + pageSize);
  }, [filteredReviewItems, currentPage, pageSize]);

  // Caso actualmente enfocado
  const currentItem = filteredReviewItems[selectedItemIndex] || reviewItems[0] || null;

  // Sincronizar formulario individual cuando cambia el caso enfocado
  useEffect(() => {
    if (currentItem) {
      const ciClean = (currentItem.ci_raw || '').replace('?', '').trim();
      setEditingCi(ciClean === 'No especificado' ? '' : ciClean);
      setEditingStudent(currentItem.estudiante || '');
      setEditingModulo(currentItem.modulo_detectado || 'Diplomado / Módulo Académico');
      setEditingNota(75.0);
      setSelectedStudentSuggestion(currentItem.sugerencia_catalogo || currentItem.estudiante || '');
      setResolutionStatus(currentItem.estado === 'RESUELTO' ? 'resolved' : 'pending');
      setShowRawContext(false);
    } else {
      setEditingCi('');
      setEditingStudent('');
      setEditingModulo('');
      setEditingNota(75.0);
      setSelectedStudentSuggestion('');
      setShowRawContext(false);
    }
  }, [currentItem]);

  // Casos seleccionados actualmente en memoria
  const selectedItemsData = useMemo(() => {
    return reviewItems.filter(item => selectedReviewIds.includes(item.id));
  }, [reviewItems, selectedReviewIds]);

  // Al abrir el modal de lote, inicializar con modo de preservación de identidad
  const openBatchModal = () => {
    if (selectedReviewIds.length === 0) {
      sileoToast.warning({
        title: 'Selección requerida',
        description: 'Marque al menos una casilla para resolver casos en lote.'
      });
      return;
    }

    setBatchMode('PRESERVE_INDIVIDUAL');
    setBatchStudent('');
    setBatchCi('');
    const firstSelected = reviewItems.find(r => selectedReviewIds.includes(r.id));
    setBatchModulo(firstSelected?.modulo_detectado || 'Módulo Académico');
    setBatchNota(80.0);
    setIsBatchModalOpen(true);
  };

  // Toggle selección de un caso individual
  const toggleSelectCase = (id, e) => {
    if (e) e.stopPropagation();
    setSelectedReviewIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  // Toggle seleccionar todos los casos filtrados
  const handleToggleSelectAll = () => {
    const allFilteredIds = filteredReviewItems.map(i => i.id);
    const areAllSelected = allFilteredIds.every(id => selectedReviewIds.includes(id));
    if (areAllSelected) {
      setSelectedReviewIds(prev => prev.filter(id => !allFilteredIds.includes(id)));
    } else {
      setSelectedReviewIds(prev => Array.from(new Set([...prev, ...allFilteredIds])));
    }
  };

  // Toggle seleccionar los casos de la página actual
  const handleToggleSelectPage = () => {
    const pageIds = paginatedReviewItems.map(i => i.id);
    const areAllPageSelected = pageIds.length > 0 && pageIds.every(id => selectedReviewIds.includes(id));
    if (areAllPageSelected) {
      setSelectedReviewIds(prev => prev.filter(id => !pageIds.includes(id)));
    } else {
      setSelectedReviewIds(prev => Array.from(new Set([...prev, ...pageIds])));
    }
  };

  // ─── ACCIONES DEL EXPEDIENTE LATERAL (DRAWER) ───
  const handleOpenExpediente = (item) => {
    setDrawerItem(item);
    setIsDrawerOpen(true);
  };

  const handleSaveDrawerReview = async (actionType, payload) => {
    if (!drawerItem) return;
    setIsSavingReview(true);
    try {
      if (actionType === 'REJECT') {
        await dataopsApi.unlinkSources({ id: drawerItem.id });
        sileoToast.info({
          title: 'Registro Rechazado',
          description: `Caso '${drawerItem.id}' descartado por inconsistencia y segregado del pipeline.`
        });
      } else {
        await dataopsApi.resolveReviewItem(drawerItem.id, {
          estudiante_resuelto: payload.estudiante_resuelto,
          ci_corregida: payload.ci_corregida,
          modulo_resuelto: payload.modulo_resuelto,
          nota_final: payload.nota_final
        });
        sileoToast.success({
          title: actionType === 'CREATE_NEW' ? 'Nuevo Estudiante Dado de Alta' : 'Registro Validado y Consolidado',
          description: `Caso '${drawerItem.id}' persistido en catálogo y Data Warehouse.`
        });
      }
      setIsDrawerOpen(false);
      setDrawerItem(null);
      await loadReviewTray();
      await loadEntities();
    } catch (err) {
      console.error(err);
      sileoToast.error({ title: 'Error al Guardar Revisión', description: err.message || 'Error en servidor' });
    } finally {
      setIsSavingReview(false);
    }
  };

  // Acción de Resolución Individual
  const handleApprove = async () => {
    if (!currentItem) return;
    try {
      await dataopsApi.resolveReviewItem(currentItem.id, {
        ci_corregida: editingCi.trim() || undefined,
        estudiante_resuelto: editingStudent.trim() || undefined,
        modulo_resuelto: editingModulo.trim() || undefined,
        nota_final: parseFloat(editingNota) || 75.0
      });
      setResolutionStatus('resolved');
      sileoToast.success({
        title: currentItem.es_perfil_nuevo ? 'Nuevo Perfil Creado y Consolidado' : 'Registro Aprobado y Consolidado',
        description: `Caso '${currentItem.id}' persistido en dim_estudiante y fact_rendimiento_academico.`
      });
      await loadReviewTray();
      await loadEntities();
    } catch (err) {
      sileoToast.error({ title: 'Error de Resolución', description: err.message });
    }
  };

  // Paso 1: Preparar la resolución en lote y abrir confirmación de DW (Observación 13)
  const handleStageBatchReview = () => {
    setIsBatchModalOpen(false);
    setIsConfirmDwOpen(true);
  };

  // Paso 2: Ejecutar la transferencia deliberada al Data Warehouse (Observación 13)
  const handleExecuteDwCommit = async () => {
    if (selectedReviewIds.length === 0) return;
    setIsExecutingDw(true);
    try {
      const payload = {
        item_ids: selectedReviewIds,
        // Si el usuario eligió 'SINGLE_HOMOLOGATION', se envía el nombre ingresado.
        // Si eligió 'PRESERVE_INDIVIDUAL' (por defecto), se envía undefined para que el backend conserve el nombre original de cada registro.
        estudiante_resuelto: batchMode === 'SINGLE_HOMOLOGATION' && batchStudent.trim() ? batchStudent.trim() : undefined,
        ci_corregida: batchCi.trim() || undefined,
        modulo_resuelto: batchModulo.trim() || undefined,
        nota_final: parseFloat(batchNota) || 80.0
      };

      const res = await dataopsApi.batchResolveReviewItems(payload);
      sileoToast.success({
        title: 'Consolidación en DW Completada',
        description: res.message || `Se transfirieron ${selectedReviewIds.length} casos validados a PostgreSQL.`
      });
      setIsConfirmDwOpen(false);
      setSelectedReviewIds([]);
      await loadReviewTray();
      await loadEntities();
    } catch (err) {
      console.error(err);
      sileoToast.error({ title: 'Falla al Consolidar en DW', description: err.message });
    } finally {
      setIsExecutingDw(false);
    }
  };

  // Acción de Desvincular Individual
  const handleUnlink = async () => {
    if (!currentItem) return;
    try {
      await dataopsApi.unlinkSources({ id: currentItem.id });
      setResolutionStatus('unlinked');
      sileoToast.info({
        title: 'Fuentes Desvinculadas',
        description: `Caso '${currentItem.id}' segregado de las fuentes conciliadas.`
      });
      await loadReviewTray();
    } catch (err) {
      sileoToast.error({ title: 'Error al Desvincular', description: err.message });
    }
  };

  // Acción de Desvincular en Lote
  const handleBatchUnlink = async () => {
    if (selectedReviewIds.length === 0) return;
    try {
      for (const id of selectedReviewIds) {
        await dataopsApi.unlinkSources({ id });
      }
      sileoToast.info({
        title: 'Casos Desvinculados en Lote',
        description: `${selectedReviewIds.length} casos segregados de fuentes activas.`
      });
      setSelectedReviewIds([]);
      await loadReviewTray();
    } catch (err) {
      sileoToast.error({ title: 'Error al Desvincular', description: err.message });
    }
  };

  const handleReset = () => {
    setResolutionStatus('pending');
    sileoToast.warning({
      title: 'Caso Reabierto',
      description: 'El registro volvió al estado de revisión humana pendiente.'
    });
  };

  // Vincular Entidad No Resuelta en Tab 2
  const handleLinkEntity = async (entityId) => {
    try {
      await dataopsApi.linkEntity(entityId);
      setEntities(prev =>
        prev.map(e => (e.id === entityId ? { ...e, status: 'LINKED' } : e))
      );
      sileoToast.success({
        title: 'Entidad Vinculada con Éxito',
        description: `Entidad #${entityId} asociada a dimensión canónica correspondiente.`
      });
    } catch (err) {
      sileoToast.error({ title: 'Error de Vinculación', description: err.message });
    }
  };

  const handleUnlinkEntity = (entityId) => {
    setEntities(prev =>
      prev.map(e => (e.id === entityId ? { ...e, status: 'PENDING' } : e))
    );
    sileoToast.info({
      title: 'Entidad Desvinculada',
      description: `Entidad #${entityId} devuelta a estado de sugerencia pendiente.`
    });
  };

  // Filtrado de entidades
  const filteredEntities = entities.filter(item => {
    if (entityFilter === 'ALL') return true;
    return item.status === entityFilter;
  });

  const pendingEntitiesCount = entities.filter(e => e.status === 'PENDING').length;

  const tabsConfig = [
    {
      id: 'review',
      label: 'Bandeja de Revisión Humana',
      icon: CheckSquare,
      count: reviewItems.length,
      badgeColor: reviewItems.length > 0 ? '#d9383a' : '#1b8754'
    },
    {
      id: 'entities',
      label: 'Entidades No Resueltas',
      icon: GitMerge,
      count: pendingEntitiesCount,
      badgeColor: '#b45309'
    },
    {
      id: 'inconsistencies',
      label: 'Registro de Inconsistencias',
      icon: AlertTriangle,
      count: reviewItems.length + pendingEntitiesCount,
      badgeColor: '#d9383a'
    },
    {
      id: 'telemetry',
      label: 'Telemetría y Rendimiento IA',
      icon: Cpu
    }
  ];


  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '0 8px 56px' }}>
      <PageHeader
        category="AUDITOR_CALIDAD · DataOps"
        title="Panel de Auditoría Humana (Human-in-the-Loop)"
        subtitle="Supervisión de registros con Score < 0.85. El Catálogo Maestro funciona como guía de cotejo; si una entidad no existe, BETO permite darla de alta y persistir sus relaciones en las tablas dimensionales correctas."
        actions={
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn-pill-ghost"
              onClick={loadReviewTray}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
              title="Recargar bandeja desde PostgreSQL"
            >
              <RotateCcw size={15} />
              <span>Actualizar</span>
            </button>
            <button
              className="btn-pill-ghost"
              onClick={() => setIsBetoOpen(true)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              <Terminal size={15} />
              <span>Telemetría BETO</span>
            </button>
          </div>
        }
      />

      {/* Navegación por pestañas */}
      <DataOpsTabs
        tabs={tabsConfig}
        activeTab={activeTab}
        onChangeTab={setActiveTab}
      />

      {/* ─── TAB 1: BANDEJA DE REVISIÓN INTERACTIVA (Score < 0.85) ─── */}
      {activeTab === 'review' && (
        <div>
          {isLoadingReview ? (
            <div className="card-mist" style={{ padding: '56px', textAlign: 'center', borderRadius: '24px' }}>
              <Activity className="animate-spin" size={32} color="var(--color-gira-gold)" style={{ margin: '0 auto 16px' }} />
              <div style={{ fontSize: '15px', color: 'var(--color-slate-gray)' }}>
                Consultando bandeja de revisión en PostgreSQL (Score &lt; 0.85)...
              </div>
            </div>
          ) : reviewItems.length === 0 ? (
            <div className="card-mist" style={{ padding: '56px 24px', textAlign: 'center', borderRadius: '24px', border: '1px dashed var(--color-border)' }}>
              <div style={{ width: '60px', height: '60px', borderRadius: '50%', backgroundColor: 'rgba(27, 135, 84, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <CheckCircle2 size={34} color="#1b8754" />
              </div>
              <div style={{ textTransform: 'uppercase', fontSize: '11px', fontWeight: 700, letterSpacing: '1.2px', color: 'var(--color-gira-gold)', marginBottom: '8px' }}>
                Auditoría de Integridad &amp; Conciliación
              </div>
              <h3 style={{ fontFamily: 'var(--font-signifier)', fontSize: '26px', margin: '0 0 10px', fontWeight: 400 }}>
                Bandeja Limpia: Cero Casos Pendientes de Auditoría Humana
              </h3>
              <p style={{ maxWidth: '640px', margin: '0 auto 24px', fontSize: '14px', color: 'var(--color-slate-gray)', lineHeight: 1.6 }}>
                Todos los registros del lote activo superaron el umbral institucional (&gt;= 85%) o han sido aprobados y consolidados en el Data Warehouse canónico (dim_estudiante, dim_modulo, fact_rendimiento_academico).
              </p>
              <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }}>
                <button
                  className="btn-pill-dark"
                  onClick={() => navigate('/dataops/ingesta')}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
                >
                  <ArrowRight size={15} />
                  <span>Ir a Ingesta &amp; Pipeline</span>
                </button>
                <button
                  className="btn-pill-ghost"
                  onClick={() => navigate('/dataops/beto-ner')}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
                >
                  <span>Laboratorio BETO NER</span>
                </button>
                <button
                  className="btn-pill-ghost"
                  onClick={loadReviewTray}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
                >
                  <RotateCcw size={14} />
                  <span>Recargar Bandeja</span>
                </button>
              </div>
            </div>
          ) : (
            <div>
              {/* ─── BANDEJA DE TRABAJO: CABECERA Y FILTROS POR INCIDENCIA (PUNTO 11) ─── */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '14px',
                  marginBottom: '16px',
                  padding: '16px 20px',
                  backgroundColor: 'var(--color-surface)',
                  borderRadius: '16px',
                  border: '1px solid var(--color-border)'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-gira-gold)' }}>
                      BANDEJA DE TRABAJO HITL
                    </span>
                  </div>
                  <h3 style={{ fontFamily: 'var(--font-signifier)', fontSize: '20px', margin: 0, fontWeight: 400, color: 'var(--color-ink-black)' }}>
                    Revisión Pendiente
                  </h3>
                  <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
                    <strong>{filteredReviewItems.length}</strong> casos requieren atención humana antes de su consolidación en el DW.
                  </div>
                </div>

                {/* Filtros Rápidos por Tipo de Incidencia (Punto 11) */}
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                  {[
                    { id: 'ALL', label: `Todos (${reviewItems.length})` },
                    { id: 'MISSING_CI', label: `CI Faltante (${missingCiCount})` },
                    { id: 'NOT_FOUND', label: `No Encontrado (${notFoundCount})` },
                    { id: 'FUZZY_MATCH', label: `Coincidencia Dudosa (${fuzzyMatchCount})` },
                    { id: 'DUPLICATES', label: `Duplicados (${duplicatesCount})` },
                    { id: 'UNMAPPED_CONCEPT', label: `Concepto No Homologado (${unmappedConceptCount})` },
                    { id: 'PORTFOLIO_RISK', label: `Riesgo de Cartera (${portfolioRiskCount})` },
                  ].map(tab => (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => { setCaseFilter(tab.id); setCurrentPage(1); }}
                      style={{
                        padding: '6px 14px',
                        borderRadius: '9999px',
                        fontSize: '12px',
                        fontWeight: caseFilter === tab.id ? 700 : 500,
                        border: caseFilter === tab.id ? '1px solid var(--color-ink-black)' : '1px solid var(--color-border)',
                        backgroundColor: caseFilter === tab.id ? 'var(--color-ink-black)' : 'transparent',
                        color: caseFilter === tab.id ? '#ffffff' : 'var(--color-ink-black)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    type="button"
                    className="btn-pill-ghost"
                    onClick={handleToggleSelectAll}
                    style={{ padding: '6px 14px', fontSize: '12px' }}
                  >
                    {filteredReviewItems.length > 0 && filteredReviewItems.every(i => selectedReviewIds.includes(i.id))
                      ? 'Deseleccionar Todos'
                      : 'Seleccionar Todos'}
                  </button>
                </div>
              </div>

              {/* ─── TABLA RESUMEN DE CASOS CON MULTI-SELECCIÓN (CHECKBOXES) ─── */}
              <div style={{ marginBottom: '20px' }}>
                <ResponsiveTable>
                  <table className="steep-table">
                    <thead>
                      <tr>
                        <th style={{ width: '40px', textAlign: 'center' }}>
                          <input
                            type="checkbox"
                            checked={paginatedReviewItems.length > 0 && paginatedReviewItems.every(i => selectedReviewIds.includes(i.id))}
                            onChange={handleToggleSelectPage}
                            style={{ cursor: 'pointer', transform: 'scale(1.15)' }}
                            title="Seleccionar / deseleccionar casos de la página actual"
                          />
                        </th>
                        <th style={{ width: '90px' }}>Caso ID</th>
                        <th>Entidad & Registro Reconocido</th>
                        <th>Incidencia Identificada</th>
                        <th style={{ width: '110px' }}>Confianza BETO</th>
                        <th>Fuente & Destino Canónico</th>
                        <th style={{ textAlign: 'right', width: '150px' }}>Acción</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedReviewItems.map((item) => {
                        const isSelected = selectedReviewIds.includes(item.id);
                        const isCurrent = currentItem?.id === item.id;
                        const globalIdx = filteredReviewItems.findIndex(x => x.id === item.id);

                        const isCiMissing = !item.ci_raw || item.ci_raw === 'No especificado' || item.ci_raw.includes('?');
                        const isNotFound = item.es_perfil_nuevo || !item.sugerencia_catalogo;
                        const isFuzzy = item.rapidfuzz_cross && item.rapidfuzz_cross < 85 && !item.es_perfil_nuevo;

                        let problemLabel = 'Revisión (< 85%)';
                        let problemBg = 'rgba(0, 0, 0, 0.05)';
                        let problemColor = 'var(--color-slate-gray)';

                        if (isCiMissing) {
                          problemLabel = 'CI Faltante o Dudosa';
                          problemBg = 'rgba(217, 56, 58, 0.12)';
                          problemColor = '#d9383a';
                        } else if (isNotFound) {
                          problemLabel = 'No Encontrado en Catálogo';
                          problemBg = 'rgba(217, 155, 38, 0.15)';
                          problemColor = '#b45309';
                        } else if (isFuzzy) {
                          problemLabel = `Coincidencia Dudosa (${item.rapidfuzz_cross}%)`;
                          problemBg = 'rgba(217, 155, 38, 0.12)';
                          problemColor = '#b45309';
                        }

                        return (
                          <tr
                            key={item.id}
                            onClick={() => {
                              setSelectedItemIndex(globalIdx !== -1 ? globalIdx : 0);
                              handleOpenExpediente(item);
                            }}
                            style={{
                              cursor: 'pointer',
                              backgroundColor: isCurrent
                                ? 'rgba(217, 155, 38, 0.08)'
                                : isSelected
                                ? 'rgba(2, 132, 199, 0.05)'
                                : undefined,
                              borderLeft: isCurrent
                                ? '3px solid var(--color-gira-gold)'
                                : isSelected
                                ? '3px solid #0284c7'
                                : '3px solid transparent',
                              transition: 'background-color 0.15s ease'
                            }}
                          >
                            <td style={{ textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={(e) => toggleSelectCase(item.id, e)}
                                style={{ cursor: 'pointer', transform: 'scale(1.15)' }}
                              />
                            </td>
                            <td>
                              <code style={{ fontWeight: 700, color: 'var(--color-gira-gold)' }}>{item.id}</code>
                            </td>
                            <td>
                              {(() => {
                                const entityBadge = getEntityTargetTableBadge(item.tipo_entidad || (item.es_concepto_no_homologado ? 'CONCEPTO_FINANCIERO' : 'ESTUDIANTE'));
                                return (
                                  <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
                                      <span
                                        style={{
                                          fontSize: '10px',
                                          fontFamily: 'var(--font-mono)',
                                          fontWeight: 700,
                                          padding: '1px 6px',
                                          borderRadius: '4px',
                                          color: entityBadge.color,
                                          backgroundColor: entityBadge.bgColor,
                                          border: `1px solid ${entityBadge.borderColor}`,
                                        }}
                                      >
                                        {entityBadge.table}
                                      </span>
                                      <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)', fontWeight: 500 }}>
                                        {entityBadge.label}
                                      </span>
                                    </div>
                                    <strong style={{ color: 'var(--color-ink-black)', fontSize: '13px' }}>
                                      {item.estudiante}
                                    </strong>
                                    {item.modulo_detectado && item.modulo_detectado !== 'No especificado' && (
                                      <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', marginTop: '1px' }}>
                                        {item.modulo_detectado}
                                      </div>
                                    )}
                                  </div>
                                );
                              })()}
                            </td>
                            <td>
                              <span
                                style={{
                                  fontSize: '11px',
                                  padding: '3px 8px',
                                  borderRadius: '6px',
                                  fontWeight: 600,
                                  backgroundColor: problemBg,
                                  color: problemColor,
                                  display: 'inline-block'
                                }}
                              >
                                {problemLabel}
                              </span>
                            </td>
                            <td>
                              <span style={{
                                fontWeight: 700,
                                fontSize: '13px',
                                color: (item.ner_confidence || 0.58) >= 0.85 ? '#1b8754' : (item.ner_confidence || 0.58) >= 0.70 ? '#b45309' : '#d9383a'
                              }}>
                                {Math.round((item.ner_confidence || 0.58) * 100)}%
                              </span>
                            </td>
                            <td style={{ fontSize: '12px' }}>
                              {(() => {
                                const sourceMeta = getSourceTableMeta(item.fuente_1 || '');
                                return (
                                  <div>
                                    <div style={{ fontWeight: 600, color: 'var(--color-ink-black)', fontSize: '12px' }}>
                                      {sourceMeta.domainTitle}
                                    </div>
                                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                                      <span>{item.fuente_1}</span>
                                      <span style={{ color: 'var(--color-ash-gray)' }}>· Fila {item.line_number || 1}</span>
                                    </div>
                                  </div>
                                );
                              })()}
                            </td>
                            <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                              <button
                                type="button"
                                className="btn-pill-dark"
                                onClick={() => {
                                  setSelectedItemIndex(globalIdx !== -1 ? globalIdx : 0);
                                  handleOpenExpediente(item);
                                }}
                                style={{
                                  padding: '5px 14px',
                                  fontSize: '12px',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '6px'
                                }}
                              >
                                <CheckSquare size={13} />
                                <span>Revisar Expediente</span>
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </ResponsiveTable>

                {/* ─── CONTROLES DE PAGINACIÓN ERGONÓMICA ─── */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 18px',
                  marginTop: '12px',
                  backgroundColor: 'var(--color-surface)',
                  borderRadius: '14px',
                  border: '1px solid var(--color-border)',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '13px', color: 'var(--color-slate-gray)' }}>
                    <span>
                      Mostrando <strong>{filteredReviewItems.length === 0 ? 0 : (currentPage - 1) * pageSize + 1}</strong> a <strong>{Math.min(filteredReviewItems.length, currentPage * pageSize)}</strong> de <strong>{filteredReviewItems.length}</strong> casos
                    </span>
                    <span style={{ color: 'var(--color-border)' }}>|</span>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                      <span>Por página:</span>
                      <select
                        value={pageSize}
                        onChange={(e) => {
                          setPageSize(Number(e.target.value));
                          setCurrentPage(1);
                        }}
                        style={{
                          padding: '3px 8px',
                          borderRadius: '8px',
                          border: '1px solid var(--color-border)',
                          backgroundColor: 'var(--color-paper-white)',
                          color: 'var(--color-ink-black)',
                          fontSize: '12px',
                          cursor: 'pointer'
                        }}
                      >
                        <option value={10}>10</option>
                        <option value={15}>15</option>
                        <option value={25}>25</option>
                        <option value={50}>50</option>
                      </select>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                      className="btn-pill-ghost"
                      onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                      disabled={currentPage === 1}
                      style={{
                        padding: '5px 12px',
                        fontSize: '12px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        opacity: currentPage === 1 ? 0.4 : 1,
                        cursor: currentPage === 1 ? 'not-allowed' : 'pointer'
                      }}
                    >
                      <ChevronLeft size={14} /> Anterior
                    </button>

                    <span style={{ fontSize: '13px', fontWeight: 600, padding: '0 8px' }}>
                      Página {currentPage} de {totalPages}
                    </span>

                    <button
                      className="btn-pill-ghost"
                      onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                      disabled={currentPage >= totalPages}
                      style={{
                        padding: '5px 12px',
                        fontSize: '12px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        opacity: currentPage >= totalPages ? 0.4 : 1,
                        cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer'
                      }}
                    >
                      Siguiente <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              </div>

              {/* ─── BARRA FLOTANTE DE ACCIONES EN LOTE (BATCH RESOLVE BAR) ─── */}
              {selectedReviewIds.length > 0 && (
                <div
                  style={{
                    position: 'sticky',
                    bottom: '24px',
                    zIndex: 80,
                    backgroundColor: 'var(--color-ink-black)',
                    color: '#ffffff',
                    padding: '16px 24px',
                    borderRadius: '20px',
                    boxShadow: '0 12px 36px rgba(0, 0, 0, 0.35)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '16px',
                    marginBottom: '24px',
                    animation: 'fadeInUp 0.25s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{
                      backgroundColor: 'var(--color-gira-gold)',
                      color: '#000000',
                      borderRadius: '50%',
                      width: '28px',
                      height: '28px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                      fontSize: '13px'
                    }}>
                      {selectedReviewIds.length}
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '14px' }}>
                        {selectedReviewIds.length} caso(s) seleccionados para resolución conjunta
                      </div>
                      <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.7)' }}>
                        Se consolidarán en dim_estudiante, dim_modulo y fact_rendimiento_academico en una sola transacción.
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <button
                      className="btn-pill-ghost"
                      onClick={() => setSelectedReviewIds([])}
                      style={{ color: '#ffffff', borderColor: 'rgba(255, 255, 255, 0.25)', padding: '8px 16px', fontSize: '12px' }}
                    >
                      Deseleccionar
                    </button>

                    <button
                      className="btn-pill-ghost"
                      onClick={handleBatchUnlink}
                      style={{ color: '#f87171', borderColor: 'rgba(248, 113, 113, 0.4)', padding: '8px 16px', fontSize: '12px' }}
                    >
                      Desvincular {selectedReviewIds.length} Seleccionados
                    </button>

                    <button
                      className="btn-pill-dark"
                      onClick={openBatchModal}
                      style={{
                        backgroundColor: 'var(--color-gira-gold)',
                        color: '#000000',
                        fontWeight: 700,
                        padding: '8px 20px',
                        fontSize: '13px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px'
                      }}
                    >
                      <Sparkles size={16} />
                      <span>Resolver {selectedReviewIds.length} Caso(s) en Lote →</span>
                    </button>
                  </div>
                </div>
              )}

              {/* ─── EXPEDIENTE SELECCIONADO / ACCESO DIRECTO AL DRAWER (OBSERVACIÓN 11 Y 12) ─── */}
              {currentItem && (
                <div
                  className="floating-artifact"
                  style={{
                    padding: '18px 24px',
                    borderRadius: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '16px',
                    marginBottom: '20px',
                    borderLeft: '4px solid var(--color-gira-gold)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <div style={{
                      backgroundColor: 'rgba(217, 155, 38, 0.12)',
                      color: 'var(--color-gira-gold)',
                      padding: '10px',
                      borderRadius: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <CheckSquare size={22} />
                    </div>
                    <div>
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.8px', color: 'var(--color-gira-gold)' }}>
                        Caso Activo · {currentItem.id}
                      </div>
                      <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
                        {currentItem.estudiante} — <span style={{ fontWeight: 400, color: 'var(--color-slate-gray)' }}>{currentItem.modulo_detectado}</span>
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                        {currentItem.fuente_1} (Fila {currentItem.line_number || 1}) · Confianza BETO: <strong>{Math.round((currentItem.ner_confidence || 0.58) * 100)}%</strong>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <button
                      type="button"
                      className="btn-pill-ghost"
                      onClick={() => setIsBetoOpen(true)}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', padding: '7px 14px' }}
                    >
                      <Terminal size={14} />
                      <span>Telemetría BETO</span>
                    </button>
                    <button
                      type="button"
                      className="btn-pill-dark"
                      onClick={() => handleOpenExpediente(currentItem)}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '8px 18px',
                        fontSize: '13px',
                        backgroundColor: 'var(--color-gira-gold)',
                        color: '#000000',
                        fontWeight: 700
                      }}
                    >
                      <CheckSquare size={15} />
                      <span>Abrir Expediente de Revisión →</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ─── TAB 2: ENTIDADES NO RESUELTAS (RapidFuzz) ─── */}
      {activeTab === 'entities' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
            <div style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>
              Mapeo difuso de entidades crudas hacia dimensiones maestras 3NF. Si una entidad no existe, el sistema la deriva a creación dimensional.
            </div>

            <div style={{ display: 'flex', gap: '6px' }}>
              {['ALL', 'PENDING', 'LINKED'].map((filterMode) => (
                <button
                  key={filterMode}
                  onClick={() => setEntityFilter(filterMode)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '9999px',
                    fontSize: '12px',
                    fontWeight: entityFilter === filterMode ? 600 : 500,
                    border: '1px solid var(--color-border)',
                    backgroundColor: entityFilter === filterMode ? 'var(--color-ink-black)' : 'transparent',
                    color: entityFilter === filterMode ? '#ffffff' : 'var(--color-slate-gray)',
                    cursor: 'pointer'
                  }}
                >
                  {filterMode === 'ALL' ? 'Todas' : filterMode === 'PENDING' ? 'Pendientes' : 'Vinculadas'}
                </button>
              ))}
            </div>
          </div>

          <div>
            <ResponsiveTable>
              <table className="steep-table">
                <thead>
                  <tr>
                    <th>Cadena Detectada en Fuentes</th>
                    <th>Tipo de Entidad</th>
                    <th>Entidad Canónica Sugerida</th>
                    <th>Código Canónico</th>
                    <th>Score Match RapidFuzz</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEntities.map((ent) => (
                    <tr key={ent.id}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{ent.raw_text}</td>
                      <td><span className="badge-source">{ent.entity_type}</span></td>
                      <td>{ent.suggested_canonical}</td>
                      <td><code>{ent.canonical_code || 'DIM-PEND'}</code></td>
                      <td>
                        <span style={{ fontWeight: 600, color: ent.score >= 90 ? '#1b8754' : '#b45309' }}>
                          {ent.score}%
                        </span>
                      </td>
                      <td>
                        {ent.status === 'LINKED' ? (
                          <button
                            className="btn-pill-ghost"
                            onClick={() => handleUnlinkEntity(ent.id)}
                            style={{ padding: '4px 10px', fontSize: '11px', color: '#b45309' }}
                          >
                            Desvincular
                          </button>
                        ) : (
                          <button
                            className="btn-pill-dark"
                            onClick={() => handleLinkEntity(ent.id)}
                            style={{ padding: '5px 12px', fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                          >
                            <Link2 size={13} />
                            <span>Vincular</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ResponsiveTable>
          </div>
        </div>
      )}

      {/* ─── TAB 3: REGISTRO DE INCONSISTENCIAS ─── */}
      {activeTab === 'inconsistencies' && (
        <div>
          {reviewItems.length === 0 && entities.length === 0 ? (
            <div className="card-mist" style={{ padding: '48px 24px', textAlign: 'center', borderRadius: '24px', border: '1px dashed var(--color-border)' }}>
              <div style={{ width: '56px', height: '56px', borderRadius: '50%', backgroundColor: 'rgba(27, 135, 84, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <CheckCircle2 size={32} color="#1b8754" />
              </div>
              <div style={{ textTransform: 'uppercase', fontSize: '11px', fontWeight: 700, letterSpacing: '1.2px', color: 'var(--color-gira-gold)', marginBottom: '8px' }}>
                Trazabilidad de Calidad de Datos
              </div>
              <h3 style={{ fontFamily: 'var(--font-signifier)', fontSize: '24px', margin: '0 0 10px', fontWeight: 400 }}>
                Registro Limpio: Cero Inconsistencias Activas
              </h3>
              <p style={{ maxWidth: '600px', margin: '0 auto', fontSize: '14px', color: 'var(--color-slate-gray)', lineHeight: 1.6 }}>
                No se detectaron discrepancias dimensionales ni anomalías en los bloques tabulares del lote activo.
              </p>
            </div>
          ) : (
            <ResponsiveTable>
              <table className="steep-table">
                <thead>
                  <tr>
                    <th>Ticket ID</th>
                    <th>Archivo Origen</th>
                    <th>Código de Error</th>
                    <th>Descripción de Inconsistencia</th>
                    <th>Severidad</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {reviewItems.map((item, idx) => (
                    <tr key={`inc-rev-${item.id || idx}`} className="row-critical-alert">
                      <td><code>INC-{item.db_id || idx + 1}</code></td>
                      <td>{item.fuente_1 || 'Lote Activo'}</td>
                      <td><code>{item.es_perfil_nuevo ? 'ALTA_DIMENSIONAL_REQUERIDA' : 'ERR_SCORE_AMBIGUO'}</code></td>
                      <td>{item.disparador || `Ambigüedad en entidad '${item.estudiante}'`}</td>
                      <td>
                        <span className="tag-critical-field">
                          {item.es_perfil_nuevo ? 'NEW_PROFILE' : 'CRITICAL'}
                        </span>
                      </td>
                      <td>
                        <span style={{ color: '#b45309', fontWeight: 600 }}>
                          {item.estado === 'RESUELTO' ? 'Consolidado' : 'En Revisión'}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {entities.map((ent, idx) => (
                    <tr key={`inc-ent-${ent.id || idx}`}>
                      <td><code>INC-STG-{ent.id}</code></td>
                      <td>PostgreSQL Staging</td>
                      <td><code>ERR_HOMONIMIA_BETO</code></td>
                      <td>{`Entidad no resuelta: '${ent.raw_text}' (${ent.entity_type})`}</td>
                      <td><span style={{ backgroundColor: 'rgba(180, 83, 9, 0.15)', color: '#b45309', padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>WARNING</span></td>
                      <td><span className="badge-status-completed">{ent.status === 'LINKED' ? 'Homologado' : 'Pendiente'}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ResponsiveTable>
          )}
        </div>
      )}

      {/* ─── TAB 4: TELEMETRÍA IA ─── */}
      {activeTab === 'telemetry' && telemetry && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <div className="card-mist" style={{ padding: '20px' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-slate-gray)' }}>Latencia P95 Inferencia</div>
              <div style={{ fontSize: '32px', fontFamily: 'var(--font-signifier)', fontWeight: 400, color: '#1b8754' }}>
                {telemetry.kpis?.p95_latency_sec} seg
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Por lote de registros</div>
            </div>

            <div className="card-mist" style={{ padding: '20px' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-slate-gray)' }}>Aceleración Docker</div>
              <div style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-ink-black)', margin: '8px 0' }}>
                {telemetry.kpis?.acceleration_device}
              </div>
              <div style={{ fontSize: '11px', color: '#1b8754' }}>PostgreSQL Hook: Operativo</div>
            </div>

            <div className="card-mist" style={{ padding: '20px' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-slate-gray)' }}>Throughput Tokens</div>
              <div style={{ fontSize: '32px', fontFamily: 'var(--font-signifier)', fontWeight: 400 }}>
                {telemetry.kpis?.token_throughput} tok/s
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Tokenizador BPE</div>
            </div>

            <div className="card-mist" style={{ padding: '20px' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-slate-gray)' }}>Consumo VRAM</div>
              <div style={{ fontSize: '32px', fontFamily: 'var(--font-signifier)', fontWeight: 400, color: 'var(--color-gira-gold)' }}>
                {telemetry.kpis?.vram_usage_gb}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>Asignación de memoria GPU</div>
            </div>
          </div>

          <div className="card-mist" style={{ padding: '20px', borderRadius: '20px' }}>
            <h4 style={{ fontFamily: 'var(--font-signifier)', fontSize: '18px', margin: '0 0 8px 0' }}>
              Especificaciones de Arquitectura NLP &amp; Catálogo Dimensional
            </h4>
            <div style={{ fontSize: '13px', color: 'var(--color-slate-gray)', lineHeight: 1.6 }}>
              • Modelo Base: <strong>{telemetry.model_specs?.architecture}</strong><br />
              • Umbral de Certidumbre: <strong>Score &gt;= {telemetry.model_specs?.confidence_threshold}</strong> (casos inferiores derivados a Auditoría Humana)<br />
              • Motor de Relaciones: <strong>RapidFuzz + Validación 3NF (dim_estudiante, dim_modulo, dim_docente)</strong><br />
              • Política de Nuevos Perfiles: Inserción automática de llaves canónicas en dimensiones al confirmar en HITL.
            </div>
          </div>
        </div>
      )}

      {/* ─── MODAL DE RESOLUCIÓN EN LOTE (BATCH RESOLVE MODAL) ─── */}
      {isBatchModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '16px'
          }}
          onClick={() => setIsBatchModalOpen(false)}
        >
          <div
            className="modal-panel"
            style={{
              width: '100%',
              maxWidth: '560px',
              backgroundColor: 'var(--color-surface)',
              borderRadius: '24px',
              padding: '32px',
              boxShadow: '0 20px 50px rgba(0, 0, 0, 0.3)',
              border: '1px solid var(--color-border)',
              position: 'relative'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setIsBatchModalOpen(false)}
              style={{
                position: 'absolute',
                top: '20px',
                right: '20px',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--color-slate-gray)'
              }}
            >
              <X size={20} />
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <div style={{
                backgroundColor: 'rgba(217, 155, 38, 0.15)',
                color: 'var(--color-gira-gold)',
                padding: '8px',
                borderRadius: '12px'
              }}>
                <Sparkles size={20} />
              </div>
              <h3 style={{ fontFamily: 'var(--font-signifier)', fontSize: '22px', margin: 0, fontWeight: 400 }}>
                Resolución en Lote de {selectedReviewIds.length} Casos
              </h3>
            </div>

            <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: '0 0 16px 0', lineHeight: 1.5 }}>
              Revise los registros seleccionados. El sistema protege las identidades individuales por defecto para evitar sobreescritura accidental.
            </p>

            {/* Tabla Resumen de Alumnos Seleccionados */}
            <div style={{
              maxHeight: '180px',
              overflowY: 'auto',
              marginBottom: '20px',
              borderRadius: '12px',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-mist-gray)'
            }}>
              <table className="steep-table" style={{ fontSize: '12px', width: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ width: '80px' }}>Caso</th>
                    <th>Estudiante Extraído</th>
                    <th>CI Propuesta</th>
                    <th>Módulo</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedItemsData.map((item) => (
                    <tr key={item.id}>
                      <td><code style={{ fontWeight: 700, color: 'var(--color-gira-gold)' }}>{item.id}</code></td>
                      <td><strong style={{ color: 'var(--color-ink-black)' }}>{item.estudiante}</strong></td>
                      <td><code style={{ fontSize: '11px' }}>{item.ci_raw && item.ci_raw !== 'No especificado' ? item.ci_raw : `TEMP-${item.id.replace('REV-', '')}`}</code></td>
                      <td style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)' }}>{batchModulo || item.modulo_detectado}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Selector de Modo de Resolución (Protección contra sobreescritura de nombres) */}
            <div style={{ marginBottom: '20px', padding: '16px', borderRadius: '14px', backgroundColor: 'var(--color-paper-white)', border: '1px solid var(--color-border)' }}>
              <div style={{ fontSize: '12.5px', fontWeight: 700, marginBottom: '10px', color: 'var(--color-ink-black)' }}>
                Tratamiento de Nombres e Identidad:
              </div>

              <label style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', marginBottom: '12px', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="batchMode"
                  checked={batchMode === 'PRESERVE_INDIVIDUAL'}
                  onChange={() => setBatchMode('PRESERVE_INDIVIDUAL')}
                  style={{ marginTop: '3px' }}
                />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
                    Conservar nombres individuales de cada registro (Recomendado)
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '2px' }}>
                    Cada uno de los {selectedReviewIds.length} estudiantes mantendrá su nombre detectado por BETO. Se registrarán o vincularán sus perfiles respectivos en el catálogo sin sobreescribir identidades.
                  </div>
                </div>
              </label>

              <label style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="batchMode"
                  checked={batchMode === 'SINGLE_HOMOLOGATION'}
                  onChange={() => setBatchMode('SINGLE_HOMOLOGATION')}
                  style={{ marginTop: '3px' }}
                />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
                    Homologar todos los casos a un solo estudiante
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '2px' }}>
                    Use esta opción únicamente si todos los registros seleccionados corresponden a la misma persona física con variaciones ortográficas.
                  </div>
                </div>
              </label>

              {batchMode === 'SINGLE_HOMOLOGATION' && (
                <div style={{ marginTop: '12px', paddingLeft: '24px' }}>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                    Nombre Canónico Unificado:
                  </label>
                  <input
                    type="text"
                    value={batchStudent}
                    onChange={(e) => setBatchStudent(e.target.value)}
                    placeholder="ej. Lucía Quispe Morales"
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: '10px',
                      border: '1px solid var(--color-border)',
                      fontSize: '13px'
                    }}
                  />
                </div>
              )}
            </div>

            {/* Atributos Comunes Opcionales */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '24px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                  Módulo / Diplomado Común:
                </label>
                <input
                  type="text"
                  value={batchModulo}
                  onChange={(e) => setBatchModulo(e.target.value)}
                  placeholder="ej. Módulo Académico"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '10px',
                    border: '1px solid var(--color-border)',
                    fontSize: '13px'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                  Calificación Homologada:
                </label>
                <input
                  type="number"
                  value={batchNota}
                  onChange={(e) => setBatchNota(e.target.value)}
                  placeholder="80.0"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '10px',
                    border: '1px solid var(--color-border)',
                    fontSize: '13px',
                    fontFamily: 'var(--font-mono)'
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn-pill-ghost"
                onClick={() => setIsBatchModalOpen(false)}
                style={{ padding: '8px 18px', fontSize: '13px' }}
              >
                Cancelar
              </button>
              <button
                className="btn-pill-dark"
                onClick={handleStageBatchReview}
                style={{
                  backgroundColor: 'var(--color-gira-gold)',
                  color: '#000000',
                  fontWeight: 700,
                  padding: '8px 20px',
                  fontSize: '13px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <span>Guardar Revisión</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Confirmación Deliberada de Inserción en DW (Observación 13) */}
      {isConfirmDwOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(5px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 110,
            padding: '20px'
          }}
          onClick={() => !isExecutingDw && setIsConfirmDwOpen(false)}
        >
          <div
            className="floating-artifact"
            style={{
              width: '100%',
              maxWidth: '520px',
              padding: '32px',
              borderRadius: '24px',
              backgroundColor: 'var(--color-surface)',
              boxShadow: '0 24px 60px rgba(0, 0, 0, 0.35)',
              position: 'relative'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
              <div style={{
                backgroundColor: 'rgba(27, 135, 84, 0.15)',
                color: '#1b8754',
                padding: '10px',
                borderRadius: '14px'
              }}>
                <Database size={24} />
              </div>
              <div>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.8px', color: 'var(--color-gira-gold)' }}>
                  PASO 2 DE 2 · PERSISTENCIA TRANSACCIONAL
                </div>
                <h3 style={{ fontFamily: 'var(--font-signifier)', fontSize: '22px', margin: 0, fontWeight: 400, color: 'var(--color-ink-black)' }}>
                  Confirmar Inserción en Data Warehouse
                </h3>
              </div>
            </div>

            <p style={{ fontSize: '13.5px', color: 'var(--color-slate-gray)', lineHeight: 1.6, margin: '0 0 16px 0' }}>
              Se transferirán <strong>{selectedReviewIds.length}</strong> registros validados a las tablas canónicas de PostgreSQL:
            </p>

            <div style={{
              padding: '14px 18px',
              borderRadius: '12px',
              backgroundColor: 'var(--color-mist-gray)',
              marginBottom: '20px',
              fontSize: '12.5px',
              lineHeight: 1.7,
              border: '1px solid var(--color-border)'
            }}>
              <div>• <code style={{ fontWeight: 700 }}>public.dim_estudiante</code> ({batchMode === 'PRESERVE_INDIVIDUAL' ? `${selectedReviewIds.length} perfiles individuales preservados` : '1 perfil unificado'})</div>
              <div>• <code style={{ fontWeight: 700 }}>public.dim_modulo</code> (Dimensión curricular homologada)</div>
              <div>• <code style={{ fontWeight: 700 }}>public.fact_rendimiento_academico</code> (Hechos de auditoría confirmados)</div>
            </div>

            <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginBottom: '24px' }}>
              Esta acción es definitiva y cerrará los casos en la bandeja de auditoría humana HITL.
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn-pill-ghost"
                onClick={() => setIsConfirmDwOpen(false)}
                disabled={isExecutingDw}
                style={{ padding: '8px 18px', fontSize: '13px' }}
              >
                Cancelar
              </button>
              <button
                className="btn-pill-dark"
                onClick={handleExecuteDwCommit}
                disabled={isExecutingDw}
                style={{
                  backgroundColor: '#1b8754',
                  color: '#ffffff',
                  fontWeight: 700,
                  padding: '8px 22px',
                  fontSize: '13px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                {isExecutingDw ? (
                  <>
                    <Activity size={15} className="spinner" />
                    <span>Consolidando en PostgreSQL...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle size={15} />
                    <span>Confirmar Consolidación en DW</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Drawer Lateral de BETO */}
      <BetoDrawer
        isOpen={isBetoOpen}
        onClose={() => setIsBetoOpen(false)}
      />

      {/* Expediente Lateral de Revisión (HITL · Observación 12) */}
      <CaseReviewDrawer
        isOpen={isDrawerOpen}
        onClose={() => {
          setIsDrawerOpen(false);
          setDrawerItem(null);
        }}
        item={drawerItem}
        catalogStudents={catalogStudents}
        onSaveReview={handleSaveDrawerReview}
        isSaving={isSavingReview}
      />
    </div>
  );
}
