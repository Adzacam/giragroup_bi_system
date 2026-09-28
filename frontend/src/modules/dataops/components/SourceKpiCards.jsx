import React from 'react';
import { FileSpreadsheet, ListTree, AlertCircle, Clock } from 'lucide-react';

export default function SourceKpiCards({ kpis }) {
  const total_fuentes = kpis?.total_fuentes ?? 0;
  const registros_detectados = kpis?.registros_detectados ?? 0;
  const archivos_advertencias = kpis?.archivos_advertencias ?? 0;
  const ultima_sincronizacion = kpis?.ultima_sincronizacion || (total_fuentes > 0 ? 'Hoy, sincronizado' : 'Sin registros');

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '40px' }}>
      <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
          <FileSpreadsheet color="var(--color-slate-gray)" />
          <h3 style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Total Fuentes Cargadas
          </h3>
        </div>
        <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-ink-black)', marginBottom: '8px' }}>
          {total_fuentes} archivos
        </div>
        <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>Excel, CSV, Moodle, Forms</div>
      </div>
      
      <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
          <ListTree color="var(--color-slate-gray)" />
          <h3 style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Registros Detectados
          </h3>
        </div>
        <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-ink-black)', marginBottom: '8px' }}>
          {registros_detectados.toLocaleString()} filas
        </div>
        <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>Listas para procesamiento</div>
      </div>

      <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
          <AlertCircle color="var(--color-alert-amber)" />
          <h3 style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Archivos con Advertencias
          </h3>
        </div>
        <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-alert-amber)', marginBottom: '8px' }}>
          {archivos_advertencias} archivos
        </div>
        <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>Requieren mapeo asistido</div>
      </div>

      <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
          <Clock color="var(--color-slate-gray)" />
          <h3 style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Última Sincronización
          </h3>
        </div>
        <div className="serif-display" style={{ fontSize: '28px', fontWeight: '500', color: 'var(--color-ink-black)', marginBottom: '8px', lineHeight: '1.2' }}>
          {ultima_sincronizacion}
        </div>
        <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>Job automático: POST /ingest</div>
      </div>
    </div>
  );
}
