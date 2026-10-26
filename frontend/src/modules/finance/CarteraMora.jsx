import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, RefreshCw, ExternalLink } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import KpiCard from '../../components/shared/KpiCard';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import useKineticScroll from '../../hooks/useKineticScroll';
import { academicApi } from '../../api/academicApi';
import { kpiApi } from '../../api/kpiApi';

export default function CarteraMora() {
  useKineticScroll();
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [registrosMora, setRegistrosMora] = useState([]);
  const [resumenFin, setResumenFin] = useState({
    estudiantesEnMora: 0,
    porcentajeMora: 0,
    saldoVencidoBs: 0,
    recaudadoTotalBs: 0,
  });

  const maskCi = (ci) => {
    if (!ci || ci === 'S/C') return 'S/C';
    const str = String(ci).trim();
    if (str.length <= 4) return str;
    return `${str.slice(0, 3)}***${str.slice(-2)}`;
  };

  const cargarCartera = useCallback(async () => {
    setIsLoading(true);
    try {
      const [alertasRes, kpiFinRes] = await Promise.allSettled([
        academicApi.getAlertasTempranas({ regla_filtro: 'FINANCIERO' }),
        kpiApi.getKpisFinanciero(),
      ]);

      let alumnosMora = 0;
      let pctMora = 0;
      let moraBs = 0;

      if (alertasRes.status === 'fulfilled' && alertasRes.value) {
        const val = alertasRes.value;
        const cardFin = val.tarjetas?.riesgo_financiero || {};
        alumnosMora = cardFin.total_alumnos || 0;
        pctMora = cardFin.porcentaje_matricula || 0;
        moraBs = cardFin.monto_mora_bs || 0;
        setRegistrosMora(val.estudiantes || []);
      }

      let recaudadoBs = 0;
      if (kpiFinRes.status === 'fulfilled' && kpiFinRes.value) {
        const kf = kpiFinRes.value;
        recaudadoBs = Number(kf.total_recaudado_bs ?? kf.recaudacion_total ?? 0);
        if (!moraBs && kf.total_deuda_mora_bs) {
          moraBs = Number(kf.total_deuda_mora_bs);
        }
      }

      setResumenFin({
        estudiantesEnMora: alumnosMora,
        porcentajeMora: pctMora,
        saldoVencidoBs: moraBs,
        recaudadoTotalBs: recaudadoBs,
      });
    } catch (err) {
      console.error('Error al cargar cartera y mora desde el DW:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    cargarCartera();
  }, [cargarCartera]);

  const filtered = registrosMora.filter(
    (m) =>
      (m.nombre_completo || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (m.ci || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (m.programa || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
        <PageHeader
          category="ANÁLISIS FINANCIERO · DATOS REALES DW"
          title="Gestión de Cartera, Mora y"
          italicWord="Riesgo"
          subtitle="Control de cuentas por cobrar vencidas consolidado desde fact_situacion_financiera y acoplado al Motor Determinístico de Alertas Tempranas."
        />
        <div style={{ display: 'flex', gap: '10px', marginTop: '18px' }}>
          <button
            type="button"
            onClick={() => navigate('/alertas-tempranas')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '7px',
              padding: '8px 14px',
              borderRadius: '10px',
              fontSize: '12.5px',
              fontWeight: 700,
              border: '1px solid rgba(217, 155, 38, 0.45)',
              background: '#0C1E33',
              color: '#FAF9F6',
              cursor: 'pointer',
            }}
          >
            <ExternalLink size={14} style={{ color: '#D99B26' }} />
            Vista 3: Alertas Cruzadas (IF/THEN)
          </button>
          <button
            type="button"
            onClick={cargarCartera}
            disabled={isLoading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '7px',
              padding: '8px 13px',
              borderRadius: '10px',
              fontSize: '12.5px',
              fontWeight: 600,
              border: '1px solid var(--color-border)',
              background: 'var(--color-paper-white)',
              color: 'var(--color-ink-black)',
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            Actualizar
          </button>
        </div>
      </div>

      {/* ── KPIs Reales del Data Warehouse ───────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '20px',
          marginBottom: '32px',
        }}
      >
        <KpiCard
          label="Estudiantes en Mora (>= 2 Cuotas)"
          number={String(resumenFin.estudiantesEnMora)}
          numberSuffix=" alumnos"
          sublabel={`${resumenFin.porcentajeMora}% de la matrícula auditada`}
          badgeText="Regla Financiera"
          badgeType={resumenFin.estudiantesEnMora > 0 ? 'danger' : 'success'}
        />
        <KpiCard
          label="Saldo Exigible en Mora"
          numberPrefix="Bs. "
          number={Number(resumenFin.saldoVencidoBs || 0).toLocaleString()}
          numberSuffix=""
          sublabel="Total deuda consolidada en fact_situacion_financiera"
          badgeText="Cartera Vencida"
          badgeType="warning"
        />
        <KpiCard
          label="Recaudación Consolidada DW"
          numberPrefix="Bs. "
          number={Number(resumenFin.recaudadoTotalBs || 0).toLocaleString()}
          numberSuffix=""
          sublabel="Pagos verificados en el esquema constelación"
          badgeText="Verificado"
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
            placeholder="Buscar por estudiante, CI o programa..."
            className="form-input"
            style={{ paddingLeft: '40px' }}
          />
        </div>
      </div>

      {/* ── Tabla de Cartera y Mora (Sin Datos Demo) ──────────── */}
      <ResponsiveTable>
        <table className="steep-table">
          <thead>
            <tr>
              <th>Cédula (CI)</th>
              <th>Estudiante</th>
              <th>Programa / Módulo</th>
              <th>Cuotas Impagas</th>
              <th>Saldo en Mora</th>
              <th>Tag Reglas</th>
              <th>Prioridad</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '36px', color: 'var(--color-slate-gray)' }}>
                  No existen registros de mora (&gt;= 2 cuotas impagas) consolidados actualmente en fact_situacion_financiera.
                </td>
              </tr>
            ) : (
              filtered.map((item) => (
                <tr key={item.id_estudiante} className={item.cantidad_reglas >= 2 ? 'row-critical-alert' : ''}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '13px' }}>
                    {maskCi(item.ci)}
                  </td>
                  <td style={{ fontWeight: 600 }}>{item.nombre_completo}</td>
                  <td style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
                    {item.programa} · {item.modulo}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700, color: '#D99B26' }}>
                    [{item.cuotas_mora}]
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600 }}>
                    Bs. {Number(item.deuda_mora_bs || 0).toLocaleString()}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700 }}>
                    {item.tag}
                  </td>
                  <td>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: '9999px',
                        fontSize: '11px',
                        fontWeight: 700,
                        backgroundColor: item.cantidad_reglas >= 2 ? 'rgba(217, 56, 58, 0.14)' : 'rgba(217, 155, 38, 0.16)',
                        color: item.cantidad_reglas >= 2 ? '#D9383A' : '#D99B26',
                      }}
                    >
                      {item.prioridad}
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
