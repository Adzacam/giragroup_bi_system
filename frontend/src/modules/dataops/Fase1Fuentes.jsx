import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, Trash2 } from 'lucide-react';
import { dataopsApi } from '../../api/dataopsApi';
import SourceKpiCards from './components/SourceKpiCards';
import SourcesTable from './components/SourcesTable';
import UploadModal from './components/UploadModal';
import PageHeader from '../../components/shared/PageHeader';
import { sileoToast } from '../../services/sileoToast';
import { useNotifications } from '../../context/NotificationContext';
import { NOTIFICATION_CATEGORIES, NOTIFICATION_SEVERITIES } from '../../constants/systemConstants';

export default function Fase1Fuentes() {
  const navigate = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [sources, setSources] = useState([]);
  const [selectedSourceIds, setSelectedSourceIds] = useState([]);
  const [kpis, setKpis] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reprocessingId, setReprocessingId] = useState(null);
  const [selectedDetail, setSelectedDetail] = useState(null);

  const { notify } = useNotifications();

  const loadSources = async () => {
    setIsLoading(true);
    try {
      const res = await dataopsApi.getSources();
      const loadedSources = res.data || [];
      setSources(loadedSources);
      setKpis(res.kpis || null);
      // Mantener seleccionados solo los IDs que aún existan
      setSelectedSourceIds((prev) =>
        prev.filter((id) => loadedSources.some((s) => s.id === id))
      );
    } catch (err) {
      console.error('Error al cargar fuentes:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

  const handleToggleSelect = (id) => {
    setSelectedSourceIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSelectAll = (selectAll) => {
    if (selectAll) {
      setSelectedSourceIds(sources.map((s) => s.id));
    } else {
      setSelectedSourceIds([]);
    }
  };

  const handleClearSelection = () => {
    setSelectedSourceIds([]);
  };

  const handleProcessSelected = (ids) => {
    navigate(`/dataops/procesamiento?autoRun=true&docIds=${ids.join(',')}`);
  };

  const handleDeleteSource = async (id, name) => {
    try {
      await dataopsApi.deleteSource(id);
      sileoToast.success({
        title: 'Archivo Eliminado',
        description: `El archivo '${name}' fue eliminado exitosamente del sistema.`,
      });
      await loadSources();
    } catch (err) {
      sileoToast.error({
        title: 'Error al Eliminar',
        description: `No se pudo eliminar el archivo: ${err.message}`,
      });
    }
  };

  const handleDeleteSelected = async (ids) => {
    if (!ids || ids.length === 0) return;
    try {
      await dataopsApi.deleteBatch(ids);
      sileoToast.success({
        title: 'Lote Eliminado',
        description: `Se eliminaron ${ids.length} archivo(s) seleccionados del sistema.`,
      });
      setSelectedSourceIds([]);
      await loadSources();
    } catch (err) {
      sileoToast.error({
        title: 'Error al Eliminar Lote',
        description: `No se pudo completar la eliminación: ${err.message}`,
      });
    }
  };

  const handleClearProcessed = async () => {
    const completedSources = sources.filter((s) => s.status === 'completed');
    if (completedSources.length === 0) {
      sileoToast.info({
        title: 'Sin fuentes completadas',
        description: 'No hay archivos en estado completado para limpiar de la cola activa.',
      });
      return;
    }

    try {
      const ids = completedSources.map((s) => s.id);
      await dataopsApi.deleteBatch(ids);

      sileoToast.success({
        title: 'Cola de Fuentes Depurada',
        description: `${ids.length} archivo(s) completados fueron eliminados de la base de datos y la cola activa.`
      });

      setSelectedSourceIds((prev) => prev.filter((id) => !ids.includes(id)));
      await loadSources();
    } catch (err) {
      sileoToast.error({
        title: 'Error al Depurar Cola',
        description: `Ocurrió un error al limpiar los archivos completados.`,
      });
    }
  };

  const completedCount = sources.filter((s) => s.status === 'completed').length;

  const handleReprocess = async (id) => {
    setReprocessingId(id);
    try {
      const res = await dataopsApi.processBatch(id);
      notify({
        title: 'Reprocesamiento Completado',
        message: `El archivo fue reevaluado a través de las 6 etapas del pipeline.`,
        category: NOTIFICATION_CATEGORIES.CALIDAD_DATAOPS,
        severity: NOTIFICATION_SEVERITIES.INFO,
        link: '/dataops/procesamiento'
      });
      await loadSources();
    } catch (err) {
      notify({
        title: 'Falla al Reprocesar',
        message: 'No se pudo completar el re-procesamiento del lote seleccionado.',
        category: NOTIFICATION_CATEGORIES.CALIDAD_DATAOPS,
        severity: NOTIFICATION_SEVERITIES.CRITICAL
      });
    } finally {
      setReprocessingId(null);
    }
  };

  return (
    <div className="module-container" style={{ padding: '8px 0', maxWidth: '1200px', margin: '0 auto' }}>
      {/* ── Encabezado Institucional ── */}
      <PageHeader
        category="Fase 1: Ingesta y Fuentes de Datos"
        title="Ingesta y Gestión de Fuentes Documentales"
        subtitle="Plataforma centralizada para la carga, validación preliminar y catalogación de archivos crudos (Excel, CSV, Moodle, Forms) antes de su procesamiento y normalización hacia el Data Warehouse."
        action={
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              className="btn-pill-ghost"
              onClick={handleClearProcessed}
              type="button"
              disabled={completedCount === 0}
              style={{
                padding: '9px 18px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '13.5px',
                opacity: completedCount === 0 ? 0.45 : 1,
                backgroundColor: 'var(--color-paper-white)',
                color: 'var(--color-ink-black)',
                border: '1px solid var(--color-border)',
              }}
              title={
                completedCount === 0
                  ? 'No hay archivos completados en la cola activa'
                  : `Limpiar ${completedCount} archivo(s) completados de la lista activa`
              }
            >
              <Trash2 size={15} />
              Limpiar Procesados ({completedCount})
            </button>

            <button 
              className="btn-pill-dark" 
              onClick={() => setIsModalOpen(true)}
              type="button"
              style={{ padding: '10px 24px', display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}
            >
              <UploadCloud size={18} />
              + Nueva Carga de Archivo
            </button>
          </div>
        }
      />

      {/* ── Summary KPI Cards ── */}
      <SourceKpiCards kpis={kpis} />

      {/* ── Files Table ── */}
      <SourcesTable
        sources={sources}
        selectedIds={selectedSourceIds}
        onToggleSelect={handleToggleSelect}
        onSelectAll={handleSelectAll}
        onClearSelection={handleClearSelection}
        onProcessSelected={handleProcessSelected}
        onReprocess={handleReprocess}
        onSelectDetail={(item) => setSelectedDetail(item)}
        onDeleteSource={handleDeleteSource}
        onDeleteSelected={handleDeleteSelected}
        isReprocessingId={reprocessingId}
      />

      {/* ── Upload Modal con Barra de Progreso y Detección Real ── */}
      <UploadModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onUploadSuccess={() => loadSources()}
        existingSources={sources}
      />

      {/* ── Detalle de Archivo Modal ── */}
      {selectedDetail && (
        <div className="modal-backdrop" style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(23, 25, 28, 0.45)',
          backdropFilter: 'blur(6px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1300, padding: '20px'
        }}>
          <div className="modal-panel floating-artifact" style={{
            padding: '30px', borderRadius: 'var(--radius-cards)',
            maxWidth: '460px', width: '100%', border: '1px solid var(--color-border)'
          }}>
            <h3 className="serif-heading" style={{ fontSize: '20px', margin: '0 0 16px 0', color: 'var(--color-ink-black)' }}>
              Detalle de Auditoría Documental
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13.5px', marginBottom: '24px' }}>
              <div><strong>Nombre:</strong> {selectedDetail.name}</div>
              <div><strong>Tipo:</strong> {selectedDetail.type}</div>
              <div><strong>Registros:</strong> {selectedDetail.records}</div>
              <div><strong>Fecha de Ingesta:</strong> {selectedDetail.date}</div>
              <div><strong>Hash Criptográfico:</strong> <span style={{ fontFamily: 'var(--font-mono)' }}>sha256:{selectedDetail.sha256}</span></div>
              <div><strong>Estado:</strong> <span style={{ color: 'var(--color-alert-green)', fontWeight: 600 }}>{selectedDetail.status}</span></div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn-pill-dark"
                onClick={() => setSelectedDetail(null)}
                style={{ padding: '8px 20px', fontSize: '13px' }}
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
