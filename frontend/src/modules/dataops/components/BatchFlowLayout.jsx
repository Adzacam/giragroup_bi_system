import React from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { CheckCircle2, FileSpreadsheet, Layers, PlusCircle } from 'lucide-react';
import BatchFlowHeader from './BatchFlowHeader';
import BatchFlowStepper from './BatchFlowStepper';
import { useLoteContext } from '../hooks/useLoteContext';
import { clearLoteFlowSession } from '../context/LoteFlowContext';

export default function BatchFlowLayout({
  currentStep = 1,
  selectedDocId = null,
  onSelectDocId = null,
  children,
}) {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const effectiveRouteId = id || searchParams.get('lote');
  let ultimoActivo = null;
  try { ultimoActivo = localStorage.getItem('last_active_batch_id'); } catch { /* sin storage */ }
  const targetId = effectiveRouteId || ultimoActivo;

  // Contexto del lote en React Query: se comparte entre pasos (sin recargas al retroceder) y se invalida al mutar
  const { data: batchContext = null } = useLoteContext(targetId);
  const readOnly = batchContext?.estado_flujo === 'CONSOLIDADO';

  // Flujo cerrado: se limpia el lote activo para que Ingesta arranque en blanco con archivos nuevos
  const handleNuevoLote = () => {
    clearLoteFlowSession(targetId);
    try { localStorage.removeItem('last_active_batch_id'); } catch { /* sin storage */ }
    navigate('/dataops/ingesta');
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
        allCompleted={readOnly}
      />

      {/* Barra de pestañas por archivo dentro del lote para pasos ②, ③ y ④ (#17) */}
      {!readOnly && currentStep >= 2 && archivosLote.length > 0 && typeof onSelectDocId === 'function' && (
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
        {readOnly ? (
          <div className="floating-artifact" role="status" style={{ padding: '48px 24px', textAlign: 'center' }}>
            <CheckCircle2 size={48} color="#1B8754" style={{ margin: '0 auto 16px auto', display: 'block' }} />
            <h3 className="serif-heading" style={{ fontSize: '20px', margin: '0 0 8px 0', color: 'var(--color-ink-black)' }}>
              ¡Flujo completado!
            </h3>
            <p style={{ fontSize: '13.5px', color: 'var(--color-slate-gray)', maxWidth: '520px', margin: '0 auto 20px auto' }}>
              {`Ingesta, lectura de BETO y revisión humana terminaron: ${batchContext?.total_registros ?? 0} registros de ${archivosLote.length} archivo(s) ya están en el Data Warehouse. Este lote quedó cerrado.`}
            </p>
            <button type="button" className="btn-pill-gold" onClick={handleNuevoLote}>
              <PlusCircle size={15} /> Iniciar nuevo lote
            </button>
          </div>
        ) : children}
      </div>
    </div>
  );
}

