import React, { useState } from 'react';
import {
  FileSpreadsheet, FileText, Database, Split, Sparkles, CheckCircle2,
  TableProperties, Layers, ShieldCheck, ArrowRight, Code, Eye
} from 'lucide-react';

export default function HeterogeneousReadersCard() {
  const [activeReader, setActiveReader] = useState('excel');

  const readers = [
    {
      id: 'excel',
      sprintTask: 'Sprint 2 · Tarea 1',
      title: 'Lector Excel / Sheets',
      subtitle: 'Limpieza estructural & cabeceras',
      icon: FileSpreadsheet,
      badge: '.XLSX / .XLS',
      badgeColor: '#2563eb',
      spec: 'Aislamiento de islas tabulares rectangulares (B5:H180), remoción de celdas combinadas y títulos administrativos.',
      features: [
        'Detección automática de filas de metadatos no tabulares (cabeceras decorativas).',
        'Normalización canónica de columnas: NOMBRES Y APELLIDOS → nombre_completo, CALIF_FINAL → nota_final.',
        'Manejo de múltiples hojas (pestañas) y libros de calificaciones consolidados.'
      ],
      sampleRaw: `Fila 1: [UNIVERSIDAD GIRA - GOBERNANZA ACADÉMICA] (CELDA COMBINADA)
Fila 2: [Docente: Dr. Carlos A. Gómez | Gestión 2026-I]
Fila 4: [NRO | NOMBRES Y APELLIDOS | DOC_IDENTIDAD/CI | CALIF_FINAL | ESTADO]
Fila 5: [ 1  | Daza Adriano        | 4892019 LP?      | 75.0        | APROBADO]`,
      sampleClean: `{
  "origen": "Excel / Google Sheets",
  "isla_detectada": "B4:E32",
  "cabeceras_mapeadas": {
    "NOMBRES Y APELLIDOS": "nombre_completo",
    "DOC_IDENTIDAD/CI": "ci_estudiante",
    "CALIF_FINAL": "nota_final"
  },
  "estado_limpieza": "100% Sanitizado (Sin celdas combinadas)"
}`
    },
    {
      id: 'forms',
      sprintTask: 'Sprint 2 · Tarea 2',
      title: 'Lector Google Forms (CSV)',
      subtitle: 'Datos de admisión & postulaciones',
      icon: FileText,
      badge: 'CSV DELIMITADO',
      badgeColor: '#7c3aed',
      spec: 'Parseo de respuestas de formularios web con marca temporal (timestamp) y datos de aspirantes.',
      features: [
        'Extracción de marca temporal de postulación y parseo de correos electrónicos institucionales.',
        'Normalización de campos de admisión: Nombre Completo, Teléfono/WhatsApp, Programa de Interés.',
        'Validación de delimitadores coma/punto y coma con tolerancia a saltos de línea en preguntas abiertas.'
      ],
      sampleRaw: `Marca temporal,Nombre del postulante,Correo electrónico,Programa de interés,CI
2026/08/14 10:14:22 GMT-4,Adriano Daza Meneses,a.daza@correo.bo,Maestría en Big Data,4892019
2026/08/14 11:02:15 GMT-4,Carlos Alberto Gomez,c.gomez@correo.bo,Diplomado DataOps,3451234`,
      sampleClean: `{
  "origen": "Google Forms (CSV)",
  "delimitador": "Coma (,)",
  "contexto_ingesta": "Admisiones & Prospección",
  "columnas_identificadas": [
    "timestamp_admision",
    "nombre_postulante",
    "email_contacto",
    "codigo_programa_interes"
  ],
  "registros_validos": "100% Sintaxis RFC 4180"
}`
    },
    {
      id: 'moodle',
      sprintTask: 'Sprint 2 · Tarea 3',
      title: 'Lector Reportes Moodle',
      subtitle: 'Calificaciones de aula virtual (CSV/XLSX)',
      icon: Database,
      badge: 'MOODLE LMS',
      badgeColor: '#ea580c',
      spec: 'Extracción directa de calificaciones de actividades, foros, cuestionarios y nota final del curso.',
      features: [
        'Estructura jerárquica: Nombre de curso, Módulo, Tarea evaluativa y Total ponderado.',
        'Mapeo de identificadores de usuario (Número ID, Nombre de usuario Moodle a CI/Código de estudiante).',
        'Normalización de notas sobre escala porcentual estándar [0 - 100 pts].'
      ],
      sampleRaw: `Nombre,Apellido,Número de ID,Dirección de correo,Cuestionario 1 (Puntos),Total del curso
Adriano,Daza,EST-402,adaza@campus.edu.bo,88.00,88.00 / 100.00
Carlos,Gomez,DOC-109,cgomez@campus.edu.bo,95.00,95.00 / 100.00`,
      sampleClean: `{
  "origen": "Aula Virtual Moodle",
  "formato": "Exportación de Libro de Calificaciones",
  "metadatos_modulo": "MOD-302: Gestión de Datos e Inteligencia",
  "escala_convertida": "Base canónica 100 puntos",
  "asistencia_evaluada": "Sincronizada con registros de actividad"
}`
    },
    {
      id: 'dispatcher',
      sprintTask: 'Sprint 2 · Tarea 4',
      title: 'Dispatcher Inteligente',
      subtitle: 'Identificación y enrutamiento dinámico',
      icon: Split,
      badge: 'DISPATCHER.PY',
      badgeColor: 'var(--color-gira-gold, #D99B26)',
      spec: 'Inspecciona firmas binarias (magic bytes), extensión y patrones semánticos de cabeceras en milisegundos.',
      features: [
        'Análisis heurístico en O(1): detecta si el archivo es Acta POS, Formulario CSV o Exportación LMS.',
        'Enrutamiento automático al lector correspondiente sin necesidad de configuración manual.',
        'Registro inmediato del hash criptográfico SHA-256 para trazabilidad e inmutabilidad en auditoría.'
      ],
      sampleRaw: `[Magic Bytes]: 50 4B 03 04 (ZIP container / OOXML)
[Extensión]: .xlsx
[Cabeceras Preliminares]: ["NOMBRES", "CALIF_FINAL", "DOC_IDENTIDAD"]
[Decisión Dispatcher]: Confianza 98.4% -> Enrutado a ExcelReader`,
      sampleClean: `{
  "modulo": "dispatcher.py",
  "algoritmo": "Heurística de Magic Bytes + Extensión + Token Matching",
  "tiempo_enrutamiento": "45ms",
  "lector_seleccionado": "ExcelStructuralCleaner",
  "pipeline_stages_programadas": 6,
  "contrato_asignado": "CONTRATO_CANONICO_STAGING_V2"
}`
    }
  ];

  const current = readers.find(r => r.id === activeReader) || readers[0];

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
            <Sparkles size={13} /> Arquitectura DataOps · Lectores Especializados & Dispatcher
          </span>
          <h3 className="serif-heading" style={{ fontSize: '20px', margin: '4px 0 0 0', color: 'var(--color-ink-black)' }}>
            Ecosistema de Ingesta Documental Heterogénea
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
            Desarrollo de lectores dedicados para cada fuente documental con aislamiento estructural, sanitizado y enrutamiento automático.
          </p>
        </div>

        {/* Selector de Lector */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {readers.map((r) => {
            const Icon = r.icon;
            const isSel = r.id === activeReader;
            return (
              <button
                key={r.id}
                type="button"
                onClick={() => setActiveReader(r.id)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '7px 14px',
                  borderRadius: '9999px',
                  fontSize: '12.5px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: isSel ? '1px solid var(--color-ink-black)' : '1px solid var(--color-border)',
                  backgroundColor: isSel ? 'var(--color-ink-black)' : 'var(--color-fog-white)',
                  color: isSel ? 'var(--color-paper-white)' : 'var(--color-slate-gray)',
                  transition: 'all 0.15s ease',
                }}
              >
                <Icon size={14} color={isSel ? '#ffffff' : r.badgeColor} />
                <span>{r.title}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Tarjeta de Especificación Técnica del Lector Seleccionado */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '20px',
          padding: '20px',
          borderRadius: '16px',
          backgroundColor: 'var(--color-fog-white)',
          border: '1px solid var(--color-border)',
        }}
      >
        {/* Columna Izquierda: Especificaciones y Capacidades */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
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
              {current.sprintTask}
            </span>
            <span
              style={{
                backgroundColor: current.badgeColor,
                color: '#ffffff',
                fontSize: '10.5px',
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: '6px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {current.badge}
            </span>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-ink-black)' }}>
              {current.subtitle}
            </span>
          </div>

          <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', lineHeight: '1.5', margin: '0 0 14px 0' }}>
            {current.spec}
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {current.features.map((feat, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '12.5px' }}>
                <CheckCircle2 size={15} color="#1b8754" style={{ marginTop: '2px', flexShrink: 0 }} />
                <span style={{ color: 'var(--color-ink-black)' }}>{feat}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Columna Derecha: Entrada Cruda vs Contrato Sanitizado */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-slate-gray)', marginBottom: '4px', letterSpacing: '0.5px' }}>
              Entrada Cruda (Formato Heterogéneo)
            </div>
            <pre
              style={{
                margin: 0,
                padding: '10px 12px',
                borderRadius: '10px',
                backgroundColor: '#17191c',
                color: '#fca5a5',
                fontSize: '11.5px',
                fontFamily: 'var(--font-mono)',
                overflowX: 'auto',
                lineHeight: 1.4,
              }}
            >
              {current.sampleRaw}
            </pre>
          </div>

          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-gira-gold)', marginBottom: '4px', letterSpacing: '0.5px' }}>
              Salida Limpia & Mapeada Canónica
            </div>
            <pre
              style={{
                margin: 0,
                padding: '10px 12px',
                borderRadius: '10px',
                backgroundColor: '#0f1113',
                color: '#86efac',
                fontSize: '11.5px',
                fontFamily: 'var(--font-mono)',
                overflowX: 'auto',
                lineHeight: 1.4,
              }}
            >
              {current.sampleClean}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
