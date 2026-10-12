import React, { useState } from 'react';
import {
  Cpu, Database, Sparkles, CheckCircle2, AlertTriangle, ArrowRight,
  RefreshCw, Layers, ShieldCheck, Tag, Link2
} from 'lucide-react';
import { sileoToast } from '../../../services/sileoToast';

export default function BetoCatalogIntegrationViewer() {
  const [selectedSampleIndex, setSelectedSampleIndex] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const samples = [
    {
      id: 'SAMPLE_ACTA_01',
      title: 'Acta de Calificaciones (Excel/Sheets)',
      sourceType: 'Acta POS 2026 Modulo 3',
      rawText: 'ESTUDIANTE: Adriano Daza Meneses | CI: 4892019 LP | MODULO: Modulo 3 Gestion y Gobernanza de Datos | DOCENTE: Dr. Carlos Gomez Murillo | NOTA_FINAL: 88 pts | CONDICION: APROBADO',
      entities: [
        {
          text: 'Adriano Daza Meneses',
          label: 'ESTUDIANTE',
          tag: 'B-ESTUDIANTE',
          confidence: 0.948,
          catalogMatch: { table: 'Catálogo de Estudiantes', id: 'EST-402', canonical: 'Adriano Daza Meneses', ci: '4892019 LP' },
          status: 'MATCH_EXACTO'
        },
        {
          text: 'Dr. Carlos Gomez Murillo',
          label: 'DOCENTE',
          tag: 'B-DOCENTE',
          confidence: 0.892,
          catalogMatch: { table: 'Plantel Docente', id: 'DOC-109', canonical: 'Dr. Carlos A. Gómez Murillo', area: 'Ciencia de Datos' },
          status: 'MATCH_CANONICO'
        },
        {
          text: 'Modulo 3 Gestion y Gobernanza de Datos',
          label: 'MODULO',
          tag: 'B-MODULO',
          confidence: 0.915,
          catalogMatch: { table: 'Módulos y Programas', id: 'MOD-302', canonical: 'MOD-302: Gestión y Gobernanza de Datos', creditos: 4 },
          status: 'MATCH_CANONICO'
        },
        {
          text: '88 pts',
          label: 'CALIFICACION',
          tag: 'B-VALOR',
          confidence: 0.990,
          catalogMatch: { valor: 88.0, rango: '0-100', estado: 'Aprobado' },
          status: 'VALIDADO'
        }
      ],
      dwFact: {
        id_estudiante: 402,
        id_modulo: 302,
        id_docente: 109,
        nota_final: 88.00,
        estado: 'APROBADO',
        confianza_global: 0.936,
        requiere_revision: false
      }
    },
    {
      id: 'SAMPLE_FORMS_02',
      title: 'Formulario de Admisión (Google Forms CSV)',
      sourceType: 'Inscripciones Postgrado 2026',
      rawText: 'POSTULANTE: Carlos Alberto Gomez Meneses | CI: 4892019 LP? | PROGRAMA: Maestria Big Data e Inteligencia Artificial | FECHA_REGISTRO: 2026-03-14 | TELEFONO: 77291044',
      entities: [
        {
          text: 'Carlos Alberto Gomez Meneses',
          label: 'ESTUDIANTE',
          tag: 'B-ESTUDIANTE',
          confidence: 0.912,
          catalogMatch: { table: 'Catálogo de Estudiantes', id: 'EST-514', canonical: 'Carlos A. Gómez Meneses', ci: '4892019 LP' },
          status: 'HOMONIMIA_DETECTADA'
        },
        {
          text: '4892019 LP?',
          label: 'DOCUMENTO_CI',
          tag: 'B-IDENTIDAD',
          confidence: 0.640,
          catalogMatch: { table: 'Catálogo de Estudiantes', id: 'DUDOSO', canonical: 'CI con sufijo de interrogación (?)' },
          status: 'REQUIERE_REVISION'
        },
        {
          text: 'Maestria Big Data e Inteligencia Artificial',
          label: 'MODULO / PROGRAMA',
          tag: 'B-PROGRAMA',
          confidence: 0.942,
          catalogMatch: { table: 'Módulos y Programas', id: 'POS-2026-B', canonical: 'Maestría en Big Data & Business Analytics', creditos: 60 },
          status: 'MATCH_CANONICO'
        }
      ],
      dwFact: {
        id_estudiante: 514,
        id_modulo: 2026,
        id_docente: null,
        nota_final: null,
        estado: 'POSTULANTE_PENDIENTE',
        confianza_global: 0.831,
        requiere_revision: true
      }
    },
    {
      id: 'SAMPLE_MOODLE_03',
      title: 'Reporte Aula Virtual (Moodle XML/CSV)',
      sourceType: 'Libro de Calificaciones Aula Virtual',
      rawText: 'USER_FULLNAME: Maria Elena Quispe Ramos | COURSE: MOD-302-GIRA-2026 | ITEM: Evaluacion Final | GRADE: 94.50 / 100 | STATUS: COMPLETED',
      entities: [
        {
          text: 'Maria Elena Quispe Ramos',
          label: 'ESTUDIANTE',
          tag: 'B-ESTUDIANTE',
          confidence: 0.965,
          catalogMatch: { table: 'Catálogo de Estudiantes', id: 'EST-389', canonical: 'María Elena Quispe Ramos', ci: '6192841 LP' },
          status: 'MATCH_EXACTO'
        },
        {
          text: 'MOD-302-GIRA-2026',
          label: 'MODULO',
          tag: 'B-MODULO',
          confidence: 0.958,
          catalogMatch: { table: 'Módulos y Programas', id: 'MOD-302', canonical: 'MOD-302: Gestión y Gobernanza de Datos', creditos: 4 },
          status: 'MATCH_CANONICO'
        },
        {
          text: '94.50 / 100',
          label: 'CALIFICACION',
          tag: 'B-VALOR',
          confidence: 0.995,
          catalogMatch: { valor: 94.5, rango: '0-100', estado: 'Excelente' },
          status: 'VALIDADO'
        }
      ],
      dwFact: {
        id_estudiante: 389,
        id_modulo: 302,
        id_docente: 109,
        nota_final: 94.50,
        estado: 'APROBADO_EXCELENCIA',
        confianza_global: 0.972,
        requiere_revision: false
      }
    },
    {
      id: 'SAMPLE_NUEVO_PERFIL_04',
      title: 'Planilla Externa (Nuevo Perfil No Catalogado)',
      sourceType: 'Planificacion y Ejecucion Academica',
      rawText: '51 | 2025-08-23 | DIPLOMADO | Escuela de Tecnologia | Pedro Condo | MODULO: Arquitectura y Analitica de Datos | NOTA_FINAL: 82 pts',
      entities: [
        {
          text: 'Pedro Condo',
          label: 'ESTUDIANTE',
          tag: 'B-ESTUDIANTE',
          confidence: 0.920,
          catalogMatch: { table: 'Catálogo de Estudiantes', id: 'ALTA_DIMENSIONAL', canonical: 'Alta automática en Catálogo de Estudiantes (ID generado)' },
          status: 'NUEVO_PERFIL'
        },
        {
          text: 'Arquitectura y Analitica de Datos',
          label: 'MODULO',
          tag: 'B-MODULO',
          confidence: 0.885,
          catalogMatch: { table: 'Módulos y Programas', id: 'MOD-AUTO', canonical: 'Alta o resolución en Módulos y Programas', creditos: 4 },
          status: 'MATCH_CANONICO'
        },
        {
          text: '82 pts',
          label: 'CALIFICACION',
          tag: 'B-VALOR',
          confidence: 0.985,
          catalogMatch: { valor: 82.0, rango: '0-100', estado: 'Aprobado' },
          status: 'VALIDADO'
        }
      ],
      dwFact: {
        id_estudiante: 'AUTO_ID_EST',
        id_modulo: 'AUTO_ID_MOD',
        id_docente: null,
        nota_final: 82.00,
        estado: 'APROBADO',
        confianza_global: 0.930,
        requiere_revision: false
      }
    }
  ];

  const currentSample = samples[selectedSampleIndex];

  const handleRunAnalysis = () => {
    setIsAnalyzing(true);
    setTimeout(() => {
      setIsAnalyzing(false);
      sileoToast.success({
        title: 'Análisis Semántico BETO Concluido',
        description: `Entidades extraídas y cruzadas contra el catálogo dimensional en 68ms (Score: ${(currentSample.dwFact.confianza_global * 100).toFixed(1)}%).`
      });
    }, 700);
  };

  return (
    <div
      className="floating-artifact"
      style={{
        padding: '24px',
        borderRadius: 'var(--radius-cards)',
        border: '1px solid var(--color-border)',
        backgroundColor: 'var(--color-paper-white)',
        marginBottom: '24px',
        boxShadow: 'var(--shadow-subtle)',
      }}
    >
      {/* Encabezado del visor */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '28px',
                height: '28px',
                borderRadius: '8px',
                backgroundColor: 'rgba(217, 155, 38, 0.15)',
                color: 'var(--color-gira-gold, #D99B26)',
              }}
            >
              <Cpu size={16} />
            </span>
            <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-gira-gold)', fontWeight: 700 }}>
              Análisis Semántico BETO NER & Resolución con Catálogos Maestros
            </span>
          </div>
          <h3 className="serif-heading" style={{ fontSize: '19px', margin: '4px 0 2px 0', color: 'var(--color-ink-black)' }}>
            Extracción de Entidades & Vinculación a Data Warehouse
          </h3>
          <p style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)', margin: 0, maxWidth: '820px' }}>
            BETO v2.4 procesa el texto plano canónico, clasifica entidades mediante Named Entity Recognition y consulta los catálogos canónicos de PostgreSQL (<strong style={{ color: 'var(--color-sienna-brown)' }}>Estudiantes</strong>, <strong style={{ color: 'var(--color-sienna-brown)' }}>Módulos y Programas</strong>, <strong style={{ color: 'var(--color-sienna-brown)' }}>Plantel Docente</strong>) para resolver claves foráneas antes de insertar en <strong style={{ color: 'var(--color-sienna-brown)' }}>Rendimiento Académico</strong>.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            onClick={handleRunAnalysis}
            disabled={isAnalyzing}
            className="btn-pill-dark"
            style={{
              padding: '7px 16px',
              fontSize: '12.5px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'var(--color-ink-black)',
            }}
          >
            <Sparkles size={14} className={isAnalyzing ? 'spin' : ''} />
            <span>{isAnalyzing ? 'Analizando BETO...' : 'Ejecutar Inferencia BETO'}</span>
          </button>
        </div>
      </div>

      {/* Selector de Muestra de Texto Plano */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '18px', overflowX: 'auto', paddingBottom: '4px' }}>
        {samples.map((s, idx) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setSelectedSampleIndex(idx)}
            style={{
              padding: '6px 14px',
              borderRadius: '9999px',
              border: selectedSampleIndex === idx ? '2px solid var(--color-gira-gold)' : '1px solid var(--color-border)',
              backgroundColor: selectedSampleIndex === idx ? 'rgba(217, 155, 38, 0.08)' : 'var(--color-fog-white)',
              color: selectedSampleIndex === idx ? 'var(--color-ink-black)' : 'var(--color-slate-gray)',
              fontSize: '12px',
              fontWeight: selectedSampleIndex === idx ? 700 : 500,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.15s ease',
            }}
          >
            {s.title}
          </button>
        ))}
      </div>

      {/* Grid del Flujo Semántico (Paso 1 -> Paso 2 -> Paso 3) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '16px',
        }}
      >
        {/* PASO A: Entrada en Texto Plano */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--color-fog-white)',
            borderRadius: '16px',
            border: '1px solid var(--color-border)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '11px', textTransform: 'uppercase', fontWeight: 700, color: 'var(--color-slate-gray)' }}>
              1. Entrada en Texto Plano Canónico
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', backgroundColor: 'var(--color-mist-gray)', fontFamily: 'var(--font-mono)' }}>
              Registros de Ingesta
            </span>
          </div>

          <div
            style={{
              backgroundColor: 'var(--color-paper-white)',
              padding: '12px 14px',
              borderRadius: '12px',
              border: '1px solid var(--color-border)',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              color: 'var(--color-ink-black)',
              lineHeight: 1.6,
              wordBreak: 'break-word',
            }}
          >
            {currentSample.rawText}
          </div>

          <div style={{ marginTop: '10px', fontSize: '11px', color: 'var(--color-slate-gray)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle2 size={12} color="#1b8754" />
            <span>Formato serializado bajo contrato unificado del pipeline</span>
          </div>
        </div>

        {/* PASO B: Inferencia BETO NER & Cruzado con Catálogos */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--color-fog-white)',
            borderRadius: '16px',
            border: '1px solid var(--color-border)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '11px', textTransform: 'uppercase', fontWeight: 700, color: 'var(--color-gira-gold)' }}>
              2. Extracción NER & Cruce con Catálogo
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', backgroundColor: 'rgba(217, 155, 38, 0.15)', color: 'var(--color-sienna-brown)', fontWeight: 600 }}>
              BETO v2.4 + RapidFuzz
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {currentSample.entities.map((ent, i) => {
              const isAlert = ent.status === 'REQUIERE_REVISION' || ent.confidence < 0.85;

              return (
                <div
                  key={i}
                  style={{
                    backgroundColor: 'var(--color-paper-white)',
                    padding: '8px 12px',
                    borderRadius: '10px',
                    border: isAlert ? '1px solid rgba(217, 56, 58, 0.35)' : '1px solid var(--color-border)',
                    borderLeft: isAlert ? '3px solid var(--color-alert-red)' : '3px solid #1b8754',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
                      "{ent.text}"
                    </span>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        padding: '1px 6px',
                        borderRadius: '4px',
                        backgroundColor: isAlert ? 'rgba(217, 56, 58, 0.12)' : 'rgba(27, 135, 84, 0.12)',
                        color: isAlert ? 'var(--color-alert-red)' : '#1b8754',
                        fontFamily: 'var(--font-mono)'
                      }}
                    >
                      {(ent.confidence * 100).toFixed(1)}% conf.
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--color-slate-gray)' }}>
                    <Tag size={10} color="var(--color-gira-gold)" />
                    <span style={{ fontWeight: 600 }}>{ent.label}</span>
                    <span>→ Catálogo:</span>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-sienna-brown)' }}>
                      {ent.catalogMatch.table || 'Valor Validado'} ({ent.catalogMatch.id || ent.catalogMatch.valor})
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* PASO C: Registro Ensamblado para DW */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--color-fog-white)',
            borderRadius: '16px',
            border: '1px solid var(--color-border)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '11px', textTransform: 'uppercase', fontWeight: 700, color: '#1b8754' }}>
              3. Inserción a Data Warehouse
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', backgroundColor: 'rgba(27, 135, 84, 0.12)', color: '#1b8754', fontWeight: 600 }}>
              Rendimiento Académico
            </span>
          </div>

          <div
            style={{
              backgroundColor: 'var(--color-paper-white)',
              padding: '12px',
              borderRadius: '12px',
              border: '1px solid var(--color-border)',
              fontSize: '11.5px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <div style={{ color: 'var(--color-slate-gray)', marginBottom: '6px' }}>-- Tupla de Hechos Consolidada:</div>
            <div style={{ color: '#2563eb' }}>REGISTRO EN RENDIMIENTO ACADÉMICO (</div>
            <div style={{ paddingLeft: '12px', color: 'var(--color-ink-black)' }}>
              id_estudiante, id_modulo, id_docente, nota_final, estado_academico, score_confianza, requiere_revision
            </div>
            <div style={{ color: '#2563eb' }}>VALORES (</div>
            <div style={{ paddingLeft: '12px', color: '#b45309' }}>
              {currentSample.dwFact.id_estudiante}, {currentSample.dwFact.id_modulo}, {currentSample.dwFact.id_docente || 'NULL'}, {currentSample.dwFact.nota_final || 'NULL'}, '{currentSample.dwFact.estado}', {currentSample.dwFact.confianza_global}, {String(currentSample.dwFact.requiere_revision).toUpperCase()}
            </div>
            <div style={{ color: '#2563eb' }}>);</div>
          </div>

          <div style={{ marginTop: '12px' }}>
            {currentSample.dwFact.requiere_revision ? (
              <div
                style={{
                  padding: '8px 12px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(217, 56, 58, 0.1)',
                  border: '1px solid rgba(217, 56, 58, 0.25)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '11.5px',
                  color: 'var(--color-alert-red)',
                  fontWeight: 600,
                }}
              >
                <AlertTriangle size={14} />
                <span>Score &lt; 0.85: Derivado a Auditoría Humana (Human-in-the-Loop)</span>
              </div>
            ) : (
              <div
                style={{
                  padding: '8px 12px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(27, 135, 84, 0.1)',
                  border: '1px solid rgba(27, 135, 84, 0.25)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '11.5px',
                  color: '#1b8754',
                  fontWeight: 600,
                }}
              >
                <ShieldCheck size={14} />
                <span>Score ≥ 0.85: Validación exitosa y confirmación en DW</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
