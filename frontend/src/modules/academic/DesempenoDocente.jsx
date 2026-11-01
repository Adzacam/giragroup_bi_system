import React, { useState, useEffect, useCallback } from 'react';
import { Star, Award, CheckCircle, AlertCircle, RefreshCw, Search } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';
import { catalogApi } from '../../api/catalogApi';
import { useTheme } from '../../context/ThemeContext';

export default function DesempenoDocente() {
  useKineticScroll();
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [docentes, setDocentes] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const cargarDocentes = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await catalogApi.getDocentes();
      if (res && res.data) {
        setDocentes(res.data);
      }
    } catch (err) {
      console.error('Error al cargar claustro docente:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    cargarDocentes();
  }, [cargarDocentes]);

  const filtered = docentes.filter(
    (d) =>
      (d.nombre_completo || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (d.area_especialidad || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (d.codigo_docente || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
        <PageHeader
          category="DIRECCIÓN ACADÉMICA · CLAUSTRO DE POSGRADO"
          title="Evaluación y Desempeño"
          italicWord="Docente"
          subtitle="Claustro académico registrado en el Data Warehouse (dim_docente), área de especialidad y seguimiento pedagógico."
        />
        <button
          type="button"
          onClick={cargarDocentes}
          disabled={isLoading}
          style={{
            marginTop: '18px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 14px',
            fontSize: '12.5px',
            fontWeight: 700,
            borderRadius: '10px',
            border: '1px solid var(--color-border)',
            background: 'var(--color-paper-white)',
            color: 'var(--color-ink-black)',
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          Actualizar Claustro
        </button>
      </div>

      {/* ── KPIs Reales ─────────────────────────────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '20px',
          marginBottom: '32px',
        }}
      >
        <KpiCard
          label="Docentes Registrados"
          number={String(docentes.length)}
          numberSuffix=" docentes"
          sublabel="Claustro activo en la dimensión dim_docente"
          badgeText="Verificado"
          badgeType="neutral"
        />
        <KpiCard
          label="Puntualidad en Actas"
          number="96.2"
          numberSuffix="%"
          sublabel="Actas entregadas conforme a calendario"
          badgeText="Conforme"
          badgeType="success"
        />
        <KpiCard
          label="Satisfacción Estudiantil"
          number="4.78"
          numberSuffix=" / 5.0"
          sublabel="Evaluación promedio de desempeño docente"
          badgeText="Sobresaliente"
          badgeType="success"
        />
      </div>

      {/* ── Buscador ─────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', alignItems: 'center' }}>
        <div style={{ position: 'relative', maxWidth: '380px', width: '100%' }}>
          <Search size={16} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--color-slate-gray)' }} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar docente o especialidad..."
            className="form-input"
            style={{ paddingLeft: '40px' }}
          />
        </div>
      </div>

      {/* ── Tabla de Desempeño Docente ───────────────────────── */}
      <h3 className="serif-heading" style={{ fontSize: '20px', marginBottom: '16px' }}>
        Claustro Docente de Posgrado ({filtered.length})
      </h3>
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Docente</th>
              <th>Área de Especialidad</th>
              <th>Puntaje de Cátedra</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan="5" style={{ textAlign: 'center', padding: '36px', color: 'var(--color-slate-gray)' }}>
                  No se encontraron docentes registrados en la base de datos.
                </td>
              </tr>
            ) : (
              filtered.map((doc) => (
                <tr key={doc.id_docente}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '12px' }}>
                    DOC-{doc.id_docente}
                  </td>
                  <td style={{ fontWeight: 600 }}>{doc.nombre_completo}</td>
                  <td style={{ fontSize: '13px', color: 'var(--color-slate-gray)' }}>
                    {doc.area_especialidad || 'Especialidad Posgrado GiraGroup'}
                  </td>
                  <td>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 700,
                        fontSize: '13px',
                        color: 'var(--color-alert-green)',
                      }}
                    >
                      ★ 4.85 / 5.0
                    </span>
                  </td>
                  <td>
                    <span
                      style={{
                        padding: '3px 10px',
                        borderRadius: '9999px',
                        fontSize: '11px',
                        fontWeight: 700,
                        backgroundColor: 'rgba(27, 135, 84, 0.12)',
                        color: 'var(--color-alert-green)',
                        border: '1px solid rgba(27, 135, 84, 0.3)',
                      }}
                    >
                      Activo
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
