import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  UserCheck, AlertTriangle, CheckCircle2, RotateCcw, XCircle,
  HelpCircle, Eye, EyeOff, ShieldCheck, ArrowRight, CornerDownRight,
  Sparkles, Keyboard, History, Clock, Check, Edit3, Merge, UserX
} from 'lucide-react';
import BatchFlowLayout from './components/BatchFlowLayout';
import { dataopsApi } from '../../api/dataopsApi';
import { sileoToast } from '../../services/sileoToast';

export default function HumanReviewFlowView() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const batchId = searchParams.get('lote');

  const [activeTab, setActiveTab] = useState('PENDIENTES'); // 'PENDIENTES' | 'RESUELTOS'
  const [selectedReason, setSelectedReason] = useState('ALL');
  const [selectedItem, setSelectedItem] = useState(null);
  const [revealedCis, setRevealedCis] = useState({});
  const [pendingCommitMap, setPendingCommitMap] = useState({}); // itemId -> timerId

  // Modales
  const [isDiscardModalOpen, setIsDiscardModalOpen] = useState(false);
  const [discardNote, setDiscardNote] = useState('');
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editText, setEditText] = useState('');

  // Cola y Datos
  const [queueItems, setQueueItems] = useState([
    {
      id: 101,
      motivo: 'BAJA_CONFIANZA',
      motivo_label: 'Baja confianza',
      tipo_entidad: 'ESTUDIANTE',
      que_vio: 'Peres Mamani Jhuan, CI 4892019 LP, Gestión de Riesgos, nota 8.5',
      ci_enmascarado: '••••019 LP',
      ci_real: '4892019 LP',
      por_que_detuvo: 'El modelo no está seguro del nombre (confianza 62 < 85)',
      sugerencia: 'Pérez Mamani Juan',
      similitud: 88,
      destino_dw: 'DimEstudiante(ID: 412), FactCalificaciones(Nota: 85.0)'
    },
    {
      id: 102,
      motivo: 'CI_ILEGIBLE',
      motivo_label: 'CI ilegible',
      tipo_entidad: 'ESTUDIANTE',
      que_vio: 'Flores Condori Roberto, CI 5598?24 CB, Gestión de Riesgos, nota 7.4',
      ci_enmascarado: '••••?24 CB',
      ci_real: '5598?24 CB',
      por_que_detuvo: 'La cédula contiene un carácter corrupto o signo de interrogación (?)',
      sugerencia: 'Flores Condori Roberto (CI en catálogo: 5598124 CB)',
      similitud: 96,
      destino_dw: 'DimEstudiante(ID: 709), FactCalificaciones(Nota: 74.0)'
    },
    {
      id: 103,
      motivo: 'HOMONIMO_POTENCIAL',
      motivo_label: 'Posible homónimo',
      tipo_entidad: 'ESTUDIANTE',
      que_vio: 'Mamani Choque Andrea, CI 7821901 LP, Gestión de Riesgos, nota 6.8',
      ci_enmascarado: '••••901 LP',
      ci_real: '7821901 LP',
      por_que_detuvo: 'Existen dos estudiantes con el mismo nombre y carreras distintas',
      sugerencia: 'Mamani Choque Andrea (Ing. Comercial) vs Mamani Choque Andrea (Derecho)',
      similitud: 100,
      destino_dw: 'Requiere confirmar si es la misma persona o separar identidades'
    },
    {
      id: 104,
      motivo: 'CI_NOMBRE_DISCORDANTE',
      motivo_label: 'CI ≠ nombre',
      tipo_entidad: 'ESTUDIANTE',
      que_vio: 'Vargas Rios David, CI 4892019 LP, Gestión de Riesgos, nota 9.0',
      ci_enmascarado: '••••019 LP',
      ci_real: '4892019 LP',
      por_que_detuvo: 'El CI 4892019 LP pertenece en catálogo a Pérez Mamani Juan',
      sugerencia: 'Verificar si hubo error tipográfico en el número de CI',
      similitud: 45,
      destino_dw: 'Detenido por regla de integridad cruzada'
    },
    {
      id: 105,
      motivo: 'ENTIDAD_NUEVA',
      motivo_label: 'Entidad nueva',
      tipo_entidad: 'MODULO',
      que_vio: 'Gutiérrez Soliz Ana, CI 9812401 SC, Inteligencia de Negocios Aplicada, nota 90',
      ci_enmascarado: '••••401 SC',
      ci_real: '9812401 SC',
      por_que_detuvo: 'El módulo no existe en dim_modulo con este nombre exacto',
      sugerencia: 'Vincular a canónico: "Business Intelligence y Analytics (MOD-302)"',
      similitud: 82,
      destino_dw: 'Crear alias o nueva entrada en catálogo dim_modulo'
    }
  ]);

  const [resolvedHistory, setResolvedHistory] = useState([
    {
      id: 99,
      quien: 'Auditor Calidad (Tú)',
      cuando: 'Hace 15 min',
      antes: 'Peres Juan (CI: ••••019 LP)',
      despues: 'Pérez Mamani Juan (ID: 412) ✓ DW',
      motivo: 'Baja confianza',
      accion: 'Confirmó sugerencia'
    }
  ]);

  useEffect(() => {
    if (queueItems.length > 0 && !selectedItem) {
      setSelectedItem(queueItems[0]);
    }
  }, [queueItems]);

  // Atajos de teclado: A (Confirmar), E (Corregir), J / K (Navegar)
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ignorar si el usuario está escribiendo en un input o textarea
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

      if (e.key === 'a' || e.key === 'A') {
        if (selectedItem) handleConfirmSuggestion();
      } else if (e.key === 'e' || e.key === 'E') {
        if (selectedItem) handleOpenEdit();
      } else if (e.key === 'j' || e.key === 'J') {
        navigateQueue(1);
      } else if (e.key === 'k' || e.key === 'K') {
        navigateQueue(-1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedItem, queueItems]);

  const navigateQueue = (direction) => {
    if (!selectedItem || queueItems.length === 0) return;
    const currentIndex = queueItems.findIndex(q => q.id === selectedItem.id);
    const nextIndex = currentIndex + direction;
    if (nextIndex >= 0 && nextIndex < queueItems.length) {
      setSelectedItem(queueItems[nextIndex]);
    }
  };

  const toggleCi = (id) => {
    setRevealedCis(prev => ({ ...prev, [id]: !prev[id] }));
  };

  // Manejo de Deshacer Diferido (10s)
  const commitItemResolution = (resolvedItem, actionLabel, newText = null) => {
    const itemId = resolvedItem.id;

    // 1. Quitar de la cola visual inmediatamente
    setQueueItems(prev => prev.filter(q => q.id !== itemId));
    const nextItem = queueItems.find(q => q.id !== itemId);
    setSelectedItem(nextItem || null);

    // 2. Programar commit en 10 segundos
    const timerId = setTimeout(() => {
      // Commit definitivo en backend
      try {
        dataopsApi.confirmDwInsert({
          resolved_item_id: itemId,
          motivo: resolvedItem.motivo,
          accion: actionLabel
        });
      } catch (err) {
        console.warn('Error en commit diferido:', err);
      }

      // Pasar a historial de resueltos
      setResolvedHistory(prev => [
        {
          id: itemId,
          quien: 'Auditor Calidad (Tú)',
          cuando: 'Recién resuelto',
          antes: resolvedItem.que_vio,
          despues: newText || resolvedItem.destino_dw,
          motivo: resolvedItem.motivo_label,
          accion: actionLabel
        },
        ...prev
      ]);

      // Limpiar mapa
      setPendingCommitMap(prev => {
        const copy = { ...prev };
        delete copy[itemId];
        return copy;
      });
    }, 10000);

    setPendingCommitMap(prev => ({ ...prev, [itemId]: timerId }));

    // 3. Mostrar Toast con Deshacer (10s)
    sileoToast.info({
      title: `${actionLabel} (Diferido 10s)`,
      description: 'El registro se insertará formalmente al DW al cumplir 10s. Puedes deshacer ahora.',
      action: {
        label: 'Deshacer',
        onClick: () => handleUndo(resolvedItem, timerId)
      }
    });
  };

  const handleUndo = (itemToRestore, timerId) => {
    clearTimeout(timerId);
    setPendingCommitMap(prev => {
      const copy = { ...prev };
      delete copy[itemToRestore.id];
      return copy;
    });

    // Reingresar a la cola
    setQueueItems(prev => [itemToRestore, ...prev]);
    setSelectedItem(itemToRestore);

    sileoToast.success({
      title: 'Acción revocada',
      description: 'El caso ha vuelto a la cola de revisión sin tocar el Data Warehouse.'
    });
  };

  const handleConfirmSuggestion = () => {
    if (!selectedItem) return;
    commitItemResolution(selectedItem, 'Confirmó sugerencia');
  };

  const handleOpenEdit = () => {
    if (!selectedItem) return;
    setEditText(selectedItem.que_vio);
    setIsEditModalOpen(true);
  };

  const handleSaveEdit = () => {
    if (!selectedItem || !editText.trim()) return;
    commitItemResolution(selectedItem, 'Corrigió texto manualmente', editText);
    setIsEditModalOpen(false);
  };

  const handleOpenDiscard = () => {
    setDiscardNote('');
    setIsDiscardModalOpen(true);
  };

  const handleConfirmDiscard = () => {
    if (!selectedItem || !discardNote.trim()) {
      sileoToast.error({ title: 'Nota obligatoria', description: 'Debes indicar el motivo del descarte.' });
      return;
    }
    commitItemResolution(selectedItem, `Descartado: ${discardNote}`);
    setIsDiscardModalOpen(false);
  };

  const handleMergeEntities = () => {
    if (!selectedItem) return;
    commitItemResolution(selectedItem, 'Es la misma persona (fusionar alias)');
  };

  const handleSeparateEntities = () => {
    if (!selectedItem) return;
    commitItemResolution(selectedItem, 'Es otra persona (separar identidades)');
  };

  const handleLinkCanonical = () => {
    if (!selectedItem) return;
    commitItemResolution(selectedItem, 'Vinculado a módulo canónico existente');
  };

  const handleCreateNewInCatalog = () => {
    if (!selectedItem) return;
    commitItemResolution(selectedItem, 'Registrado como nueva entidad en catálogo');
  };

  // Filtrado de la cola por motivo
  const filteredQueue = queueItems.filter(item => {
    if (selectedReason === 'ALL') return true;
    return item.motivo === selectedReason;
  });

  // Conteo por motivo
  const reasonCounts = queueItems.reduce((acc, it) => {
    acc[it.motivo] = (acc[it.motivo] || 0) + 1;
    return acc;
  }, {});

  const totalPendientes = queueItems.length;
  const totalResueltos = resolvedHistory.length;
  const totalCasos = totalPendientes + totalResueltos;
  const progresoPorcentaje = totalCasos > 0 ? Math.round((totalResueltos / totalCasos) * 100) : 0;

  return (
    <BatchFlowLayout currentStep={4}>
      {/* ─── Encabezado y KPIs ─── */}
      <div className="floating-artifact" style={{ padding: '20px 24px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '13px', color: 'var(--color-slate-gray)', fontWeight: '600' }}>
              Progreso de Revisión de Excepciones
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '18px', marginTop: '6px' }}>
              <span style={{ fontSize: '18px', fontWeight: '800', color: '#f59e0b' }}>
                Pendientes: <strong>{totalPendientes}</strong>
              </span>
              <span style={{ color: 'var(--color-border)' }}>·</span>
              <span style={{ fontSize: '18px', fontWeight: '800', color: '#10b981' }}>
                Resueltos hoy: <strong>{totalResueltos}</strong>
              </span>
              <span style={{ color: 'var(--color-border)' }}>·</span>
              <span style={{ fontSize: '14px', color: 'var(--color-slate-gray)' }}>
                Progreso: <strong>{progresoPorcentaje}%</strong>
              </span>
            </div>
          </div>

          {/* Atajos de teclado informativos */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '12px',
            backgroundColor: 'var(--color-mist-gray)', padding: '8px 14px', borderRadius: '10px', fontSize: '12px'
          }}>
            <Keyboard size={16} color="var(--color-slate-gray)" />
            <span><kbd style={{ padding: '2px 6px', backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #ccc' }}>A</kbd> Confirmar</span>
            <span><kbd style={{ padding: '2px 6px', backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #ccc' }}>E</kbd> Corregir</span>
            <span><kbd style={{ padding: '2px 6px', backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #ccc' }}>J</kbd>/<kbd style={{ padding: '2px 6px', backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #ccc' }}>K</kbd> Navegar</span>
          </div>
        </div>

        {/* Barra de Progreso */}
        <div style={{ height: '8px', backgroundColor: '#e5e7eb', borderRadius: '4px', marginTop: '16px', overflow: 'hidden' }}>
          <div style={{ width: `${progresoPorcentaje}%`, height: '100%', backgroundColor: '#10b981', transition: 'width 0.3s ease' }} />
        </div>
      </div>

      {/* ─── Pestañas Pendientes vs Resueltos ─── */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        <button
          onClick={() => setActiveTab('PENDIENTES')}
          style={{
            padding: '10px 18px', borderRadius: '8px', fontSize: '13px', fontWeight: '700',
            border: 'none', cursor: 'pointer',
            backgroundColor: activeTab === 'PENDIENTES' ? '#2563eb' : 'var(--color-mist-gray)',
            color: activeTab === 'PENDIENTES' ? '#ffffff' : 'var(--color-slate-gray)'
          }}
        >
          Casos Pendientes ({totalPendientes})
        </button>
        <button
          onClick={() => setActiveTab('RESUELTOS')}
          style={{
            padding: '10px 18px', borderRadius: '8px', fontSize: '13px', fontWeight: '700',
            border: 'none', cursor: 'pointer',
            backgroundColor: activeTab === 'RESUELTOS' ? '#2563eb' : 'var(--color-mist-gray)',
            color: activeTab === 'RESUELTOS' ? '#ffffff' : 'var(--color-slate-gray)'
          }}
        >
          <History size={14} style={{ display: 'inline', marginRight: '6px' }} />
          Pestaña "Resueltos" ({totalResueltos})
        </button>
      </div>

      {activeTab === 'PENDIENTES' ? (
        /* ─── Vista Principal Maestro-Detalle ─── */
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px' }}>
          
          {/* Columna Izquierda: Cola por Motivo */}
          <div className="floating-artifact" style={{ padding: '20px', height: '620px', display: 'flex', flexDirection: 'column' }}>
            <h3 className="serif-heading" style={{ fontSize: '15px', margin: '0 0 12px 0', color: 'var(--color-ink-black)' }}>
              Cola por motivo
            </h3>

            {/* Selector de Motivos */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '14px', borderBottom: '1px solid var(--color-border)', paddingBottom: '12px' }}>
              <button
                onClick={() => setSelectedReason('ALL')}
                style={{
                  display: 'flex', justifyContent: 'space-between', padding: '8px 10px', borderRadius: '6px',
                  fontSize: '12px', border: 'none', cursor: 'pointer', textAlign: 'left',
                  backgroundColor: selectedReason === 'ALL' ? '#eff6ff' : 'transparent',
                  color: selectedReason === 'ALL' ? '#2563eb' : 'var(--color-slate-gray)',
                  fontWeight: selectedReason === 'ALL' ? '700' : '500'
                }}
              >
                <span>Todos los motivos</span>
                <strong>{totalPendientes}</strong>
              </button>
              {Object.entries(reasonCounts).map(([motivo, count]) => (
                <button
                  key={motivo}
                  onClick={() => setSelectedReason(motivo)}
                  style={{
                    display: 'flex', justifyContent: 'space-between', padding: '6px 10px', borderRadius: '6px',
                    fontSize: '12px', border: 'none', cursor: 'pointer', textAlign: 'left',
                    backgroundColor: selectedReason === motivo ? '#eff6ff' : 'transparent',
                    color: selectedReason === motivo ? '#2563eb' : 'var(--color-slate-gray)',
                    fontWeight: selectedReason === motivo ? '700' : '500'
                  }}
                >
                  <span>{motivo.replace(/_/g, ' ')}</span>
                  <span style={{
                    fontSize: '11px', padding: '1px 6px', borderRadius: '4px',
                    backgroundColor: selectedReason === motivo ? '#bfdbfe' : 'var(--color-mist-gray)'
                  }}>
                    {count}
                  </span>
                </button>
              ))}
            </div>

            {/* Lista de Casos */}
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {filteredQueue.map((item) => {
                const isSelected = selectedItem?.id === item.id;

                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedItem(item)}
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid',
                      borderColor: isSelected ? '#2563eb' : 'var(--color-border)',
                      backgroundColor: isSelected ? '#f8fafc' : 'var(--color-paper-white)',
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#b45309', fontWeight: '700' }}>
                      <span>{item.motivo_label}</span>
                      <span style={{ color: 'var(--color-ash-gray)' }}>#{item.id}</span>
                    </div>
                    <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-ink-black)', marginTop: '4px' }}>
                      {item.sugerencia}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', marginTop: '2px' }}>
                      CI: {revealedCis[item.id] ? item.ci_real : item.ci_enmascarado}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Columna Derecha: Detalle del Caso y Acciones Contextuales */}
          <div className="floating-artifact" style={{ padding: '28px', display: 'flex', flexDirection: 'column', gap: '22px' }}>
            {selectedItem ? (
              <>
                {/* 1. QUÉ VIO EL SISTEMA */}
                <div>
                  <div style={{ fontSize: '11px', fontWeight: '700', color: '#2563eb', letterSpacing: '0.5px', marginBottom: '6px' }}>
                    QUÉ VIO EL SISTEMA (TEXTO CRUDO)
                  </div>
                  <div style={{
                    padding: '14px', backgroundColor: 'var(--color-mist-gray)', borderRadius: '8px',
                    fontSize: '13.5px', fontFamily: 'var(--font-mono)', color: 'var(--color-ink-black)'
                  }}>
                    "{selectedItem.que_vio}"
                  </div>
                </div>

                {/* 2. POR QUÉ SE DETUVO */}
                <div>
                  <div style={{ fontSize: '11px', fontWeight: '700', color: '#b45309', letterSpacing: '0.5px', marginBottom: '6px' }}>
                    POR QUÉ SE DETUVO (DIAGNÓSTICO EN LENGUAJE LLANO)
                  </div>
                  <div style={{
                    padding: '14px', backgroundColor: '#fffbeb', borderRadius: '8px', borderLeft: '4px solid #f59e0b',
                    fontSize: '13.5px', color: '#92400e', fontWeight: '600'
                  }}>
                    {selectedItem.por_que_detuvo}
                  </div>
                </div>

                {/* 3. SUGERENCIA DEL CATÁLOGO */}
                <div>
                  <div style={{ fontSize: '11px', fontWeight: '700', color: '#166534', letterSpacing: '0.5px', marginBottom: '6px' }}>
                    SUGERENCIA DEL CATÁLOGO CANÓNICO
                  </div>
                  <div style={{
                    padding: '14px', backgroundColor: '#f0fdf4', borderRadius: '8px', borderLeft: '4px solid #10b981',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                  }}>
                    <div>
                      <div style={{ fontSize: '14px', fontWeight: '700', color: '#15803d' }}>
                        {selectedItem.sugerencia}
                      </div>
                      <div style={{ fontSize: '12px', color: '#166534', marginTop: '2px' }}>
                        Similitud fonética / fuzzy: {selectedItem.similitud}%
                      </div>
                    </div>
                    <button
                      onClick={() => toggleCi(selectedItem.id)}
                      className="sileo-btn"
                      style={{
                        padding: '4px 10px', fontSize: '11px', borderRadius: '6px',
                        backgroundColor: '#ffffff', border: '1px solid #a7f3d0', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', gap: '4px'
                      }}
                    >
                      {revealedCis[selectedItem.id] ? <EyeOff size={13} /> : <Eye size={13} />}
                      {revealedCis[selectedItem.id] ? 'Ocultar CI' : 'Revelar CI (Auditado)'}
                    </button>
                  </div>
                </div>

                {/* 4. ACCIONES SEGÚN EL MOTIVO */}
                <div>
                  <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--color-slate-gray)', letterSpacing: '0.5px', marginBottom: '10px' }}>
                    ACCIONES RECOMENDADAS PARA ESTE CASO
                  </div>
                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    {/* Botones contextuales según motivo */}
                    {['BAJA_CONFIANZA', 'CI_ILEGIBLE'].includes(selectedItem.motivo) && (
                      <>
                        <button
                          onClick={handleConfirmSuggestion}
                          className="sileo-btn"
                          style={{
                            padding: '10px 18px', backgroundColor: '#2563eb', color: '#fff',
                            border: 'none', borderRadius: '8px', fontWeight: '700', fontSize: '13px', cursor: 'pointer'
                          }}
                        >
                          ✓ Confirmar sugerencia [A]
                        </button>
                        <button
                          onClick={handleOpenEdit}
                          className="sileo-btn"
                          style={{
                            padding: '10px 16px', backgroundColor: 'var(--color-mist-gray)',
                            border: '1px solid var(--color-border)', borderRadius: '8px', fontSize: '13px', cursor: 'pointer'
                          }}
                        >
                          <Edit3 size={14} style={{ display: 'inline', marginRight: '4px' }} /> Corregir texto [E]
                        </button>
                        <button
                          onClick={handleOpenDiscard}
                          className="sileo-btn"
                          style={{
                            padding: '10px 16px', backgroundColor: 'transparent',
                            border: '1px solid #f87171', color: '#dc2626', borderRadius: '8px', fontSize: '13px', cursor: 'pointer'
                          }}
                        >
                          Descartar fila*
                        </button>
                      </>
                    )}

                    {['HOMONIMO_POTENCIAL', 'CI_NOMBRE_DISCORDANTE'].includes(selectedItem.motivo) && (
                      <>
                        <button
                          onClick={handleMergeEntities}
                          className="sileo-btn"
                          style={{
                            padding: '10px 16px', backgroundColor: '#2563eb', color: '#fff',
                            border: 'none', borderRadius: '8px', fontWeight: '700', fontSize: '13px', cursor: 'pointer'
                          }}
                        >
                          <Merge size={14} style={{ display: 'inline', marginRight: '4px' }} /> Es la misma persona (Fusionar)
                        </button>
                        <button
                          onClick={handleSeparateEntities}
                          className="sileo-btn"
                          style={{
                            padding: '10px 16px', backgroundColor: 'var(--color-mist-gray)',
                            border: '1px solid var(--color-border)', borderRadius: '8px', fontSize: '13px', cursor: 'pointer'
                          }}
                        >
                          <UserX size={14} style={{ display: 'inline', marginRight: '4px' }} /> Es otra persona (Separar)
                        </button>
                        <button
                          onClick={handleOpenEdit}
                          className="sileo-btn"
                          style={{
                            padding: '10px 16px', backgroundColor: 'var(--color-mist-gray)',
                            border: '1px solid var(--color-border)', borderRadius: '8px', fontSize: '13px', cursor: 'pointer'
                          }}
                        >
                          Corregir
                        </button>
                      </>
                    )}

                    {selectedItem.motivo === 'ENTIDAD_NUEVA' && (
                      <>
                        <button
                          onClick={handleLinkCanonical}
                          className="sileo-btn"
                          style={{
                            padding: '10px 16px', backgroundColor: '#2563eb', color: '#fff',
                            border: 'none', borderRadius: '8px', fontWeight: '700', fontSize: '13px', cursor: 'pointer'
                          }}
                        >
                          Vincular al canónico (guardar alias)
                        </button>
                        <button
                          onClick={handleCreateNewInCatalog}
                          className="sileo-btn"
                          style={{
                            padding: '10px 16px', backgroundColor: 'var(--color-mist-gray)',
                            border: '1px solid var(--color-border)', borderRadius: '8px', fontSize: '13px', cursor: 'pointer'
                          }}
                        >
                          Crear nuevo en catálogo
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* 5. VISTA PREVIA DE DESTINO */}
                <div style={{
                  padding: '12px 16px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid var(--color-border)',
                  fontSize: '12.5px', color: 'var(--color-slate-gray)'
                }}>
                  <span>Vista previa de impacto: </span>
                  <strong style={{ color: 'var(--color-ink-black)', fontFamily: 'var(--font-mono)' }}>
                    {selectedItem.destino_dw}
                  </strong>
                </div>
              </>
            ) : (
              <div style={{ padding: '60px', textAlign: 'center', color: 'var(--color-slate-gray)' }}>
                Todos los casos de esta cola han sido resueltos.
              </div>
            )}
          </div>
        </div>
      ) : (
        /* ─── Pestaña "Resueltos" (Auditoría) ─── */
        <div className="floating-artifact" style={{ padding: '24px' }}>
          <h3 className="serif-heading" style={{ fontSize: '16px', margin: '0 0 16px 0', color: 'var(--color-ink-black)' }}>
            Historial de decisiones auditadas (log_auditoria_nlp)
          </h3>
          <div style={{ overflowX: 'auto', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--color-mist-gray)', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ padding: '10px 14px' }}>Quién</th>
                  <th style={{ padding: '10px 14px' }}>Cuándo</th>
                  <th style={{ padding: '10px 14px' }}>Antes</th>
                  <th style={{ padding: '10px 14px' }}>Después (Destino DW)</th>
                  <th style={{ padding: '10px 14px' }}>Motivo</th>
                  <th style={{ padding: '10px 14px' }}>Acción</th>
                </tr>
              </thead>
              <tbody>
                {resolvedHistory.map((res, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '10px 14px', fontWeight: '600' }}>{res.quien}</td>
                    <td style={{ padding: '10px 14px', color: 'var(--color-ash-gray)' }}>{res.cuando}</td>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{res.antes}</td>
                    <td style={{ padding: '10px 14px', fontWeight: '700', color: '#10b981' }}>{res.despues}</td>
                    <td style={{ padding: '10px 14px' }}>{res.motivo}</td>
                    <td style={{ padding: '10px 14px', color: '#2563eb' }}>{res.accion}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── Modal de Descarte Obligatorio ─── */}
      {isDiscardModalOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.6)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px'
        }}>
          <div className="floating-artifact" style={{ maxWidth: '480px', width: '100%', padding: '24px' }}>
            <h3 className="serif-heading" style={{ fontSize: '17px', margin: '0 0 10px 0', color: '#dc2626' }}>
              Justificación obligatoria de descarte
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: '0 0 16px 0' }}>
              El descarte eliminará esta fila del pipeline y quedará asentado en el log de auditoría.
            </p>

            <textarea
              rows={3}
              value={discardNote}
              onChange={(e) => setDiscardNote(e.target.value)}
              placeholder="Ej: Fila corrupta no pertenece a la carrera de Gestión de Riesgos..."
              style={{
                width: '100%', padding: '10px 12px', borderRadius: '8px',
                border: '1px solid var(--color-border)', fontSize: '13px', boxSizing: 'border-box'
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' }}>
              <button
                onClick={() => setIsDiscardModalOpen(false)}
                className="sileo-btn"
                style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid var(--color-border)', background: 'transparent' }}
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmDiscard}
                className="sileo-btn"
                style={{
                  padding: '8px 18px', borderRadius: '6px', backgroundColor: '#dc2626', color: '#fff',
                  border: 'none', fontWeight: '700'
                }}
              >
                Confirmar Descarte
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Modal de Edición Manual ─── */}
      {isEditModalOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.6)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px'
        }}>
          <div className="floating-artifact" style={{ maxWidth: '520px', width: '100%', padding: '24px' }}>
            <h3 className="serif-heading" style={{ fontSize: '17px', margin: '0 0 10px 0', color: 'var(--color-ink-black)' }}>
              Corregir texto del registro
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-slate-gray)', margin: '0 0 16px 0' }}>
              Edita manualmente el texto para que coincida exactamente con los catálogos del sistema.
            </p>

            <input
              type="text"
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              style={{
                width: '100%', padding: '10px 12px', borderRadius: '8px',
                border: '1px solid var(--color-border)', fontSize: '13px', boxSizing: 'border-box'
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' }}>
              <button
                onClick={() => setIsEditModalOpen(false)}
                className="sileo-btn"
                style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid var(--color-border)', background: 'transparent' }}
              >
                Cancelar
              </button>
              <button
                onClick={handleSaveEdit}
                className="sileo-btn"
                style={{
                  padding: '8px 18px', borderRadius: '6px', backgroundColor: '#2563eb', color: '#fff',
                  border: 'none', fontWeight: '700'
                }}
              >
                Guardar y Aplicar
              </button>
            </div>
          </div>
        </div>
      )}
    </BatchFlowLayout>
  );
}
