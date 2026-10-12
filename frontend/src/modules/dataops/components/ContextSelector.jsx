import React from 'react';
import { BookOpen, UserCheck, FileText, GraduationCap, DollarSign, Layers } from 'lucide-react';

export const DOCUMENT_CONTEXTS = [
  {
    id: 'ALL',
    label: 'Todas las Fuentes Ingeridas',
    category: 'Consolidado',
    description: 'Visualizar todos los archivos y fuentes documentales cargadas en el sistema.',
    sourceTypeDefault: 'Todos los Formatos',
    icon: Layers,
    badgeColor: 'var(--color-gira-gold, #D99B26)'
  },
  {
    id: 'ACTA_NOTAS',
    label: 'Acta de Calificaciones y Notas',
    category: 'Academico',
    description: 'Hojas de cálculo de notas finales, módulos y códigos POS (XLSX, Google Sheets).',
    sourceTypeDefault: 'Acta Calificaciones (Excel)',
    icon: GraduationCap,
    badgeColor: '#1b8754'
  },
  {
    id: 'ASISTENCIA',
    label: 'Registro de Asistencia y Participación',
    category: 'Academico',
    description: 'Listas de control, ausencias y porcentajes de asistencia por sesión (CSV, XLSX).',
    sourceTypeDefault: 'Registro de Asistencia (CSV)',
    icon: UserCheck,
    badgeColor: '#0284c7'
  },
  {
    id: 'ADMISIONES',
    label: 'Formulario de Admisión e Inscripción',
    category: 'Marketing/Admisiones',
    description: 'Exportaciones de Google Forms con postulantes, CI, contactos y programa (CSV).',
    sourceTypeDefault: 'Inscripciones (Google Forms)',
    icon: FileText,
    badgeColor: '#d99b26'
  },
  {
    id: 'AULA_MOODLE',
    label: 'Reporte Evaluativo Aula Virtual',
    category: 'Plataforma Virtual',
    description: 'Libros de calificaciones y registros de actividades de Moodle (XML, CSV, XLSX).',
    sourceTypeDefault: 'Reporte de Aula Virtual (Moodle)',
    icon: BookOpen,
    badgeColor: '#8b5cf6'
  },
  {
    id: 'COBRANZAS',
    label: 'Cartera de Cobranzas y Pagos',
    category: 'Financiero',
    description: 'Cuotas pendientes, estados de cuenta y comprobantes de recaudación (Sheets).',
    sourceTypeDefault: 'Cartera de Cobranza (Sheets)',
    icon: DollarSign,
    badgeColor: '#5d2a1a'
  }
];

export default function ContextSelector({ selectedContext = 'ALL', onSelectContext, counts = {} }) {
  return (
    <div style={{ marginBottom: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <label
          style={{
            display: 'block',
            fontSize: '11px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '1px',
            color: 'var(--color-gira-gold, #D99B26)',
            fontFamily: 'var(--font-sohne, inherit)',
          }}
        >
          Selector de Contexto Documental · Filtrado Categorizado
        </label>
        {selectedContext !== 'ALL' && (
          <button
            type="button"
            onClick={() => onSelectContext && onSelectContext('ALL')}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '11.5px',
              color: 'var(--color-sienna-brown)',
              fontWeight: 600,
              cursor: 'pointer',
              textDecoration: 'underline'
            }}
          >
            Ver Todas las Fuentes ({counts.ALL || 0})
          </button>
        )}
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '10px',
        }}
      >
        {DOCUMENT_CONTEXTS.map((ctx) => {
          const isSelected = ctx.id === selectedContext;
          const Icon = ctx.icon;
          const count = counts[ctx.id] ?? 0;

          return (
            <div
              key={ctx.id}
              onClick={() => onSelectContext(isSelected && ctx.id !== 'ALL' ? 'ALL' : ctx.id)}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                padding: '12px 14px',
                borderRadius: '16px',
                border: isSelected
                  ? '2px solid var(--color-gira-gold, #D99B26)'
                  : '1px solid var(--color-border, #ececec)',
                backgroundColor: isSelected
                  ? 'var(--color-paper-white, #ffffff)'
                  : 'var(--color-mist-gray, #f2f2f3)',
                cursor: 'pointer',
                transition: 'all 0.18s ease',
                boxShadow: isSelected ? '0 4px 14px rgba(217, 155, 38, 0.15)' : 'none',
              }}
            >
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: isSelected ? 'rgba(217, 155, 38, 0.15)' : 'rgba(0,0,0,0.05)',
                  color: isSelected ? 'var(--color-gira-gold, #D99B26)' : 'var(--color-slate-gray, #777b86)',
                  flexShrink: 0,
                }}
              >
                <Icon size={17} />
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '4px', marginBottom: '3px' }}>
                  <div
                    style={{
                      fontSize: '12px',
                      fontWeight: isSelected ? 700 : 600,
                      color: isSelected ? 'var(--color-ink-black, #17191c)' : 'inherit',
                      lineHeight: 1.25,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                    title={ctx.label}
                  >
                    {ctx.label}
                  </div>
                  <span
                    style={{
                      fontSize: '10.5px',
                      fontWeight: 700,
                      padding: '1px 6px',
                      borderRadius: '9999px',
                      backgroundColor: isSelected ? 'var(--color-gira-gold)' : 'var(--color-border)',
                      color: isSelected ? '#0C1E33' : 'var(--color-slate-gray)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {count}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: '11px',
                    color: 'var(--color-slate-gray, #777b86)',
                    lineHeight: 1.3,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {ctx.description}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
