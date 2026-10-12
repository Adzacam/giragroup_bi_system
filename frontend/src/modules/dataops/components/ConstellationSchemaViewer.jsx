import React, { useState } from 'react';
import { Database, Table, Key, CheckCircle, ArrowRight, ShieldCheck, Sparkles, Layers } from 'lucide-react';

export default function ConstellationSchemaViewer() {
  const [selectedTable, setSelectedTable] = useState('fact_rendimiento_academico');

  const constellationTables = [
    {
      id: 'fact_rendimiento_academico',
      name: 'fact_rendimiento_academico',
      type: 'FACT (HECHO ACADÉMICO)',
      description: 'Hechos de rendimiento académico consolidados por estudiante, docente, módulo y tiempo.',
      columns: [
        { name: 'id_hecho_aca', pgType: 'SERIAL PRIMARY KEY', originField: 'Autoincrementable DW', rule: 'Surrogate Key' },
        { name: 'id_estudiante', pgType: 'INTEGER REFERENCES dim_estudiante', originField: 'DOC_IDENTIDAD / CI', rule: 'FK Lookup canónico' },
        { name: 'id_docente', pgType: 'INTEGER REFERENCES dim_docente', originField: 'DOCENTE / PROFESOR', rule: 'FK Lookup con RapidFuzz' },
        { name: 'id_modulo', pgType: 'INTEGER REFERENCES dim_modulo', originField: 'COD_MODULO / MATERIA', rule: 'FK Lookup canónico' },
        { name: 'id_tiempo', pgType: 'INTEGER REFERENCES dim_tiempo', originField: 'FECHA_EVAL / TIMESTAMP', rule: 'FK Dimensión Tiempo' },
        { name: 'id_documento', pgType: 'INTEGER REFERENCES dim_origen', originField: 'id_documento (Upload)', rule: 'Trazabilidad de auditoría' },
        { name: 'nota_final', pgType: 'NUMERIC(5, 2)', originField: 'CALIF_FINAL / TOTAL', rule: 'Cast float [0 - 100]' },
        { name: 'asistencia_pct', pgType: 'NUMERIC(5, 2)', originField: 'ASISTENCIA / ASIST_PCT', rule: 'Default 100.0 si N/A' },
        { name: 'nivel_confianza_ia', pgType: 'NUMERIC(5, 4)', originField: 'Inferencia BETO v2.4', rule: 'Score probabilístico' },
        { name: 'requiere_revision', pgType: 'BOOLEAN', originField: 'Score < 0.85 o CI dudoso', rule: 'Disparador GIRA-50' },
        { name: 'estado_academico', pgType: 'VARCHAR(50)', originField: 'ESTADO / CONDICION', rule: 'APROBADO | REPROBADO' }
      ]
    },
    {
      id: 'dim_estudiante',
      name: 'dim_estudiante',
      type: 'DIMENSION (ESTUDIANTES)',
      description: 'Catálogo canónico de estudiantes homologados entre actas, admisiones y aula virtual.',
      columns: [
        { name: 'id_estudiante', pgType: 'SERIAL PRIMARY KEY', originField: 'Surrogate Key', rule: 'ID interno DW' },
        { name: 'codigo_estudiante', pgType: 'VARCHAR(50) UNIQUE', originField: 'ID_ESTUDIANTE / NUM_ID', rule: 'Código de matrícula' },
        { name: 'nombre_completo', pgType: 'VARCHAR(200) NOT NULL', originField: 'NOMBRES Y APELLIDOS', rule: 'Normalización de mayúsculas' },
        { name: 'ci_estudiante', pgType: 'VARCHAR(30)', originField: 'DOC_IDENTIDAD / CI', rule: 'Limpieza alfanumérica' },
        { name: 'ciudad', pgType: 'VARCHAR(100)', originField: 'EXPEDIDO / SEDE', rule: 'La Paz, Cbba, SCZ' },
        { name: 'nivel_academico', pgType: 'VARCHAR(50)', originField: 'TIPO_PROGRAMA', rule: 'Pregrado | Postgrado' }
      ]
    },
    {
      id: 'dim_modulo',
      name: 'dim_modulo',
      type: 'DIMENSION (MÓDULOS & CURSOS)',
      description: 'Catálogo curricular de programas, asignaturas y módulos académicos.',
      columns: [
        { name: 'id_modulo', pgType: 'SERIAL PRIMARY KEY', originField: 'Surrogate Key', rule: 'ID interno DW' },
        { name: 'codigo_modulo', pgType: 'VARCHAR(50) UNIQUE', originField: 'COD_MODULO / SIGLA', rule: 'MOD-302, POS-101' },
        { name: 'nombre_modulo', pgType: 'VARCHAR(200) NOT NULL', originField: 'ASIGNATURA / CURSO', rule: 'Nombre curricular oficial' },
        { name: 'area', pgType: 'VARCHAR(100)', originField: 'FACULTAD / AREA', rule: 'Tecnología, Negocios, etc.' },
        { name: 'creditos', pgType: 'INTEGER DEFAULT 4', originField: 'HORAS_ACAD', rule: 'Ponderación crediticia' }
      ]
    },
    {
      id: 'staging_registros_crudos',
      name: 'staging_registros_crudos',
      type: 'STAGING (BUFFER DE INGESTA)',
      description: 'Buffer transaccional donde se asientan los registros crudos serializados antes del cargue definitivo al DW.',
      columns: [
        { name: 'id', pgType: 'SERIAL PRIMARY KEY', originField: 'ID Registro Staging', rule: 'Autoincrementable' },
        { name: 'id_documento', pgType: 'INTEGER REFERENCES dim_origen', originField: 'ID Fuente Ingerida', rule: 'CASCADE delete' },
        { name: 'categoria', pgType: 'VARCHAR(50)', originField: 'Dispatcher Class', rule: 'ACADEMICO | FINANCIERO' },
        { name: 'texto_plano', pgType: 'TEXT', originField: 'Contrato de Salida', rule: 'Registro serializado único' },
        { name: 'n_filas', pgType: 'INTEGER', originField: 'Bloque tabular', rule: 'Recuento de filas de isla' },
        { name: 'requiere_revision', pgType: 'BOOLEAN DEFAULT FALSE', originField: 'Filtro Score < 0.85', rule: 'Disparador HITL' },
        { name: 'score_confianza', pgType: 'NUMERIC(5, 4)', originField: 'Confianza BETO/RapidFuzz', rule: 'Ponderado IA' },
        { name: 'resuelto', pgType: 'BOOLEAN DEFAULT FALSE', originField: 'Auditoría Humana', rule: 'Bandera de aprobación' }
      ]
    }
  ];

  const current = constellationTables.find(t => t.id === selectedTable) || constellationTables[0];

  return (
    <div
      className="floating-artifact"
      style={{
        borderRadius: 'var(--radius-cards)',
        border: '1px solid var(--color-border)',
        padding: '24px 28px',
        backgroundColor: 'var(--color-paper-white)',
        marginBottom: '24px',
        boxShadow: 'var(--shadow-subtle)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
            <span
              style={{
                backgroundColor: 'rgba(217, 155, 38, 0.15)',
                color: 'var(--color-gira-gold, #D99B26)',
                fontSize: '10.5px',
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: '6px',
                letterSpacing: '0.4px',
                border: '1px solid rgba(217, 155, 38, 0.3)',
              }}
            >
              Sprint 2 · Tarea 6
            </span>
            <span
              style={{
                fontSize: '11px',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                color: 'var(--color-gira-gold, #D99B26)',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              <Database size={13} /> PostgreSQL 16 · Esquema Constelación Kimball
            </span>
          </div>
          <h3 className="serif-heading" style={{ fontSize: '20px', margin: '4px 0 0 0', color: 'var(--color-ink-black)' }}>
            Ajuste del Esquema Constelación según Ingesta Real
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
            Mapeo formal de los campos reales identificados en las fuentes documentales hacia las dimensiones y hechos de PostgreSQL.
          </p>
        </div>

        {/* Selector de Tabla */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {constellationTables.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setSelectedTable(t.id)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '9999px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                border: t.id === selectedTable ? '1px solid var(--color-ink-black)' : '1px solid var(--color-border)',
                backgroundColor: t.id === selectedTable ? 'var(--color-ink-black)' : 'var(--color-fog-white)',
                color: t.id === selectedTable ? 'var(--color-paper-white)' : 'var(--color-slate-gray)',
                transition: 'all 0.15s ease',
              }}
            >
              <Table size={13} />
              <span>{t.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Detalle de la Tabla del Esquema */}
      <div
        style={{
          backgroundColor: 'var(--color-fog-white)',
          border: '1px solid var(--color-border)',
          borderRadius: '16px',
          padding: '16px 20px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                backgroundColor: current.type.includes('FACT') ? 'rgba(217, 155, 38, 0.18)' : current.type.includes('STAGING') ? 'rgba(59, 130, 246, 0.18)' : 'rgba(34, 197, 94, 0.18)',
                color: current.type.includes('FACT') ? 'var(--color-sienna-brown)' : current.type.includes('STAGING') ? '#2563eb' : '#15803d',
                padding: '3px 8px',
                borderRadius: '6px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {current.type}
            </span>
            <span style={{ fontSize: '13px', color: 'var(--color-slate-gray)', marginLeft: '10px' }}>
              {current.description}
            </span>
          </div>

          <span style={{ fontSize: '11.5px', fontFamily: 'var(--font-mono)', color: 'var(--color-slate-gray)' }}>
            PostgreSQL: <code>public.{current.name}</code>
          </span>
        </div>

        {/* Tabla de Columnas */}
        <div style={{ overflowX: 'auto' }}>
          <table className="steep-table" style={{ width: '100%', fontSize: '12.5px' }}>
            <thead>
              <tr>
                <th>Columna PostgreSQL</th>
                <th>Tipo de Dato SQL</th>
                <th>Campo Real Ingestado</th>
                <th>Regla de Homologación</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {current.columns.map((col, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-ink-black)' }}>
                    {col.name}
                  </td>
                  <td>
                    <code style={{ fontSize: '11.5px', color: 'var(--color-sienna-brown)' }}>
                      {col.pgType}
                    </code>
                  </td>
                  <td>
                    <span style={{ backgroundColor: 'var(--color-paper-white)', padding: '2px 8px', borderRadius: '4px', border: '1px solid var(--color-border)', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                      {col.originField}
                    </span>
                  </td>
                  <td style={{ color: 'var(--color-slate-gray)' }}>
                    {col.rule}
                  </td>
                  <td>
                    <span className="badge-status-completed" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', padding: '2px 8px' }}>
                      <CheckCircle size={11} /> Sincronizado
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
