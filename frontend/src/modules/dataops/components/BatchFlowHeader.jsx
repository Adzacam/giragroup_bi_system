import React from 'react';
import { Layers, FileSpreadsheet, Scale, Building2, Shield, Calendar, BookOpen, Sparkles } from 'lucide-react';
import { useAuth } from '../../../context/AuthContext';
import { useCatalogProgramCount } from '../../../hooks/useCatalogProgramCount';

export default function BatchFlowHeader({ batchContext, currentStep = 1, onSelectBatch }) {
  const { role, user } = useAuth();
  const totalProgramas = useCatalogProgramCount();
  const activeRole = role || user?.role || 'AUDITOR_CALIDAD';

  const renderContextualBadges = () => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '5px',
          padding: '4px 10px',
          borderRadius: '999px',
          fontSize: '11.5px',
          fontWeight: 700,
          backgroundColor: 'var(--dataops-gold-bg, rgba(217, 155, 38, 0.12))',
          color: 'var(--color-gira-gold, #D99B26)',
          border: '1px solid var(--dataops-gold-border, rgba(217, 155, 38, 0.35))',
        }}
      >
        <Calendar size={12} /> Fechas: Reconocimiento Automático
      </span>
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '5px',
          padding: '4px 10px',
          borderRadius: '999px',
          fontSize: '11.5px',
          fontWeight: 700,
          backgroundColor: 'rgba(12, 30, 51, 0.08)',
          color: 'var(--color-ink-black)',
          border: '1px solid rgba(12, 30, 51, 0.22)',
        }}
      >
        <BookOpen size={12} /> Catálogo Maestro: {totalProgramas ?? '—'} Prog. Activos
      </span>
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '5px',
          padding: '4px 10px',
          borderRadius: '999px',
          fontSize: '11.5px',
          fontWeight: 700,
          backgroundColor: 'var(--color-mist-gray)',
          color: 'var(--color-ink-black)',
          border: '1px solid var(--color-border)',
        }}
      >
        <Shield size={12} color="#1B8754" /> Rol: {activeRole === 'AUDITOR_CALIDAD' ? 'Coordinador ACRA' : activeRole}
      </span>
    </div>
  );

  if (!batchContext) {
    return (
      <div className="floating-artifact" style={{
        padding: '16px 24px',
        marginBottom: '20px',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '36px', height: '36px', borderRadius: '10px',
            backgroundColor: 'rgba(217, 155, 38, 0.12)', color: 'var(--color-gira-gold, #D99B26)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Layers size={18} />
          </div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--color-ink-black)', fontFamily: 'var(--font-sohne)' }}>
              Flujo de Ingesta & Procesamiento de Lote
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
              Carga multifuente (1 a N archivos .xlsx, .csv) y aplanamiento asimétrico
            </div>
          </div>
        </div>

        {renderContextualBadges()}
      </div>
    );
  }

  const {
    id_lote,
    id_documento,
    nombre_archivo = 'Lote sin nombre',
    institucion = 'GiraGroup Posgrado',
    tipo_fuente = 'GSHEETS_ACTA_NOTAS',
    escala_label = 'No aplica',
    periodo = 'Por detectar',
    total_archivos = 1,
    total_registros = 0,
    pendientes_revision = 0,
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
      borderLeft: '4px solid var(--color-gira-gold, #D99B26)'
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
              {id_lote ? `Lote #${id_lote}: ` : 'Lote: '}{nombre_archivo}
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
            <span style={{ color: 'var(--color-border)' }}>·</span>
            <span style={{
              fontSize: '12px',
              padding: '2px 8px',
              borderRadius: '6px',
              backgroundColor: 'var(--dataops-info-bg)',
              color: 'var(--dataops-info-text)',
              border: '1px solid var(--dataops-info-border)',
              fontWeight: '600',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <Calendar size={12} /> Fechas: {periodo}
            </span>
          </div>

          <div style={{ fontSize: '12px', color: 'var(--color-ash-gray)', marginTop: '4px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <span>Lote ID: <strong>#{id_lote || id_documento}</strong></span>
            <span>Archivos en lote: <strong>{total_archivos}</strong></span>
            <span>Registros: <strong>{total_registros}</strong></span>
            {pendientes_revision > 0 && (
              <span style={{ color: 'var(--dataops-warning-text)', fontWeight: '600' }}>
                En revisión: <strong>{pendientes_revision}</strong>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Badges de Catálogo, Fechas y Rol */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        {renderContextualBadges()}

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
    </div>
  );
}
