import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import {
  UserCheck, AlertTriangle, AlertCircle, CheckCircle2, RotateCcw, XCircle,
  HelpCircle, Eye, EyeOff, ShieldCheck, ArrowRight, CornerDownRight,
  Sparkles, Keyboard, History, Clock, Check, Edit3, Merge, UserX,
  FileDown, Database, GraduationCap, CreditCard, ShoppingCart, ShieldAlert,
  ChevronDown, ChevronUp, FileText, Download
} from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import { dataopsApi } from '../../api/dataopsApi';
import { sileo } from 'sileo';
import { sileoToast } from '../../services/sileoToast';

export default function HumanReviewFlowView() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Soporta id por params (:id) o por query (?lote=)
  const batchId = id || searchParams.get('lote');

  const [activeTab, setActiveTab] = useState('PENDIENTES'); // 'PENDIENTES' | 'RESUELTOS'
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [selectedArea, setSelectedArea] = useState('TODAS'); // 'TODAS' | 'academica' | 'financiera' | 'comercial' | 'calidad'
  const [selectedReason, setSelectedReason] = useState('ALL');
  const [selectedItem, setSelectedItem] = useState(null);
  const [revealedCis, setRevealedCis] = useState({});
  const [isMobileEvidenceOpen, setIsMobileEvidenceOpen] = useState(false);

  // Formulario de edición del caso seleccionado
  const [formEstudiante, setFormEstudiante] = useState('');
  const [formCi, setFormCi] = useState('');
  const [formModulo, setFormModulo] = useState('');
  const [formNota, setFormNota] = useState('');
  const [formMonto, setFormMonto] = useState('');
  const [formCuotas, setFormCuotas] = useState('');
  const [formNotaAuditor, setFormNotaAuditor] = useState('');
  const [formMes, setFormMes] = useState('');
  const [formGestion, setFormGestion] = useState('');
  const [unClicTotal, setUnClicTotal] = useState(0);
  const [isAprobandoBloque, setIsAprobandoBloque] = useState(false);

  // Modales
  const [isDiscardModalOpen, setIsDiscardModalOpen] = useState(false);
  const [discardNote, setDiscardNote] = useState('');
  const [isCatalogModalOpen, setIsCatalogModalOpen] = useState(false);
  const [isConsolidatingDw, setIsConsolidatingDw] = useState(false);

  // Cola y Datos
  const [isLoading, setIsLoading] = useState(true);
  const [queueItems, setQueueItems] = useState([]);
  const [resolvedHistory, setResolvedHistory] = useState([]);
  const [aprobadosResumen, setAprobadosResumen] = useState({
    total_aprobados: 0,
    fact_rendimiento_academico: 0,
    fact_situacion_financiera: 0,
  });

  useEffect(() => {
    loadReviewQueue(selectedDocId);
  }, [batchId, selectedDocId]);

  const loadReviewQueue = async (docFilter = null) => {
    try {
      setIsLoading(true);
      let effectiveId = batchId || localStorage.getItem('last_active_batch_id');
      if (!effectiveId) {
        setQueueItems([]);
        setSelectedItem(null);
        setIsLoading(false);
        return;
      }

      const res = await dataopsApi.getReviewTray(
        effectiveId ? Number(effectiveId) : null,
        { docId: docFilter, pageSize: 500 }
      );

      if (res && res.data) {
        setQueueItems(res.data);
        setUnClicTotal(res.un_clic_total ?? res.data.filter((q) => q.un_clic).length);
        if (Array.isArray(res.resolved_history)) {
          setResolvedHistory(res.resolved_history);
        }
        if (res.aprobados_resumen) {
          setAprobadosResumen(res.aprobados_resumen);
        }
        if (res.data.length > 0) {
          selectItemForEdit(res.data[0]);
        } else {
          setSelectedItem(null);
        }
      } else {
        setQueueItems([]);
        setSelectedItem(null);
      }
    } catch (err) {
      console.warn('Error cargando bandeja de revisión:', err);
      setQueueItems([]);
      setSelectedItem(null);
    } finally {
      setIsLoading(false);
    }
  };

  const selectItemForEdit = (item) => {
    setSelectedItem(item);
    setFormEstudiante(item.estudiante || '');
    setFormCi(item.ci || item.ci_enmascarado || '');
    setFormModulo(item.modulo_detectado || item.modulo || '');
    setFormNota(item.nota_final !== undefined ? String(item.nota_final) : '');
    setFormMonto(item.monto_deuda !== undefined ? String(item.monto_deuda) : '');
    setFormCuotas(item.cuotas_impagas !== undefined ? String(item.cuotas_impagas) : '0');
    setFormNotaAuditor('');
    setFormMes(item.mes ? String(item.mes) : '');
    setFormGestion(item.gestion ? String(item.gestion) : '');
  };

  // Aprobación en bloque de los casos de un clic: los manuales quedan en la bandeja
  const handleAprobarUnClic = async () => {
    if (unClicTotal === 0) return;
    if (!window.confirm(`Se aprobarán ${unClicTotal} casos de un clic (el candidato coincide por nombre o el hecho está completo). Los casos manuales seguirán en la bandeja. ¿Continuar?`)) {
      return;
    }
    try {
      setIsAprobandoBloque(true);
      const effectiveId = batchId || localStorage.getItem('last_active_batch_id');
      const res = await dataopsApi.aprobarCasosUnClic(effectiveId, selectedDocId);
      sileoToast.success({ title: 'Aprobación en bloque', description: res.message });
      await loadReviewQueue(selectedDocId);
    } catch (err) {
      sileoToast.error({
        title: 'No se pudo aprobar en bloque',
        description: err.response?.data?.detail || err.message,
      });
    } finally {
      setIsAprobandoBloque(false);
    }
  };

  const toggleCi = async (id) => {
    if (revealedCis[id]) {
      setRevealedCis(prev => {
        const copy = { ...prev };
        delete copy[id];
        return copy;
      });
      return;
    }

    try {
      const res = await dataopsApi.revelarCi(id);
      const ciRevealed = res?.ci_real || res?.ci;
      if (ciRevealed) {
        setRevealedCis(prev => ({ ...prev, [id]: ciRevealed }));
        setFormCi(ciRevealed);
      }
    } catch (err) {
      const status = err.response?.status;
      sileoToast.error({
        title: status === 403 ? 'Permiso denegado (RBAC)' : 'No se pudo revelar el CI',
        description: err.response?.data?.detail || 'Se requiere rol ADMIN o AUDITOR_CALIDAD para revelar datos personales.'
      });
    }
  };

  // Filtrado de elementos en la bandeja
  const filteredQueue = useMemo(() => {
    return queueItems.filter(item => {
      if (selectedArea !== 'TODAS') {
        if (selectedArea === 'calidad') {
          if (!item.en_calidad && item.area !== 'calidad') return false;
        } else if (item.area !== selectedArea) {
          return false;
        }
      }
      if (selectedReason !== 'ALL' && item.motivo !== selectedReason) {
        return false;
      }
      return true;
    });
  }, [queueItems, selectedArea, selectedReason]);

  // Aprobación diferida (Heurística 3, control y libertad): la API se llama a los 10 s y
  // mientras tanto el toast ofrece "Deshacer". Al salir de la vista se envían las pendientes.
  const DESHACER_MS = 10000;
  const aprobacionesPendientes = useRef(new Map());
  const campoEstudianteRef = useRef(null);

  useEffect(() => () => {
    aprobacionesPendientes.current.forEach(({ timer, enviar }) => {
      clearTimeout(timer);
      enviar();
    });
  }, []);

  const enviarAprobacion = async (item, payload, estudiante) => {
    aprobacionesPendientes.current.delete(item.id);
    try {
      await dataopsApi.resolveReviewItem(item.id, payload);
      setResolvedHistory(prev => [
        {
          id: item.id,
          quien: 'Auditor Calidad (Tú)',
          cuando: 'Recién resuelto',
          antes: item.que_vio,
          despues: estudiante || item.sugerencia,
          motivo: item.motivo_label,
          accion: 'RESUELTO_HUMANO'
        },
        ...prev
      ]);
      setAprobadosResumen(prev => ({
        ...prev,
        total_aprobados: prev.total_aprobados + 1,
        fact_rendimiento_academico: item.area === 'academica' ? prev.fact_rendimiento_academico + 1 : prev.fact_rendimiento_academico,
        fact_situacion_financiera: item.area === 'financiera' ? prev.fact_situacion_financiera + 1 : prev.fact_situacion_financiera,
      }));
    } catch (err) {
      console.error('Error resolviendo caso:', err);
      setQueueItems(prev => (prev.some(q => q.id === item.id) ? prev : [item, ...prev]));
      sileoToast.error({
        title: `Caso #${item.id} no se consolidó`,
        description: err.response?.data?.detail || err.message || 'Volvió a la bandeja.'
      });
    }
  };

  // Resolver caso individual: Aprobar y Consolidar
  const handleResolveApprove = () => {
    if (!selectedItem) return;
    const item = selectedItem;
    const estudiante = formEstudiante.trim();
    const payload = {
      accion: 'APROBAR',
      estudiante_resuelto: estudiante,
      ci_corregida: formCi.trim(),
      modulo_resuelto: formModulo.trim(),
      nota_final: formNota ? parseFloat(formNota) : undefined,
      monto_deuda: formMonto ? parseFloat(formMonto) : undefined,
      cuotas_impagas: formCuotas ? parseInt(formCuotas, 10) : undefined,
      nota_auditor: formNotaAuditor.trim(),
      mes: formMes ? parseInt(formMes, 10) : undefined,
      gestion: formGestion ? parseInt(formGestion, 10) : undefined
    };

    const indice = queueItems.findIndex(q => q.id === item.id);
    const updatedQueue = queueItems.filter(q => q.id !== item.id);
    setQueueItems(updatedQueue);
    const nextItem = updatedQueue[0];
    if (nextItem) {
      selectItemForEdit(nextItem);
    } else {
      setSelectedItem(null);
    }

    const enviar = () => enviarAprobacion(item, payload, estudiante);
    const timer = setTimeout(enviar, DESHACER_MS);
    aprobacionesPendientes.current.set(item.id, { timer, enviar });

    const toastId = sileoToast.action({
      title: `Caso #${item.id} aprobado`,
      description: `${estudiante || 'Estudiante'} se consolidará en el Data Warehouse en 10 s.`,
      duration: DESHACER_MS,
      button: {
        title: 'Deshacer',
        onClick: () => {
          clearTimeout(timer);
          aprobacionesPendientes.current.delete(item.id);
          setQueueItems(prev => {
            const copia = prev.filter(q => q.id !== item.id);
            copia.splice(Math.max(indice, 0), 0, item);
            return copia;
          });
          selectItemForEdit(item);
          sileo.dismiss(toastId);
        }
      }
    });
  };

  // Atajos de teclado de la bandeja: A aprobar, E editar, J siguiente, K anterior
  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey || isDiscardModalOpen || isCatalogModalOpen) return;
      const destino = e.target;
      if (destino?.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(destino?.tagName)) return;
      const tecla = e.key.toLowerCase();
      if (tecla === 'j' || tecla === 'k') {
        if (!filteredQueue.length) return;
        const actual = filteredQueue.findIndex(q => q.id === selectedItem?.id);
        const siguiente = tecla === 'j' ? actual + 1 : actual - 1;
        e.preventDefault();
        selectItemForEdit(filteredQueue[Math.max(0, Math.min(siguiente, filteredQueue.length - 1))]);
      } else if (tecla === 'a' && selectedItem) {
        e.preventDefault();
        handleResolveApprove();
      } else if (tecla === 'e' && selectedItem) {
        e.preventDefault();
        campoEstudianteRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  });

  // Descartar registro
  const handleConfirmDiscard = async () => {
    if (!selectedItem) return;
    const currentId = selectedItem.id;

    try {
      await dataopsApi.resolveReviewItem(currentId, {
        accion: 'DESCARTAR',
        motivo_descarte: discardNote.trim()
      });

      sileoToast.info({
        title: `Registro #${currentId} descartado`,
        description: 'Se ha archivado en el log de incidencias.'
      });

      setResolvedHistory(prev => [
        {
          id: currentId,
          quien: 'Auditor Calidad (Tú)',
          cuando: 'Descartado',
          antes: selectedItem.que_vio,
          despues: 'Descartado por auditor',
          motivo: selectedItem.motivo_label,
          accion: 'DESCARTADO'
        },
        ...prev
      ]);

      const updatedQueue = queueItems.filter(q => q.id !== currentId);
      setQueueItems(updatedQueue);

      const nextItem = updatedQueue.find(q => q.id !== currentId);
      if (nextItem) {
        selectItemForEdit(nextItem);
      } else {
        setSelectedItem(null);
      }

      setIsDiscardModalOpen(false);
      setDiscardNote('');
    } catch (err) {
      console.error('Error descartando registro:', err);
      sileoToast.error({
        title: 'Error al descartar registro',
        description: err.response?.data?.detail || err.message
      });
    }
  };

  // Agregar parámetro a Catálogo Guía (Cero-PII)
  const handleAddParameterToCatalog = () => {
    sileoToast.success({
      title: 'Parámetro incorporado al Catálogo Guía (Cero-PII)',
      description: `Se vinculó "${formModulo || 'Oferta Curricular'}" a la oferta institucional del catálogo.`
    });
    setIsCatalogModalOpen(false);
  };

  // Exportar Log de Incidencias a CSV
  const handleExportIncidentsCsv = () => {
    try {
      const rows = [
        ['ID', 'Area', 'Motivo', 'Estudiante', 'CI', 'Modulo', 'Archivo Origen', 'Destino DW', 'Texto Detectado', 'Estado']
      ];

      queueItems.forEach(item => {
        rows.push([
          `REV-${item.id}`,
          item.area || 'General',
          item.motivo_label || item.motivo,
          `"${(item.estudiante || '').replace(/"/g, '""')}"`,
          item.ci || item.ci_enmascarado || '',
          `"${(item.modulo_detectado || '').replace(/"/g, '""')}"`,
          `"${(item.archivo_origen || '').replace(/"/g, '""')}"`,
          `"${(item.destino_dw || '').replace(/"/g, '""')}"`,
          `"${(item.que_vio || '').replace(/"/g, '""')}"`,
          'PENDIENTE_REVISION'
        ]);
      });

      const csvContent = 'data:text/csv;charset=utf-8,\uFEFF' + rows.map(e => e.join(';')).join('\n');
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement('a');
      link.setAttribute('href', encodedUri);
      link.setAttribute('download', `log_incidencias_lote_${batchId || 'activo'}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      sileoToast.success({
        title: 'Log de incidencias exportado exitosamente',
        description: `Se descargó el archivo con ${queueItems.length} casos para auditoría.`
      });
    } catch (err) {
      console.error('Error exportando CSV:', err);
      sileoToast.error({
        title: 'Error al exportar CSV',
        description: 'No se pudo generar el archivo de incidencias.'
      });
    }
  };

  // Consolidar Aprobados en DW
  const handleConsolidateDw = async () => {
    try {
      setIsConsolidatingDw(true);
      const effectiveBatchId = batchId || localStorage.getItem('last_active_batch_id');
      const res = await dataopsApi.confirmDwInsert({
        id_lote: effectiveBatchId ? Number(effectiveBatchId) : undefined,
        doc_id: selectedDocId ? Number(selectedDocId) : undefined
      });

      sileoToast.success({
        title: 'Data Warehouse Consolidado',
        description: `${res?.inserted_dw || aprobadosResumen.total_aprobados} registros consolidados exitosamente.`
      });
      loadReviewQueue(selectedDocId);
    } catch (err) {
      console.error('Error consolidando DW:', err);
      sileoToast.error({
        title: 'Error al consolidar DW',
        description: err.response?.data?.detail || err.message
      });
    } finally {
      setIsConsolidatingDw(false);
    }
  };

  const effectiveBatchNumber = batchId || localStorage.getItem('last_active_batch_id') || '—';

  return (
    <BatchFlowLayout
      currentStep={4}
      selectedDocId={selectedDocId}
      onSelectDocId={setSelectedDocId}
    >
      {/* ── Encabezado Principal ── */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <h2 className="serif-heading" style={{ fontSize: '24px', margin: 0, color: 'var(--color-ink-black)' }}>
                Bandeja de revisión humana y conciliación
              </h2>
              <span
                style={{
                  fontSize: '11.5px',
                  fontWeight: '700',
                  padding: '4px 10px',
                  borderRadius: '999px',
                  backgroundColor: queueItems.length === 0 ? 'rgba(27, 135, 84, 0.12)' : 'rgba(217, 155, 38, 0.14)',
                  color: queueItems.length === 0 ? '#1B8754' : '#B8801A',
                  border: `1px solid ${queueItems.length === 0 ? 'rgba(27, 135, 84, 0.3)' : 'rgba(217, 155, 38, 0.35)'}`,
                }}
              >
                {queueItems.length === 0 ? 'Bandeja al día' : `${queueItems.length} pendientes`}
              </span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: 0 }}>
              Lote: <strong>LOTE-{effectiveBatchNumber}</strong> · Resuelve discrepancias y consolida registros en el Data Warehouse.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn-pill-secondary"
              onClick={handleExportIncidentsCsv}
            >
              <Download size={14} /> Exportar Log de Incidencias (.CSV)
            </button>
            <button
              type="button"
              className="btn-pill-gold"
              onClick={handleConsolidateDw}
              disabled={isConsolidatingDw || aprobadosResumen.total_aprobados === 0}
            >
              <Database size={15} /> Consolidar Aprobados al DW ({aprobadosResumen.total_aprobados})
            </button>
          </div>
        </div>
      </div>

      {/* ── Barra de Pestañas: Pendientes vs Resueltos ── */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', borderBottom: '1px solid var(--color-border)', paddingBottom: '8px' }}>
        <button
          type="button"
          onClick={() => setActiveTab('PENDIENTES')}
          style={{
            background: 'none',
            border: 'none',
            padding: '8px 16px',
            fontSize: '13.5px',
            fontWeight: activeTab === 'PENDIENTES' ? '700' : '500',
            color: activeTab === 'PENDIENTES' ? 'var(--color-ink-black)' : 'var(--color-slate-gray)',
            borderBottom: activeTab === 'PENDIENTES' ? '2px solid var(--color-gira-gold, #D99B26)' : 'none',
            cursor: 'pointer'
          }}
        >
          Pendientes ({queueItems.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('RESUELTOS')}
          style={{
            background: 'none',
            border: 'none',
            padding: '8px 16px',
            fontSize: '13.5px',
            fontWeight: activeTab === 'RESUELTOS' ? '700' : '500',
            color: activeTab === 'RESUELTOS' ? 'var(--color-ink-black)' : 'var(--color-slate-gray)',
            borderBottom: activeTab === 'RESUELTOS' ? '2px solid var(--color-gira-gold, #D99B26)' : 'none',
            cursor: 'pointer'
          }}
        >
          Historial de Resueltos ({resolvedHistory.length})
        </button>
      </div>

      {/* ── Filtros por Área de Trabajo ── */}
      {activeTab === 'PENDIENTES' && (
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', marginBottom: '18px' }}>
          <button
            type="button"
            className="btn-pill-gold"
            style={{ padding: '6px 14px', fontSize: '12px' }}
            disabled={unClicTotal === 0 || isAprobandoBloque}
            onClick={handleAprobarUnClic}
          >
            {isAprobandoBloque ? 'Aprobando…' : `Aprobar casos de un clic (${unClicTotal})`}
          </button>
          <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-slate-gray)' }}>Área:</span>
          <button
            type="button"
            className={`pill-filter ${selectedArea === 'TODAS' ? 'active' : ''}`}
            onClick={() => setSelectedArea('TODAS')}
          >
            Todas ({queueItems.length})
          </button>
          <button
            type="button"
            className={`pill-filter ${selectedArea === 'academica' ? 'active' : ''}`}
            onClick={() => setSelectedArea('academica')}
          >
            🎓 Académica
          </button>
          <button
            type="button"
            className={`pill-filter ${selectedArea === 'financiera' ? 'active' : ''}`}
            onClick={() => setSelectedArea('financiera')}
          >
            💳 Financiera
          </button>
          <button
            type="button"
            className={`pill-filter ${selectedArea === 'comercial' ? 'active' : ''}`}
            onClick={() => setSelectedArea('comercial')}
          >
            🛒 Comercial
          </button>
          <button
            type="button"
            className={`pill-filter ${selectedArea === 'calidad' ? 'active' : ''}`}
            onClick={() => setSelectedArea('calidad')}
          >
            🛡️ Calidad / Catálogo
          </button>
        </div>
      )}

      {/* ── Vista Principal de Pestañas ── */}
      {activeTab === 'RESUELTOS' ? (
        /* Pestaña: Historial de Resueltos */
        <div className="floating-artifact" style={{ padding: '0', overflow: 'hidden' }}>
          <table className="dataops-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Auditor</th>
                <th>Fecha / Hora</th>
                <th>Texto Original</th>
                <th>Resolución / Destino</th>
                <th>Motivo</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {resolvedHistory.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '36px', color: 'var(--color-slate-gray)' }}>
                    No se han resuelto registros en esta sesión todavía.
                  </td>
                </tr>
              ) : (
                resolvedHistory.map((item, idx) => (
                  <tr key={idx}>
                    <td><code>REV-{item.id}</code></td>
                    <td>{item.quien}</td>
                    <td>{item.cuando}</td>
                    <td><div style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.antes}</div></td>
                    <td><strong>{item.despues}</strong></td>
                    <td>{item.motivo}</td>
                    <td>
                      <span style={{ fontSize: '11px', fontWeight: '700', color: item.accion === 'DESCARTADO' ? '#D9383A' : '#1B8754' }}>
                        {item.accion}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        /* Pestaña: Pendientes con Layout Split-Screen Desktop / Mobile */
        <div>
          {isLoading ? (
            <div className="floating-artifact" style={{ padding: '64px', textAlign: 'center', color: 'var(--color-slate-gray)' }}>
              Cargando casos derivados a revisión humana...
            </div>
          ) : queueItems.length === 0 ? (
            <div className="floating-artifact" style={{ padding: '48px', textAlign: 'center' }}>
              <CheckCircle2 size={48} color="#1B8754" style={{ margin: '0 auto 16px auto', display: 'block' }} />
              <h3 className="serif-heading" style={{ fontSize: '20px', margin: '0 0 8px 0', color: 'var(--color-ink-black)' }}>
                ¡Bandeja de revisión completada!
              </h3>
              <p style={{ fontSize: '13.5px', color: 'var(--color-slate-gray)', maxWidth: '480px', margin: '0 auto 20px auto' }}>
                Todos los registros han sido aprobados o resueltos. Ya puedes consolidar los hechos en el Data Warehouse.
              </p>
              <button
                type="button"
                className="btn-pill-gold"
                onClick={handleConsolidateDw}
                disabled={isConsolidatingDw || aprobadosResumen.total_aprobados === 0}
              >
                <Database size={15} /> Consolidar al Data Warehouse ({aprobadosResumen.total_aprobados})
              </button>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '20px', alignItems: 'start' }}>
              {/* Columna Izquierda: Cola de Casos Pendientes */}
              <div className="floating-artifact" style={{ padding: '12px' }}>
                <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-slate-gray)', textTransform: 'uppercase', marginBottom: '8px', padding: '4px 6px' }}>
                  Cola de Casos ({filteredQueue.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '560px', overflowY: 'auto' }}>
                  {filteredQueue.map(item => {
                    const isSelected = selectedItem && selectedItem.id === item.id;
                    return (
                      <div
                        key={item.id}
                        onClick={() => selectItemForEdit(item)}
                        style={{
                          padding: '10px 12px',
                          borderRadius: '8px',
                          cursor: 'pointer',
                          backgroundColor: isSelected ? 'var(--dataops-row-selected, rgba(217, 155, 38, 0.12))' : 'var(--color-paper-white)',
                          border: `1px solid ${isSelected ? 'var(--color-gira-gold, #D99B26)' : 'var(--color-border)'}`,
                          transition: 'all 0.15s ease'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                          <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--color-slate-gray)' }}>
                            REV-{item.id}
                          </span>
                          <span
                            style={{
                              fontSize: '10px',
                              fontWeight: '700',
                              padding: '1px 5px',
                              borderRadius: '4px',
                              backgroundColor: item.area === 'academica' ? 'rgba(12, 30, 51, 0.08)' : 'rgba(217, 155, 38, 0.15)',
                              color: item.area === 'academica' ? '#0C1E33' : '#B8801A'
                            }}
                          >
                            {item.area || 'General'}
                          </span>
                        </div>
                        <div style={{ fontWeight: '600', fontSize: '12.5px', color: 'var(--color-ink-black)', marginBottom: '2px' }}>
                          {item.estudiante || 'Sin nombre'}
                        </div>
                        <div style={{ fontSize: '11px', color: '#D9383A' }}>
                          {item.motivo_label || item.motivo}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Columna Derecha: Split-Screen Desktop de Resolución */}
              {selectedItem && (
                <div>
                  {/* Botón Móvil Colapsable de Evidencia Documental */}
                  <div className="mobile-only-toggle" style={{ marginBottom: '14px' }}>
                    <button
                      type="button"
                      className="btn-pill-secondary"
                      style={{ width: '100%', justifyContent: 'center', padding: '12px 16px', fontWeight: '700', fontSize: '13px' }}
                      onClick={() => setIsMobileEvidenceOpen(prev => !prev)}
                      aria-label="Ver u ocultar evidencia en texto plano"
                    >
                      <FileText size={16} />
                      <span>{isMobileEvidenceOpen ? '📄 Ocultar evidencia documental ▲' : '📄 Ver oración en texto plano ▼'}</span>
                    </button>
                  </div>

                  <div className="split-screen-review">
                    {/* Panel Izquierdo: Evidencia & Cruce Multifuente */}
                    <div className={`floating-artifact review-evidence-panel ${!isMobileEvidenceOpen ? 'mobile-hidden' : ''}`} style={{ padding: '20px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <span className="chip-cat chip-origen">
                          {selectedItem.archivo_origen || 'Documento Origen'}
                        </span>
                      <span style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)' }}>
                        ID Doc: {selectedItem.id_documento || 'Lote'}
                      </span>
                    </div>

                    <h4 className="serif-heading" style={{ fontSize: '16px', margin: '0 0 10px 0', color: 'var(--color-ink-black)' }}>
                      Evidencia documental original
                    </h4>

                    {/* Texto Extraído Original con Tokens */}
                    <div
                      style={{
                        padding: '14px',
                        borderRadius: '10px',
                        backgroundColor: 'var(--color-mist-gray)',
                        border: '1px solid var(--color-border)',
                        fontFamily: 'var(--font-mono, monospace)',
                        fontSize: '12px',
                        lineHeight: '1.6',
                        color: 'var(--color-ink-black)',
                        marginBottom: '16px'
                      }}
                    >
                      {selectedItem.que_vio || selectedItem.contexto_raw || 'No se dispone del texto original.'}
                    </div>

                    {/* Alerta de Cruce Multifuente (Abandono escolar / mora) */}
                    {(selectedItem.alerta_abandono || selectedItem.cruce_multifuente) && (
                      <div className="multi-source-alert">
                        <AlertTriangle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
                        <div>
                          <strong style={{ fontSize: '13px' }}>Cruce Multifuente de Abandono Detectado:</strong>
                          <div style={{ marginTop: '4px', fontSize: '12.5px' }}>
                            {selectedItem.cruce_multifuente?.descripcion || (
                              'El estudiante presenta inasistencia crítica (>20%) en actas académicas correlacionada con mora financiera (≥2 cuotas impagas en cobranzas).'
                            )}
                          </div>
                          {selectedItem.cruce_multifuente?.archivo_cruzado && (
                            <div style={{ fontSize: '11.5px', marginTop: '4px', opacity: 0.9 }}>
                              Archivo cruzado: <em>{selectedItem.cruce_multifuente.archivo_cruzado}</em>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Sugerencia de Catálogo Guía (Cero-PII) */}
                    <div className="zero-pii-card" style={{ marginTop: '16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: 'var(--color-ink-black)', fontWeight: '700' }}>
                        <ShieldCheck size={16} color="#1B8754" /> Catálogo Guía Institucional (Cero-PII)
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '0 0 10px 0', lineHeight: '1.4' }}>
                        {selectedItem.es_nuevo_catalogo ? (
                          'Se detectó un módulo no registrado en la oferta académica. Puedes incorporar este término al catálogo curricular.'
                        ) : (
                          'Este registro se vincula determinísticamente a la oferta curricular sin persistir PII personal en las dimensiones maestras.'
                        )}
                      </p>
                      {selectedItem.es_nuevo_catalogo && (
                        <button
                          type="button"
                          className="btn-pill-secondary"
                          style={{ fontSize: '11.5px', padding: '6px 12px' }}
                          onClick={() => setIsCatalogModalOpen(true)}
                        >
                          <Sparkles size={13} color="var(--color-gira-gold, #D99B26)" /> Incorporar término al Catálogo Guía
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Panel Derecho: Resolución, Conciliación y Acciones */}
                  <div className="floating-artifact" style={{ padding: '20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                      <h4 className="serif-heading" style={{ fontSize: '16px', margin: 0, color: 'var(--color-ink-black)' }}>
                        Resolución y conciliación
                      </h4>
                      <span style={{ fontSize: '11px', fontWeight: '700', color: '#B8801A', backgroundColor: 'rgba(217, 155, 38, 0.12)', padding: '2px 8px', borderRadius: '4px' }}>
                        Motivo: {selectedItem.motivo_label || selectedItem.motivo}
                      </span>
                    </div>

                    {/* Formulario de corrección */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div>
                        <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '4px' }}>
                          Nombre de Estudiante / Entidad:
                        </label>
                        <input
                          type="text"
                          className="dataops-input"
                          ref={campoEstudianteRef}
                          aria-keyshortcuts="E"
                          value={formEstudiante}
                          onChange={(e) => setFormEstudiante(e.target.value)}
                        />
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        <div>
                          <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-slate-gray)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <span>Cédula de Identidad:</span>
                            <button
                              type="button"
                              onClick={() => toggleCi(selectedItem.id)}
                              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-gira-gold, #D99B26)', padding: 0 }}
                              title="Revelar Cédula"
                            >
                              {revealedCis[selectedItem.id] ? <EyeOff size={13} /> : <Eye size={13} />}
                            </button>
                          </label>
                          <input
                            type="text"
                            className="dataops-input"
                            value={formCi}
                            onChange={(e) => setFormCi(e.target.value)}
                          />
                        </div>

                        <div>
                          <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '4px' }}>
                            Módulo Académico:
                          </label>
                          <input
                            type="text"
                            className="dataops-input"
                            value={formModulo}
                            onChange={(e) => setFormModulo(e.target.value)}
                          />
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        {selectedItem.area === 'academica' ? (
                          <div>
                            <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '4px' }}>
                              Nota Final (Base 100):
                            </label>
                            <input
                              type="number"
                              className="dataops-input"
                              placeholder="Ej: 85"
                              value={formNota}
                              onChange={(e) => setFormNota(e.target.value)}
                            />
                          </div>
                        ) : (
                          <>
                            <div>
                              <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '4px' }}>
                                Monto Deuda (Bs.):
                              </label>
                              <input
                                type="number"
                                className="dataops-input"
                                placeholder="Ej: 1200"
                                value={formMonto}
                                onChange={(e) => setFormMonto(e.target.value)}
                              />
                            </div>
                            <div>
                              <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '4px' }}>
                                Cuotas Impagas:
                              </label>
                              <input
                                type="number"
                                className="dataops-input"
                                placeholder="Ej: 2"
                                value={formCuotas}
                                onChange={(e) => setFormCuotas(e.target.value)}
                              />
                            </div>
                          </>
                        )}
                      </div>

                      {selectedItem.tipo_entidad === 'HECHO' && (
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                          <div>
                            <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '4px' }}>
                              Mes{(selectedItem.campos_faltantes || []).includes('fecha') ? ' (falta)' : ''}:
                            </label>
                            <select className="dataops-input" value={formMes} onChange={(e) => setFormMes(e.target.value)}>
                              <option value="">—</option>
                              {['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'].map((m, i) => (
                                <option key={m} value={i + 1}>{m}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '4px' }}>
                              Gestión:
                            </label>
                            <input
                              type="number"
                              className="dataops-input"
                              placeholder="Ej: 2025"
                              min="2000"
                              max="2100"
                              value={formGestion}
                              onChange={(e) => setFormGestion(e.target.value)}
                            />
                          </div>
                        </div>
                      )}

                      <div>
                        <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '4px' }}>
                          Nota de Auditoría / Justificación:
                        </label>
                        <input
                          type="text"
                          className="dataops-input"
                          placeholder="Ej: Corregido según acta física firmada por dirección de posgrado..."
                          value={formNotaAuditor}
                          onChange={(e) => setFormNotaAuditor(e.target.value)}
                        />
                      </div>
                    </div>

                    {/* Botones de Acción (52px Touch Ergonomics en Mobile) */}
                    <div className="thumb-action-bar">
                      <button
                        type="button"
                        className="thumb-action-btn reject"
                        onClick={() => setIsDiscardModalOpen(true)}
                        aria-label="Rechazar caso"
                      >
                        <XCircle size={19} /> ❌ Rechazar
                      </button>
                      <button
                        type="button"
                        className="thumb-action-btn approve"
                        onClick={handleResolveApprove}
                        aria-label="Aprobar caso"
                        aria-keyshortcuts="A"
                      >
                        <CheckCircle2 size={19} /> ✅ Aprobar
                      </button>
                    </div>
                    <p className="hitl-atajos" aria-label="Atajos de teclado">
                      <Keyboard size={13} aria-hidden="true" />
                      <kbd>A</kbd> aprobar · <kbd>E</kbd> editar · <kbd>J</kbd>/<kbd>K</kbd> siguiente/anterior · deshacer 10 s
                    </p>
                  </div>
                </div>
              </div>
            )}
            </div>
          )}
        </div>
      )}

      {/* ── Resumen de Hechos Consolidados en DW (Bloque Inferior) ── */}
      <div
        className="floating-artifact"
        style={{
          marginTop: '24px',
          padding: '20px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <Database size={18} color="var(--color-gira-gold, #D99B26)" />
            <strong style={{ fontSize: '15px', color: 'var(--color-ink-black)' }}>
              Consolidación en Data Warehouse
            </strong>
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>
            Total aprobados listos: <strong>{aprobadosResumen.total_aprobados}</strong> (
            Académicos: <code>fact_rendimiento_academico</code> +{aprobadosResumen.fact_rendimiento_academico} · 
            Financieros: <code>fact_situacion_financiera</code> +{aprobadosResumen.fact_situacion_financiera})
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn-pill-secondary"
            onClick={() => {
              const navId = effectiveBatchNumber !== '—' ? effectiveBatchNumber : (localStorage.getItem('last_active_batch_id') || '');
              navigate(`/dataops/lote/${navId}/beto`);
            }}
          >
            ← Volver a ③ Lectura de BETO
          </button>

          <button
            type="button"
            className="btn-pill-gold"
            onClick={handleConsolidateDw}
            disabled={isConsolidatingDw || aprobadosResumen.total_aprobados === 0}
          >
            {isConsolidatingDw ? 'Consolidando transaccionalmente...' : 'Consolidar Aprobados al DW →'}
          </button>
        </div>
      </div>

      {/* ── Modal de Descarte ── */}
      {isDiscardModalOpen && (
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
              maxWidth: '440px',
              width: '100%',
              padding: '24px',
              backgroundColor: 'var(--color-paper-white)',
              borderRadius: '16px'
            }}
          >
            <h3 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 10px 0', color: '#D9383A' }}>
              Confirmar descarte de caso REV-{selectedItem?.id}
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', lineHeight: '1.45', margin: '0 0 14px 0' }}>
              Este registro no será insertado en el Data Warehouse y quedará asentado en el log de incidencias con marca de descartado.
            </p>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '4px' }}>
                Motivo de descarte (Obligatorio para auditoría):
              </label>
              <input
                type="text"
                className="dataops-input"
                placeholder="Ej: Registro duplicado o dato ilegible..."
                value={discardNote}
                onChange={(e) => setDiscardNote(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn-pill-secondary"
                onClick={() => setIsDiscardModalOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="thumb-action-btn reject"
                style={{ minHeight: '38px', padding: '8px 16px', fontSize: '13px' }}
                onClick={handleConfirmDiscard}
              >
                Confirmar Descarte
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal de Incorporación a Catálogo Guía ── */}
      {isCatalogModalOpen && (
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
              maxWidth: '460px',
              width: '100%',
              padding: '24px',
              backgroundColor: 'var(--color-paper-white)',
              borderRadius: '16px'
            }}
          >
            <h3 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 10px 0', color: 'var(--color-ink-black)' }}>
              Incorporar al Catálogo Guía (Cero-PII)
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', lineHeight: '1.45', margin: '0 0 14px 0' }}>
              Se agregará el término curricular al catálogo institucional para resolver futuras apariciones automáticamente.
            </p>
            <div style={{ marginBottom: '14px' }}>
              <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '4px' }}>
                Módulo a registrar:
              </label>
              <input
                type="text"
                className="dataops-input"
                value={formModulo}
                onChange={(e) => setFormModulo(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn-pill-secondary"
                onClick={() => setIsCatalogModalOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-pill-gold"
                style={{ fontSize: '13px', padding: '8px 16px' }}
                onClick={handleAddParameterToCatalog}
              >
                Guardar en Catálogo
              </button>
            </div>
          </div>
        </div>
      )}
    </BatchFlowLayout>
  );
}
