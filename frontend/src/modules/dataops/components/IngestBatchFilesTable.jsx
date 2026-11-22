import React from 'react';
import { FileSpreadsheet, ShieldCheck } from 'lucide-react';
import Button from '../../../components/shared/Button';
import Paginacion from '../../../components/shared/Paginacion';
import AnimatedNumberV2 from '../../../v2/motion/AnimatedNumberV2';

export default function IngestBatchFilesTable({ prepKpis, inspectedPagination, expandedDetailKey, onToggleExpand }) {
  return (
    <>
      {prepKpis && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 14 }}>
          {prepKpis.map(([label, value]) => (
            <div key={label} style={{ padding: '12px 16px', borderRadius: 10, border: '1px solid var(--color-border)', backgroundColor: 'var(--color-mist-gray)' }}>
              <p style={{ color: 'var(--color-slate-gray)', fontSize: 11.5, margin: 0 }}>{label}</p>
              <p style={{ color: 'var(--color-ink-black)', fontSize: 20, fontWeight: 700, margin: '4px 0 0' }}>
                {value == null ? 'Sin dato' : <AnimatedNumberV2 value={value.toLocaleString('es-BO')} />}
              </p>
            </div>
          ))}
        </div>
      )}
      <div style={{ overflowX: 'auto', maxWidth: '100%', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
        <table className="dataops-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12.5px' }}>
          <thead>
            <tr>
              <th>Archivo</th><th>Origen detectado</th><th>Filas</th><th>Protección</th><th>Estado</th><th style={{ textAlign: 'center' }}>Vista previa</th>
            </tr>
          </thead>
          <tbody>
            {inspectedPagination.visibles.map((item) => {
              const isExpanded = expandedDetailKey === item.key;
              return (
                <React.Fragment key={item.key}>
                  <tr className="dataops-table-row" style={{ cursor: 'default' }}>
                    <td style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <FileSpreadsheet size={15} color="var(--color-gira-gold)" />
                        <span>{item.nombre}</span>
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', fontWeight: 400, marginTop: '3px' }}>
                        {item.origen} · Registros: {item.filas} · Fechas: {item.fechas}
                      </div>
                    </td>
                    <td><span className="chip-cat chip-origen" style={{ fontWeight: 700 }}>{item.origen}</span></td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{item.filas}</td>
                    <td>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: 700, color: 'var(--color-alert-green)', backgroundColor: 'var(--dataops-success-bg)', padding: '2px 8px', borderRadius: '4px' }}>
                        <ShieldCheck size={12} /> Protección del servidor
                      </span>
                    </td>
                    <td><span className="chip-cat chip-fecha">[{item.estado}]</span></td>
                    <td style={{ textAlign: 'center' }}>
                      <Button variant="ghost" type="button" onClick={() => onToggleExpand(isExpanded ? null : item.key)} style={{ padding: '4px 10px', fontSize: '11px' }}>
                        {isExpanded ? 'Ocultar' : 'Vista previa'}
                      </Button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={6} style={{ padding: 0 }}>
                        <div className="dataops-row-detail">
                          <span><strong>Archivo:</strong> {item.nombre}</span>
                          <span><strong>Origen:</strong> {item.origen}</span>
                          <span><strong>Registros:</strong> {item.filas}</span>
                          <span><strong>Fechas:</strong> {item.fechas}</span>
                          <span><strong>Estado:</strong> {item.estado}</span>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
        <Paginacion {...inspectedPagination} onChange={inspectedPagination.setPagina} />
      </div>
    </>
  );
}
