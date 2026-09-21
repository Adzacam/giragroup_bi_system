import React, { useState } from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle, Terminal, Unlink, Activity } from 'lucide-react';
import BetoDrawer from './BetoDrawer';

export default function Fase3RevisionHumana() {
  const [isBetoOpen, setIsBetoOpen] = useState(false);

  return (
    <div className="module-container" style={{ padding: '24px', fontFamily: 'Inter, sans-serif' }}>
      <header style={{ marginBottom: '32px' }}>
        <p className="subtitle" style={{ textTransform: 'uppercase', fontSize: '12px', fontWeight: '600', letterSpacing: '0.05em', color: '#666' }}>
          AUDITOR_CALIDAD · DataOps
        </p>
        <h2 className="serif-display" style={{ fontFamily: 'Newsreader, serif', fontSize: '32px', marginTop: '8px', marginBottom: '16px', color: '#17191c' }}>
          Ensamblaje de Registro y Doble Confianza
        </h2>
      </header>

      <div className="floating-artifact" style={{ backgroundColor: '#fff', borderRadius: '16px', padding: '24px', marginBottom: '32px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)', borderLeft: '4px solid #e53e3e' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <span style={{ backgroundColor: '#e53e3e', color: '#fff', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <AlertTriangle size={14} /> REQUIERE REVISIÓN
              </span>
              <span style={{ fontSize: '14px', fontWeight: '500', color: '#4a5568' }}>Disparador de Validación de Matrícula y CI Activado</span>
            </div>
            <div style={{ fontSize: '14px', color: '#c53030', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
              ▲ Campo Crítico Dudoso: Cédula de Identidad (CI) incompleta
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '12px', color: '#718096', marginBottom: '4px' }}>Score General</div>
            <div className="serif-display" style={{ fontSize: '32px', fontWeight: '600', color: '#17191c', lineHeight: '1' }}>87%</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginTop: '24px', paddingTop: '24px', borderTop: '1px solid #e2e8f0' }}>
          <div>
            <div style={{ fontSize: '12px', color: '#718096', marginBottom: '8px', fontWeight: '600' }}>Confianza NER BETO</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '24px', fontWeight: '600', color: '#38a169' }}>94.0%</span>
              <span style={{ color: '#38a169', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '4px' }}><CheckCircle size={14}/> Óptimo</span>
            </div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#718096', marginBottom: '8px', fontWeight: '600' }}>Vinculación Cross-Source RapidFuzz</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '24px', fontWeight: '600', color: '#d97706' }}>88.0%</span>
              <span style={{ color: '#d97706', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '4px' }}><Activity size={14}/> Homonimia detectada</span>
            </div>
          </div>
        </div>
      </div>

      <div className="floating-artifact" style={{ backgroundColor: '#fff', borderRadius: '24px', padding: '24px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)', marginBottom: '32px', overflowX: 'auto' }}>
        <table className="steep-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#4a5568' }}>
              <th style={{ padding: '16px 12px', fontWeight: '600' }}>Atributo Dimensional</th>
              <th style={{ padding: '16px 12px', fontWeight: '600' }}>Fuente 1: Acta Excel</th>
              <th style={{ padding: '16px 12px', fontWeight: '600' }}>Fuente 2: Google Forms</th>
              <th style={{ padding: '16px 12px', fontWeight: '600' }}>Fuente 3: Moodle</th>
              <th style={{ padding: '16px 12px', fontWeight: '600' }}>NER BETO</th>
              <th style={{ padding: '16px 12px', fontWeight: '600' }}>RapidFuzz Cross</th>
              <th style={{ padding: '16px 12px', fontWeight: '600' }}>Estado de Campo</th>
            </tr>
          </thead>
          <tbody>
            <tr className="row-critical-alert" style={{ borderBottom: '1px solid #f7fafc', backgroundColor: '#fff5f5' }}>
              <td style={{ padding: '16px 12px', fontWeight: '600', color: '#c53030' }}>CI Estudiante</td>
              <td style={{ padding: '16px 12px', fontFamily: 'JetBrains Mono, monospace' }}>4892019 LP?</td>
              <td style={{ padding: '16px 12px' }}><span className="badge-kimball-na" style={{ color: '#a0aec0', fontSize: '12px' }}>N/A</span></td>
              <td style={{ padding: '16px 12px' }}><span className="badge-kimball-na" style={{ color: '#a0aec0', fontSize: '12px' }}>N/A</span></td>
              <td style={{ padding: '16px 12px', color: '#d97706', fontWeight: '600' }}>0.54</td>
              <td style={{ padding: '16px 12px', color: '#a0aec0' }}>-</td>
              <td style={{ padding: '16px 12px' }}>
                <span className="tag-critical-field" style={{ backgroundColor: '#fed7d7', color: '#c53030', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '500' }}>Dudoso (Sufijo ?)</span>
              </td>
            </tr>
            <tr style={{ borderBottom: '1px solid #f7fafc' }}>
              <td style={{ padding: '16px 12px', fontWeight: '500' }}>Nombre Completo</td>
              <td style={{ padding: '16px 12px' }}>Daza Adriano</td>
              <td style={{ padding: '16px 12px' }}>Adriano Daza Meneses</td>
              <td style={{ padding: '16px 12px' }}>Daza M., Adriano</td>
              <td style={{ padding: '16px 12px', color: '#38a169', fontWeight: '600' }}>0.94</td>
              <td style={{ padding: '16px 12px', color: '#d97706', fontWeight: '600' }}>88%</td>
              <td style={{ padding: '16px 12px', color: '#4a5568', fontSize: '13px' }}>Conciliado</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #f7fafc' }}>
              <td style={{ padding: '16px 12px', fontWeight: '500' }}>Módulo</td>
              <td style={{ padding: '16px 12px' }}>Modulo 3</td>
              <td style={{ padding: '16px 12px' }}><span className="badge-kimball-na" style={{ color: '#a0aec0', fontSize: '12px' }}>N/A</span></td>
              <td style={{ padding: '16px 12px' }}>MOD-302: Gestión de Datos</td>
              <td style={{ padding: '16px 12px', color: '#38a169', fontWeight: '600' }}>0.88</td>
              <td style={{ padding: '16px 12px', color: '#38a169', fontWeight: '600' }}>92%</td>
              <td style={{ padding: '16px 12px', color: '#4a5568', fontSize: '13px' }}>Homologado</td>
            </tr>
            <tr>
              <td style={{ padding: '16px 12px', fontWeight: '500' }}>Calificación Final</td>
              <td style={{ padding: '16px 12px' }}>75 pts</td>
              <td style={{ padding: '16px 12px' }}><span className="badge-kimball-na" style={{ color: '#a0aec0', fontSize: '12px' }}>N/A</span></td>
              <td style={{ padding: '16px 12px' }}>75.00 / 100</td>
              <td style={{ padding: '16px 12px', color: '#38a169', fontWeight: '600' }}>0.97</td>
              <td style={{ padding: '16px 12px', color: '#38a169', fontWeight: '600' }}>100%</td>
              <td style={{ padding: '16px 12px', color: '#4a5568', fontSize: '13px' }}>Validado [0-100]</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="card-mist" style={{ backgroundColor: '#f2f2f3', padding: '24px', borderRadius: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: '600', color: '#17191c' }}>Análisis de Transparencia</h4>
          <p style={{ margin: 0, fontSize: '13px', color: '#4a5568', maxWidth: '600px', lineHeight: '1.5' }}>
            El modelo RapidFuzz determinó una coincidencia del 88% en el Nombre Completo debido a variaciones en el orden y omisión del segundo apellido. Se requiere confirmación humana para el CI dudoso antes de consolidar el registro maestro.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn-pill-ghost" style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: 'transparent', color: '#e53e3e', borderRadius: '9999px', padding: '10px 20px', border: '1px solid #fc8181', cursor: 'pointer', fontWeight: '500' }}>
            <Unlink size={16} /> Desvincular Fuentes
          </button>
          <button 
            className="btn-pill-dark" 
            onClick={() => setIsBetoOpen(true)}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: '#17191c', color: '#fff', borderRadius: '9999px', padding: '10px 20px', border: 'none', cursor: 'pointer', fontWeight: '500' }}
          >
            <Terminal size={16} /> Ver Telemetría en Vivo
          </button>
        </div>
      </div>

      <BetoDrawer isOpen={isBetoOpen} onClose={() => setIsBetoOpen(false)} />
    </div>
  );
}
