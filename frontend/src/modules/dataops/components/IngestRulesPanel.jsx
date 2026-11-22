import React from 'react';
import { Calendar, RefreshCw, ShieldCheck } from 'lucide-react';
import { UMBRAL_INDICE_REGISTRO } from '../../../constants/dataopsConfig';

export default function IngestRulesPanel({ isProcessing, uploadProgress, uploadStageText }) {
  return (
    <div className="floating-artifact" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div>
        <h2 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 4px 0', color: 'var(--color-ink-black)' }}>
          Reglas de procesamiento
        </h2>
        <p style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)', margin: 0 }}>
          Las fechas se leen del archivo. La confianza mínima y la protección de datos son fijas.
        </p>
      </div>

      <div style={{ padding: '12px 14px', borderRadius: '10px', backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)', display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
        <Calendar size={18} color="var(--color-gira-gold)" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <div style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>Fechas:</span>
            <span className="chip-cat chip-fecha">Automático en archivo</span>
          </div>
          <p style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', margin: '3px 0 0 0', lineHeight: 1.4 }}>
            Se reconocen las fechas de las columnas y encabezados del archivo.
          </p>
        </div>
      </div>

      <div style={{ padding: '12px 14px', borderRadius: '10px', backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)' }}>
        <strong style={{ color: 'var(--color-ink-black)', fontSize: '12.5px' }}>{UMBRAL_INDICE_REGISTRO} % fijo</strong>
        <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>Es el mínimo de confianza para aceptar un registro directamente. Consulta los rangos en el glosario.</p>
      </div>
      <div style={{ padding: '12px 14px', borderRadius: '10px', backgroundColor: 'var(--color-mist-gray)', border: '1px solid var(--color-border)' }}>
        <strong style={{ color: 'var(--color-ink-black)', fontSize: '12.5px' }}><ShieldCheck size={15} /> Datos personales siempre protegidos</strong>
        <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>La protección se aplica en el servidor y no se puede desactivar desde esta pantalla.</p>
      </div>

      {isProcessing && (
        <div style={{ marginTop: 'auto', padding: '12px 14px', borderRadius: '8px', backgroundColor: 'var(--dataops-gold-bg)', border: '1px solid var(--dataops-gold-border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <RefreshCw size={13} className="animate-spin" color="var(--color-gira-gold)" />
              {uploadProgress < 100 ? 'Subiendo archivos...' : 'Procesando en servidor...'}
            </span>
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-gira-gold)' }}>{uploadProgress}%</span>
          </div>
          <div style={{ width: '100%', height: '8px', borderRadius: '4px', backgroundColor: 'var(--color-border)', overflow: 'hidden', position: 'relative' }}>
            <div style={{ width: `${Math.max(5, uploadProgress)}%`, height: '100%', background: 'var(--color-gira-gold)', borderRadius: '4px', transition: 'width 0.3s ease-in-out' }} />
          </div>
          <p style={{ fontSize: '11px', color: 'var(--color-slate-gray)', margin: '6px 0 0 0', lineHeight: 1.3 }}>
            {uploadStageText || (uploadProgress < 100 ? `Cargando lote: ${uploadProgress}%` : 'Ejecutando pipeline y diagnósticos estructurales...')}
          </p>
        </div>
      )}
    </div>
  );
}
