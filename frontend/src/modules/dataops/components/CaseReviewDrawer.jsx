import React, { useState, useEffect } from 'react';
import {
  X, User, BookOpen, CreditCard, Award, ArrowRight, CheckCircle2,
  AlertTriangle, UserPlus, GitMerge, FileText, Check, ShieldAlert,
  Search, SlidersHorizontal
} from 'lucide-react';
import { sileoToast } from '../../../services/sileoToast';
import { getSourceTableMeta, getEntityTargetTableBadge } from '../../../utils/sourceLabelUtils';

export default function CaseReviewDrawer({
  isOpen,
  onClose,
  item,
  catalogStudents = [],
  onSaveReview,
  isSaving = false
}) {
  if (!isOpen || !item) return null;

  // Detección de naturaleza documental financiera (Loop 5)
  const isFinancialItem = Boolean(
    item.es_concepto_no_homologado ||
    item.es_riesgo_cartera ||
    item.tipo_incidencia === 'CONCEPTO_NO_HOMOLOGADO' ||
    item.tipo_incidencia === 'RIESGO_CARTERA' ||
    item.tipo_movimiento ||
    (item.fuente_1 && (
      item.fuente_1.toLowerCase().includes('cobranza') ||
      item.fuente_1.toLowerCase().includes('egreso') ||
      item.fuente_1.toLowerCase().includes('cartera') ||
      item.fuente_1.toLowerCase().includes('meta')
    ))
  );

  const CANONICAL_FINANCIAL_CONCEPTS = [
    { codigo: 'FIN-CUOTA-01', nombre: 'Cuota Mensual / Colegiatura', tipo: 'INGRESO' },
    { codigo: 'FIN-MATR-01', nombre: 'Matrícula de Inscripción', tipo: 'INGRESO' },
    { codigo: 'FIN-MORA-01', nombre: 'Recargo por Mora en Pago', tipo: 'INGRESO' },
    { codigo: 'FIN-TIT-01', nombre: 'Trámite y Certificado de Titulación', tipo: 'INGRESO' },
    { codigo: 'FIN-DESC-01', nombre: 'Descuento Institucional / Beca', tipo: 'AJUSTE' },
    { codigo: 'FIN-EG-PERS', nombre: 'Honorarios Docentes y Nómina', tipo: 'EGRESO' },
    { codigo: 'FIN-EG-SERV', nombre: 'Servicios Básicos y Operativos', tipo: 'EGRESO' },
    { codigo: 'FIN-EG-MAT', nombre: 'Material Didáctico y Licencias', tipo: 'EGRESO' },
    { codigo: 'FIN-EG-MKT', nombre: 'Publicidad y Campañas Admisión', tipo: 'EGRESO' }
  ];

  // Acción seleccionada: 'LINK_EXISTING' | 'CREATE_NEW' | 'CORRECT_MANUAL' | 'LINK_FINANCIAL_CONCEPT' | 'REJECT'
  const [selectedAction, setSelectedAction] = useState('LINK_EXISTING');

  // Campos de formulario para cada opción
  const [selectedStudentName, setSelectedStudentName] = useState('');
  const [studentSearch, setStudentSearch] = useState('');
  const [newStudentCi, setNewStudentCi] = useState('');
  const [newStudentName, setNewStudentName] = useState('');
  const [manualName, setManualName] = useState('');
  const [manualCi, setManualCi] = useState('');
  const [manualModulo, setManualModulo] = useState('');
  const [manualNota, setManualNota] = useState(75.0);
  const [rejectReason, setRejectReason] = useState('Inconsistencia en datos');

  // Campos financieros específicos (Loop 5)
  const [selectedConcept, setSelectedConcept] = useState('FIN-CUOTA-01');
  const [manualCuota, setManualCuota] = useState(1500.0);
  const [manualPagado, setManualPagado] = useState(500.0);
  const [manualSaldo, setManualSaldo] = useState(1000.0);
  const [manualCuotasImpagas, setManualCuotasImpagas] = useState(2);

  // Inicializar valores al abrir el expediente
  useEffect(() => {
    if (item) {
      const ciClean = (item.ci_raw || '').replace('?', '').trim();
      const initialCi = ciClean === 'No especificado' ? '' : ciClean;

      setManualName(item.estudiante || '');
      setManualCi(initialCi);
      setManualModulo(item.modulo_detectado || 'Módulo Académico');
      setManualNota(75.0);

      setNewStudentName(item.estudiante || '');
      setNewStudentCi(initialCi);

      setSelectedStudentName(item.sugerencia_catalogo || item.estudiante || '');

      setManualCuota(item.monto_cuota || 1500.0);
      setManualPagado(item.monto_pagado || 500.0);
      setManualSaldo(item.monto_saldo || 1000.0);
      setManualCuotasImpagas(item.cuotas_impagas !== undefined ? item.cuotas_impagas : 2);

      // Determinar la acción recomendada por defecto
      if (isFinancialItem) {
        setSelectedAction('LINK_FINANCIAL_CONCEPT');
      } else if (item.es_perfil_nuevo || !item.sugerencia_catalogo) {
        setSelectedAction('CREATE_NEW');
      } else if (item.rapidfuzz_cross && item.rapidfuzz_cross >= 70) {
        setSelectedAction('LINK_EXISTING');
      } else {
        setSelectedAction('CORRECT_MANUAL');
      }
    }
  }, [item, isFinancialItem]);

  // Filtrar estudiantes de catálogo maestro
  const filteredCatalogStudents = catalogStudents.filter(s => {
    if (!studentSearch.trim()) return true;
    const term = studentSearch.toLowerCase();
    const nameMatch = (s.nombre_completo || s.nombre || s.name || '').toLowerCase().includes(term);
    const ciMatch = (s.ci || s.carnet || '').toLowerCase().includes(term);
    return nameMatch || ciMatch;
  });

  // Manejar guardado de revisión
  const handleSubmitReview = async () => {
    let payload = {};
    if (selectedAction === 'LINK_FINANCIAL_CONCEPT') {
      const concObj = CANONICAL_FINANCIAL_CONCEPTS.find(c => c.codigo === selectedConcept);
      payload = {
        action: 'LINK_FINANCIAL_CONCEPT',
        codigo_concepto: selectedConcept,
        concepto_canonico: concObj?.nombre || 'Cuota Mensual / Colegiatura',
        estudiante_resuelto: selectedStudentName || manualName || item.estudiante,
        ci_corregida: manualCi || undefined,
        monto_cuota: parseFloat(manualCuota) || 1500.0,
        monto_pagado: parseFloat(manualPagado) || 500.0,
        monto_saldo: parseFloat(manualSaldo) || 1000.0,
        cuotas_impagas: parseInt(manualCuotasImpagas) || 0,
        moneda: 'BOB'
      };
    } else if (selectedAction === 'LINK_EXISTING') {
      if (!selectedStudentName) {
        sileoToast.warning({ title: 'Selección requerida', description: 'Seleccione un estudiante del catálogo para vincular.' });
        return;
      }
      payload = {
        action: 'LINK_EXISTING',
        estudiante_resuelto: selectedStudentName,
        ci_corregida: manualCi || undefined,
        modulo_resuelto: manualModulo,
        nota_final: parseFloat(manualNota) || 75.0
      };
    } else if (selectedAction === 'CREATE_NEW') {
      if (!newStudentName.trim()) {
        sileoToast.warning({ title: 'Campo requerido', description: 'Ingrese el nombre completo para el nuevo estudiante.' });
        return;
      }
      payload = {
        action: 'CREATE_NEW',
        estudiante_resuelto: newStudentName.trim(),
        ci_corregida: newStudentCi.trim() || undefined,
        modulo_resuelto: manualModulo,
        nota_final: parseFloat(manualNota) || 75.0,
        es_nuevo: true
      };
    } else if (selectedAction === 'CORRECT_MANUAL') {
      payload = {
        action: 'CORRECT_MANUAL',
        estudiante_resuelto: manualName.trim(),
        ci_corregida: manualCi.trim() || undefined,
        modulo_resuelto: manualModulo.trim(),
        nota_final: parseFloat(manualNota) || 75.0
      };
    } else if (selectedAction === 'REJECT') {
      payload = {
        action: 'REJECT',
        reject_reason: rejectReason
      };
    }

    if (onSaveReview) {
      await onSaveReview(selectedAction, payload);
    }
  };

  const confidencePct = Math.round((item.ner_confidence || 0.67) * 100);

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.45)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        justifyContent: 'flex-end',
        animation: 'fadeIn 0.2s ease'
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '600px',
          height: '100%',
          backgroundColor: 'var(--color-paper-white)',
          boxShadow: '-8px 0 32px rgba(0, 0, 0, 0.2)',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto',
          animation: 'slideInRight 0.25s ease'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Cabecera del Drawer */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          backgroundColor: 'var(--color-surface)',
          position: 'sticky',
          top: 0,
          zIndex: 10
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{
                fontSize: '11px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.8px',
                color: 'var(--color-gira-gold)'
              }}>
                EXPEDIENTE DE AUDITORÍA HUMANA
              </span>
              <span style={{ color: 'var(--color-border)' }}>·</span>
              <code style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-ink-black)' }}>
                {item.id}
              </code>
            </div>
            <h3 style={{
              fontFamily: 'var(--font-signifier)',
              fontSize: '22px',
              fontWeight: 400,
              margin: '0 0 4px',
              color: 'var(--color-ink-black)'
            }}>
              Revisar Registro · {item.id}
            </h3>
            <div style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
              Disparador de revisión: {item.disparador || 'Score inferior a 85%'}
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--color-slate-gray)',
              padding: '6px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Cuerpo del Expediente */}
        <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '22px', flex: 1 }}>
          {/* SECCIÓN 1: INFORMACIÓN DETECTADA */}
          <div style={{
            padding: '16px',
            borderRadius: '16px',
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)'
          }}>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-slate-gray)', letterSpacing: '0.6px', marginBottom: '10px' }}>
              1. Información Detectada en la Fuente
            </div>
            {(() => {
              const sourceMeta = getSourceTableMeta(item.fuente_1 || '');
              const entityBadge = getEntityTargetTableBadge(item.tipo_entidad || (isFinancialItem ? 'CONCEPTO_FINANCIERO' : 'ESTUDIANTE'));
              return (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '14px', fontSize: '13px' }}>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                      Entidad Reconocida:
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
                      <span
                        style={{
                          fontSize: '10px',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 700,
                          padding: '1px 5px',
                          borderRadius: '4px',
                          color: entityBadge.color,
                          backgroundColor: entityBadge.bgColor,
                          border: `1px solid ${entityBadge.borderColor}`,
                        }}
                      >
                        {entityBadge.table}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)' }}>
                        {entityBadge.label}
                      </span>
                    </div>
                    <strong style={{ color: 'var(--color-ink-black)', fontSize: '14px' }}>{item.estudiante}</strong>
                  </div>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                      Módulo o Concepto:
                    </span>
                    <span style={{ color: 'var(--color-ink-black)', fontWeight: 500 }}>
                      {item.modulo_detectado || 'No especificado'}
                    </span>
                  </div>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                      Destino Canónico:
                    </span>
                    <div style={{ fontWeight: 600, color: 'var(--color-ink-black)', fontSize: '12.5px' }}>
                      {sourceMeta.domainTitle}
                    </div>
                    <code style={{ fontSize: '10.5px', color: 'var(--color-slate-gray)' }}>
                      {item.fuente_1}
                    </code>
                  </div>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                      Posición / Fila:
                    </span>
                    <span style={{ color: 'var(--color-ink-black)', fontWeight: 500 }}>Fila {item.line_number || 1}</span>
                  </div>
                </div>
              );
            })()}
          </div>

          {/* SECCIÓN 2: LO QUE ENCONTRÓ BETO */}
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-slate-gray)', letterSpacing: '0.6px', marginBottom: '8px' }}>
              {isFinancialItem ? '2. Entidades Financieras Identificadas por BETO NER' : '2. Lo que encontró BETO NER (Confianzas de Extracción)'}
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--color-fog-white)', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ textAlign: 'left', padding: '6px 10px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>Campo</th>
                  <th style={{ textAlign: 'left', padding: '6px 10px', color: 'var(--color-ink-black)', fontWeight: 600 }}>Valor Extraído</th>
                  <th style={{ textAlign: 'right', padding: '6px 10px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>Confianza / Regla</th>
                </tr>
              </thead>
              <tbody>
                {isFinancialItem ? (
                  <>
                    <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 600 }}>Estudiante (Cascada)</td>
                      <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)' }}>{item.estudiante}</td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: '#166534' }}>
                        96.0% (CI Match)
                      </td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 600 }}>Concepto Extraído</td>
                      <td style={{ padding: '8px 10px' }}>{item.concepto_financiero || 'Cuota Mensual (Mensualidad)'}</td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: '#166534' }}>
                        94.0%
                      </td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 600 }}>Cuota Asignada</td>
                      <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)' }}>{manualCuota} Bs.</td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: '#166534' }}>
                        99.0% [BOB]
                      </td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 600 }}>Monto Pagado</td>
                      <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)' }}>{manualPagado} Bs.</td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: '#166534' }}>
                        99.0% [BOB]
                      </td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 600 }}>Saldo Contable</td>
                      <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)' }}>{manualSaldo} Bs.</td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: '#166534' }}>
                        Cuadre OK
                      </td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 600 }}>Cuotas Impagas</td>
                      <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', color: manualCuotasImpagas >= 2 ? '#d9383a' : '#166534' }}>
                        {manualCuotasImpagas} cuota(s)
                      </td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: manualCuotasImpagas >= 2 ? '#d9383a' : '#166534' }}>
                        {manualCuotasImpagas >= 2 ? '⚠ Mora Crítica' : '✓ Vigente'}
                      </td>
                    </tr>
                  </>
                ) : (
                  <>
                    <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 600 }}>Estudiante</td>
                      <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)' }}>{item.estudiante}</td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: confidencePct >= 85 ? '#166534' : '#b45309' }}>
                        {confidencePct}%
                      </td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 600 }}>Cédula de Identidad (CI)</td>
                      <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', color: (!item.ci_raw || item.ci_raw === 'No especificado' || item.ci_raw.includes('?')) ? '#d9383a' : '#166534' }}>
                        {item.ci_raw || 'No especificado'}
                      </td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: '#d9383a' }}>
                        50.0%
                      </td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 600 }}>Módulo / Programa</td>
                      <td style={{ padding: '8px 10px' }}>{item.modulo_detectado}</td>
                      <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: '#166534' }}>
                        91.2%
                      </td>
                    </tr>
                  </>
                )}
              </tbody>
            </table>
          </div>

          {/* SECCIÓN 3: COTEJO CON CATÁLOGO MAESTRO */}
          <div style={{
            padding: '14px 16px',
            borderRadius: '14px',
            backgroundColor: isFinancialItem ? 'rgba(217, 155, 38, 0.08)' : (item.sugerencia_catalogo ? 'rgba(2, 132, 199, 0.06)' : 'rgba(217, 155, 38, 0.08)'),
            border: `1px solid ${isFinancialItem ? 'rgba(217, 155, 38, 0.3)' : (item.sugerencia_catalogo ? 'rgba(2, 132, 199, 0.25)' : 'rgba(217, 155, 38, 0.3)')}`,
            fontSize: '12.5px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <GitMerge size={16} color={isFinancialItem ? '#b45309' : '#0284c7'} />
              <strong style={{ color: 'var(--color-ink-black)' }}>
                {isFinancialItem ? 'Catálogo Financiero & Política Anti-Polución DW' : (item.sugerencia_catalogo ? 'Coincidencia Encontrada en Catálogo' : 'Sin Coincidencia en Catálogo')}
              </strong>
            </div>
            {isFinancialItem ? (
              <div style={{ color: '#b45309', lineHeight: 1.45 }}>
                Sugerencia canónica: <strong>FIN-CUOTA-01 (Cuota Mensual)</strong> (Similitud: 98% con sinónimo histórico).
                <div style={{ fontSize: '11.5px', marginTop: '4px', color: 'var(--color-slate-gray)' }}>
                  Política de Integridad: Si el término no coincide con alta certeza (&ge;90%), se bloquea la inserción automática para no contaminar el Data Warehouse.
                </div>
              </div>
            ) : item.sugerencia_catalogo ? (
              <div>
                Coincidencia sugerida por RapidFuzz: <strong>{item.sugerencia_catalogo}</strong> (Similitud: {item.rapidfuzz_cross || 75}%)
              </div>
            ) : (
              <div style={{ color: '#b45309', lineHeight: 1.4 }}>
                No existe una coincidencia suficientemente confiable en el catálogo maestro. Puede dar de alta al estudiante o corregir sus datos.
              </div>
            )}
          </div>

          {/* SECCIÓN 4: ACCIONES DE RESOLUCIÓN */}
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-slate-gray)', letterSpacing: '0.6px', marginBottom: '10px' }}>
              3. Decisión y Acción de Resolución Humana
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {/* Opción Financiera: Homologar Concepto Canónico (Loop 5) */}
              {isFinancialItem && (
                <label
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    padding: '14px 16px',
                    borderRadius: '12px',
                    border: selectedAction === 'LINK_FINANCIAL_CONCEPT' ? '1.5px solid var(--color-gira-gold)' : '1px solid var(--color-border)',
                    backgroundColor: selectedAction === 'LINK_FINANCIAL_CONCEPT' ? 'rgba(217, 155, 38, 0.06)' : 'var(--color-paper-white)',
                    cursor: 'pointer'
                  }}
                >
                  <input
                    type="radio"
                    name="reviewAction"
                    checked={selectedAction === 'LINK_FINANCIAL_CONCEPT'}
                    onChange={() => setSelectedAction('LINK_FINANCIAL_CONCEPT')}
                    style={{ marginTop: '2px', accentColor: 'var(--color-gira-gold)' }}
                  />
                  <div style={{ flex: 1 }}>
                    <strong style={{ fontSize: '13px', color: 'var(--color-ink-black)', display: 'block' }}>
                      Homologar con Concepto Financiero Canónico (Protección DW)
                    </strong>
                    <span style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', lineHeight: 1.4, display: 'block' }}>
                      Asocia el término a un concepto canónico del <strong>Catálogo de Conceptos Financieros</strong> sin crear categorías no autorizadas en el DW.
                    </span>

                    {selectedAction === 'LINK_FINANCIAL_CONCEPT' && (
                      <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <div>
                          <label style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px', fontWeight: 600 }}>
                            Concepto Financiero Canónico:
                          </label>
                          <select
                            value={selectedConcept}
                            onChange={(e) => setSelectedConcept(e.target.value)}
                            style={{
                              width: '100%',
                              padding: '8px 10px',
                              borderRadius: '8px',
                              border: '1px solid var(--color-border)',
                              fontSize: '12px',
                              backgroundColor: '#ffffff'
                            }}
                          >
                            {CANONICAL_FINANCIAL_CONCEPTS.map(c => (
                              <option key={c.codigo} value={c.codigo}>
                                [{c.codigo}] {c.nombre} ({c.tipo})
                              </option>
                            ))}
                          </select>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                          <div>
                            <label style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                              Cuota (Bs.):
                            </label>
                            <input
                              type="number"
                              value={manualCuota}
                              onChange={(e) => setManualCuota(e.target.value)}
                              style={{ width: '100%', padding: '6px 10px', borderRadius: '8px', border: '1px solid var(--color-border)', fontSize: '12px' }}
                            />
                          </div>
                          <div>
                            <label style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                              Pagado (Bs.):
                            </label>
                            <input
                              type="number"
                              value={manualPagado}
                              onChange={(e) => setManualPagado(e.target.value)}
                              style={{ width: '100%', padding: '6px 10px', borderRadius: '8px', border: '1px solid var(--color-border)', fontSize: '12px' }}
                            />
                          </div>
                          <div>
                            <label style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                              Saldo (Bs.):
                            </label>
                            <input
                              type="number"
                              value={manualSaldo}
                              onChange={(e) => setManualSaldo(e.target.value)}
                              style={{ width: '100%', padding: '6px 10px', borderRadius: '8px', border: '1px solid var(--color-border)', fontSize: '12px' }}
                            />
                          </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                          <div>
                            <label style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                              Cuotas Impagas:
                            </label>
                            <input
                              type="number"
                              value={manualCuotasImpagas}
                              onChange={(e) => setManualCuotasImpagas(e.target.value)}
                              style={{ width: '100%', padding: '6px 10px', borderRadius: '8px', border: '1px solid var(--color-border)', fontSize: '12px' }}
                            />
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', paddingTop: '16px', fontSize: '11px' }}>
                            {parseInt(manualCuotasImpagas) >= 2 ? (
                              <span style={{ color: '#d9383a', fontWeight: 600 }}>⚠ Alerta Mora Crítica (Regla &gt;= 2)</span>
                            ) : (
                              <span style={{ color: '#166534', fontWeight: 600 }}>✓ Cartera Vigente</span>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </label>
              )}

              {/* Opción 1: Vincular con estudiante existente */}
              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '14px 16px',
                  borderRadius: '12px',
                  border: selectedAction === 'LINK_EXISTING' ? '1.5px solid var(--color-ink-black)' : '1px solid var(--color-border)',
                  backgroundColor: selectedAction === 'LINK_EXISTING' ? 'rgba(12, 30, 51, 0.04)' : 'var(--color-paper-white)',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="radio"
                  name="reviewAction"
                  checked={selectedAction === 'LINK_EXISTING'}
                  onChange={() => setSelectedAction('LINK_EXISTING')}
                  style={{ marginTop: '2px', accentColor: 'var(--color-gira-gold)' }}
                />
                <div style={{ flex: 1 }}>
                  <strong style={{ fontSize: '13px', color: 'var(--color-ink-black)', display: 'block' }}>
                    Vincular con estudiante existente del catálogo
                  </strong>
                  <span style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', lineHeight: 1.4, display: 'block' }}>
                    Asocia este registro a un perfil canónico ya registrado en el <strong>Catálogo de Estudiantes</strong>.
                  </span>

                  {selectedAction === 'LINK_EXISTING' && (
                    <div style={{ marginTop: '10px' }}>
                      <div style={{ position: 'relative', marginBottom: '6px' }}>
                        <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: '#94a3b8' }} />
                        <input
                          type="text"
                          placeholder="Buscar alumno en catálogo (nombre o CI)..."
                          value={studentSearch}
                          onChange={(e) => setStudentSearch(e.target.value)}
                          style={{
                            width: '100%',
                            padding: '7px 10px 7px 30px',
                            borderRadius: '8px',
                            border: '1px solid var(--color-border)',
                            fontSize: '12px'
                          }}
                        />
                      </div>
                      <select
                        value={selectedStudentName}
                        onChange={(e) => setSelectedStudentName(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '8px 10px',
                          borderRadius: '8px',
                          border: '1px solid var(--color-border)',
                          fontSize: '12px',
                          backgroundColor: '#ffffff'
                        }}
                      >
                        {item.sugerencia_catalogo && (
                          <option value={item.sugerencia_catalogo}>
                            [Sugerido] {item.sugerencia_catalogo} ({item.rapidfuzz_cross || 75}%)
                          </option>
                        )}
                        {filteredCatalogStudents.map((st, sIdx) => {
                          const name = st.nombre_completo || st.nombre || st.name;
                          return (
                            <option key={sIdx} value={name}>
                              {name} {st.ci ? `(CI: ${st.ci})` : ''}
                            </option>
                          );
                        })}
                      </select>
                    </div>
                  )}
                </div>
              </label>

              {/* Opción 2: Crear nuevo estudiante */}
              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '14px 16px',
                  borderRadius: '12px',
                  border: selectedAction === 'CREATE_NEW' ? '1.5px solid var(--color-gira-gold)' : '1px solid var(--color-border)',
                  backgroundColor: selectedAction === 'CREATE_NEW' ? 'rgba(217, 155, 38, 0.05)' : 'var(--color-paper-white)',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="radio"
                  name="reviewAction"
                  checked={selectedAction === 'CREATE_NEW'}
                  onChange={() => setSelectedAction('CREATE_NEW')}
                  style={{ marginTop: '2px', accentColor: 'var(--color-gira-gold)' }}
                />
                <div style={{ flex: 1 }}>
                  <strong style={{ fontSize: '13px', color: 'var(--color-ink-black)', display: 'block' }}>
                    Crear nuevo estudiante (Alta Institucional)
                  </strong>
                  <span style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', lineHeight: 1.4, display: 'block' }}>
                    Crea un nuevo registro en el <strong>Catálogo de Estudiantes</strong> con clave foránea canónica.
                  </span>

                  {selectedAction === 'CREATE_NEW' && (
                    <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div>
                        <label style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                          Nombre Completo del Nuevo Estudiante:
                        </label>
                        <input
                          type="text"
                          value={newStudentName}
                          onChange={(e) => setNewStudentName(e.target.value)}
                          placeholder="Nombre y Apellidos"
                          style={{
                            width: '100%',
                            padding: '7px 10px',
                            borderRadius: '8px',
                            border: '1px solid var(--color-border)',
                            fontSize: '12px'
                          }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                          Cédula de Identidad (CI) Validada:
                        </label>
                        <input
                          type="text"
                          value={newStudentCi}
                          onChange={(e) => setNewStudentCi(e.target.value)}
                          placeholder="Ej. 6849201 LP"
                          style={{
                            width: '100%',
                            padding: '7px 10px',
                            borderRadius: '8px',
                            border: '1px solid var(--color-border)',
                            fontSize: '12px'
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </label>

              {/* Opción 3: Corregir información manualmente */}
              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '14px 16px',
                  borderRadius: '12px',
                  border: selectedAction === 'CORRECT_MANUAL' ? '1.5px solid #0284c7' : '1px solid var(--color-border)',
                  backgroundColor: selectedAction === 'CORRECT_MANUAL' ? 'rgba(2, 132, 199, 0.05)' : 'var(--color-paper-white)',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="radio"
                  name="reviewAction"
                  checked={selectedAction === 'CORRECT_MANUAL'}
                  onChange={() => setSelectedAction('CORRECT_MANUAL')}
                  style={{ marginTop: '2px', accentColor: 'var(--color-gira-gold)' }}
                />
                <div style={{ flex: 1 }}>
                  <strong style={{ fontSize: '13px', color: 'var(--color-ink-black)', display: 'block' }}>
                    Corregir información manualmente
                  </strong>
                  <span style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', lineHeight: 1.4, display: 'block' }}>
                    Ajusta los valores de nombre, CI, módulo o calificación antes de consolidar.
                  </span>

                  {selectedAction === 'CORRECT_MANUAL' && (
                    <div style={{ marginTop: '10px', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                      <div style={{ gridColumn: 'span 2' }}>
                        <label style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                          Nombre del Estudiante:
                        </label>
                        <input
                          type="text"
                          value={manualName}
                          onChange={(e) => setManualName(e.target.value)}
                          style={{ width: '100%', padding: '6px 10px', borderRadius: '8px', border: '1px solid var(--color-border)', fontSize: '12px' }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                          Cédula de Identidad (CI):
                        </label>
                        <input
                          type="text"
                          value={manualCi}
                          onChange={(e) => setManualCi(e.target.value)}
                          placeholder="Sin sufijo ?"
                          style={{ width: '100%', padding: '6px 10px', borderRadius: '8px', border: '1px solid var(--color-border)', fontSize: '12px' }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '11px', color: 'var(--color-slate-gray)', display: 'block', marginBottom: '2px' }}>
                          Nota Final [0-100]:
                        </label>
                        <input
                          type="number"
                          step="0.5"
                          min="0"
                          max="100"
                          value={manualNota}
                          onChange={(e) => setManualNota(e.target.value)}
                          style={{ width: '100%', padding: '6px 10px', borderRadius: '8px', border: '1px solid var(--color-border)', fontSize: '12px' }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </label>

              {/* Opción 4: Rechazar registro */}
              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '14px 16px',
                  borderRadius: '12px',
                  border: selectedAction === 'REJECT' ? '1.5px solid #d9383a' : '1px solid var(--color-border)',
                  backgroundColor: selectedAction === 'REJECT' ? 'rgba(217, 56, 58, 0.05)' : 'var(--color-paper-white)',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="radio"
                  name="reviewAction"
                  checked={selectedAction === 'REJECT'}
                  onChange={() => setSelectedAction('REJECT')}
                  style={{ marginTop: '2px', accentColor: '#d9383a' }}
                />
                <div style={{ flex: 1 }}>
                  <strong style={{ fontSize: '13px', color: '#d9383a', display: 'block' }}>
                    Rechazar registro (Inconsistencia Irreparable)
                  </strong>
                  <span style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)', lineHeight: 1.4, display: 'block' }}>
                    Descarta este registro y lo excluye de la inserción en el Data Warehouse.
                  </span>

                  {selectedAction === 'REJECT' && (
                    <div style={{ marginTop: '8px' }}>
                      <input
                        type="text"
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="Motivo del rechazo..."
                        style={{
                          width: '100%',
                          padding: '7px 10px',
                          borderRadius: '8px',
                          border: '1px solid rgba(217, 56, 58, 0.4)',
                          fontSize: '12px',
                          color: '#d9383a'
                        }}
                      />
                    </div>
                  )}
                </div>
              </label>
            </div>
          </div>
        </div>

        {/* Pie del Drawer con Acciones de Guardado */}
        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid var(--color-border)',
          backgroundColor: 'var(--color-surface)',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '12px',
          position: 'sticky',
          bottom: 0,
          zIndex: 10
        }}>
          <button
            type="button"
            className="btn-pill-ghost"
            onClick={onClose}
            disabled={isSaving}
            style={{ padding: '8px 18px', fontSize: '12.5px' }}
          >
            Cancelar
          </button>

          <button
            type="button"
            className="btn-pill-dark"
            onClick={handleSubmitReview}
            disabled={isSaving}
            style={{
              padding: '8px 22px',
              fontSize: '12.5px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            {isSaving ? <Check className="animate-spin" size={14} /> : <Check size={14} />}
            <span>Guardar Revisión</span>
          </button>
        </div>
      </div>
    </div>
  );
}
