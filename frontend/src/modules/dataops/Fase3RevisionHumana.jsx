import React, { useState, useEffect } from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle, Terminal, Unlink, Activity } from 'lucide-react';
import BetoDrawer from './BetoDrawer';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import PageHeader from '../../components/shared/PageHeader';
import { sileoToast } from '../../services/sileoToast';

export default function Fase3RevisionHumana() {
  const [isBetoOpen, setIsBetoOpen] = useState(false);

  useEffect(() => {
    sileoToast.warning({
      title: 'Revisión Humana Requerida',
      description: 'Disparador GIRA-50: Cédula de Identidad con sufijo dudoso detectada.'
    });
  }, []);

  return (
    <div className="module-container" style={{ padding: '8px 0', maxWidth: '1200px', margin: '0 auto' }}>
      <PageHeader
        category="DataOps · Revisión de Integridad"
        title="Ensamblaje de Registro y Doble Confianza"
        subtitle="Verificación y reconciliación cruzada de registros crudos multi-fuente mediante NER BETO y similitud difusa."
      />

      {/* ── Critical Alert Banner ── */}
      <div className="floating-artifact" style={{ borderRadius: 'var(--radius-cards)', padding: '24px', marginBottom: '32px', borderLeft: '4px solid var(--color-alert-red)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
              <span style={{ backgroundColor: 'var(--color-alert-red)', color: '#ffffff', padding: '4px 8px', borderRadius: '4px', fontSize: '11.5px', fontWeight: '700', display: 'inline-flex', alignItems: 'center', gap: '4px', letterSpacing: '0.5px' }}>
                <AlertTriangle size={13} /> REQUIERE REVISIÓN
              </span>
              <span style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--color-ink-black)' }}>Disparador de Validación de Matrícula y CI Activado</span>
            </div>
            <div style={{ fontSize: '13.5px', color: 'var(--color-alert-red)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              ▲ Campo Crítico Dudoso: Cédula de Identidad (CI) incompleta
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', marginBottom: '2px', textTransform: 'uppercase' }}>Score General</div>
            <div className="serif-display" style={{ fontSize: '32px', fontWeight: 600, color: 'var(--color-ink-black)', lineHeight: '1' }}>87%</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px', marginTop: '20px', paddingTop: '20px', borderTop: '1px solid var(--color-border)' }}>
          <div>
            <div style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', marginBottom: '6px', fontWeight: 600, textTransform: 'uppercase' }}>Confianza NER BETO</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-alert-green)' }}>94.0%</span>
              <span style={{ color: 'var(--color-alert-green)', fontSize: '12.5px', display: 'inline-flex', alignItems: 'center', gap: '4px', fontWeight: 500 }}><CheckCircle size={14}/> Óptimo</span>
            </div>
          </div>
          <div>
            <div style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', marginBottom: '6px', fontWeight: 600, textTransform: 'uppercase' }}>Vinculación Cross-Source RapidFuzz</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-alert-amber)' }}>88.0%</span>
              <span style={{ color: 'var(--color-alert-amber)', fontSize: '12.5px', display: 'inline-flex', alignItems: 'center', gap: '4px', fontWeight: 500 }}><Activity size={14}/> Homonimia</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Dimensional Attributes Table ── */}
      <ResponsiveTable style={{ marginBottom: '32px' }}>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Atributo Dimensional</th>
              <th>Fuente 1: Acta Excel</th>
              <th>Fuente 2: Google Forms</th>
              <th>Fuente 3: Moodle</th>
              <th>NER BETO</th>
              <th>RapidFuzz Cross</th>
              <th>Estado de Campo</th>
            </tr>
          </thead>
          <tbody>
            <tr className="row-critical-alert">
              <td style={{ fontWeight: 600, color: 'var(--color-alert-red)' }}>CI Estudiante</td>
              <td style={{ fontFamily: 'var(--font-mono)' }}>4892019 LP?</td>
              <td><span className="badge-kimball-na">N/A</span></td>
              <td><span className="badge-kimball-na">N/A</span></td>
              <td style={{ color: 'var(--color-alert-amber)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>0.54</td>
              <td style={{ color: 'var(--color-ash-gray)', fontFamily: 'var(--font-mono)' }}>-</td>
              <td>
                <span className="tag-critical-field">Dudoso (Sufijo ?)</span>
              </td>
            </tr>
            <tr>
              <td style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>Nombre Completo</td>
              <td>Daza Adriano</td>
              <td>Adriano Daza Meneses</td>
              <td>Daza M., Adriano</td>
              <td style={{ color: 'var(--color-alert-green)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>0.94</td>
              <td style={{ color: 'var(--color-alert-amber)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>88%</td>
              <td style={{ color: 'var(--color-slate-gray)' }}>Conciliado</td>
            </tr>
            <tr>
              <td style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>Módulo</td>
              <td>Modulo 3</td>
              <td><span className="badge-kimball-na">N/A</span></td>
              <td>MOD-302: Gestión de Datos</td>
              <td style={{ color: 'var(--color-alert-green)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>0.88</td>
              <td style={{ color: 'var(--color-alert-green)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>92%</td>
              <td style={{ color: 'var(--color-slate-gray)' }}>Homologado</td>
            </tr>
            <tr>
              <td style={{ fontWeight: 600, color: 'var(--color-ink-black)' }}>Calificación Final</td>
              <td>75 pts</td>
              <td><span className="badge-kimball-na">N/A</span></td>
              <td>75.00 / 100</td>
              <td style={{ color: 'var(--color-alert-green)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>0.97</td>
              <td style={{ color: 'var(--color-alert-green)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>100%</td>
              <td style={{ color: 'var(--color-slate-gray)' }}>Validado [0-100]</td>
            </tr>
          </tbody>
        </table>
      </ResponsiveTable>

      {/* ── Action Box ── */}
      <div className="card-mist" style={{ padding: '24px', borderRadius: 'var(--radius-cards)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h4 style={{ margin: '0 0 6px 0', fontSize: '15px', fontWeight: 600, color: 'var(--color-ink-black)' }}>Análisis de Transparencia</h4>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-slate-gray)', maxWidth: '620px', lineHeight: 1.5 }}>
            El modelo RapidFuzz determinó una coincidencia del 88% en el Nombre Completo debido a variaciones en el orden y omisión del segundo apellido. Se requiere confirmación humana para el CI dudoso antes de consolidar el registro maestro.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button type="button" className="btn-pill-ghost" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--color-alert-red)', borderColor: 'rgba(217, 56, 58, 0.4)', padding: '10px 20px', fontSize: '13px' }}>
            <Unlink size={15} /> Desvincular Fuentes
          </button>
          <button 
            type="button"
            className="btn-pill-dark" 
            onClick={() => setIsBetoOpen(true)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 20px', fontSize: '13px' }}
          >
            <Terminal size={15} /> Ver Telemetría en Vivo
          </button>
        </div>
      </div>

      <BetoDrawer isOpen={isBetoOpen} onClose={() => setIsBetoOpen(false)} />
    </div>
  );
}
