import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { FileSpreadsheet, Layers, Cpu, ArrowRight } from 'lucide-react';
import BatchFlowHeader from './BatchFlowHeader';
import BatchFlowStepper from './BatchFlowStepper';
import { dataopsApi } from '../../../api/dataopsApi';

export default function BatchFlowLayout({
  currentStep = 1,
  selectedDocId = null,
  onSelectDocId = null,
  children,
}) {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [batchContext, setBatchContext] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const effectiveRouteId = id || searchParams.get('lote');

  useEffect(() => {
    if (effectiveRouteId) {
      loadBatchContext(effectiveRouteId);
    } else {
      const savedLoteId = localStorage.getItem('last_active_batch_id');
      if (savedLoteId && currentStep > 1) {
        loadBatchContext(savedLoteId);
      }
    }
  }, [effectiveRouteId, currentStep]);

  const loadBatchContext = async (batchId) => {
    try {
      setIsLoading(true);
      const res = await dataopsApi.getLoteContext(batchId);
      if (res && res.status === 'success') {
        setBatchContext(res);
        localStorage.setItem('last_active_batch_id', String(res.id_lote || batchId));
      } else {
        const sources = await dataopsApi.getSources();
        const found = sources?.data?.find(
          (s) => s.id === Number(batchId) || s.id_documento === Number(batchId) || s.id_lote === Number(batchId)
        );
        if (found) {
          setBatchContext({
            id_lote: found.id_lote || batchId,
            id_documento: found.id_documento || found.id || batchId,
            nombre_archivo: found.nombre_archivo || `Lote_${batchId}.xlsx`,
            institucion: found.institucion || 'Unifranz',
            tipo_fuente: found.tipo_fuente || found.tipo_documento || 'ACTA',
            tipo_escala: found.tipo_escala || null,
            escala_label: found.tipo_escala === 'DECIMAL_10'
              ? 'Sobre 10'
              : found.tipo_escala === 'VIGESIMAL_20'
              ? 'Sobre 20'
              : found.tipo_escala === 'CENTESIMAL_100'
              ? 'Sobre 100'
              : 'No aplica',
            periodo: found.periodo || '2026-1',
            total_archivos: 1,
            total_registros: found.total_registros || found.registros_detectados || 0,
            pendientes_revision: found.inconsistencias || 0,
            archivos: [
              {
                id_documento: found.id_documento || found.id || Number(batchId),
                nombre_archivo: found.nombre_archivo || `Lote_${batchId}.xlsx`,
                tipo_fuente: found.tipo_fuente || 'ACTA',
                tipo_escala: found.tipo_escala || null,
                total_registros: found.total_registros || found.registros_detectados || 0,
                pendientes_revision: found.inconsistencias || 0,
              },
            ],
          });
        }
      }
    } catch (err) {
      console.warn('Error al cargar contexto del lote:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectBatch = () => {
    navigate('/dataops/ingesta');
  };

  const archivosLote = batchContext?.archivos || [];

  return (
    <div className="batch-flow-container" style={{ maxWidth: '1440px', margin: '0 auto', padding: '0 8px' }}>
      <BatchFlowHeader
        batchContext={batchContext}
        currentStep={currentStep}
        onSelectBatch={handleSelectBatch}
      />
      <BatchFlowStepper
        currentStep={currentStep}
        batchId={effectiveRouteId || batchContext?.id_lote || batchContext?.id_documento}
        pendientesCount={batchContext?.pendientes_revision || 0}
      />

      {/* Barra de Accesos Rápidos ("Herramientas Técnicas del Lote") */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '10px 16px',
          marginBottom: '16px',
          borderRadius: '12px',
          backgroundColor: 'rgba(217, 155, 38, 0.08)',
          border: '1px solid rgba(217, 155, 38, 0.35)',
          flexWrap: 'wrap',
          gap: '10px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12.5px', color: 'var(--color-ink-black)' }}>
          <Cpu size={16} color="var(--color-gira-gold, #D99B26)" />
          <span>
            <strong>Herramientas Técnicas del Lote:</strong> Explore <strong>Embeddings (768 dimensiones)</strong>, el <strong>Esquema Constelación (8 entidades)</strong> y la <strong>Consola HITL e Inconsistencias</strong>.
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => navigate('/dataops/beto-ner')}
            style={{
              padding: '6px 14px',
              borderRadius: '999px',
              fontSize: '12px',
              fontWeight: 700,
              backgroundColor: 'var(--color-ink-black)',
              color: 'var(--color-paper-white)',
              border: 'none',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>🔬 Laboratorio BETO NER</span>
            <ArrowRight size={13} />
          </button>
          <button
            type="button"
            onClick={() => navigate('/dataops/auditoria-humana')}
            style={{
              padding: '6px 14px',
              borderRadius: '999px',
              fontSize: '12px',
              fontWeight: 700,
              backgroundColor: 'var(--color-paper-white)',
              color: 'var(--color-ink-black)',
              border: '1px solid var(--color-border)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>🛡️ Consola HITL e Inconsistencias</span>
            <ArrowRight size={13} />
          </button>
        </div>
      </div>

      {/* Barra de pestañas por archivo dentro del lote para pasos ②, ③ y ④ (#17) */}
      {currentStep >= 2 && archivosLote.length > 0 && typeof onSelectDocId === 'function' && (
        <div
          className="floating-artifact"
          style={{
            padding: '10px 16px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            overflowX: 'auto',
            backgroundColor: 'var(--color-paper-white)',
          }}
        >
          <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-slate-gray)', display: 'inline-flex', alignItems: 'center', gap: '6px', marginRight: '4px', whiteSpace: 'nowrap' }}>
            <Layers size={14} color="#2563eb" /> Archivos del lote:
          </span>

          <button
            type="button"
            onClick={() => onSelectDocId(null)}
            style={{
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: selectedDocId === null ? '700' : '600',
              border: '1px solid',
              borderColor: selectedDocId === null ? '#2563eb' : 'var(--color-border)',
              backgroundColor: selectedDocId === null ? '#2563eb' : 'var(--color-mist-gray)',
              color: selectedDocId === null ? '#ffffff' : 'var(--color-ink-black)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            Todos los archivos ({archivosLote.length})
          </button>

          {archivosLote.map((arc) => {
            const isSelected = Number(selectedDocId) === Number(arc.id_documento);
            return (
              <button
                key={arc.id_documento}
                type="button"
                onClick={() => onSelectDocId(arc.id_documento)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: isSelected ? '700' : '600',
                  border: '1px solid',
                  borderColor: isSelected ? '#2563eb' : 'var(--color-border)',
                  backgroundColor: isSelected ? 'var(--dataops-info-bg)' : 'var(--color-paper-white)',
                  color: isSelected ? 'var(--dataops-info-text)' : 'var(--color-slate-gray)',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  whiteSpace: 'nowrap',
                }}
              >
                <FileSpreadsheet size={13} />
                <span>{arc.nombre_archivo}</span>
                <span style={{
                  fontSize: '10.5px',
                  padding: '1px 6px',
                  borderRadius: '999px',
                  backgroundColor: 'var(--color-mist-gray)',
                  color: 'var(--color-ink-black)',
                }}>
                  {arc.tipo_fuente} · {arc.total_registros} reg.
                </span>
              </button>
            );
          })}
        </div>
      )}

      <div className="batch-flow-content">
        {children}
      </div>
    </div>
  );
}

