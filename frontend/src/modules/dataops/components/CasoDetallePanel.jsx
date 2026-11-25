import React, { useRef, useState } from 'react';
import Button from '../../../components/shared/Button';
import { useRevealCampo } from '../hooks/useRevealCi';
import { maskTexto, textoMotivo } from '../../../constants/motivosBandeja';
import EntityHighlightText from './EntityHighlightText';
import ReviewActionRenderer from './ReviewActionRenderer';
import { dataopsApi } from '../../../api/dataopsApi';
import { sileoToast } from '../../../services/sileoToast';
import { mensajeError } from '../../../utils/mensajeError';
import { DATAOPS_QUERY_KEY, queryClient } from '../../../api/queryClient';

export default function CasoDetallePanel({
  item,
  readOnly = false,
  isResuelto = false,
  busy = false,
  schedule,
  activeActionIdx = 0,
  onSelectActionIdx = null,
}) {
  const { toggleCampo, getValor } = useRevealCampo();
  const [loadingCampo, setLoadingCampo] = useState(null);
  const revealLock = useRef(false);

  if (!item) {
    return (
      <div style={{ padding: 24, border: '1px dashed var(--color-border)', borderRadius: 12, color: 'var(--color-slate-gray)', fontSize: 13 }}>
        Selecciona un caso de la lista para ver el detalle y las acciones disponibles.
      </div>
    );
  }

  const ciRev = getValor(item.id, 'ci');
  const nomRev = getValor(item.id, 'nombre');
  const mailRev = getValor(item.id, 'correo');
  const hasCi = Boolean(item.ci_enmascarado && !['Sin dato', 'No provisto', 'No especificado'].includes(item.ci_enmascarado));
  const hasCorreo = Boolean(
    item.tiene_correo ||
    (item.correo_enmascarado && !['Sin dato', 'No provisto', 'No especificado'].includes(item.correo_enmascarado))
  );
  const hasNombre = item.tiene_nombre !== false;

  const reveal = async (campo) => {
    if (revealLock.current) return;
    revealLock.current = true;
    setLoadingCampo(campo);
    try {
      await toggleCampo(item.id, campo);
    } finally {
      revealLock.current = false;
      setLoadingCampo(null);
    }
  };

  const handleExecute = (targetItem, accion, form) => {
    const cleanPayload = { accion: accion.codigo };
    Object.entries(form || {}).forEach(([k, v]) => {
      if (v !== '' && v !== undefined && v !== null) cleanPayload[k] = v;
    });
    schedule(`${accion.etiqueta} (caso ${targetItem.id})`, () =>
      dataopsApi.resolveReviewItem(targetItem.id, cleanPayload)
    );
  };

  const handleReopen = async (targetItem) => {
    try {
      await dataopsApi.reopenReviewItem(targetItem.id);
      sileoToast.success({ title: 'Caso reabierto', description: 'El caso volvió a la bandeja de pendientes.' });
      queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    } catch (err) {
      sileoToast.error({ title: 'No se pudo reabrir el caso', description: mensajeError(err) });
    }
  };

  return (
    <div style={{ padding: 18, border: '1px solid var(--color-border)', borderRadius: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
        <div>
          <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--color-slate-gray)' }}>Caso #{item.id}</span>
          <h3 className="serif-heading" style={{ fontSize: 17, margin: '2px 0' }}>{textoMotivo(item.motivo, item.motivo_label)}</h3>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', alignSelf: 'start', flexWrap: 'wrap' }}>
          {item.prioridad && (
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                padding: '3px 9px',
                borderRadius: 999,
                background: item.prioridad === 'ALTA' ? 'var(--dataops-warning-bg)' : 'var(--dataops-info-bg)',
                color: item.prioridad === 'ALTA' ? 'var(--dataops-warning-text)' : 'var(--dataops-info-text)',
              }}
            >
              Prioridad {item.prioridad}
            </span>
          )}
          <span style={{ fontSize: 11.5, padding: '3px 10px', borderRadius: 999, background: 'var(--dataops-info-bg)', color: 'var(--dataops-info-text)' }}>
            {item.area || 'academica'}
          </span>
        </div>
      </div>

      <p style={{ fontSize: 13, color: 'var(--color-ink-black)', marginBottom: 8 }}>
        {maskTexto(item.motivo_detalle || item.por_que_detuvo)}
      </p>
      {item.regla_relacion && (
        <div style={{ fontSize: 12, padding: '8px 10px', borderRadius: 8, background: 'var(--dataops-info-bg)', color: 'var(--dataops-info-text)', marginBottom: 10 }}>
          <strong>Regla:</strong> {item.regla_relacion}{item.valor_relacion ? ` · Valor: ${item.valor_relacion}` : ''}
          {item.detalle_relacion ? ` — ${item.detalle_relacion}` : ''}
        </div>
      )}
      <p style={{ fontSize: 12, color: 'var(--color-slate-gray)', marginBottom: 10 }}>
        Archivo: <strong>{item.archivo_origen || 'Sin dato'}</strong> · CI: <strong>{ciRev || item.ci_enmascarado || 'Sin CI'}</strong>
        {nomRev ? ` · Nombre: ${nomRev}` : ''}{(mailRev || (hasCorreo && item.correo_enmascarado)) ? ` · Correo: ${mailRev || item.correo_enmascarado}` : ''}
      </p>

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
        {hasCi && (
          <Button variant="ghost" style={{ fontSize: 11, padding: '4px 10px' }} isLoading={loadingCampo === 'ci'} onClick={() => reveal('ci')}>
            {ciRev ? 'Ocultar cédula' : 'Revelar con auditoría'}
          </Button>
        )}
        {hasNombre && (
          <Button variant="ghost" style={{ fontSize: 11, padding: '4px 10px' }} isLoading={loadingCampo === 'nombre'} onClick={() => reveal('nombre')}>
            {nomRev ? 'Ocultar nombre' : 'Revelar nombre'}
          </Button>
        )}
        {hasCorreo && (
          <Button variant="ghost" style={{ fontSize: 11, padding: '4px 10px' }} isLoading={loadingCampo === 'correo'} onClick={() => reveal('correo')}>
            {mailRev ? 'Ocultar correo' : 'Revelar correo'}
          </Button>
        )}
      </div>

      {(() => {
        const area = String(item.area || 'academica').toLowerCase();
        const chipsPorArea = [];
        if (item.programa) chipsPorArea.push(`Programa: ${item.programa}`);
        if (area === 'financiera' || area === 'financiero') {
          if (item.monto_deuda != null) chipsPorArea.push(`Deuda: ${item.monto_deuda}`);
          if (item.cuotas_impagas != null) chipsPorArea.push(`Cuotas impagas: ${item.cuotas_impagas}`);
          if (item.codigo_pos) chipsPorArea.push(`POS: ${item.codigo_pos}`);
        } else if (area === 'evaluacion_docente') {
          if (item.docente) chipsPorArea.push(`Docente: ${item.docente}`);
          if (item.modulo_detectado || item.numero_modulo != null) chipsPorArea.push(`Módulo: ${item.modulo_detectado || item.numero_modulo}`);
        } else if (area === 'comercial' || area === 'marketing' || area === 'admision') {
          if (item.codigo_pos) chipsPorArea.push(`POS: ${item.codigo_pos}`);
          if (item.modulo_detectado) chipsPorArea.push(`Programa/Módulo: ${item.modulo_detectado}`);
        } else {
          if (item.modulo_detectado || item.numero_modulo != null) chipsPorArea.push(`Módulo: ${item.modulo_detectado || item.numero_modulo}`);
          if (item.nota_final != null) chipsPorArea.push(`Nota: ${item.nota_final}`);
          if (item.docente) chipsPorArea.push(`Docente: ${item.docente}`);
        }
        const guia = item.motivo === 'DESACUERDO_REGLA_BETO'
          ? 'Recomendación: confirma si el nombre leído es una persona real (si es cuenta institucional o ruido, usa Descartar).'
          : (item.motivo === 'BAJA_CONFIANZA' || item.motivo === 'BAJA_CONFIANZA_IA')
            ? 'Recomendación: verifica los campos clave del área y confirma o corrige la entidad antes de consolidar.'
            : item.motivo === 'SIN_LECTURA'
              ? 'Recomendación: la fila no tiene estructura legible; completa los datos faltantes o descártala.'
              : item.sugerencia
                ? `Candidato sugerido: ${item.sugerencia}`
                : null;
        if (!chipsPorArea.length && !guia) return null;
        return (
          <div style={{ fontSize: 12, padding: '10px 12px', borderRadius: 10, background: 'var(--dataops-warning-bg)', color: 'var(--dataops-warning-text)', marginBottom: 10, lineHeight: 1.45 }}>
            {chipsPorArea.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: guia ? 6 : 0 }}>
                {chipsPorArea.map((chip) => (
                  <span key={chip} style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 999, background: 'var(--color-pure-white)', color: 'var(--color-ink-black)', border: '1px solid var(--color-border)' }}>
                    {chip}
                  </span>
                ))}
              </div>
            )}
            {guia && <div>{guia}</div>}
          </div>
        );
      })()}

      {item.que_vio && (
        <details style={{ marginBottom: 12 }}>
          <summary style={{ cursor: 'pointer', fontSize: 12, color: 'var(--dataops-info-text)', fontWeight: 600 }}>
            Ver línea original y entidades IOB2
          </summary>
          <div style={{ fontSize: 12, padding: 10, marginTop: 6, borderRadius: 8, background: 'var(--color-mist-gray)', color: 'var(--color-ink-black)', wordBreak: 'break-word' }}>
            <EntityHighlightText text={item.que_vio} betoEnts={item.beto_ents || []} entidades={item.entidades || []} />
          </div>
        </details>
      )}

      <ReviewActionRenderer
        item={item}
        readOnly={readOnly || isResuelto}
        busy={busy}
        onExecute={handleExecute}
        onReopen={isResuelto && !readOnly ? handleReopen : null}
        activeActionIdx={activeActionIdx}
        onSelectActionIdx={onSelectActionIdx}
      />
    </div>
  );
}
