import React, { useState } from 'react';
import { UploadCloud, FileSpreadsheet, ListTree, AlertCircle, Clock, FileText, CheckCircle, Database } from 'lucide-react';

export default function Fase1Fuentes() {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="module-container" style={{ padding: '24px', fontFamily: 'Inter, sans-serif' }}>
      <header style={{ marginBottom: '32px' }}>
        <p className="subtitle" style={{ textTransform: 'uppercase', fontSize: '12px', fontWeight: '600', letterSpacing: '0.05em', color: '#666' }}>
          Fase 1: Ingesta y Carga
        </p>
        <h2 className="serif-display" style={{ fontFamily: 'Newsreader, serif', fontSize: '32px', marginTop: '8px', marginBottom: '16px', color: '#17191c' }}>
          Ingesta y Gestión de Fuentes Documentales
        </h2>
        <p style={{ color: '#4a5568', maxWidth: '800px', lineHeight: '1.6' }}>
          Plataforma centralizada para la carga, validación preliminar y catalogación de archivos crudos (Excel, CSV, Moodle, Forms) antes de su procesamiento y normalización.
        </p>
        <button 
          className="btn-pill-dark" 
          onClick={() => setIsModalOpen(true)}
          style={{ marginTop: '24px', backgroundColor: '#17191c', color: '#fff', borderRadius: '9999px', padding: '10px 24px', border: 'none', cursor: 'pointer', fontWeight: '500', display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <UploadCloud size={18} />
          + Nueva Carga de Archivo
        </button>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '24px', marginBottom: '40px' }}>
        <div className="card-mist" style={{ backgroundColor: '#f2f2f3', padding: '24px', borderRadius: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <FileSpreadsheet color="#4a5568" />
            <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#4a5568', margin: 0 }}>Total Fuentes Cargadas</h3>
          </div>
          <div className="serif-signifier" style={{ fontFamily: 'Newsreader, serif', fontSize: '36px', fontWeight: '500', color: '#17191c', marginBottom: '8px' }}>14 archivos</div>
          <div style={{ fontSize: '13px', color: '#718096' }}>Excel, CSV, Moodle, Forms</div>
        </div>
        
        <div className="card-mist" style={{ backgroundColor: '#f2f2f3', padding: '24px', borderRadius: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <ListTree color="#4a5568" />
            <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#4a5568', margin: 0 }}>Registros Detectados</h3>
          </div>
          <div className="serif-signifier" style={{ fontFamily: 'Newsreader, serif', fontSize: '36px', fontWeight: '500', color: '#17191c', marginBottom: '8px' }}>1,248 filas</div>
          <div style={{ fontSize: '13px', color: '#718096' }}>Listas para procesamiento</div>
        </div>

        <div className="card-mist" style={{ backgroundColor: '#f2f2f3', padding: '24px', borderRadius: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <AlertCircle color="#d97706" />
            <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#4a5568', margin: 0 }}>Archivos con Advertencias</h3>
          </div>
          <div className="serif-signifier color-alert-amber" style={{ fontFamily: 'Newsreader, serif', fontSize: '36px', fontWeight: '500', color: '#d97706', marginBottom: '8px' }}>2 archivos</div>
          <div style={{ fontSize: '13px', color: '#718096' }}>Requieren mapeo asistido</div>
        </div>

        <div className="card-mist" style={{ backgroundColor: '#f2f2f3', padding: '24px', borderRadius: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <Clock color="#4a5568" />
            <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#4a5568', margin: 0 }}>Última Sincronización</h3>
          </div>
          <div className="serif-signifier" style={{ fontFamily: 'Newsreader, serif', fontSize: '28px', fontWeight: '500', color: '#17191c', marginBottom: '8px', lineHeight: '1.2' }}>Hoy, 08:30 AM</div>
          <div style={{ fontSize: '13px', color: '#718096' }}>Job automático: POST /ingest</div>
        </div>
      </div>

      <div className="floating-artifact" style={{ backgroundColor: '#fff', borderRadius: '24px', padding: '24px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
        <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '20px' }}>Archivos Procesados Recientemente</h3>
        <div style={{ overflowX: 'auto' }}>
          <table className="steep-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#4a5568', fontSize: '13px' }}>
                <th style={{ padding: '16px 8px', fontWeight: '600' }}>Nombre del Archivo</th>
                <th style={{ padding: '16px 8px', fontWeight: '600' }}>Tipo de Fuente</th>
                <th style={{ padding: '16px 8px', fontWeight: '600' }}>Registros</th>
                <th style={{ padding: '16px 8px', fontWeight: '600' }}>Fecha y Hora</th>
                <th style={{ padding: '16px 8px', fontWeight: '600' }}>Estado</th>
                <th style={{ padding: '16px 8px', fontWeight: '600' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid #f7fafc' }}>
                <td style={{ padding: '16px 8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <FileSpreadsheet size={20} color="#2b6cb0" />
                    <div>
                      <div style={{ fontWeight: '500', fontSize: '14px', color: '#17191c' }}>Acta_POS_2026_Modulo3.xlsx</div>
                      <div style={{ fontSize: '11px', color: '#a0aec0', fontFamily: 'JetBrains Mono, monospace' }}>sha256: 8f4e2a...</div>
                    </div>
                  </div>
                </td>
                <td style={{ padding: '16px 8px' }}><span className="badge-source" style={{ backgroundColor: '#ebf8ff', color: '#2b6cb0', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '500' }}>Excel Acta</span></td>
                <td style={{ padding: '16px 8px', fontSize: '14px' }}>342</td>
                <td style={{ padding: '16px 8px', fontSize: '14px', color: '#4a5568' }}>2026-09-20 10:15</td>
                <td style={{ padding: '16px 8px' }}><span className="badge-status-completed" style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#38a169', fontSize: '13px', fontWeight: '500' }}><CheckCircle size={14} /> Completado</span></td>
                <td style={{ padding: '16px 8px' }}>
                  <button style={{ background: 'none', border: 'none', color: '#4a5568', textDecoration: 'underline', cursor: 'pointer', fontSize: '13px' }}>Detalle</button>
                </td>
              </tr>
              <tr style={{ borderBottom: '1px solid #f7fafc' }}>
                <td style={{ padding: '16px 8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <FileText size={20} color="#805ad5" />
                    <div>
                      <div style={{ fontWeight: '500', fontSize: '14px', color: '#17191c' }}>Respuestas_Encuesta_M3.csv</div>
                      <div style={{ fontSize: '11px', color: '#a0aec0', fontFamily: 'JetBrains Mono, monospace' }}>sha256: 3a9c1b...</div>
                    </div>
                  </div>
                </td>
                <td style={{ padding: '16px 8px' }}><span className="badge-source" style={{ backgroundColor: '#faf5ff', color: '#805ad5', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '500' }}>Google Forms</span></td>
                <td style={{ padding: '16px 8px', fontSize: '14px' }}>215</td>
                <td style={{ padding: '16px 8px', fontSize: '14px', color: '#4a5568' }}>2026-09-19 14:30</td>
                <td style={{ padding: '16px 8px' }}><span className="badge-status-completed" style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#38a169', fontSize: '13px', fontWeight: '500' }}><CheckCircle size={14} /> Completado</span></td>
                <td style={{ padding: '16px 8px' }}>
                  <button style={{ background: 'none', border: 'none', color: '#4a5568', textDecoration: 'underline', cursor: 'pointer', fontSize: '13px' }}>Detalle</button>
                </td>
              </tr>
              <tr>
                <td style={{ padding: '16px 8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <Database size={20} color="#dd6b20" />
                    <div>
                      <div style={{ fontWeight: '500', fontSize: '14px', color: '#17191c' }}>Moodle_Grades_Export.xml</div>
                      <div style={{ fontSize: '11px', color: '#a0aec0', fontFamily: 'JetBrains Mono, monospace' }}>sha256: c5f2d8...</div>
                    </div>
                  </div>
                </td>
                <td style={{ padding: '16px 8px' }}><span className="badge-source" style={{ backgroundColor: '#feebc8', color: '#dd6b20', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '500' }}>Aula Moodle</span></td>
                <td style={{ padding: '16px 8px', fontSize: '14px' }}>691</td>
                <td style={{ padding: '16px 8px', fontSize: '14px', color: '#4a5568' }}>2026-09-18 09:45</td>
                <td style={{ padding: '16px 8px' }}><span className="badge-status-completed" style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#d97706', fontSize: '13px', fontWeight: '500' }}><AlertCircle size={14} /> Advertencias (2)</span></td>
                <td style={{ padding: '16px 8px' }}>
                  <button style={{ background: 'none', border: 'none', color: '#4a5568', textDecoration: 'underline', cursor: 'pointer', fontSize: '13px' }}>Detalle</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-backdrop" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="modal-panel" style={{ backgroundColor: '#fff', padding: '32px', borderRadius: '24px', width: '100%', maxWidth: '500px', boxShadow: '0 20px 40px rgba(0,0,0,0.1)' }}>
            <h3 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '24px', color: '#17191c' }}>Cargar Nueva Fuente Documental</h3>
            
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#4a5568', marginBottom: '8px' }}>Tipo de Archivo</label>
              <select style={{ width: '100%', padding: '12px 16px', borderRadius: '16px', border: '1px solid #e2e8f0', fontSize: '14px', outline: 'none' }}>
                <option>Acta Calificaciones (Excel)</option>
                <option>Google Forms (CSV)</option>
                <option>Aula Moodle (XML/CSV)</option>
              </select>
            </div>

            <div className="drop-zone" style={{ border: '2px dashed #cbd5e0', borderRadius: '16px', padding: '40px 20px', textAlign: 'center', marginBottom: '24px', backgroundColor: '#f7fafc', cursor: 'pointer' }}>
              <UploadCloud size={32} color="#a0aec0" style={{ margin: '0 auto 12px' }} />
              <p style={{ fontSize: '14px', color: '#4a5568', margin: 0 }}>Arrastra tu archivo aquí o haz clic para explorar</p>
              <p style={{ fontSize: '12px', color: '#a0aec0', marginTop: '8px' }}>Soporta .xlsx, .csv, .xml (Max 50MB)</p>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button 
                className="btn-pill-ghost" 
                onClick={() => setIsModalOpen(false)}
                style={{ backgroundColor: 'transparent', color: '#4a5568', borderRadius: '9999px', padding: '10px 24px', border: '1px solid #e2e8f0', cursor: 'pointer', fontWeight: '500' }}
              >
                Cancelar
              </button>
              <button 
                className="btn-pill-dark"
                style={{ backgroundColor: '#17191c', color: '#fff', borderRadius: '9999px', padding: '10px 24px', border: 'none', cursor: 'pointer', fontWeight: '500' }}
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
