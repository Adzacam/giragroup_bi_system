import React from 'react';
import { Layers, FileSpreadsheet, Scale, Building2, CheckCircle2, Clock, AlertTriangle, ChevronRight } from 'lucide-react';

export default function BatchFlowHeader({ batchContext, currentStep = 1, onSelectBatch }) {
  if (!batchContext) {
    return (
      <div className="floating-artifact" style={{ padding: '16px 24px', marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '36px', height: '36px', borderRadius: '10px',
            backgroundColor: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Layers size={18} />
          </div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--color-ink-black)' }}>
              Flujo de Ingesta & Procesamiento de Lote
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
              Seleccione o suba un archivo para iniciar la transformación guiada
            </div>
          </div>
        </div>
      </div>
    );
  }

  const {
    nombre_archivo = 'Lote sin nombre',
    institucion = 'Universidad Franz Tamayo',
    tipo_fuente = 'Acta de calificaciones',
    escala_label = 'Sobre 100',
    total_registros = 0,
    pendientes_revision = 0,
    id_documento
  } = batchContext;

  return (
    <div className="floating-artifact" style={{
      padding: '16px 24px',
      marginBottom: '20px',
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '16px',
      borderLeft: '4px solid #3b82f6'
    }}>
      {/* Información del Lote */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
        <div style={{
          width: '40px', height: '40px', borderRadius: '10px',
          backgroundColor: 'var(--dataops-info-bg)', color: 'var(--dataops-info-text)',
          border: '1px solid var(--dataops-info-border)',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <FileSpreadsheet size={20} />
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '15px', fontWeight: '700', color: 'var(--color-ink-black)', fontFamily: 'var(--font-mono)' }}>
              Lote: {nombre_archivo}
            </span>
            <span style={{ color: 'var(--color-border)' }}>·</span>
            <span style={{ fontSize: '13px', color: 'var(--color-slate-gray)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <Building2 size={13} /> {institucion}
            </span>
            <span style={{ color: 'var(--color-border)' }}>·</span>
            <span style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>
              {tipo_fuente}
            </span>
            <span style={{ color: 'var(--color-border)' }}>·</span>
            <span style={{
              fontSize: '12px',
              padding: '2px 8px',
              borderRadius: '6px',
              backgroundColor: 'var(--dataops-warning-bg)',
              color: 'var(--dataops-warning-text)',
              border: '1px solid var(--dataops-warning-border)',
              fontWeight: '600',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <Scale size={12} /> Escala: {escala_label}
            </span>
          </div>

          <div style={{ fontSize: '12px', color: 'var(--color-ash-gray)', marginTop: '4px', display: 'flex', gap: '12px' }}>
            <span>ID Doc: #{id_documento}</span>
            <span>Registros: <strong>{total_registros}</strong></span>
            {pendientes_revision > 0 && (
              <span style={{ color: 'var(--dataops-warning-text)', fontWeight: '600' }}>
                En revisión: <strong>{pendientes_revision}</strong>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Acción o Selector */}
      {onSelectBatch && (
        <button
          onClick={onSelectBatch}
          className="sileo-btn"
          style={{
            fontSize: '12px',
            padding: '6px 12px',
            backgroundColor: 'var(--color-mist-gray)',
            color: 'var(--color-slate-gray)',
            border: '1px solid var(--color-border)',
            borderRadius: '8px',
            cursor: 'pointer'
          }}
        >
          Cambiar Lote
        </button>
      )}
    </div>
  );
}
