import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Cpu, CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck,
  HelpCircle, ChevronDown, ChevronUp, Eye, EyeOff, Database,
  User, BookOpen, Award, FileText, Check, Sparkles, ChevronLeft,
  ChevronRight, Search, TableProperties
} from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import { dataopsApi } from '../../api/dataopsApi';
import { sileoToast } from '../../services/sileoToast';

export default function BetoReadingFlowView() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [filterState, setFilterState] = useState('ALL'); // 'ALL' | 'AUTOMATICO' | 'REVISION'
  const [tableFilter, setTableFilter] = useState('ALL'); // 'ALL' | 'AUTOMATICO' | 'REVISION'
  const [searchQuery, setSearchQuery] = useState('');
  const [tablePage, setTablePage] = useState(1);
  const tablePageSize = 10;

  const [showHowScoreWorks, setShowHowScoreWorks] = useState(false);
  const [showModelDetails, setShowModelDetails] = useState(false);
  const [revealedCis, setRevealedCis] = useState({});
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [isInserting, setIsInserting] = useState(false);
  const [insertedSuccess, setInsertedSuccess] = useState(false);
  const [dwInsertDesglose, setDwInsertDesglose] = useState(null);

  useEffect(() => {
    setTablePage(1);
    loadReadingData(selectedDocId);
  }, [id, selectedDocId]);

  const loadReadingData = async (docFilter = null) => {
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
        setSelectedRecord(null);
        return;
      }

      const res = await dataopsApi.getLoteBetoReading(batchIdToLoad, { docId: docFilter });
      if (res && res.registros && res.registros.length > 0) {
        setData(res);
        const firstReview = res.registros.find(r => r.estado === 'REVISION') || res.registros[0];
        setSelectedRecord(firstReview);
      } else {
        setData(res || null);
        setSelectedRecord(null);
      }
    } catch (err) {
      console.warn('Error al cargar beto-reading:', err);
      setData(null);
      setSelectedRecord(null);
    } finally {
      setLoading(false);
    }
  };

  const capaA = data?.capa_a_resumen || {
    total_analizados: 0,
    directo_dw: 0,
    a_revision: 0,
    indice_medio: 0,
    porcentaje_automatico: 0
  };

  const allRecords = data?.registros || [];

  // Filtro de lista izquierda (Capa B)
  const masterListFiltered = allRecords.filter(r => {
    if (filterState === 'ALL') return true;
    return r.estado === filterState;
  });

  // Filtro de tabla completa (Capa C)
  const tableFiltered = allRecords.filter(r => {
    if (tableFilter !== 'ALL' && r.estado !== tableFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        (r.estudiante || '').toLowerCase().includes(q) ||
        (r.modulo || '').toLowerCase().includes(q) ||
        (r.ci_enmascarado && r.ci_enmascarado.toLowerCase().includes(q)) ||
        (revealedCis[r.id] && String(revealedCis[r.id]).toLowerCase().includes(q))
      );
    }
    return true;
  });

  const tableTotalPages = Math.ceil(tableFiltered.length / tablePageSize) || 1;
  const paginatedTableRows = tableFiltered.slice((tablePage - 1) * tablePageSize, tablePage * tablePageSize);

  const toggleCiReveal = async (recordId) => {
    if (revealedCis[recordId]) {
      setRevealedCis(prev => {
        const copy = { ...prev };
        delete copy[recordId];
        return copy;
      });
      return;
    }

    try {
      const res = await dataopsApi.revelarCi(recordId);
      const ciRevealed = res?.ci_real || res?.ci;
      if (ciRevealed) {
        setRevealedCis(prev => ({
          ...prev,
          [recordId]: ciRevealed
        }));
      }
    } catch (err) {
      const status = err.response?.status;
      sileoToast.error({
        title: status === 403 ? 'Permiso denegado (RBAC)' : 'No se pudo revelar el CI',
        description: err.response?.data?.detail || 'Se requiere rol ADMIN o AUDITOR_CALIDAD para revelar datos personales.'
      });
    }
  };

  const handleConfirmInsertDw = async () => {
    try {
      setIsInserting(true);
      const effectiveBatchId = id || localStorage.getItem('last_active_batch_id');
      const res = await dataopsApi.confirmDwInsert({
        id_lote: effectiveBatchId ? Number(effectiveBatchId) : undefined,
        doc_id: selectedDocId ? Number(selectedDocId) : undefined
      });
      setInsertedSuccess(true);
      const desglose = res?.desglose || {
        inserted_academico: res?.inserted_dw ?? capaA.directo_dw,
        inserted_financiero: 0
      };
      setDwInsertDesglose(desglose);
      const totalInserted = res?.inserted_dw ?? (desglose.inserted_academico + desglose.inserted_financiero);
      sileoToast.success({
        title: `${totalInserted} registros insertados al Data Warehouse`,
        description: `Académicos: +${desglose.inserted_academico} · Financieros: +${desglose.inserted_financiero}`
      });
      setIsConfirmModalOpen(false);
    } catch (err) {
      console.error('Error en confirmación DW:', err);
      sileoToast.error({
        title: 'Error al insertar en Data Warehouse',
        description: err.response?.data?.detail || err.message || 'Error en la transacción de carga.'
      });
      setIsConfirmModalOpen(false);
    } finally {
      setIsInserting(false);
    }
  };

  const renderTokenIcon = (iconName) => {
    switch (iconName) {
      case 'user': return <User size={12} />;
      case 'book': return <BookOpen size={12} />;
      case 'award': return <Award size={12} />;
      default: return <FileText size={12} />;
    }
  };

  return (
    <BatchFlowLayout
      currentStep={3}
      selectedDocId={selectedDocId}
      onSelectDocId={setSelectedDocId}
    >
      {loading ? (
        <div className="floating-artifact" style={{ padding: '64px 24px', textAlign: 'center' }}>
          <div style={{ fontSize: '15px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>
            Cargando inferencias y métricas del modelo BETO...
          </div>
        </div>
      ) : allRecords.length === 0 ? (
        <div className="floating-artifact" style={{ padding: '64px 24px', textAlign: 'center' }}>
          <Cpu size={48} color="var(--color-slate-gray)" style={{ margin: '0 auto 16px auto', display: 'block' }} />
          <h3 className="serif-heading" style={{ fontSize: '20px', margin: '0 0 10px 0', color: 'var(--color-ink-black)' }}>
            No hay lecturas de BETO registradas para este lote
          </h3>
          <p style={{ fontSize: '14px', color: 'var(--color-slate-gray)', maxWidth: '520px', margin: '0 auto 24px auto', lineHeight: '1.5' }}>
            Selecciona o procesa un archivo fuente en el paso ① Ingesta para que el modelo BETO pueda clasificar los registros y extraer entidades.
          </p>
          <button
            onClick={() => navigate('/dataops/ingesta')}
            className="sileo-btn"
            style={{
              padding: '10px 20px', backgroundColor: '#2563eb', color: '#fff',
              border: 'none', borderRadius: '8px', fontWeight: '700', fontSize: '13px', cursor: 'pointer'
            }}
          >
            Ir al paso ① Ingesta
          </button>
        </div>
      ) : (
        <>
          {/* ─── Capa A. Resumen (4 tarjetas + barra apilada) ─── */}
          <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '16px', marginBottom: '16px' }}>
          <div className="floating-artifact" style={{ padding: '20px 24px' }}>
            <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>Analizados</div>
            <div style={{ fontSize: '28px', fontWeight: '800', color: 'var(--color-ink-black)', marginTop: '4px' }}>
              {capaA.total_analizados}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-ash-gray)', marginTop: '4px' }}>
              100% de registros leídos
            </div>
          </div>

          <div className="floating-artifact" style={{ padding: '20px 24px', borderLeft: '4px solid #10b981' }}>
            <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>Directo al DW (≥85)</div>
            <div style={{ fontSize: '28px', fontWeight: '800', color: '#10b981', marginTop: '4px' }}>
              {capaA.directo_dw}
            </div>
            <div style={{ fontSize: '11px', color: '#059669', marginTop: '4px' }}>
              {capaA.porcentaje_automatico}% automatización
            </div>
          </div>

          <div className="floating-artifact" style={{ padding: '20px 24px', borderLeft: '4px solid #f59e0b' }}>
            <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>A revisión humana</div>
            <div style={{ fontSize: '28px', fontWeight: '800', color: '#f59e0b', marginTop: '4px' }}>
              {capaA.a_revision}
            </div>
            <div style={{ fontSize: '11px', color: '#b45309', marginTop: '4px' }}>
              Elementos con score &lt; 85 o reglas
            </div>
          </div>

          <div className="floating-artifact" style={{ padding: '20px 24px' }}>
            <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>Índice medio</div>
            <div style={{ fontSize: '28px', fontWeight: '800', color: '#2563eb', marginTop: '4px' }}>
              {capaA.indice_medio} <span style={{ fontSize: '14px', fontWeight: '500', color: 'var(--color-slate-gray)' }}>/ 99</span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-ash-gray)', marginTop: '4px' }}>
              Calidad semántica global
            </div>
          </div>
        </div>

        {/* Barra apilada interactiva */}
        <div className="floating-artifact" style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '8px' }}>
            <span style={{ fontWeight: '600', color: 'var(--color-ink-black)' }}>Distribución del Lote</span>
            <span style={{ color: 'var(--color-slate-gray)' }}>
              verde = automático ({capaA.directo_dw}) · ámbar = revisión ({capaA.a_revision})
            </span>
          </div>
          <div style={{
            height: '14px',
            borderRadius: '9999px',
            backgroundColor: '#e5e7eb',
            overflow: 'hidden',
            display: 'flex'
          }}>
            <div
              style={{
                width: `${capaA.porcentaje_automatico}%`,
                backgroundColor: '#10b981',
                transition: 'width 0.4s ease'
              }}
              title={`Directo al DW: ${capaA.directo_dw}`}
            />
            <div
              style={{
                width: `${100 - capaA.porcentaje_automatico}%`,
                backgroundColor: '#f59e0b',
                transition: 'width 0.4s ease'
              }}
              title={`A revisión: ${capaA.a_revision}`}
            />
          </div>
        </div>
      </div>

      {/* ─── Texto de ayuda de la vista ─── */}
      <div className="dataops-banner-info" style={{ marginBottom: '24px' }}>
        <HelpCircle size={20} color="var(--dataops-info-text)" style={{ flexShrink: 0 }} />
        <div>
          <strong>Cómo funciona BETO:</strong> BETO lee cada línea, identifica estudiantes, módulos y docentes, y mide cuán seguro está. Si el elemento más débil queda bajo 85, un humano lo revisa.
        </div>
      </div>

      {/* ─── Capa B. Maestro–Detalle (Lista Izq | 4 Pasos Der) ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px', marginBottom: '28px' }}>
        
        {/* Lista de Registros a la Izquierda */}
        <div className="floating-artifact" style={{ padding: '20px', display: 'flex', flexDirection: 'column', height: '640px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h3 className="serif-heading" style={{ fontSize: '15px', margin: 0, color: 'var(--color-ink-black)' }}>
              Registros
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
              {masterListFiltered.length}
            </span>
          </div>

          {/* Filtros rápidos: Todos · Auto · Revisión */}
          <div style={{ display: 'flex', gap: '6px', marginBottom: '14px' }}>
            {['ALL', 'AUTOMATICO', 'REVISION'].map((mode) => (
              <button
                key={mode}
                onClick={() => setFilterState(mode)}
                style={{
                  flex: 1,
                  padding: '6px 4px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  fontWeight: '600',
                  border: '1px solid',
                  borderColor: filterState === mode ? 'var(--color-accent-blue)' : 'var(--color-border)',
                  backgroundColor: filterState === mode ? 'var(--dataops-info-bg)' : 'var(--color-paper-white)',
                  color: filterState === mode ? 'var(--dataops-info-text)' : 'var(--color-slate-gray)',
                  cursor: 'pointer'
                }}
              >
                {mode === 'ALL' ? 'Todos' : mode === 'AUTOMATICO' ? 'Auto' : 'Revisión'}
              </button>
            ))}
          </div>

          {/* Lista scrollable con bullets solicitados: ● Pérez M. 62 ámbar */}
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {masterListFiltered.map((rec) => {
              const isSelected = selectedRecord?.id === rec.id;
              const isAuto = rec.estado === 'AUTOMATICO';
              const bulletColor = isAuto ? '#10b981' : '#f59e0b';
              const badgeLabel = isAuto ? 'verde' : 'ámbar';

              return (
                <div
                  key={rec.id}
                  onClick={() => setSelectedRecord(rec)}
                  style={{
                    padding: '12px',
                    borderRadius: '10px',
                    border: '1px solid',
                    borderColor: isSelected ? 'var(--color-accent-blue)' : 'var(--color-border)',
                    backgroundColor: isSelected ? 'var(--dataops-row-selected)' : 'var(--color-paper-white)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        fontSize: '14px',
                        color: bulletColor,
                        lineHeight: 1
                      }}>
                        ●
                      </span>
                      <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-ink-black)' }}>
                        {rec.estudiante}
                      </span>
                    </div>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: '700',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      backgroundColor: isAuto ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                      color: isAuto ? '#059669' : '#b45309'
                    }}>
                      {rec.indice_registro} {badgeLabel}
                    </span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', marginTop: '4px', paddingLeft: '14px' }}>
                    {rec.modulo}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Panel Detalle a la Derecha: 4 Pasos Visibles */}
        <div className="floating-artifact" style={{ padding: '28px', display: 'flex', flexDirection: 'column', gap: '22px' }}>
          {selectedRecord ? (
            <>
              {/* Encabezado del Detalle */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--color-border)', paddingBottom: '14px' }}>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>Cómo leyó BETO esta línea</div>
                  <h3 className="serif-heading" style={{ fontSize: '18px', margin: '4px 0 0 0', color: 'var(--color-ink-black)' }}>
                    {selectedRecord.estudiante}
                  </h3>
                </div>
                <span style={{
                  fontSize: '12px',
                  fontWeight: '700',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  backgroundColor: selectedRecord.estado === 'AUTOMATICO' ? '#ecfdf5' : '#fffbeb',
                  color: selectedRecord.estado === 'AUTOMATICO' ? '#059669' : '#b45309',
                  border: selectedRecord.estado === 'AUTOMATICO' ? '1px solid #a7f3d0' : '1px solid #fde68a'
                }}>
                  {selectedRecord.estado === 'AUTOMATICO' ? '✓ Aprobado Automático (≥85)' : '⚠ A Revisión Humana'}
                </span>
              </div>

              {/* 1 LECTURA */}
              <div>
                <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--dataops-info-text)', letterSpacing: '0.5px', marginBottom: '8px' }}>
                  1 · LECTURA (CHIPS CON COLOR E ÍCONO/ETIQUETA)
                </div>
                <div style={{
                  padding: '14px',
                  backgroundColor: 'var(--color-mist-gray)',
                  borderRadius: '10px',
                  lineHeight: '2.4',
                  fontSize: '13.5px'
                }}>
                  {selectedRecord.lectura?.tokens ? selectedRecord.lectura.tokens.map((tok, i) => (
                    <span
                      key={i}
                      style={{
                        margin: '0 4px',
                        padding: '4px 10px',
                        borderRadius: '6px',
                        backgroundColor: 'var(--dataops-chip-bg)',
                        border: `1.5px solid ${tok.color}`,
                        color: 'var(--color-ink-black)',
                        fontWeight: '600',
                        fontSize: '12.5px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                    >
                      <span style={{ color: tok.color, display: 'inline-flex', alignItems: 'center' }}>
                        {renderTokenIcon(tok.icon)}
                      </span>
                      <span>{tok.text}</span>
                      <span style={{
                        fontSize: '10px',
                        textTransform: 'uppercase',
                        padding: '1px 5px',
                        borderRadius: '4px',
                        backgroundColor: tok.color,
                        color: '#ffffff',
                        fontWeight: '700'
                      }}>
                        {tok.tag}
                      </span>
                    </span>
                  )) : selectedRecord.raw_text}
                </div>
              </div>

              {/* 2 CONFIANZA POR ELEMENTO */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--dataops-info-text)', letterSpacing: '0.5px' }}>
                    2 · CONFIANZA POR ELEMENTO
                  </div>
                  <button
                    onClick={() => setShowHowScoreWorks(!showHowScoreWorks)}
                    style={{
                      background: 'none', border: 'none', color: 'var(--dataops-info-text)', fontSize: '12px',
                      cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px'
                    }}
                  >
                    ¿Cómo se calcula? {showHowScoreWorks ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>

                {/* Desplegable: fórmula de cálculo */}
                {showHowScoreWorks && (
                  <div className="dataops-banner-info" style={{ marginBottom: '12px', fontSize: '12px', display: 'block' }}>
                    Fórmula del índice de confianza: <code>min(99, lectura del modelo + bono catálogo + bono aparición repetida)</code>.
                    <br />
                    <strong>Compuerta mínima:</strong> Los bonos solo se aplican si la lectura base del modelo alcanza al menos <strong>70 / 100</strong>. <em>El catálogo suma, nunca resta.</em>
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {selectedRecord.confianza_elementos.map((elem, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ width: '90px', fontSize: '13px', fontWeight: '600', color: 'var(--color-ink-black)' }}>
                        {elem.elemento}
                      </span>
                      <div style={{ flex: 1, height: '8px', backgroundColor: 'var(--color-border)', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${elem.indice}%`,
                          height: '100%',
                          backgroundColor: elem.indice >= 85 ? '#10b981' : '#f59e0b'
                        }} />
                      </div>
                      <span style={{ width: '40px', fontSize: '13px', fontWeight: '700', color: elem.indice >= 85 ? '#059669' : '#b45309', textAlign: 'right' }}>
                        {elem.indice}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)', width: '200px' }}>
                        {elem.explicacion}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 3 VERIFICACIÓN DE REGLAS */}
              <div>
                <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--dataops-info-text)', letterSpacing: '0.5px', marginBottom: '8px' }}>
                  3 · VERIFICACIÓN DE REGLAS FIJAS (APRUEBAN O DETIENEN, NO SUMAN CONFIANZA)
                </div>
                <div style={{
                  display: 'flex',
                  gap: '16px',
                  padding: '12px 16px',
                  borderRadius: '10px',
                  backgroundColor: 'var(--color-mist-gray)',
                  fontSize: '13px',
                  flexWrap: 'wrap'
                }}>
                  {/* CI */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ color: selectedRecord.verificacion_reglas?.ci?.valido ? '#10b981' : '#ef4444', fontWeight: '700' }}>
                      {selectedRecord.verificacion_reglas?.ci?.valido ? '✓' : '✗'}
                    </span>
                    <span>CI:</span>
                    <strong style={{ fontFamily: 'var(--font-mono)' }}>
                      {revealedCis[selectedRecord.id]
                        ? revealedCis[selectedRecord.id]
                        : selectedRecord.verificacion_reglas?.ci?.valor_enmascarado}
                    </strong>
                    <button
                      onClick={() => toggleCiReveal(selectedRecord.id)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--dataops-info-text)', padding: '0 2px' }}
                      title="Revelar CI (auditado)"
                    >
                      {revealedCis[selectedRecord.id] ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>

                  <span style={{ color: 'var(--color-border)' }}>|</span>

                  {/* Nota */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ color: selectedRecord.verificacion_reglas?.nota?.valido ? '#10b981' : '#ef4444', fontWeight: '700' }}>
                      {selectedRecord.verificacion_reglas?.nota?.valido ? '✓' : '✗'}
                    </span>
                    <span>Nota:</span>
                    <strong>{selectedRecord.verificacion_reglas?.nota?.motivo}</strong>
                  </div>

                  <span style={{ color: 'var(--color-border)' }}>|</span>

                  {/* Monto */}
                  <div style={{ color: selectedRecord.verificacion_reglas?.monto?.valido === false ? '#ef4444' : 'var(--color-slate-gray)' }}>
                    <strong>{selectedRecord.verificacion_reglas?.monto?.motivo || 'Monto: —'}</strong>
                  </div>
                </div>
              </div>

              {/* 4 DECISIÓN */}
              <div className={selectedRecord.estado === 'AUTOMATICO' ? 'dataops-banner-success' : 'dataops-banner-warning'} style={{ display: 'block' }}>
                <div style={{ fontSize: '12px', fontWeight: '700', marginBottom: '4px' }}>
                  4 · DECISIÓN EN LENGUAJE LLANO
                </div>
                <div style={{ fontSize: '14px', fontWeight: '600' }}>
                  Índice del registro = el más bajo: <strong>{selectedRecord.decision?.indice_mas_bajo}</strong>
                </div>
                <div style={{ fontSize: '13px', marginTop: '4px' }}>
                  → {selectedRecord.estado === 'AUTOMATICO' ? 'Directo al DW' : 'A revisión humana'}: "{selectedRecord.decision?.motivo_llano}"
                </div>
              </div>
            </>
          ) : (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-slate-gray)' }}>
              Selecciona un registro a la izquierda para inspeccionar la lectura de BETO
            </div>
          )}
        </div>
      </div>

      {/* ─── Confirmación Explícita de Inserción al DW ─── */}
      <div className="floating-artifact" style={{
        padding: '22px 26px',
        marginBottom: '28px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px',
        backgroundColor: 'var(--color-mist-gray)',
        border: '1.5px solid var(--dataops-info-border)',
        borderRadius: '14px'
      }}>
        <div>
          <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={18} color="var(--dataops-info-text)" /> Inserción de Registros Automáticos al Data Warehouse
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>
            {insertedSuccess
              ? `✓ Insertados en el DW: +${dwInsertDesglose?.inserted_academico ?? capaA.directo_dw} en Rendimiento Académico · +${dwInsertDesglose?.inserted_financiero ?? 0} en Situación Financiera y Cobranzas.`
              : `Hay ${capaA.directo_dw} registros con índice del registro ≥ 85 aprobados listos para cargarse al DW según su tipo documental.`}
          </div>
        </div>

        <button
          onClick={() => setIsConfirmModalOpen(true)}
          disabled={insertedSuccess || isInserting || capaA.directo_dw === 0}
          className="sileo-btn"
          style={{
            padding: '14px 24px',
            borderRadius: '12px',
            backgroundColor: insertedSuccess ? '#10b981' : '#2563eb',
            color: '#ffffff',
            border: 'none',
            fontSize: '14px',
            fontWeight: '700',
            cursor: insertedSuccess ? 'default' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)'
          }}
        >
          {insertedSuccess ? (
            <>
              <CheckCircle2 size={18} /> {capaA.directo_dw} Registros Insertados en DW
            </>
          ) : (
            <>
              <Database size={18} /> Insertar {capaA.directo_dw} registros al DW
            </>
          )}
        </button>
      </div>

      {/* ─── Capa C. Tabla de Todos los Registros ─── */}
      <div className="floating-artifact" style={{ padding: '24px', marginBottom: '28px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '14px' }}>
          <div>
            <h3 className="serif-heading" style={{ fontSize: '17px', margin: 0, color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <TableProperties size={18} color="var(--dataops-info-text)" /> Capa C · Tabla de todos los registros del lote
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--color-slate-gray)', margin: '4px 0 0 0' }}>
              Inspección tabular completa: haz click en cualquier fila para cargarla en el detalle de BETO
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            {/* Buscador */}
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--color-ash-gray)' }} />
              <input
                type="text"
                placeholder="Buscar por estudiante..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="dataops-input"
                style={{
                  padding: '7px 12px 7px 30px',
                  borderRadius: '8px',
                  fontSize: '12px'
                }}
              />
            </div>

            {/* Filtros Rápidos */}
            <div style={{ display: 'flex', gap: '4px' }}>
              {['ALL', 'AUTOMATICO', 'REVISION'].map((mode) => (
                <button
                  key={mode}
                  onClick={() => setTableFilter(mode)}
                  style={{
                    padding: '7px 12px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: '600',
                    border: '1px solid',
                    borderColor: tableFilter === mode ? 'var(--color-accent-blue)' : 'var(--color-border)',
                    backgroundColor: tableFilter === mode ? 'var(--dataops-info-bg)' : 'var(--color-paper-white)',
                    color: tableFilter === mode ? 'var(--dataops-info-text)' : 'var(--color-slate-gray)',
                    cursor: 'pointer'
                  }}
                >
                  {mode === 'ALL' ? 'Todos' : mode === 'AUTOMATICO' ? 'Automático' : 'Revisión'}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Tabla */}
        <div style={{ overflowX: 'auto', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--color-mist-gray)', borderBottom: '1px solid var(--color-border)' }}>
                <th style={{ padding: '12px 14px', width: '110px', color: 'var(--color-slate-gray)' }}>Estado</th>
                <th style={{ padding: '12px 14px', color: 'var(--color-ink-black)' }}>Estudiante</th>
                <th style={{ padding: '12px 14px', color: 'var(--color-ink-black)' }}>Módulo</th>
                <th style={{ padding: '12px 14px', color: 'var(--color-ink-black)' }}>Nota Normalizada</th>
                <th style={{ padding: '12px 14px', width: '80px', color: 'var(--color-ink-black)', textAlign: 'center' }}>Índice</th>
                <th style={{ padding: '12px 14px', color: 'var(--color-slate-gray)' }}>Motivo de la Decisión</th>
              </tr>
            </thead>
            <tbody>
              {paginatedTableRows.map((row) => {
                const isAuto = row.estado === 'AUTOMATICO';
                const isSelected = selectedRecord?.id === row.id;

                return (
                  <tr
                    key={row.id}
                    onClick={() => setSelectedRecord(row)}
                    style={{
                      borderBottom: '1px solid var(--color-border)',
                      backgroundColor: isSelected ? 'var(--dataops-row-selected)' : 'transparent',
                      cursor: 'pointer'
                    }}
                  >
                    <td style={{ padding: '12px 14px' }}>
                      <span style={{
                        padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '700',
                        backgroundColor: isAuto ? '#ecfdf5' : '#fffbeb',
                        color: isAuto ? '#059669' : '#b45309',
                        border: isAuto ? '1px solid #a7f3d0' : '1px solid #fde68a'
                      }}>
                        {isAuto ? 'Automático' : 'Revisión'}
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px', fontWeight: '700', color: 'var(--color-ink-black)' }}>
                      {row.estudiante}
                    </td>
                    <td style={{ padding: '12px 14px', color: 'var(--color-slate-gray)' }}>
                      {row.modulo}
                    </td>
                    <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: '600', color: 'var(--dataops-info-text)' }}>
                      {row.nota_normalizada}
                    </td>
                    <td style={{ padding: '12px 14px', textAlign: 'center', fontWeight: '800', color: isAuto ? '#059669' : '#b45309' }}>
                      {row.indice_registro}
                    </td>
                    <td style={{ padding: '12px 14px', fontSize: '12px', color: isAuto ? 'var(--color-ash-gray)' : '#b45309' }}>
                      {row.decision?.motivo_llano || row.motivo}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        {tableTotalPages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-slate-gray)' }}>
              Mostrando {paginatedTableRows.length} de {tableFiltered.length} registros
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                disabled={tablePage <= 1}
                onClick={() => setTablePage(p => Math.max(1, p - 1))}
                className="sileo-btn"
                style={{ padding: '6px 12px', fontSize: '12px', borderRadius: '6px', border: '1px solid var(--color-border)' }}
              >
                <ChevronLeft size={14} /> Anterior
              </button>
              <span style={{ padding: '6px 12px', fontSize: '12px', color: 'var(--color-slate-gray)' }}>
                {tablePage} / {tableTotalPages}
              </span>
              <button
                disabled={tablePage >= tableTotalPages}
                onClick={() => setTablePage(p => Math.min(tableTotalPages, p + 1))}
                className="sileo-btn"
                style={{ padding: '6px 12px', fontSize: '12px', borderRadius: '6px', border: '1px solid var(--color-border)' }}
              >
                Siguiente <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ─── Modal de Vista Previa de Inserción DW ─── */}
      {isConfirmModalOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.6)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px'
        }}>
          <div className="floating-artifact" style={{ maxWidth: '540px', width: '100%', padding: '28px' }}>
            <h3 className="serif-heading" style={{ fontSize: '18px', margin: '0 0 12px 0', color: 'var(--color-ink-black)' }}>
              Confirmar Inserción en Data Warehouse
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: '0 0 20px 0' }}>
              Se aplicará la transacción de carga sobre las entidades de negocio según el dominio documental de cada archivo:
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '24px', fontSize: '13px' }}>
              <div style={{ padding: '10px 14px', backgroundColor: 'var(--color-mist-gray)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between' }}>
                <span><strong>Rendimiento Académico</strong> / <strong>Situación Financiera y Cobranzas</strong></span>
                <strong>+{capaA.directo_dw} filas aprobadas (≥85)</strong>
              </div>
              <div style={{ padding: '10px 14px', backgroundColor: 'var(--color-mist-gray)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between' }}>
                <span><strong>Catálogo de Estudiantes</strong> (Coincidencias / Nuevos)</span>
                <strong>Verificado ✓</strong>
              </div>
              <div style={{ padding: '10px 14px', backgroundColor: 'var(--color-mist-gray)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between' }}>
                <span><strong>Registros de Ingesta</strong> (A revisión ④)</span>
                <strong>{capaA.a_revision} pendientes</strong>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                onClick={() => setIsConfirmModalOpen(false)}
                className="sileo-btn"
                style={{ padding: '10px 18px', borderRadius: '8px', border: '1px solid var(--color-border)', backgroundColor: 'transparent' }}
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmInsertDw}
                disabled={isInserting}
                className="sileo-btn"
                style={{
                  padding: '10px 20px', borderRadius: '8px', backgroundColor: '#2563eb', color: '#ffffff',
                  border: 'none', fontWeight: '700'
                }}
              >
                {isInserting ? 'Insertando...' : 'Confirmar e Insertar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Pie Colapsado: Detalle del Modelo ─── */}
      <div className="floating-artifact" style={{ padding: '16px 20px', marginBottom: '28px' }}>
        <button
          onClick={() => setShowModelDetails(!showModelDetails)}
          style={{
            width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            background: 'none', border: 'none', cursor: 'pointer', padding: 0
          }}
        >
          <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-slate-gray)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={16} /> Detalle del modelo y calibración de inferencia
          </span>
          {showModelDetails ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {showModelDetails && (
          <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid var(--color-border)', display: 'flex', gap: '28px', flexWrap: 'wrap', fontSize: '12px' }}>
            <div>
              <span style={{ color: 'var(--color-slate-gray)' }}>Arquitectura: </span>
              <strong>{data?.modelo_info?.nombre}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--color-slate-gray)' }}>F1 en Validación: </span>
              <strong style={{ color: '#10b981' }}>{data?.modelo_info?.f1_validacion}</strong>
              <span style={{ color: 'var(--color-ash-gray)', marginLeft: '4px' }}>(Conjunto de validación)</span>
            </div>
            <div>
              <span style={{ color: 'var(--color-slate-gray)' }}>Umbral de corte: </span>
              <strong>{data?.modelo_info?.umbral_vigente}%</strong>
            </div>
          </div>
        )}
      </div>

      {/* ─── Navegación al Paso ④ ─── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          onClick={() => navigate(`/dataops/lote/${id}/texto`)}
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
          ← Volver a Texto Plano ②
        </button>

        <button
          onClick={() => navigate(`/dataops/revision?lote=${id}`)}
          className="sileo-btn"
          style={{
            padding: '14px 26px',
            borderRadius: '12px',
            backgroundColor: capaA.a_revision > 0 ? '#d97706' : '#2563eb',
            color: '#ffffff',
            border: 'none',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: '700',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            boxShadow: '0 4px 14px rgba(217, 119, 6, 0.3)'
          }}
        >
          Pasar a Revisión Humana ④ ({capaA.a_revision} pendientes) <ArrowRight size={18} />
        </button>
      </div>
      </>
    )}
  </BatchFlowLayout>
  );
}
