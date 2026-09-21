import React from 'react';
import { Star, Award, CheckCircle, AlertCircle, FileCheck } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';

const MOCK_DOCENTES = [
  { id: 1, codigo: 'DOC-109', nombre: 'Dr. Carlos Alberto Gómez Murillo', modulo: 'Arquitectura de Datos & MLOps', puntuacion: 4.88, evaluaciones: 32, actas: '14 / 14', estado: 'Sobresaliente' },
  { id: 2, codigo: 'DOC-112', nombre: 'MSc. Valeria Quiroga Morales', modulo: 'Modelos de Riesgo & Machine Learning', puntuacion: 4.76, evaluaciones: 28, actas: '9 / 9', estado: 'Sobresaliente' },
  { id: 3, codigo: 'DOC-120', nombre: 'Ing. Fernando Tapia Dávalos', modulo: 'Sistemas Distribuidos & Cloud', puntuacion: 4.62, evaluaciones: 30, actas: '12 / 12', estado: 'Muy Bueno' },
  { id: 4, codigo: 'DOC-135', nombre: 'Lic. Mariana Siles Benítez', modulo: 'Gobernanza de Información & Ética IA', puntuacion: 4.54, evaluaciones: 26, actas: '6 / 6', estado: 'Muy Bueno' },
  { id: 5, codigo: 'DOC-142', nombre: 'MSc. Roberto Mendoza Justiniano', modulo: 'Programación Estadística con Python', puntuacion: 3.75, evaluaciones: 29, actas: '7 / 8', estado: 'En Observación' },
];

export default function DesempenoDocente() {
  useKineticScroll();

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <PageHeader
        category="DIRECCIÓN ACADÉMICA"
        title="Evaluación y Desempeño"
        italicWord="Docente"
        subtitle="Métricas de satisfacción estudiantil NPS, cumplimiento en la entrega de actas y calidad pedagógica consolidada."
      />

      {/* ── KPIs ─────────────────────────────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '20px',
          marginBottom: '32px',
        }}
      >
        <KpiCard
          label="Satisfacción Global NPS"
          number="4.72"
          numberSuffix=" / 5.0"
          sublabel="Promedio de 145 encuestas del trimestre"
          badgeText="Excelente"
          badgeType="success"
        />
        <KpiCard
          label="Puntualidad en Actas"
          number="96.2"
          numberSuffix="%"
          sublabel="48 actas consolidadas a tiempo"
          badgeText="Conforme"
          badgeType="success"
        />
        <KpiCard
          label="Docentes Evaluados"
          number="38"
          sublabel="100% de la plantilla de postgrado"
          badgeText="Completo"
          badgeType="neutral"
        />
        <KpiCard
          label="Atención Pedagógica"
          number="1"
          numberSuffix=" docente"
          sublabel="Puntaje inferior a 3.8 / 5.0"
          badgeText="Seguimiento"
          badgeType="warning"
        />
      </div>

      {/* ── Tabla de Desempeño Docente ───────────────────────── */}
      <h3 className="serif-heading" style={{ fontSize: '22px', marginBottom: '16px' }}>
        Resultados Individuales por Docente de Cátedra
      </h3>
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Código</th>
              <th>Docente</th>
              <th>Módulo Impartido</th>
              <th>Puntaje NPS</th>
              <th>Encuestas</th>
              <th>Actas Entregadas</th>
              <th>Calificación</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_DOCENTES.map((doc) => (
              <tr key={doc.id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '13px' }}>
                  {doc.codigo}
                </td>
                <td style={{ fontWeight: 500 }}>{doc.nombre}</td>
                <td style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>{doc.modulo}</td>
                <td>
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      fontSize: '13.5px',
                      color: doc.puntuacion >= 4.5 ? 'var(--color-alert-green)' : 'var(--color-alert-amber)',
                    }}
                  >
                    ★ {doc.puntuacion.toFixed(2)}
                  </span>
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{doc.evaluaciones}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{doc.actas}</td>
                <td>
                  <span
                    style={{
                      padding: '2px 9px',
                      borderRadius: '9999px',
                      fontSize: '11px',
                      fontWeight: 600,
                      backgroundColor:
                        doc.estado === 'Sobresaliente'
                          ? '#dcfce7'
                          : doc.estado === 'Muy Bueno'
                          ? '#e0f2fe'
                          : '#fef3c7',
                      color:
                        doc.estado === 'Sobresaliente'
                          ? 'var(--color-alert-green)'
                          : doc.estado === 'Muy Bueno'
                          ? '#0369a1'
                          : 'var(--color-alert-amber)',
                    }}
                  >
                    {doc.estado}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
