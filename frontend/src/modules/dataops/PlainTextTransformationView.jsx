import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  FileText, ArrowRight, AlertTriangle, CheckCircle2,
  HelpCircle, ChevronLeft, ChevronRight, Layers, Sparkles
} from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import { dataopsApi } from '../../api/dataopsApi';

export default function PlainTextTransformationView() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [hoveredLine, setHoveredLine] = useState(null);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  useEffect(() => {
    setPage(1);
    loadRawVsText(selectedDocId);
  }, [id, selectedDocId]);

  const loadRawVsText = async (docFilter = null) => {
    try {
      setLoading(true);
      let batchIdToLoad = id;
      if (!batchIdToLoad) {
        batchIdToLoad = localStorage.getItem('last_active_batch_id');
      }
      if (!batchIdToLoad) {
        const sources = await dataopsApi.getSources();
        if (sources?.data?.length > 0) {
          batchIdToLoad = sources.data[0].id_lote || sources.data[0].id || sources.data[0].id_documento;
          if (batchIdToLoad) localStorage.setItem('last_active_batch_id', batchIdToLoad);
        }
      }

      if (!batchIdToLoad) {
        setData(null);
        return;
      }

      const res = await dataopsApi.getLoteRawVsText(batchIdToLoad, docFilter);
      if (res && res.registros) {
        setData(res);
      } else {
        setData(null);
      }
    } catch (err) {
      console.warn('Error cargando raw-vs-text:', err);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const kpis = data?.kpis || {
    filas_leidas: 0,
    filas_omitidas: 0,
    columnas_detectadas: 0,
    total_alertas: 0
  };

  const registros = data?.registros || [];
  const totalPages = Math.ceil(registros.length / pageSize) || 1;
  const paginatedRegistros = registros.slice((page - 1) * pageSize, page * pageSize);

  return (
    <BatchFlowLayout
      currentStep={2}
      selectedDocId={selectedDocId}
      onSelectDocId={setSelectedDocId}
    >
      {loading ? (
        <div className="floating-artifact" style={{ padding: '64px 24px', textAlign: 'center' }}>
          <div style={{ fontSize: '15px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>
            Transformando y cargando estructura de texto plano...
          </div>
        </div>
      ) : registros.length === 0 ? (
        <div className="floating-artifact" style={{ padding: '64px 24px', textAlign: 'center' }}>
          <FileText size={48} color="var(--color-slate-gray)" style={{ margin: '0 auto 16px auto', display: 'block' }} />
          <h3 className="serif-heading" style={{ fontSize: '20px', margin: '0 0 10px 0', color: 'var(--color-ink-black)' }}>
            No hay registros de texto plano para este lote
          </h3>
          <p style={{ fontSize: '14px', color: 'var(--color-slate-gray)', maxWidth: '520px', margin: '0 auto 24px auto', lineHeight: '1.5' }}>
            No se encontraron líneas estructuradas para el identificador seleccionado. Carga un archivo en la pestaña ① Ingesta para iniciar el procesamiento.
          </p>
          <button
            onClick={() => navigate('/dataops/ingesta')}
            className="sileo-btn"
            style={{
              padding: '10px 20px', backgroundColor: '#2563eb', color: '#fff',
              border: 'none', borderRadius: '8px', fontWeight: '700', fontSize: '13px', cursor: 'pointer'
            }}
          >
            Ir a ① Ingesta
          </button>
        </div>
      ) : (
        <>
          {/* ─── Fila Superior: KPIs y Explicación ─── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="floating-artifact" style={{ padding: '20px 24px' }}>
          <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>Filas leídas</div>
          <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--color-ink-black)', marginTop: '4px' }}>
            {kpis.filas_leidas}
          </div>
          <div style={{ fontSize: '11px', color: '#10b981', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <CheckCircle2 size={13} /> 100% parseado UTF-8
          </div>
        </div>

        <div className="floating-artifact" style={{ padding: '20px 24px' }}>
          <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>Omitidas (vacías)</div>
          <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--color-ink-black)', marginTop: '4px' }}>
            {kpis.filas_omitidas}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-ash-gray)', marginTop: '4px' }}>
            Filas de cabecera o ruido
          </div>
        </div>

        <div className="floating-artifact" style={{ padding: '20px 24px' }}>
          <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>Columnas detectadas</div>
          <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--color-ink-black)', marginTop: '4px' }}>
            {kpis.columnas_detectadas}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--dataops-info-text)', marginTop: '4px' }}>
            Nombre · CI · Módulo · Nota
          </div>
        </div>

        <div className="floating-artifact" style={{ padding: '20px 24px' }}>
          <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>Alertas de calidad</div>
          <div style={{ fontSize: '26px', fontWeight: '800', color: kpis.total_alertas > 0 ? '#f59e0b' : 'var(--color-ink-black)', marginTop: '4px' }}>
            {kpis.total_alertas}
          </div>
          <div style={{ fontSize: '11px', color: kpis.total_alertas > 0 ? 'var(--dataops-warning-text)' : 'var(--color-ash-gray)', marginTop: '4px' }}>
            {kpis.total_alertas > 0 ? 'Accionables antes de BETO' : 'Sin inconsistencias'}
          </div>
        </div>
      </div>

      {/* ─── Mensaje de Ayuda ─── */}
      <div className="dataops-banner-info" style={{ marginBottom: '24px' }}>
        <HelpCircle size={20} color="var(--dataops-info-text)" style={{ flexShrink: 0 }} />
        <div>
          <strong>¿Qué hace esta vista?</strong> Cada fila de tu archivo original se convierte en una oración de texto continuo para que el modelo de lenguaje BETO pueda leerla. Es una copia de trabajo que preserva intacto tu archivo original.
        </div>
      </div>

      {/* ─── Alertas Accionables (si existen) ─── */}
      {data?.alertas && data.alertas.length > 0 && (
        <div className="dataops-banner-warning" style={{ marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--dataops-warning-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={16} /> Alertas de formato en el lote ({data.alertas.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {data.alertas.map((alt, i) => (
              <div key={i} style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                • Fila #{alt.line}: <strong>{alt.motivo}</strong>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Mapeo Interactivo: Fila Excel vs Oración BETO ─── */}
      <div className="floating-artifact" style={{ padding: '24px', marginBottom: '28px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h3 className="serif-heading" style={{ fontSize: '17px', margin: 0, color: 'var(--color-ink-black)' }}>
              Comparativa de transformación (Fila original → Oración para BETO)
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
              Pasa el cursor sobre una fila para resaltar su oración correspondiente
            </p>
          </div>
        </div>

        {/* Tabla Dividida de Dos Secciones */}
        <div style={{ overflowX: 'auto', borderRadius: '12px', border: '1px solid var(--color-border)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--color-mist-gray)', borderBottom: '1px solid var(--color-border)' }}>
                <th style={{ padding: '12px 14px', width: '50px', color: 'var(--color-slate-gray)' }}>#</th>
                <th style={{ padding: '12px 16px', width: '45%', color: 'var(--color-ink-black)', borderRight: '1px solid var(--color-border)' }}>
                  Fila original (Excel / CSV)
                </th>
                <th style={{ padding: '12px 16px', color: 'var(--color-ink-black)' }}>
                  Línea de texto que lee BETO
                </th>
              </tr>
            </thead>
            <tbody>
              {paginatedRegistros.map((row) => {
                const isHovered = hoveredLine === row.line_number;

                return (
                  <tr
                    key={row.line_number}
                    onMouseEnter={() => setHoveredLine(row.line_number)}
                    onMouseLeave={() => setHoveredLine(null)}
                    style={{
                      borderBottom: '1px solid var(--color-border)',
                      backgroundColor: isHovered ? 'var(--dataops-row-hover)' : 'transparent',
                      transition: 'background-color 0.15s ease'
                    }}
                  >
                    {/* Número de fila */}
                    <td style={{
                      padding: '12px 14px',
                      color: isHovered ? 'var(--dataops-info-text)' : 'var(--color-ash-gray)',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: isHovered ? '700' : '400'
                    }}>
                      #{row.line_number}
                    </td>

                    {/* Fila original tabular */}
                    <td style={{
                      padding: '12px 16px',
                      borderRight: '1px solid var(--color-border)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '12.5px',
                      color: 'var(--color-slate-gray)'
                    }}>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                        {row.fila_original ? row.fila_original.map((val, idx) => (
                          <span
                            key={idx}
                            style={{
                              backgroundColor: isHovered ? 'var(--dataops-chip-bg)' : 'var(--color-mist-gray)',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              border: isHovered ? '1px solid var(--dataops-info-border)' : '1px solid var(--color-border)',
                              color: val.includes('?') ? 'var(--dataops-warning-text)' : 'var(--color-ink-black)'
                            }}
                          >
                            {val}
                          </span>
                        )) : row.fila_original_raw}

                        {row.alerta && (
                          <span style={{ color: '#f59e0b', fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '2px' }} title={row.alerta}>
                            <AlertTriangle size={13} />
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Oración de texto BETO */}
                    <td style={{
                      padding: '12px 16px',
                      color: isHovered ? 'var(--dataops-info-text)' : 'var(--color-ink-black)',
                      fontWeight: isHovered ? '600' : '400',
                      lineHeight: '1.5'
                    }}>
                      <span>"{row.oracion_beto}"</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        {totalPages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
              Mostrando {paginatedRegistros.length} de {registros.length} filas
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="sileo-btn"
                style={{ padding: '6px 12px', fontSize: '12px', borderRadius: '6px', border: '1px solid var(--color-border)' }}
              >
                <ChevronLeft size={14} /> Anterior
              </button>
              <span style={{ padding: '6px 12px', fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                {page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                className="sileo-btn"
                style={{ padding: '6px 12px', fontSize: '12px', borderRadius: '6px', border: '1px solid var(--color-border)' }}
              >
                Siguiente <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ─── Botón Flotante / Acciones Inferiores ─── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px' }}>
        <button
          onClick={() => navigate('/dataops/ingesta')}
          className="sileo-btn"
          style={{
            padding: '12px 20px',
            borderRadius: '10px',
            backgroundColor: 'var(--color-mist-gray)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-slate-gray)',
            cursor: 'pointer',
            fontSize: '13px',
            fontWeight: '600'
          }}
        >
          ← Volver a Ingesta
        </button>

        <button
          onClick={() => {
            const activeId = id || localStorage.getItem('last_active_batch_id');
            navigate(activeId ? `/dataops/lote/${activeId}/beto` : '/dataops/beto');
          }}
          className="sileo-btn"
          style={{
            padding: '14px 26px',
            borderRadius: '12px',
            backgroundColor: '#2563eb',
            color: '#ffffff',
            border: 'none',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: '700',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            boxShadow: '0 4px 14px rgba(37, 99, 235, 0.3)'
          }}
        >
          Continuar a Lectura de BETO ③ <ArrowRight size={18} />
        </button>
      </div>
      </>
    )}
  </BatchFlowLayout>
  );
}
