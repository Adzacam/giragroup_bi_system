import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import BatchFlowHeader from './BatchFlowHeader';
import BatchFlowStepper from './BatchFlowStepper';
import { dataopsApi } from '../../../api/dataopsApi';

export default function BatchFlowLayout({ currentStep = 1, children }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [batchContext, setBatchContext] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (id) {
      loadBatchContext(id);
    } else {
      // Intentar cargar el último lote activo desde localStorage o fuentes
      const savedLoteId = localStorage.getItem('last_active_batch_id');
      if (savedLoteId && currentStep > 1) {
        loadBatchContext(savedLoteId);
      }
    }
  }, [id, currentStep]);

  const loadBatchContext = async (batchId) => {
    try {
      setIsLoading(true);
      const res = await fetch(`/api/v1/dataops/lote/${batchId}/context`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setBatchContext(data);
        localStorage.setItem('last_active_batch_id', batchId);
      } else {
        // Fallback context para desarrollo si la BD no tiene el id exacto
        setBatchContext({
          id_documento: batchId,
          nombre_archivo: `Acta_Unifranz_Lote_${batchId}.xlsx`,
          institucion: 'Universidad Franz Tamayo (Unifranz)',
          tipo_fuente: 'Acta de calificaciones',
          tipo_escala: 'CENTESIMAL_100',
          escala_label: 'Sobre 100',
          periodo: '2026-1',
          total_registros: 480,
          pendientes_revision: 23
        });
      }
    } catch (err) {
      console.warn('Usando fallback de contexto para el lote:', err);
      setBatchContext({
        id_documento: batchId,
        nombre_archivo: `Acta_Unifranz_Lote_${batchId}.xlsx`,
        institucion: 'Universidad Franz Tamayo (Unifranz)',
        tipo_fuente: 'Acta de calificaciones',
        tipo_escala: 'CENTESIMAL_100',
        escala_label: 'Sobre 100',
        periodo: '2026-1',
        total_registros: 480,
        pendientes_revision: 23
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectBatch = () => {
    navigate('/dataops/ingesta');
  };

  return (
    <div className="batch-flow-container" style={{ maxWidth: '1440px', margin: '0 auto', padding: '0 8px' }}>
      <BatchFlowHeader
        batchContext={batchContext}
        currentStep={currentStep}
        onSelectBatch={handleSelectBatch}
      />
      <BatchFlowStepper
        currentStep={currentStep}
        batchId={id || batchContext?.id_documento}
        pendientesCount={batchContext?.pendientes_revision || 0}
      />
      <div className="batch-flow-content">
        {children}
      </div>
    </div>
  );
}
