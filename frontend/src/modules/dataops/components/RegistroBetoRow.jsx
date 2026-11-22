import React, { useRef, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import Button from '../../../components/shared/Button';
import EntityHighlightText from './EntityHighlightText';
import { useRevealCampo } from '../hooks/useRevealCi';
import AnimatedProgressBarV2 from '../../../v2/motion/AnimatedProgressBarV2';

const ESTADOS = { AUTOMATICO: 'Aceptación directa', REVISION: 'En revisión', INCONSISTENCIA: 'Con incidencias' };
const AREAS = { academica: 'Académica', evaluacion_docente: 'Evaluación docente', financiera: 'Financiera', comercial: 'Comercial', calidad: 'Calidad' };
const fmt = value => typeof value === 'number' ? value.toLocaleString('es-BO') : 'Sin dato';
const fmtDec = value => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2).replace('.', ',') : null;

export const ORIGEN_INFO = {
  CI_EXACTA: { label: 'Cédula exacta', bg: 'var(--dataops-success-bg)', color: 'var(--dataops-success-text)', bar: 'var(--dataops-success-text)' },
  REGLA_ENCABEZADO: { label: 'Encabezado del archivo', bg: 'var(--color-mist-gray)', color: 'var(--color-ink-black)', bar: 'var(--color-ink-black)' },
  ENCABEZADO: { label: 'Encabezado del archivo', bg: 'var(--color-mist-gray)', color: 'var(--color-ink-black)', bar: 'var(--color-ink-black)' },
  FUZZY: { label: 'Coincidencia aproximada', bg: 'var(--dataops-warning-bg)', color: 'var(--dataops-warning-text)', bar: 'var(--dataops-warning-text)' },
  REGEX: { label: 'Patrón', bg: 'var(--color-mist-gray)', color: 'var(--color-slate-gray)', bar: 'var(--color-slate-gray)' },
  BETO: { label: 'Leído por BETO', bg: 'var(--dataops-info-bg)', color: 'var(--dataops-info-text)', bar: 'var(--color-gira-gold)' },
};

function modeloEtiqueta(entity) {
  const lbl = String(entity?.label || '').toUpperCase();
  if (lbl.includes('ESTUDIANTE')) return 'PER_ESTUDIANTE';
  if (lbl.includes('DOCENTE')) return 'PER_DOCENTE';
  if (lbl.includes('MODULO') || lbl.includes('MÓDULO')) return 'MODULO';
  if (lbl.includes('PROGRAMA')) return 'PROGRAMA';
  if (lbl.includes('CI') || lbl.includes('DOCUMENTO')) return 'CI (por regla)';
  return entity?.tag || entity?.label || 'ENTIDAD';
}

function textoConfianzaEntidad(entity, info) {
  const origen = entity?.origen_confianza || entity?.fuente_resolucion || '';
  const conf = entity?.confianza ?? entity?.betoConfidence;
  if (origen === 'BETO' && conf != null) return `BETO p = ${fmtDec(Number(conf))}`;
  if (origen === 'REGLA_ENCABEZADO' || origen === 'ENCABEZADO') {
    const sim = entity?.detalleConfianza?.similitudEncabezado;
    const val = entity?.detalleConfianza?.validez ?? entity?.detalleConfianza?.catalogo;
    const simTxt = sim != null ? `similitud ${fmtDec(Number(sim))}` : 'encabezado';
    const valTxt = val != null && Number(val) < 0.99 ? `validez ${fmtDec(Number(val))}` : 'valor validado';
    return `Regla por encabezado: ${simTxt} · ${valTxt}`;
  }
  if (conf != null) return `${info.label}: ${fmtDec(Number(conf))}`;
  return info.label;
}

