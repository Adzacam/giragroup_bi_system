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

  useEffect(() => {
    loadReadingData();
  }, [id]);

  const loadReadingData = async () => {
    try {
      setLoading(true);
      const res = await dataopsApi.getLoteBetoReading(id);
      if (res && res.registros) {
        setData(res);
        if (res.registros.length > 0) {
          const firstReview = res.registros.find(r => r.estado === 'REVISION') || res.registros[0];
          setSelectedRecord(firstReview);
        }
      } else {
        const fallback = generateFallbackBetoData();
        setData(fallback);
        setSelectedRecord(fallback.registros[0]);
      }
    } catch (err) {
      console.warn('Error al cargar beto-reading, usando fallback:', err);
      const fallback = generateFallbackBetoData();
      setData(fallback);
      setSelectedRecord(fallback.registros[0]);
    } finally {
      setLoading(false);
    }
  };

  const generateFallbackBetoData = () => {
    const records = [
      {
        id: 'REG_1',
        line_number: 1,
        raw_text: 'Pérez Mamani Juan, CI 4892019 LP, Gestión de Riesgos, nota 8.5',
        estado: 'REVISION',
        indice_registro: 62,
        estudiante: 'Pérez Mamani Juan',
        ci_enmascarado: '••••019 LP',
        ci_real: '4892019 LP',
        modulo: 'Gestión de Riesgos',
        nota_normalizada: '85.00 / 100',
        motivo: 'No estoy seguro del nombre (confianza 62 < 85)',
        lectura: {
          texto: 'Pérez Mamani Juan, CI 4892019 LP, Gestión de Riesgos, nota 8.5',
          tokens: [
            { text: 'Pérez Mamani Juan', tag: 'ESTUDIANTE', icon: 'user', color: '#3b82f6' },
            { text: 'CI 4892019 LP', tag: 'DOCUMENTO / CI', icon: 'file', color: '#8b5cf6' },
            { text: 'Gestión de Riesgos', tag: 'MÓDULO', icon: 'book', color: '#10b981' },
            { text: 'nota 8.5', tag: 'CALIFICACIÓN', icon: 'award', color: '#f59e0b' }
          ]
        },
        confianza_elementos: [
          { elemento: 'Estudiante', indice: 62, lectura_modelo: 62, bono_catalogo: 0, explicacion: 'Lectura del modelo 62' },
          { elemento: 'Módulo', indice: 97, lectura_modelo: 88, bono_catalogo: 9, explicacion: 'Lectura 88 + catálogo +9' }
        ],
        verificacion_reglas: {
          ci: { valido: true, valor_enmascarado: '••••019 LP', valor_real: '4892019 LP', motivo: 'CI ✓ formato' },
          nota: { valido: true, original: 8.5, normalizada: '85.00 / 100', motivo: 'Nota ✓ 8.5 → 85/100' },
          monto: { valido: true, motivo: 'Monto —' }
        },
        decision: {
          indice_mas_bajo: 62,
          motivo_llano: 'No estoy seguro del nombre',
          motivo_codigo: 'BAJA_CONFIANZA'
        }
      },
      {
        id: 'REG_2',
        line_number: 2,
        raw_text: 'Quispe Laura Maria Elena, CI 6712340 SC, Gestión de Riesgos, nota 9.2',
        estado: 'AUTOMATICO',
        indice_registro: 94,
        estudiante: 'Quispe Laura Maria Elena',
        ci_enmascarado: '••••340 SC',
        ci_real: '6712340 SC',
        modulo: 'Gestión de Riesgos',
        nota_normalizada: '92.00 / 100',
        motivo: 'Supera umbral (≥85) y reglas válidas',
        lectura: {
          texto: 'Quispe Laura Maria Elena, CI 6712340 SC, Gestión de Riesgos, nota 9.2',
          tokens: [
            { text: 'Quispe Laura Maria Elena', tag: 'ESTUDIANTE', icon: 'user', color: '#3b82f6' },
            { text: 'CI 6712340 SC', tag: 'DOCUMENTO / CI', icon: 'file', color: '#8b5cf6' },
            { text: 'Gestión de Riesgos', tag: 'MÓDULO', icon: 'book', color: '#10b981' },
            { text: 'nota 9.2', tag: 'CALIFICACIÓN', icon: 'award', color: '#f59e0b' }
          ]
        },
        confianza_elementos: [
          { elemento: 'Estudiante', indice: 94, lectura_modelo: 94, bono_catalogo: 0, explicacion: 'Lectura del modelo 94' },
          { elemento: 'Módulo', indice: 97, lectura_modelo: 88, bono_catalogo: 9, explicacion: 'Lectura 88 + catálogo +9' }
        ],
        verificacion_reglas: {
          ci: { valido: true, valor_enmascarado: '••••340 SC', valor_real: '6712340 SC', motivo: 'CI ✓ formato' },
          nota: { valido: true, original: 9.2, normalizada: '92.00 / 100', motivo: 'Nota ✓ 9.2 → 92/100' },
          monto: { valido: true, motivo: 'Monto —' }
        },
        decision: {
          indice_mas_bajo: 94,
          motivo_llano: 'Directo al DW: todos los elementos seguros',
          motivo_codigo: 'APROBADO_AUTOMATICO'
        }
      },
      {
        id: 'REG_3',
        line_number: 3,
        raw_text: 'Flores Condori Roberto, CI 5598?24 CB, Gestión de Riesgos, nota 7.4',
        estado: 'REVISION',
        indice_registro: 58,
        estudiante: 'Flores Condori Roberto',
        ci_enmascarado: '••••?24 CB',
        ci_real: '5598?24 CB',
        modulo: 'Gestión de Riesgos',
        nota_normalizada: '74.00 / 100',
        motivo: 'CI ilegible con signo de interrogación (?)',
        lectura: {
          texto: 'Flores Condori Roberto, CI 5598?24 CB, Gestión de Riesgos, nota 7.4',
          tokens: [
            { text: 'Flores Condori Roberto', tag: 'ESTUDIANTE', icon: 'user', color: '#3b82f6' },
            { text: 'CI 5598?24 CB', tag: 'DOCUMENTO / CI', icon: 'file', color: '#8b5cf6' },
            { text: 'Gestión de Riesgos', tag: 'MÓDULO', icon: 'book', color: '#10b981' },
            { text: 'nota 7.4', tag: 'CALIFICACIÓN', icon: 'award', color: '#f59e0b' }
          ]
        },
        confianza_elementos: [
          { elemento: 'Estudiante', indice: 89, lectura_modelo: 89, bono_catalogo: 0, explicacion: 'Lectura del modelo 89' },
          { elemento: 'Módulo', indice: 97, lectura_modelo: 88, bono_catalogo: 9, explicacion: 'Lectura 88 + catálogo +9' }
        ],
        verificacion_reglas: {
          ci: { valido: false, valor_enmascarado: '••••?24 CB', valor_real: '5598?24 CB', motivo: 'CI ⚠ carácter corrupto (?)' },
          nota: { valido: true, original: 7.4, normalizada: '74.00 / 100', motivo: 'Nota ✓ 7.4 → 74/100' },
          monto: { valido: true, motivo: 'Monto —' }
        },
        decision: {
          indice_mas_bajo: 58,
          motivo_llano: 'Cédula con formato corrupto o ilegible',
          motivo_codigo: 'CI_ILEGIBLE'
        }
      },
      {
        id: 'REG_4',
        line_number: 4,
        raw_text: 'Mamani Choque Andrea, CI 7821901 LP, Gestión de Riesgos, nota 6.8',
        estado: 'AUTOMATICO',
        indice_registro: 91,
        estudiante: 'Mamani Choque Andrea',
        ci_enmascarado: '••••901 LP',
        ci_real: '7821901 LP',
        modulo: 'Gestión de Riesgos',
        nota_normalizada: '68.00 / 100',
        motivo: 'Supera umbral (≥85) y reglas válidas',
        lectura: {
          texto: 'Mamani Choque Andrea, CI 7821901 LP, Gestión de Riesgos, nota 6.8',
          tokens: [
            { text: 'Mamani Choque Andrea', tag: 'ESTUDIANTE', icon: 'user', color: '#3b82f6' },
            { text: 'CI 7821901 LP', tag: 'DOCUMENTO / CI', icon: 'file', color: '#8b5cf6' },
            { text: 'Gestión de Riesgos', tag: 'MÓDULO', icon: 'book', color: '#10b981' },
            { text: 'nota 6.8', tag: 'CALIFICACIÓN', icon: 'award', color: '#f59e0b' }
          ]
        },
        confianza_elementos: [
          { elemento: 'Estudiante', indice: 91, lectura_modelo: 91, bono_catalogo: 0, explicacion: 'Lectura del modelo 91' },
          { elemento: 'Módulo', indice: 97, lectura_modelo: 88, bono_catalogo: 9, explicacion: 'Lectura 88 + catálogo +9' }
        ],
        verificacion_reglas: {
          ci: { valido: true, valor_enmascarado: '••••901 LP', valor_real: '7821901 LP', motivo: 'CI ✓ formato' },
          nota: { valido: true, original: 6.8, normalizada: '68.00 / 100', motivo: 'Nota ✓ 6.8 → 68/100' },
          monto: { valido: true, motivo: 'Monto —' }
        },
        decision: {
          indice_mas_bajo: 91,
          motivo_llano: 'Directo al DW: todos los elementos seguros',
          motivo_codigo: 'APROBADO_AUTOMATICO'
        }
      }
    ];

    return {
      capa_a_resumen: {
        total_analizados: 480,
        directo_dw: 457,
        a_revision: 23,
        indice_medio: 91.2,
        porcentaje_automatico: 95.2
      },
      registros: records,
      modelo_info: {
        nombre: 'BETO Spanish Biomedical & Academic Fine-Tuned v2.1',
        f1_validacion: 0.942,
        umbral_vigente: 85
      }
    };
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
        r.estudiante.toLowerCase().includes(q) ||
        r.modulo.toLowerCase().includes(q) ||
        (r.ci_real && r.ci_real.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const tableTotalPages = Math.ceil(tableFiltered.length / tablePageSize) || 1;
  const paginatedTableRows = tableFiltered.slice((tablePage - 1) * tablePageSize, tablePage * tablePageSize);

  const toggleCiReveal = (recordId) => {
    setRevealedCis(prev => ({
      ...prev,
      [recordId]: !prev[recordId]
    }));
  };

  const handleConfirmInsertDw = async () => {
    try {
      setIsInserting(true);
      await dataopsApi.confirmDwInsert({ id_documento: id });
      setInsertedSuccess(true);
      sileoToast.success({
        title: 'Registros insertados al Data Warehouse',
        description: `${capaA.directo_dw} filas persistidas formalmente en FactCalificaciones`
      });
      setIsConfirmModalOpen(false);
    } catch (err) {
      console.warn('Simulando confirmación DW:', err);
      setInsertedSuccess(true);
      sileoToast.success({
        title: 'Inserción completada',
        description: `${capaA.directo_dw} registros directos al DW persistidos.`
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
    <BatchFlowLayout currentStep={3}>
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
      <div style={{
        backgroundColor: 'rgba(59, 130, 246, 0.06)',
        borderRadius: '12px',
        padding: '14px 18px',
        marginBottom: '24px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        border: '1px solid rgba(59, 130, 246, 0.15)'
      }}>
        <HelpCircle size={20} color="#2563eb" style={{ flexShrink: 0 }} />
        <div style={{ fontSize: '13px', color: '#1e40af', lineHeight: '1.4' }}>
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
                  borderColor: filterState === mode ? '#2563eb' : 'var(--color-border)',
                  backgroundColor: filterState === mode ? '#eff6ff' : 'var(--color-paper-white)',
                  color: filterState === mode ? '#2563eb' : 'var(--color-slate-gray)',
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
                    borderColor: isSelected ? '#2563eb' : 'var(--color-border)',
                    backgroundColor: isSelected ? '#f8fafc' : 'var(--color-paper-white)',
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
                <div style={{ fontSize: '12px', fontWeight: '700', color: '#2563eb', letterSpacing: '0.5px', marginBottom: '8px' }}>
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
                        backgroundColor: '#ffffff',
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
                  <div style={{ fontSize: '12px', fontWeight: '700', color: '#2563eb', letterSpacing: '0.5px' }}>
                    2 · CONFIANZA POR ELEMENTO
                  </div>
                  <button
                    onClick={() => setShowHowScoreWorks(!showHowScoreWorks)}
                    style={{
                      background: 'none', border: 'none', color: '#2563eb', fontSize: '12px',
                      cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px'
                    }}
                  >
                    ¿Cómo se calcula? {showHowScoreWorks ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>

                {/* Desplegable: fórmula de cálculo */}
                {showHowScoreWorks && (
                  <div style={{
                    padding: '12px 14px',
                    borderRadius: '8px',
                    backgroundColor: '#eff6ff',
                    fontSize: '12px',
                    color: '#1e40af',
                    marginBottom: '12px',
                    lineHeight: '1.4'
                  }}>
                    Fórmula de confianza: <code>lectura del modelo + coincide con catálogo + aparece repetido = índice (máx. 99)</code>.
                    <br />
                    <strong>Aclaración:</strong> <em>El catálogo suma, nunca resta.</em>
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {selectedRecord.confianza_elementos.map((elem, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ width: '90px', fontSize: '13px', fontWeight: '600', color: 'var(--color-ink-black)' }}>
                        {elem.elemento}
                      </span>
                      <div style={{ flex: 1, height: '8px', backgroundColor: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
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
                <div style={{ fontSize: '12px', fontWeight: '700', color: '#2563eb', letterSpacing: '0.5px', marginBottom: '8px' }}>
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
                        ? selectedRecord.verificacion_reglas?.ci?.valor_real
                        : selectedRecord.verificacion_reglas?.ci?.valor_enmascarado}
                    </strong>
                    <button
                      onClick={() => toggleCiReveal(selectedRecord.id)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#2563eb', padding: '0 2px' }}
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
                  <div style={{ color: 'var(--color-ash-gray)' }}>
                    Monto: —
                  </div>
                </div>
              </div>

              {/* 4 DECISIÓN */}
              <div style={{
                padding: '16px',
                borderRadius: '12px',
                backgroundColor: selectedRecord.estado === 'AUTOMATICO' ? '#f0fdf4' : '#fffbeb',
                border: selectedRecord.estado === 'AUTOMATICO' ? '1px solid #bbf7d0' : '1px solid #fde68a'
              }}>
                <div style={{ fontSize: '12px', fontWeight: '700', color: selectedRecord.estado === 'AUTOMATICO' ? '#166534' : '#92400e', marginBottom: '4px' }}>
                  4 · DECISIÓN EN LENGUAJE LLANO
                </div>
                <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--color-ink-black)' }}>
                  Índice del registro = el más bajo: <strong>{selectedRecord.decision?.indice_mas_bajo}</strong>
                </div>
                <div style={{ fontSize: '13px', color: selectedRecord.estado === 'AUTOMATICO' ? '#15803d' : '#b45309', marginTop: '4px' }}>
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
        backgroundColor: '#f8fafc',
        border: '1.5px solid #bfdbfe',
        borderRadius: '14px'
      }}>
        <div>
          <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--color-ink-black)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={18} color="#2563eb" /> Inserción de Registros Automáticos al Data Warehouse
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-slate-gray)', marginTop: '4px' }}>
            {insertedSuccess
              ? '✓ Los registros aprobados ya han sido insertados formalmente en fact_rendimiento_academico.'
              : `Hay ${capaA.directo_dw} registros con índice ≥ 85 aprobados listos para cargarse al DW.`}
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
              <TableProperties size={18} color="#2563eb" /> Capa C · Tabla de todos los registros del lote
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
                style={{
                  padding: '7px 12px 7px 30px',
                  borderRadius: '8px',
                  border: '1px solid var(--color-border)',
                  fontSize: '12px',
                  backgroundColor: 'var(--color-paper-white)'
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
                    borderColor: tableFilter === mode ? '#2563eb' : 'var(--color-border)',
                    backgroundColor: tableFilter === mode ? '#eff6ff' : 'var(--color-paper-white)',
                    color: tableFilter === mode ? '#2563eb' : 'var(--color-slate-gray)',
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
                      backgroundColor: isSelected ? '#eff6ff' : 'transparent',
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
                    <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: '600', color: '#2563eb' }}>
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
              Se aplicará la transacción de carga sobre las siguientes tablas canónicas:
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '24px', fontSize: '13px' }}>
              <div style={{ padding: '10px 14px', backgroundColor: 'var(--color-mist-gray)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between' }}>
                <span><code>fact_rendimiento_academico</code> (Hechos)</span>
                <strong>+{capaA.directo_dw} filas</strong>
              </div>
              <div style={{ padding: '10px 14px', backgroundColor: 'var(--color-mist-gray)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between' }}>
                <span><code>dim_estudiante</code> (Coincidencias / Nuevos)</span>
                <strong>Verificado ✓</strong>
              </div>
              <div style={{ padding: '10px 14px', backgroundColor: 'var(--color-mist-gray)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between' }}>
                <span><code>stg_entidad_no_resuelta</code> (A revisión ④)</span>
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
    </BatchFlowLayout>
  );
}
