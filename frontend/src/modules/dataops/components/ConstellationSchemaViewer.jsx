import React, { useState } from 'react';
import { Database, Table, CheckCircle, Layers, GitBranch } from 'lucide-react';

export default function ConstellationSchemaViewer() {
  const [selectedEntity, setSelectedEntity] = useState('rendimiento_academico');

  const constellationEntities = [
    {
      id: 'rendimiento_academico',
      name: 'Rendimiento Académico',
      domainGroup: 'Métrica de Negocio · Dominio Académico',
      type: 'HECHO CENTRAL (ACADÉMICO)',
      description: 'Consolidado de calificaciones finales, asistencia e índice de confianza por estudiante, docente, módulo y período.',
      columns: [
        { name: 'id_hecho_aca', pgType: 'SERIAL PRIMARY KEY', originField: 'Autoincrementable DW', rule: 'Clave subrogada de hecho' },
        { name: 'id_estudiante', pgType: 'INTEGER (FK → Estudiantes)', originField: 'DOC_IDENTIDAD / CI', rule: 'Búsqueda canónica en cascada' },
        { name: 'id_docente', pgType: 'INTEGER (FK → Plantel Docente)', originField: 'DOCENTE / PROFESOR', rule: 'Homologación con RapidFuzz' },
        { name: 'id_modulo', pgType: 'INTEGER (FK → Módulos y Programas)', originField: 'COD_MODULO / MATERIA', rule: 'Vinculación curricular oficial' },
        { name: 'id_tiempo', pgType: 'INTEGER (FK → Calendario)', originField: 'FECHA_EVAL / TIMESTAMP', rule: 'Jerarquía de gestión y mes' },
        { name: 'id_documento', pgType: 'INTEGER (FK → Origen Documental)', originField: 'Archivo Ingerido', rule: 'Trazabilidad de lote de origen' },
        { name: 'nota_final', pgType: 'NUMERIC(5, 2)', originField: 'CALIF_FINAL / TOTAL', rule: 'Rango validado [0 - 100]' },
        { name: 'asistencia_pct', pgType: 'NUMERIC(5, 2)', originField: 'ASISTENCIA / ASIST_PCT', rule: 'Porcentaje normalizado [0 - 100]' },
        { name: 'nivel_confianza_ia', pgType: 'NUMERIC(5, 4)', originField: 'Inferencia BETO + Catálogo', rule: 'Índice probabilístico híbrido' },
        { name: 'requiere_revision', pgType: 'BOOLEAN', originField: 'Score < Umbral o CI dudoso', rule: 'Derivación a Auditoría HITL' },
        { name: 'estado_academico', pgType: 'VARCHAR(50)', originField: 'ESTADO / CONDICION', rule: 'APROBADO | REPROBADO' }
      ]
    },
    {
      id: 'situacion_financiera',
      name: 'Situación Financiera y Cobranzas',
      domainGroup: 'Métrica de Negocio · Dominio Financiero',
      type: 'HECHO CENTRAL (FINANCIERO)',
      description: 'Consolidado de cuotas devengadas, pagos recaudados, saldos por cobrar y alertas de mora crítica por estudiante y programa.',
      columns: [
        { name: 'id_hecho_fin', pgType: 'SERIAL PRIMARY KEY', originField: 'Autoincrementable DW', rule: 'Clave subrogada financiera' },
        { name: 'id_estudiante', pgType: 'INTEGER (FK → Estudiantes)', originField: 'CI / NOMBRE ESTUDIANTE', rule: 'Dimensión conformada compartida' },
        { name: 'id_modulo', pgType: 'INTEGER (FK → Módulos y Programas)', originField: 'PROGRAMA / DIPLOMADO', rule: 'Dimensión conformada compartida' },
        { name: 'id_documento', pgType: 'INTEGER (FK → Origen Documental)', originField: 'Arqueo / Extracto', rule: 'Trazabilidad documental SHA-256' },
        { name: 'concepto_pago', pgType: 'VARCHAR(120)', originField: 'CONCEPTO / GLOSA', rule: 'Homologado en Catálogo Financiero' },
        { name: 'monto_programado_bs', pgType: 'NUMERIC(12, 2)', originField: 'MONTO_CUOTA / DEUDA', rule: 'Normalización monetaria BOB' },
        { name: 'monto_pagado_bs', pgType: 'NUMERIC(12, 2)', originField: 'MONTO_PAGADO / ABONO', rule: 'Normalización monetaria BOB' },
        { name: 'saldo_pendiente_bs', pgType: 'NUMERIC(12, 2)', originField: 'SALDO / PENDIENTE', rule: 'Cuadre contable (Cuota - Pagado)' },
        { name: 'cuotas_vencidas', pgType: 'INTEGER DEFAULT 0', originField: 'CUOTAS_MORA', rule: 'Alerta crítica si >= 2 cuotas' },
        { name: 'estado_cartera', pgType: 'VARCHAR(50)', originField: 'ESTADO_PAGO', rule: 'AL DÍA | MORA PREVENTIVA | MORA CRÍTICA' }
      ]
    },
    {
      id: 'estudiantes',
      name: 'Estudiantes',
      domainGroup: 'Catálogo Maestro · Dimensión Conformada',
      type: 'DIMENSIÓN CONFORMADA',
      description: 'Catálogo maestro de estudiantes compartido entre Rendimiento Académico y Situación Financiera.',
      columns: [
        { name: 'id_estudiante', pgType: 'SERIAL PRIMARY KEY', originField: 'Clave Subrogada', rule: 'Identificador único institucional' },
        { name: 'codigo_estudiante', pgType: 'VARCHAR(50) UNIQUE', originField: 'ID_ESTUDIANTE / MATRÍCULA', rule: 'Código oficial de matrícula' },
        { name: 'nombre_completo', pgType: 'VARCHAR(200) NOT NULL', originField: 'NOMBRES Y APELLIDOS', rule: 'Estandarización canónica sin ruido' },
        { name: 'ci_estudiante', pgType: 'VARCHAR(30)', originField: 'DOC_IDENTIDAD / CI', rule: 'Limpieza alfanumérica + expedición' },
        { name: 'ciudad', pgType: 'VARCHAR(100)', originField: 'EXPEDIDO / SEDE', rule: 'La Paz, Cochabamba, Santa Cruz' },
        { name: 'nivel_academico', pgType: 'VARCHAR(50)', originField: 'TIPO_PROGRAMA', rule: 'Pregrado | Postgrado | Continua' }
      ]
    },
    {
      id: 'modulos_programas',
      name: 'Módulos y Programas',
      domainGroup: 'Catálogo Maestro · Dimensión Conformada',
      type: 'DIMENSIÓN CONFORMADA',
      description: 'Catálogo curricular de programas, diplomados, módulos y asignaturas vinculado a evaluaciones y cobranzas.',
      columns: [
        { name: 'id_modulo', pgType: 'SERIAL PRIMARY KEY', originField: 'Clave Subrogada', rule: 'Identificador curricular interno' },
        { name: 'codigo_modulo', pgType: 'VARCHAR(50) UNIQUE', originField: 'COD_MODULO / SIGLA', rule: 'Código normado (MOD-302, POS-101)' },
        { name: 'nombre_modulo', pgType: 'VARCHAR(200) NOT NULL', originField: 'ASIGNATURA / CURSO', rule: 'Denominación curricular oficial' },
        { name: 'area', pgType: 'VARCHAR(100)', originField: 'FACULTAD / ÁREA', rule: 'Tecnología, Negocios, Finanzas' },
        { name: 'creditos', pgType: 'INTEGER DEFAULT 4', originField: 'HORAS_ACAD', rule: 'Ponderación académica' }
      ]
    },
    {
      id: 'plantel_docente',
      name: 'Plantel Docente',
      domainGroup: 'Catálogo Maestro · Dimensión Académica',
      type: 'DIMENSIÓN ACADÉMICA',
      description: 'Catálogo oficial de docentes, instructores y coordinadores académicos con resolución de variantes de títulos.',
      columns: [
        { name: 'id_docente', pgType: 'SERIAL PRIMARY KEY', originField: 'Clave Subrogada', rule: 'Identificador interno docente' },
        { name: 'codigo_docente', pgType: 'VARCHAR(50) UNIQUE', originField: 'COD_DOCENTE / ITEM', rule: 'Código de plantel institucional' },
        { name: 'nombre_completo', pgType: 'VARCHAR(200) NOT NULL', originField: 'DOCENTE / INSTRUCTOR', rule: 'Limpieza de prefijos (Ing., Lic., M.Sc.)' },
        { name: 'especialidad', pgType: 'VARCHAR(120)', originField: 'ÁREA_CÁTEDRA', rule: 'Especialidad académica' },
        { name: 'estado_activo', pgType: 'BOOLEAN DEFAULT TRUE', originField: 'VIGENCIA', rule: 'Control de plantel vigente' }
      ]
    },
    {
      id: 'origen_documental',
      name: 'Origen Documental y Lotes',
      domainGroup: 'Trazabilidad · Dimensión Conformada',
      type: 'DIMENSIÓN DE TRAZABILIDAD',
      description: 'Registro de auditoría de cada archivo Excel o CSV ingerido, con huella criptográfica SHA-256 para prevenir duplicados.',
      columns: [
        { name: 'id_documento', pgType: 'SERIAL PRIMARY KEY', originField: 'ID Lote Documental', rule: 'Identificador único de carga' },
        { name: 'nombre_archivo', pgType: 'VARCHAR(255) NOT NULL', originField: 'Nombre de Archivo', rule: 'Trazabilidad de fuente original' },
        { name: 'hash_sha256', pgType: 'CHAR(64) UNIQUE', originField: 'Firma Criptográfica', rule: 'Bloqueo de reprocesamiento duplicado' },
        { name: 'tipo_fuente', pgType: 'VARCHAR(50)', originField: 'Clasificador de Dominio', rule: 'ACADÉMICO | FINANCIERO | MIXTO' },
        { name: 'fecha_ingesta', pgType: 'TIMESTAMP DEFAULT NOW()', originField: 'Sello Temporal', rule: 'Auditoría cronológica de carga' },
        { name: 'estado_proceso', pgType: 'VARCHAR(40)', originField: 'Estado ETL', rule: 'COMPLETADO | EN_REVISION' }
      ]
    },
    {
      id: 'registros_ingesta',
      name: 'Registros de Ingesta',
      domainGroup: ' Zona Intermedia · Buffer Transaccional',
      type: 'BUFFER DE INGESTA',
      description: 'Repositorio intermedio donde se asientan las filas extraídas en texto plano junto a su puntuación de confianza antes de pasar al Data Warehouse.',
      columns: [
        { name: 'id', pgType: 'SERIAL PRIMARY KEY', originField: 'ID Registro Intermedio', rule: 'Secuencia transaccional' },
        { name: 'id_documento', pgType: 'INTEGER (FK → Origen Documental)', originField: 'Archivo de Origen', rule: 'Vinculación con lote documental' },
        { name: 'categoria', pgType: 'VARCHAR(50)', originField: 'Clasificador Semántico', rule: 'ACADÉMICO | FINANCIERO' },
        { name: 'texto_plano', pgType: 'TEXT', originField: 'Contrato de Texto Plano', rule: 'Oración serializada para BETO NER' },
        { name: 'n_filas', pgType: 'INTEGER', originField: 'Bloque Tabular', rule: 'Conteo de tuplas detectadas' },
        { name: 'score_confianza', pgType: 'NUMERIC(5, 4)', originField: 'Índice BETO + RapidFuzz', rule: 'Puntuación combinada [0.0 - 0.99]' },
        { name: 'requiere_revision', pgType: 'BOOLEAN DEFAULT FALSE', originField: 'Compuerta de Calidad', rule: 'Activa derivación si < umbral' },
        { name: 'resuelto', pgType: 'BOOLEAN DEFAULT FALSE', originField: 'Estado de Conciliación', rule: 'Confirmado en Data Warehouse' }
      ]
    },
    {
      id: 'cola_revision_humana',
      name: 'Cola de Revisión Humana',
      domainGroup: 'Gobernanza de Datos · Auditoría HITL',
      type: 'AUDITORÍA HUMANA (HITL)',
      description: 'Bandeja de casos ambiguos, homonimia o posibles nuevos perfiles que requieren confirmación de un operador antes de persistir en el Data Warehouse.',
      columns: [
        { name: 'id_revision', pgType: 'SERIAL PRIMARY KEY', originField: 'ID Caso HITL', rule: 'Identificador de caso en bandeja' },
        { name: 'id_registro_ingesta', pgType: 'INTEGER (FK → Registros de Ingesta)', originField: 'Fila Observada', rule: 'Trazabilidad hacia texto original' },
        { name: 'entidad_observada', pgType: 'VARCHAR(200)', originField: 'Token Extraído por BETO', rule: 'Nombre, CI o módulo con baja similitud' },
        { name: 'candidato_sugerido', pgType: 'VARCHAR(200)', originField: 'Mejor Candidato RapidFuzz', rule: 'Sugerencia asistida del catálogo' },
        { name: 'motivo_derivacion', pgType: 'VARCHAR(120)', originField: 'Diagnóstico Automático', rule: 'Sin CI | Similitud < 85% | Nuevo Perfil' },
        { name: 'accion_operador', pgType: 'VARCHAR(50)', originField: 'Resolución Humana', rule: 'VINCULAR | CREAR_NUEVO | DESCARTAR' }
      ]
    }
  ];

  const current = constellationEntities.find(t => t.id === selectedEntity) || constellationEntities[0];

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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
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
              Arquitectura Multipropósito
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
              <Database size={13} /> PostgreSQL 16 · Esquema Constelación de Hechos (Kimball)
            </span>
          </div>
          <h3 className="serif-heading" style={{ fontSize: '20px', margin: '4px 0 0 0', color: 'var(--color-ink-black)' }}>
            Modelo Dimensional de Datos Institucionales (8 Entidades)
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
            Articulación de los dos dominios centrales (Académico y Financiero) mediante dimensiones conformadas compartidas y trazabilidad de ingesta.
          </p>
        </div>
      </div>

      {/* Mapa Visual de Dimensiones Conformadas de la Constelación */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '10px',
          padding: '12px 16px',
          borderRadius: '14px',
          backgroundColor: 'rgba(12, 30, 51, 0.03)',
          border: '1px solid var(--color-border)',
          marginBottom: '16px',
          fontSize: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={16} color="#d99b26" />
          <span>
            <strong>2 Hechos Centrales:</strong> Rendimiento Académico &amp; Situación Financiera
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <GitBranch size={16} color="#16a34a" />
          <span>
            <strong>4 Dimensiones Conformadas:</strong> Estudiantes, Módulos, Docentes y Origen
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Database size={16} color="#0284c7" />
          <span>
            <strong>2 Capas de Gobernanza:</strong> Registros de Ingesta &amp; Cola de Revisión Humana
          </span>
        </div>
      </div>

      {/* Selector de Entidad con Nombres Limpios de Negocio */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
        {constellationEntities.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setSelectedEntity(t.id)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 14px',
              borderRadius: '9999px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              border: t.id === selectedEntity ? '1px solid var(--color-ink-black)' : '1px solid var(--color-border)',
              backgroundColor: t.id === selectedEntity ? 'var(--color-ink-black)' : 'var(--color-fog-white)',
              color: t.id === selectedEntity ? 'var(--color-paper-white)' : 'var(--color-slate-gray)',
              transition: 'all 0.15s ease',
            }}
          >
            <Table size={13} />
            <span>{t.name}</span>
          </button>
        ))}
      </div>

      {/* Detalle de la Entidad Seleccionada */}
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
                backgroundColor: current.type.includes('HECHO') ? 'rgba(217, 155, 38, 0.18)' : current.type.includes('BUFFER') || current.type.includes('AUDITORÍA') ? 'rgba(59, 130, 246, 0.18)' : 'rgba(34, 197, 94, 0.18)',
                color: current.type.includes('HECHO') ? 'var(--color-sienna-brown)' : current.type.includes('BUFFER') || current.type.includes('AUDITORÍA') ? '#2563eb' : '#15803d',
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

          <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--color-sienna-brown)' }}>
            {current.domainGroup}
          </span>
        </div>

        {/* Tabla de Columnas */}
        <div style={{ overflowX: 'auto' }}>
          <table className="steep-table" style={{ width: '100%', fontSize: '12.5px' }}>
            <thead>
              <tr>
                <th>Atributo del Modelo</th>
                <th>Tipo de Dato SQL</th>
                <th>Campo Real de Origen</th>
                <th>Regla de Homologación Institucional</th>
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