export default function RegistroBetoRow({ record }) {
  const { toggleCampo, getValor } = useRevealCampo();
  const [loadingCampo, setLoadingCampo] = useState(null);
  const revealLock = useRef(false);
  const ci = record.ci_enmascarado || record.ci;
  const hasCi = ci && !['No provisto', 'No especificado'].includes(ci);
  const ciRev = getValor(record.id, 'ci');
  const nombreRev = getValor(record.id, 'nombre');
  const correoRev = getValor(record.id, 'correo');
  const rawText = record.raw_text || record.lectura?.texto || '';
  const hasCorreo = Boolean(
    correoRev ||
    record.tiene_correo ||
    (record.correo_enmascarado && !['No provisto', 'No especificado', 'Sin dato'].includes(record.correo_enmascarado)) ||
    rawText.includes('@')
  );
  const reveal = async (campo) => {
    if (revealLock.current) return;
    revealLock.current = true;
    setLoadingCampo(campo);
    try { await toggleCampo(record.id, campo); } finally { revealLock.current = false; setLoadingCampo(null); }
  };
  return (
    <tr>
      <td style={{ overflowWrap: 'anywhere', verticalAlign: 'top' }}>
        <strong>Fila {record.line_number ?? 'Sin dato'}</strong>
        <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', margin: '6px 0' }}>{record.nombre_archivo || 'Sin dato'}</p>
        <p style={{ fontSize: 12 }}>Cédula: {ciRev || (hasCi ? ci : 'Sin dato')}</p>
        {nombreRev && <p style={{ fontSize: 12, marginTop: 4 }}>Nombre: {nombreRev}</p>}
        {correoRev && <p style={{ fontSize: 12, marginTop: 4 }}>Correo: {correoRev}</p>}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
          {hasCi && <Button variant="ghost" onClick={() => reveal('ci')} isLoading={loadingCampo === 'ci'} loadingText="Consultando…" aria-label={ciRev ? 'Ocultar cédula' : 'Revelar cédula con registro de auditoría'} style={{ padding: '4px 10px', fontSize: 11 }}>
            {ciRev ? <EyeOff size={13} /> : <Eye size={13} />} {ciRev ? 'Ocultar cédula' : 'Revelar con auditoría'}
          </Button>}
          <Button variant="ghost" onClick={() => reveal('nombre')} isLoading={loadingCampo === 'nombre'} loadingText="Consultando…" aria-label={nombreRev ? 'Ocultar nombre' : 'Revelar nombre con auditoría'} style={{ padding: '4px 10px', fontSize: 11 }}>
            {nombreRev ? <EyeOff size={13} /> : <Eye size={13} />} {nombreRev ? 'Ocultar nombre' : 'Revelar nombre'}
          </Button>
          {hasCorreo && <Button variant="ghost" onClick={() => reveal('correo')} isLoading={loadingCampo === 'correo'} loadingText="Consultando…" aria-label={correoRev ? 'Ocultar correo' : 'Revelar correo con auditoría'} style={{ padding: '4px 10px', fontSize: 11 }}>
            {correoRev ? <EyeOff size={13} /> : <Eye size={13} />} {correoRev ? 'Ocultar correo' : 'Revelar correo'}
          </Button>}
        </div>
      </td>
      <td style={{ overflowWrap: 'anywhere', verticalAlign: 'top' }}>
        <p>{record.modulo && record.modulo !== 'No detectado' ? record.modulo : 'Sin módulo o concepto identificado'}</p>
        <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', marginTop: 6 }}>{AREAS[record.area] || 'Sin dato'}</p>
        {record.nota_normalizada != null && <p style={{ marginTop: 6 }}>Nota: {record.nota_normalizada}/100</p>}
        {record.monto != null && <p style={{ marginTop: 6 }}>Monto: {record.monto}</p>}
      </td>
      <td style={{ verticalAlign: 'top', fontVariantNumeric: 'tabular-nums' }}>{record.indice_registro == null ? 'Sin dato' : `${fmt(record.indice_registro)} %`}</td>
      <td style={{ overflowWrap: 'anywhere', verticalAlign: 'top' }}>
        <strong style={{ color: record.estado === 'AUTOMATICO' ? 'var(--dataops-success-text)' : 'var(--dataops-warning-text)' }}>{ESTADOS[record.estado] || 'Sin dato'}</strong>
        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--color-slate-gray)' }}>
          <EntityHighlightText
            text={record.raw_text || record.lectura?.texto || ''}
            betoEnts={record.lectura?.beto_ents || []}
            entidades={record.lectura?.entidades || []}
          />
        </div>
        <details style={{ marginTop: 10 }}>
          <summary style={{ cursor: 'pointer', color: 'var(--dataops-info-text)' }}>Ver explicación y datos identificados</summary>
          <p style={{ marginTop: 10 }}>{record.decision?.motivo_llano || 'Sin observaciones adicionales.'}</p>
          <p style={{ marginTop: 10, fontSize: 12, color: 'var(--color-slate-gray)' }}>{record.raw_text || record.lectura?.texto || 'Sin texto disponible'}</p>
          <dl style={{ marginTop: 10 }}>{(record.lectura?.entidades || []).map((entity, index) => {
            const origen = entity.origen_confianza || entity.fuente_resolucion || 'REGLA_ENCABEZADO';
            const info = ORIGEN_INFO[origen] || ORIGEN_INFO.REGLA_ENCABEZADO;
            const confFinal = entity.confianza ?? entity.betoConfidence;
            const lecturaMod = entity.lecturaModelo ?? (origen === 'BETO' ? confFinal : null);
            return (
              <div key={index} style={{ marginTop: 10, paddingTop: 8, borderTop: index > 0 ? '1px solid var(--color-border)' : 'none' }}>
                <dt style={{ fontSize: 12, fontWeight: 600, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 6 }}>
                  <span>{String(entity.label || 'Dato').replaceAll('_', ' ').toLocaleLowerCase('es')}</span>
                  <span style={{ fontSize: 10.5, fontFamily: 'var(--font-mono)', padding: '2px 7px', borderRadius: 999, background: 'var(--color-mist-gray)', border: '1px solid var(--color-border)', color: 'var(--color-ink-black)' }}>{modeloEtiqueta(entity)}</span>
                  <span style={{ fontSize: 10.5, padding: '2px 8px', borderRadius: 999, background: info.bg, color: info.color }}>{info.label}</span>
                </dt>
                <dd style={{ fontSize: 12, marginTop: 4 }}>
                  {entity.token ?? 'Sin dato'}{entity.matchedCanonical != null && entity.matchedCanonical !== entity.token ? ` · Catálogo: ${entity.matchedCanonical}` : ''}
                  <p style={{ fontSize: 11, color: 'var(--color-slate-gray)', marginTop: 3 }}>{textoConfianzaEntidad(entity, info)}</p>
                  {(lecturaMod != null || confFinal != null) && (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 8, marginTop: 5 }}>
                      {lecturaMod != null && <div>
                        <span style={{ fontSize: 10.5, color: 'var(--color-slate-gray)' }}>Lectura del modelo ({Math.round(Number(lecturaMod) * 100)} %)</span>
                        <AnimatedProgressBarV2 value={Number(lecturaMod) * 100} color="var(--color-gira-gold)" height={6} ariaLabel="Lectura del modelo" />
                      </div>}
                      {confFinal != null && <div>
                        <span style={{ fontSize: 10.5, color: 'var(--color-slate-gray)' }}>Confianza medida ({Math.round(Number(confFinal) * 100)} %)</span>
                        <AnimatedProgressBarV2 value={Number(confFinal) * 100} color={info.bar} height={6} ariaLabel="Confianza medida" />
                      </div>}
                    </div>
                  )}
                </dd>
              </div>
            );
          })}</dl>
        </details>
      </td>
    </tr>
  );
}
