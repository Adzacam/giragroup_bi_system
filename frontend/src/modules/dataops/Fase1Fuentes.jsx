import React, { useState, useEffect } from 'react';
import { UploadCloud } from 'lucide-react';
import { dataopsApi } from '../../api/dataopsApi';
import SourceKpiCards from './components/SourceKpiCards';
import SourcesTable from './components/SourcesTable';
import UploadModal from './components/UploadModal';
import PageHeader from '../../components/shared/PageHeader';
import { useNotifications } from '../../context/NotificationContext';
import { NOTIFICATION_CATEGORIES, NOTIFICATION_SEVERITIES } from '../../constants/systemConstants';

export default function Fase1Fuentes() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [sources, setSources] = useState([]);
  const [kpis, setKpis] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reprocessingId, setReprocessingId] = useState(null);
  const [selectedDetail, setSelectedDetail] = useState(null);

  const { notify } = useNotifications();

  const loadSources = async () => {
    setIsLoading(true);
    try {
      const res = await dataopsApi.getSources();
      setSources(res.data || []);
      setKpis(res.kpis || null);
    } catch (err) {
      console.error('Error al cargar fuentes:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

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
          <button 
            className="btn-pill-dark" 
            onClick={() => setIsModalOpen(true)}
            type="button"
            style={{ padding: '10px 24px', display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}
          >
            <UploadCloud size={18} />
            + Nueva Carga de Archivo
          </button>
        }
      />

      {/* ── Summary KPI Cards ── */}
      <SourceKpiCards kpis={kpis} />

      {/* ── Files Table ── */}
      <SourcesTable
        sources={sources}
        onReprocess={handleReprocess}
        onSelectDetail={(item) => setSelectedDetail(item)}
        isReprocessingId={reprocessingId}
      />

      {/* ── Upload Modal con Barra de Progreso y Detección Real ── */}
      <UploadModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onUploadSuccess={() => loadSources()}
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
