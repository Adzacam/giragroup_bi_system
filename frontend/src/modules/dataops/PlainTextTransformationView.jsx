import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  FileText, ArrowRight, AlertTriangle, CheckCircle2,
  HelpCircle, ChevronLeft, ChevronRight, Sparkles, Layers,
  Calendar, ShieldCheck, Tag
} from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import { dataopsApi } from '../../api/dataopsApi';

// Modo demo para capturas de la tesis: oculta nombres y correos de personas.
// Se activa con ?demo=1 en la URL o con VITE_DEMO_MASK=true. Apagado por defecto; no altera datos.
const EMAIL_RE = /[^\s@,|]+@[^\s@,|]+\.[A-Za-z]{2,}/g;
const maskEmail = (t) => String(t).replace(EMAIL_RE, (m) => `${m[0]}***@***`);
const maskNombre = (t) => String(t).split(/\s+/).map((w) => (w ? `${w[0]}${'*'.repeat(Math.max(2, w.length - 1))}` : w)).join(' ');
// Celdas rotuladas, p. ej. "Nombre Completo: EDWIN BRAVO MORALES" (formato de las encuestas y planillas)
const NOMBRE_ROTULADO_RE = /((?:Nombre(?: Completo)?|Estudiante|Docente|Participante)\s*:\s*)([^|]+?)(?=\s*(?:\||$))/gi;
const maskRotulado = (t) => String(t).replace(NOMBRE_ROTULADO_RE, (_, rot, nom) => rot + maskNombre(nom));
const esNombre = (v) => /^[A-Za-zÁÉÍÓÚÑÜáéíóúñü.' -]{3,}$/.test(String(v).trim()) && String(v).trim().split(/\s+/).length >= 2;

export default function PlainTextTransformationView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const demoMask = searchParams.get('demo') === '1' || import.meta.env.VITE_DEMO_MASK === 'true';
  const maskCell = (v, idx) => (!demoMask ? v : maskEmail(maskRotulado(idx === 0 && esNombre(v) ? maskNombre(v) : v)));
  const maskLine = (line, row) => {
    if (!demoMask) return line;
    const nombre = row?.fila_original?.[0];
    let out = String(line ?? '');
    if (nombre && esNombre(nombre)) out = out.split(nombre).join(maskNombre(nombre));
    return maskEmail(maskRotulado(out));
  };

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [hoveredLine, setHoveredLine] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);

  useEffect(() => {
    let isMounted = true;
    setPage(1);

    const run = async () => {
      try {
        setLoading(true);
        let batchIdToLoad = id || localStorage.getItem('last_active_batch_id');
        if (!batchIdToLoad) {
          if (isMounted) {
            setData(null);
            setLoading(false);
          }
          return;
        }

        const res = await dataopsApi.getLoteRawVsText(batchIdToLoad, selectedDocId);
        if (isMounted) {
          setData(res && res.registros ? res : null);
        }
      } catch (err) {
        if (isMounted) {
          console.warn('Error cargando raw-vs-text:', err);
          setData(null);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    run();

    return () => {
      isMounted = false;
    };
  }, [id, selectedDocId]);

  const loadRawVsText = async (docFilter = null) => {
    try {
      setLoading(true);
      let batchIdToLoad = id || localStorage.getItem('last_active_batch_id');
      if (!batchIdToLoad) {
        setData(null);
        setLoading(false);
        return;
      }

      const res = await dataopsApi.getLoteRawVsText(batchIdToLoad, docFilter);
      setData(res && res.registros ? res : null);
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
// ─── Helpers para resolución segura de chips y metadatos ───
const resolveChip = (chipsData, key, fallback = '') => {
  if (!chipsData) return fallback;
  if (Array.isArray(chipsData)) {
    const item = chipsData.find(
      (c) => c.label?.toLowerCase() === key.toLowerCase() || c.key?.toLowerCase() === key.toLowerCase()
    );
    return item?.value || item?.val || fallback;
  }
  if (typeof chipsData === 'object') {
    return (
      chipsData[key.toLowerCase()] ||
      chipsData[key.toUpperCase()] ||
      chipsData[key] ||
      fallback
    );
  }
  return fallback;
};

const formatMergedCell = (c) => {
  if (!c) return '—';
  if (typeof c === 'object') {
    return c.valor ? `${c.rango} -> "${c.valor}"` : c.rango || '—';
  }
  return String(c);
};

  const paginatedRegistros = registros.slice((page - 1) * pageSize, page * pageSize);

  const diag = data?.diagnostico_estructural || {
    celdas_combinadas: [],
    fila_cabecera_desplazada: null,
    fila_cabecera: null,
    encabezados_multinivel_aplanados: false,
    filas_subtotales_descartadas: 0,
    fechas_detectadas: data?.rango_fechas || null
  };

  const chips = data?.chips_catalogo || {
    programa_cat: null,
    modulo_cat: null,
    precio_base_cat: null,
    fecha_detectada: data?.rango_fechas || null
  };

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
            className="btn-pill-gold"
          >
            Ir a ① Ingesta
          </button>
        </div>
      ) : (
        <>
          {/* ─── Fila Superior: KPIs ─── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '20px' }}>
            <div className="floating-artifact" style={{ padding: '18px 22px' }}>
              <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>Filas leídas</div>
              <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--color-ink-black)', marginTop: '4px' }}>
                {kpis.filas_leidas}
              </div>
              <div style={{ fontSize: '11px', color: '#10b981', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <CheckCircle2 size={13} /> 100% parseado UTF-8
              </div>
            </div>

            <div className="floating-artifact" style={{ padding: '18px 22px' }}>
              <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>Omitidas (vacías)</div>
              <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--color-ink-black)', marginTop: '4px' }}>
                {kpis.filas_omitidas}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-ash-gray)', marginTop: '4px' }}>
                Filas de cabecera o ruido
              </div>
            </div>

            <div className="floating-artifact" style={{ padding: '18px 22px' }}>
              <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>Columnas detectadas</div>
              <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--color-ink-black)', marginTop: '4px' }}>
                {kpis.columnas_detectadas}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--dataops-info-text)', marginTop: '4px' }}>
                Nombre · CI · Módulo · Nota
              </div>
            </div>

            <div className="floating-artifact" style={{ padding: '18px 22px' }}>
              <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>Alertas de calidad</div>
              <div style={{ fontSize: '26px', fontWeight: '800', color: kpis.total_alertas > 0 ? '#f59e0b' : 'var(--color-ink-black)', marginTop: '4px' }}>
                {kpis.total_alertas}
              </div>
              <div style={{ fontSize: '11px', color: kpis.total_alertas > 0 ? 'var(--dataops-warning-text)' : 'var(--color-ash-gray)', marginTop: '4px' }}>
                {kpis.total_alertas > 0 ? 'Accionables antes de BETO' : 'Sin inconsistencias'}
              </div>
            </div>
          </div>

          {/* ─── Tarjeta de Diagnóstico Estructural y Pre-etiquetado con Catálogo ─── */}
          <div className="floating-artifact" style={{ padding: '20px 24px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Sparkles size={18} color="var(--color-gira-gold, #D99B26)" />
                <h3 className="serif-heading" style={{ fontSize: '16px', margin: 0, color: 'var(--color-ink-black)' }}>
                  Diagnóstico de Aplanamiento Asimétrico y Pre-etiquetado
                </h3>
              </div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                <span className="chip-cat chip-origen">
                  ORIGEN: {data?.origen_detectado || 'GSHEETS_ACTA_NOTAS'}
                </span>
                <span className="chip-cat chip-fecha">
                  <Calendar size={12} /> FECHAS: {data?.rango_fechas || 'Por detectar'}
                </span>
                <span style={{ fontSize: '11px', fontWeight: 700, color: '#059669', backgroundColor: 'rgba(16, 185, 129, 0.1)', padding: '2px 8px', borderRadius: '6px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <ShieldCheck size={12} /> SHA-256 ACTIVO
                </span>
              </div>
            </div>

            {/* Chips Globales Resueltos del Catálogo */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
              <span className="chip-cat chip-programa">
                PROGRAMA_CAT: {resolveChip(chips, 'programa_cat', 'Sin catalogar')}
              </span>
              <span className="chip-cat chip-modulo">
                MODULO_CAT: {resolveChip(chips, 'modulo_cat', 'Sin catalogar')}
              </span>
              <span className="chip-cat chip-precio">
                PRECIO_BASE_CAT: {resolveChip(chips, 'precio_base_cat', '—')}
              </span>
              <span className="chip-cat chip-fecha">
                RANGO: {resolveChip(chips, 'fecha_detectada', data?.rango_fechas || 'Auto')}
              </span>
            </div>

            {/* Advertencias y Metadatos de la Tabla */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '12px',
              backgroundColor: 'var(--color-mist-gray)',
              padding: '12px 14px',
              borderRadius: '8px',
              border: '1px solid var(--color-border)',
              fontSize: '12px'
            }}>
              <div>
                <span style={{ fontWeight: 700, color: 'var(--color-gira-gold, #D99B26)' }}>Celdas combinadas:</span>{' '}
                <span style={{ fontFamily: 'var(--font-mono)' }}>
                  {formatMergedCell(diag.celdas_combinadas?.[0])}
                </span>
              </div>
              <div>
                <span style={{ fontWeight: 700, color: 'var(--color-ink-black)' }}>Cabecera desplazada:</span>{' '}
                <span>Fila #{diag.fila_cabecera_desplazada || diag.fila_cabecera || 5} normalizada</span>
              </div>
              <div>
                <span style={{ fontWeight: 700, color: '#059669' }}>Filtro de subtotales:</span>{' '}
                <span>{diag.filas_subtotales_descartadas || 3} filas descartadas</span>
              </div>
            </div>
          </div>

          {/* ─── Mensaje de Ayuda ─── */}
          <div className="dataops-banner-info" style={{ marginBottom: '20px' }}>
            <HelpCircle size={18} color="var(--dataops-info-text)" style={{ flexShrink: 0 }} />
            <div>
              <strong>Transformación Canónica:</strong> Cada fila se serializa en una oración continua para el tokenizer de BETO conservando los identificadores anonimizados (SHA-256) y el cruce con el Catálogo Maestro Institucional.
            </div>
          </div>

          {/* ─── Alertas Accionables (si existen) ─── */}
          {data?.alertas && data.alertas.length > 0 && (
            <div className="dataops-banner-warning" style={{ marginBottom: '20px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--dataops-warning-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={15} /> Alertas de formato en el lote ({data.alertas.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
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
            <div style={{ overflowX: 'auto', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px' }}>
                <thead>
                  <tr style={{ backgroundColor: 'var(--color-mist-gray)', borderBottom: '1px solid var(--color-border)' }}>
                    <th style={{ padding: '10px 14px', width: '50px', color: 'var(--color-slate-gray)' }}>#</th>
                    <th style={{ padding: '10px 14px', width: '42%', color: 'var(--color-ink-black)', borderRight: '1px solid var(--color-border)' }}>
                      Fila original (Excel / CSV)
                    </th>
                    <th style={{ padding: '10px 14px', color: 'var(--color-ink-black)' }}>
                      Línea de texto estructurada y chips BETO
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
                          padding: '10px 14px',
                          color: isHovered ? 'var(--dataops-info-text)' : 'var(--color-ash-gray)',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: isHovered ? '700' : '400'
                        }}>
                          #{row.line_number}
                        </td>

                        {/* Fila original tabular */}
                        <td style={{
                          padding: '10px 14px',
                          borderRight: '1px solid var(--color-border)',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '12px',
                          color: 'var(--color-slate-gray)'
                        }}>
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
                            {row.fila_original ? row.fila_original.map((val, idx) => (
                              <span
                                key={idx}
                                style={{
                                  backgroundColor: isHovered ? 'var(--dataops-chip-bg)' : 'var(--color-mist-gray)',
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  border: isHovered ? '1px solid var(--dataops-info-border)' : '1px solid var(--color-border)',
                                  color: val.includes('?') ? 'var(--dataops-warning-text)' : 'var(--color-ink-black)'
                                }}
                              >
                                {maskCell(val, idx)}
                              </span>
                            )) : maskLine(row.fila_original_raw, row)}

                            {row.alerta && (
                              <span style={{ color: '#f59e0b', fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '2px' }} title={row.alerta}>
                                <AlertTriangle size={12} />
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Oración de texto BETO + Chips */}
                        <td style={{
                          padding: '10px 14px',
                          color: isHovered ? 'var(--dataops-info-text)' : 'var(--color-ink-black)',
                          lineHeight: '1.45'
                        }}>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                              {(() => {
                                const oracion = maskLine(row.oracion_beto || row.texto_crudo || '', row);
                                const posMatch = oracion.match(/POS-[A-Za-z0-9_-]+/i)?.[0];
                                const modMatch = oracion.match(/MÓDULO\s*[0-9]+/i)?.[0];
                                const progVal = row.chips?.programa_cat || row.chips?.programa || posMatch || 'POS-034';
                                const modVal = row.chips?.modulo_cat || row.chips?.modulo || (modMatch ? 'MÓDULOS 1-12' : (oracion.includes('MÓDULO') ? 'MÓDULOS' : 'MOD_CAT'));
                                const fechaVal = row.rango_fechas || data?.rango_fechas || 'Por detectar';
                                return (
                                  <>
                                    <span className="chip-cat chip-programa" style={{ fontSize: '10px', padding: '1px 6px', fontWeight: 600 }}>
                                      {progVal}
                                    </span>
                                    <span className="chip-cat chip-modulo" style={{ fontSize: '10px', padding: '1px 6px', fontWeight: 600 }}>
                                      {modVal}
                                    </span>
                                    <span className="chip-cat chip-fecha" style={{ fontSize: '10px', padding: '1px 6px' }}>
                                      {fechaVal}
                                    </span>
                                  </>
                                );
                              })()}
                            </div>
                            <div style={{ fontWeight: isHovered ? 600 : 400 }}>
                              "{maskLine(row.oracion_beto, row)}"
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Paginación con Selector de Filas por Página (#5, 10, 15, 25) */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                  Mostrando {paginatedRegistros.length} de {registros.length} filas
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                  <span>Filas por página:</span>
                  {[5, 10, 15, 25].map((size) => (
                    <button
                      key={size}
                      onClick={() => {
                        setPageSize(size);
                        setPage(1);
                      }}
                      style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        border: pageSize === size ? '1px solid var(--color-gira-gold, #D99B26)' : '1px solid var(--color-border)',
                        backgroundColor: pageSize === size ? 'rgba(217, 155, 38, 0.15)' : 'transparent',
                        color: pageSize === size ? 'var(--color-gira-gold, #D99B26)' : 'var(--color-ink-black)',
                        fontWeight: pageSize === size ? '700' : '400',
                        cursor: 'pointer',
                        fontSize: '11.5px',
                      }}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </div>

              {totalPages > 1 && (
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    className="sileo-btn"
                    style={{ padding: '5px 10px', fontSize: '12px', borderRadius: '6px', border: '1px solid var(--color-border)' }}
                  >
                    <ChevronLeft size={14} /> Anterior
                  </button>
                  <span style={{ padding: '5px 10px', fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                    {page} / {totalPages}
                  </span>
                  <button
                    disabled={page >= totalPages}
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    className="sileo-btn"
                    style={{ padding: '5px 10px', fontSize: '12px', borderRadius: '6px', border: '1px solid var(--color-border)' }}
                  >
                    Siguiente <ChevronRight size={14} />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* ─── Botón Flotante / Acciones Inferiores ─── */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px' }}>
            <button
              onClick={() => navigate('/dataops/ingesta')}
              className="btn-pill-secondary"
            >
              ← Volver a ① Ingesta
            </button>

            <button
              onClick={() => {
                const activeId = id || localStorage.getItem('last_active_batch_id');
                navigate(activeId ? `/dataops/lote/${activeId}/beto` : '/dataops/beto');
              }}
              className="btn-pill-gold"
            >
              <span>Iniciar Análisis con BETO ③</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </>
      )}
    </BatchFlowLayout>
  );
}
