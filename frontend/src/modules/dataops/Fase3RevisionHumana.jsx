import React, { useState, useEffect } from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle, Terminal, Unlink, Activity, CheckCircle2, RotateCcw } from 'lucide-react';
import BetoDrawer from './BetoDrawer';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import PageHeader from '../../components/shared/PageHeader';
import { sileoToast } from '../../services/sileoToast';

export default function Fase3RevisionHumana() {
  const [isBetoOpen, setIsBetoOpen] = useState(false);
  const [resolutionStatus, setResolutionStatus] = useState('pending'); // 'pending' | 'resolved' | 'unlinked'
  const [ciValue, setCiValue] = useState('4892019 LP');

  useEffect(() => {
    if (resolutionStatus === 'pending') {
      sileoToast.warning({
        title: 'Revisión Humana Requerida',
        description: 'Disparador GIRA-50: Cédula de Identidad con sufijo dudoso detectada.'
      });
    }
  }, [resolutionStatus]);

  const handleApprove = () => {
    setResolutionStatus('resolved');
    sileoToast.success({
      title: 'Registro Reconciliado y Aprobado',
      description: `CI consolidada como "${ciValue}" y vinculada al registro maestro en Data Warehouse.`
    });
  };

  const handleUnlink = () => {
    setResolutionStatus('unlinked');
    sileoToast.info({
      title: 'Fuentes Desvinculadas',
      description: 'El registro se segregó en dos entidades independientes para reprocesamiento.'
    });
  };

  const handleReset = () => {
    setResolutionStatus('pending');
    sileoToast.info({
      title: 'Estado Restablecido',
      description: 'El caso volvió al estado pendiente de revisión humana.'
    });
  };

  const generalScore = resolutionStatus === 'resolved' ? 98 : resolutionStatus === 'unlinked' ? 65 : 87;

  return (
    <div className="module-container" style={{ padding: '8px 0', maxWidth: '1200px', margin: '0 auto' }}>
      <PageHeader
        category="Fase 3: Revisión de Integridad"
        title="Ensamblaje de Registro y Doble Confianza"
        subtitle="Verificación y reconciliación cruzada de registros crudos multi-fuente mediante NER BETO y similitud difusa."
      />

      {/* ── Critical Alert / Resolution Banner ── */}
      <div 
        className="floating-artifact" 
        style={{ 
          borderRadius: 'var(--radius-cards)', 
          padding: '24px', 
          marginBottom: '32px', 
          borderLeft: resolutionStatus === 'resolved' 
            ? '4px solid var(--color-alert-green)' 
            : resolutionStatus === 'unlinked'
            ? '4px solid var(--color-slate-gray)'
            : '4px solid var(--color-alert-red)',
          transition: 'all 0.3s ease'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
              {resolutionStatus === 'resolved' ? (
                <span style={{ backgroundColor: 'var(--color-alert-green)', color: '#ffffff', padding: '4px 10px', borderRadius: '4px', fontSize: '11.5px', fontWeight: '700', display: 'inline-flex', alignItems: 'center', gap: '5px', letterSpacing: '0.5px' }}>
                  <CheckCircle2 size={13} /> RECONCILIADO Y APROBADO
                </span>
              ) : resolutionStatus === 'unlinked' ? (
                <span style={{ backgroundColor: 'var(--color-slate-gray)', color: '#ffffff', padding: '4px 10px', borderRadius: '4px', fontSize: '11.5px', fontWeight: '700', display: 'inline-flex', alignItems: 'center', gap: '5px', letterSpacing: '0.5px' }}>
                  <Unlink size={13} /> FUENTES DESVINCULADAS
                </span>
              ) : (
                <span style={{ backgroundColor: 'var(--color-alert-red)', color: '#ffffff', padding: '4px 8px', borderRadius: '4px', fontSize: '11.5px', fontWeight: '700', display: 'inline-flex', alignItems: 'center', gap: '4px', letterSpacing: '0.5px' }}>
                  <AlertTriangle size={13} /> REQUIERE REVISIÓN
                </span>
              )}
              <span style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
                {resolutionStatus === 'resolved' 
                  ? 'Entidad canónica confirmada por Auditoría de Calidad' 
                  : resolutionStatus === 'unlinked'
                  ? 'Segregación confirmada: Entidades aisladas'
                  : 'Disparador de Validación de Matrícula y CI Activado'}
              </span>
            </div>
            <div style={{ 
              fontSize: '13.5px', 
              color: resolutionStatus === 'resolved' ? 'var(--color-alert-green)' : resolutionStatus === 'unlinked' ? 'var(--color-slate-gray)' : 'var(--color-alert-red)', 
              fontWeight: 600, 
              display: 'flex', 
              alignItems: 'center', 
              gap: '6px' 
            }}>
              {resolutionStatus === 'resolved' ? (
                <span>✔ Cédula de Identidad normalizada exitosamente como: <strong>{ciValue}</strong></span>
              ) : resolutionStatus === 'unlinked' ? (
                <span>✖ Fuentes segregadas. Requieren verificación independiente en secretaría.</span>
              ) : (
                <span>▲ Campo Crítico Dudoso: Cédula de Identidad (CI) incompleta ("4892019 LP?")</span>
              )}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', marginBottom: '2px', textTransform: 'uppercase' }}>Score General</div>
            <div className="serif-display" style={{ 
              fontSize: '32px', 
              fontWeight: 600, 
              color: resolutionStatus === 'resolved' ? 'var(--color-alert-green)' : 'var(--color-ink-black)', 
              lineHeight: '1' 
            }}>
              {generalScore}%
            </div>
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
              <span style={{ fontSize: '24px', fontWeight: 700, color: resolutionStatus === 'resolved' ? 'var(--color-alert-green)' : 'var(--color-alert-amber)' }}>
                {resolutionStatus === 'resolved' ? '98.5%' : '88.0%'}
              </span>
              <span style={{ color: resolutionStatus === 'resolved' ? 'var(--color-alert-green)' : 'var(--color-alert-amber)', fontSize: '12.5px', display: 'inline-flex', alignItems: 'center', gap: '4px', fontWeight: 500 }}>
                <Activity size={14}/> {resolutionStatus === 'resolved' ? 'Validado' : 'Homonimia'}
              </span>
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
            <tr className={resolutionStatus === 'pending' ? "row-critical-alert" : ""}>
              <td style={{ fontWeight: 600, color: resolutionStatus === 'resolved' ? 'var(--color-alert-green)' : 'var(--color-alert-red)' }}>
                CI Estudiante
              </td>
              <td style={{ fontFamily: 'var(--font-mono)' }}>
                {resolutionStatus === 'resolved' ? ciValue : '4892019 LP?'}
              </td>
              <td><span className="badge-kimball-na">N/A</span></td>
              <td><span className="badge-kimball-na">N/A</span></td>
              <td style={{ color: resolutionStatus === 'resolved' ? 'var(--color-alert-green)' : 'var(--color-alert-amber)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                {resolutionStatus === 'resolved' ? '0.98' : '0.54'}
              </td>
              <td style={{ color: 'var(--color-ash-gray)', fontFamily: 'var(--font-mono)' }}>-</td>
              <td>
                {resolutionStatus === 'resolved' ? (
                  <span style={{ color: 'var(--color-alert-green)', fontWeight: 600, fontSize: '12px' }}>✔ Homologado ({ciValue})</span>
                ) : resolutionStatus === 'unlinked' ? (
                  <span style={{ color: 'var(--color-slate-gray)', fontWeight: 600, fontSize: '12px' }}>Desvinculado</span>
                ) : (
                  <span className="tag-critical-field">Dudoso (Sufijo ?)</span>
                )}
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
          <h4 style={{ margin: '0 0 6px 0', fontSize: '15px', fontWeight: 600, color: 'var(--color-ink-black)' }}>Análisis de Transparencia &amp; Resolución</h4>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-slate-gray)', maxWidth: '620px', lineHeight: 1.5 }}>
            {resolutionStatus === 'resolved' 
              ? 'El caso ha sido reconciliado satisfactoriamente. Los datos validados fueron confirmados para persistencia dimensional.' 
              : resolutionStatus === 'unlinked'
              ? 'Las fuentes fueron segregadas. Cada registro se gestionará como entidad independiente.'
              : 'El modelo RapidFuzz determinó una coincidencia del 88% en el Nombre Completo. Se requiere confirmación humana para el CI dudoso antes de consolidar el registro maestro.'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          {resolutionStatus === 'pending' ? (
            <>
              <button 
                type="button" 
                className="btn-pill-ghost" 
                onClick={handleUnlink}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--color-alert-red)', borderColor: 'rgba(217, 56, 58, 0.4)', padding: '10px 18px', fontSize: '13px' }}
              >
                <Unlink size={15} /> Desvincular Fuentes
              </button>
              <button 
                type="button" 
                className="btn-pill-dark" 
                onClick={handleApprove}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 22px', fontSize: '13px', backgroundColor: 'var(--color-alert-green)' }}
              >
                <CheckCircle2 size={16} /> Aprobar y Consolidar Registro
              </button>
            </>
          ) : (
            <button 
              type="button" 
              className="btn-pill-ghost" 
              onClick={handleReset}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '10px 18px', fontSize: '13px' }}
            >
              <RotateCcw size={15} /> Reabrir Caso para Revisión
            </button>
          )}

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
