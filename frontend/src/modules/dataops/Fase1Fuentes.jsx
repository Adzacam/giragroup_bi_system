import React, { useState } from 'react';
import { UploadCloud, FileSpreadsheet, FileText, Database, CheckCircle, AlertCircle, Clock, ListTree } from 'lucide-react';
import ResponsiveTable from '../../components/shared/ResponsiveTable';

export default function Fase1Fuentes() {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="module-container" style={{ padding: '8px 0', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '32px' }}>
        <p className="subtitle" style={{ textTransform: 'uppercase', fontSize: '11.5px', fontWeight: '600', letterSpacing: '0.08em', color: 'var(--color-slate-gray)', margin: '0 0 8px 0' }}>
          Fase 1: Ingesta y Fuentes de Datos
        </p>
        <h2 className="serif-display" style={{ fontSize: 'clamp(28px, 3.5vw, 36px)', margin: '0 0 16px 0', color: 'var(--color-ink-black)' }}>
          Carga de Fuentes Documentales
        </h2>
        <p style={{ color: 'var(--color-slate-gray)', maxWidth: '800px', lineHeight: '1.6', fontSize: '14.5px' }}>
          Plataforma centralizada para la carga, validación preliminar y catalogación de archivos crudos (Excel, CSV, Moodle, Forms) antes de su procesamiento y normalización.
        </p>
        <button 
          className="btn-pill-dark" 
          onClick={() => setIsModalOpen(true)}
          type="button"
          style={{ marginTop: '20px', padding: '10px 24px', display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}
        >
          <UploadCloud size={18} />
          + Nueva Carga de Archivo
        </button>
      </header>

      {/* ── Summary KPI Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '40px' }}>
        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
            <FileSpreadsheet color="var(--color-slate-gray)" />
            <h3 style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Total Fuentes Cargadas
            </h3>
          </div>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-ink-black)', marginBottom: '8px' }}>
            14 archivos
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>Excel, CSV, Moodle, Forms</div>
        </div>
        
        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
            <ListTree color="var(--color-slate-gray)" />
            <h3 style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Registros Detectados
            </h3>
          </div>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-ink-black)', marginBottom: '8px' }}>
            1,248 filas
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>Listas para procesamiento</div>
        </div>

        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
            <AlertCircle color="var(--color-alert-amber)" />
            <h3 style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Alertas de Integridad
            </h3>
          </div>
          <div className="serif-display" style={{ fontSize: '36px', fontWeight: '500', color: 'var(--color-alert-amber)', marginBottom: '8px' }}>
            2 alertas
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>Cédula de Identidad nula o dudosa</div>
        </div>

        <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
            <Clock color="var(--color-slate-gray)" />
            <h3 style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-slate-gray)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Última Sincronización
            </h3>
          </div>
          <div className="serif-display" style={{ fontSize: '28px', fontWeight: '500', color: 'var(--color-ink-black)', marginBottom: '8px', lineHeight: '1.2' }}>
            Hoy, 08:30 AM
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>Job automático: POST /ingest</div>
        </div>
      </div>

      {/* ── Files Table ── */}
      <div style={{ marginTop: '32px' }}>
        <h3 className="serif-heading" style={{ fontSize: '20px', marginBottom: '16px', color: 'var(--color-ink-black)' }}>
          Archivos Procesados Recientemente
        </h3>
        <ResponsiveTable>
          <table className="steep-table">
            <thead>
              <tr>
                <th>Nombre del Archivo</th>
                <th>Tipo de Fuente</th>
                <th>Registros</th>
                <th>Fecha y Hora</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <FileSpreadsheet size={20} color="#3b82f6" />
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--color-ink-black)' }}>Acta_POS_2026_Modulo3.xlsx</div>
                      <div style={{ fontSize: '11px', color: 'var(--color-ash-gray)', fontFamily: 'var(--font-mono)' }}>sha256: 8f4e2a...</div>
                    </div>
                  </div>
                </td>
                <td><span className="badge-source">Excel Acta</span></td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>342</td>
                <td style={{ color: 'var(--color-slate-gray)' }}>2026-09-20 10:15</td>
                <td>
                  <span className="badge-status badge-status-completed" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <CheckCircle size={13} /> Completado
                  </span>
                </td>
                <td>
                  <button type="button" style={{ background: 'none', border: 'none', color: 'var(--color-slate-gray)', textDecoration: 'underline', cursor: 'pointer', fontSize: '13px' }}>
                    Detalle
                  </button>
                </td>
              </tr>
              <tr>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <FileText size={20} color="#8b5cf6" />
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--color-ink-black)' }}>Respuestas_Encuesta_M3.csv</div>
                      <div style={{ fontSize: '11px', color: 'var(--color-ash-gray)', fontFamily: 'var(--font-mono)' }}>sha256: 3a9c1b...</div>
                    </div>
                  </div>
                </td>
                <td><span className="badge-source">Google Forms</span></td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>215</td>
                <td style={{ color: 'var(--color-slate-gray)' }}>2026-09-19 14:30</td>
                <td>
                  <span className="badge-status badge-status-completed" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <CheckCircle size={13} /> Completado
                  </span>
                </td>
                <td>
                  <button type="button" style={{ background: 'none', border: 'none', color: 'var(--color-slate-gray)', textDecoration: 'underline', cursor: 'pointer', fontSize: '13px' }}>
                    Detalle
                  </button>
                </td>
              </tr>
              <tr>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <Database size={20} color="#f97316" />
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--color-ink-black)' }}>Moodle_Grades_Export.xml</div>
                      <div style={{ fontSize: '11px', color: 'var(--color-ash-gray)', fontFamily: 'var(--font-mono)' }}>sha256: c5f2d8...</div>
                    </div>
                  </div>
                </td>
                <td><span className="badge-source">Aula Moodle</span></td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>691</td>
                <td style={{ color: 'var(--color-slate-gray)' }}>2026-09-18 09:45</td>
                <td>
                  <span className="badge-status badge-status-processing" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <AlertCircle size={13} /> Advertencias (2)
                  </span>
                </td>
                <td>
                  <button type="button" style={{ background: 'none', border: 'none', color: 'var(--color-slate-gray)', textDecoration: 'underline', cursor: 'pointer', fontSize: '13px' }}>
                    Detalle
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </ResponsiveTable>
      </div>

      {/* ── Upload Modal ── */}
      {isModalOpen && (
        <div className="modal-backdrop" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1300, padding: '20px' }}>
          <div className="modal-panel" style={{ padding: '32px', borderRadius: 'var(--radius-cards)', width: '100%', maxWidth: '500px', border: '1px solid var(--color-border)' }}>
            <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '24px', color: 'var(--color-ink-black)' }}>
              Cargar Nueva Fuente Documental
            </h3>
            
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--color-slate-gray)', marginBottom: '8px' }}>
                Tipo de Archivo
              </label>
              <select className="form-input" style={{ width: '100%', padding: '12px 16px', borderRadius: 'var(--radius-inputs)' }}>
                <option>Acta Calificaciones (Excel)</option>
                <option>Google Forms (CSV)</option>
                <option>Aula Moodle (XML/CSV)</option>
              </select>
            </div>

            <div className="drop-zone" style={{ border: '2px dashed var(--color-border)', borderRadius: '16px', padding: '36px 20px', textAlign: 'center', marginBottom: '24px', cursor: 'pointer' }}>
              <UploadCloud size={32} color="var(--color-slate-gray)" style={{ margin: '0 auto 12px' }} />
              <p style={{ fontSize: '14px', color: 'var(--color-ink-black)', margin: 0, fontWeight: 500 }}>Arrastra tu archivo aquí o haz clic para explorar</p>
              <p style={{ fontSize: '12px', color: 'var(--color-ash-gray)', marginTop: '8px' }}>Soporta .xlsx, .csv, .xml (Max 50MB)</p>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button 
                type="button"
                className="btn-pill-ghost" 
                onClick={() => setIsModalOpen(false)}
                style={{ padding: '10px 24px', fontSize: '13px' }}
              >
                Cancelar
              </button>
              <button 
                type="button"
                className="btn-pill-dark"
                style={{ padding: '10px 24px', fontSize: '13px' }}
                onClick={() => {
                  alert('Archivo simulado como subido.');
                  setIsModalOpen(false);
                }}
              >
                Subir y Validar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
