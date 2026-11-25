import React, { useState } from 'react';
import Button from '../../../components/shared/Button';
import { maskTexto, textoMotivo } from '../../../constants/motivosBandeja';

export default function GruposBandeja({ data, readOnly, busy, onVerIndividual, onResolver, onSelectPatron, onSelectMotivo }) {
  const [dialog, setDialog] = useState(null);
  const [mes, setMes] = useState('');
  const [gestion, setGestion] = useState('');
  const [canonico, setCanonico] = useState('');
  const open = group => { setMes(''); setGestion(''); setCanonico(''); setDialog(group); };
  return <>
    {data?.patrones?.length > 0 && (
      <section aria-label="Bandas de similitud en CI con nombre distinto" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
        {data.patrones.map((pat) => (
          <button
            key={pat.codigo || pat.patron}
            type="button"
            onClick={() => onSelectPatron?.(pat.codigo || pat.patron)}
            title="Filtrar casos pendientes de esta banda"
            style={{
              padding: '6px 12px',
              borderRadius: 999,
              border: '1px solid var(--dataops-warning-text)',
              background: 'var(--dataops-warning-bg)',
              color: 'var(--dataops-warning-text)',
              fontSize: 12,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              cursor: 'pointer',
            }}
          >
            <strong>{pat.n.toLocaleString('es-BO')}</strong>
            <span>{pat.patron}</span>
            <span style={{ opacity: 0.8 }}>({pat.grupos} grupos)</span>
          </button>
        ))}
      </section>
    )}
    {data?.reglas_resumen?.length > 0 && (
      <section aria-label="Resumen por regla de validación" style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
        {data.reglas_resumen.map((reg) => (
          <button
            key={reg.motivo}
            type="button"
            onClick={() => onSelectMotivo?.(reg.motivo)}
            title="Ver casos pendientes de esta regla"
            style={{
              padding: '4px 10px',
              borderRadius: 999,
              border: '1px solid var(--color-border)',
              background: 'var(--dataops-info-bg)',
              color: 'var(--dataops-info-text)',
              fontSize: 11.5,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              cursor: 'pointer',
            }}
          >
            <strong>{reg.n.toLocaleString('es-BO')}</strong>
            <span>{textoMotivo(reg.motivo, reg.etiqueta)}</span>
          </button>
        ))}
      </section>
    )}
    {!data?.grupos?.length ? <p role="status">No hay grupos para esta selección.</p> : <div tabIndex={0} role="region" aria-label="Grupos de revisión humana" style={{ overflowX: 'auto' }}><table className="dataops-table" style={{ width: '100%' }}>
      <thead><tr><th scope="col">Motivo</th><th scope="col">Casos</th><th scope="col">Revisión</th></tr></thead>
      <tbody>{data.grupos.map(group => {
        const codigoCorto = group.hash_corto || (group.clave ? String(group.clave).replace(/^grupo-/, '').slice(0, 6) : null);
        const tituloPrincipal = group.etiqueta_legible || textoMotivo(group.motivo, group.titulo);
        return (
      <tr key={group.clave}>
        <td>
          <details>
            <summary title={codigoCorto ? `Ref. interna: #${codigoCorto}` : undefined} style={{ cursor: 'pointer', color: 'var(--dataops-info-text)' }}>
              <span>{tituloPrincipal}</span>
              {group.patron && <span style={{ marginLeft: 8, fontSize: 11, padding: '2px 8px', borderRadius: 999, background: 'var(--dataops-warning-bg)', color: 'var(--dataops-warning-text)' }}>{group.patron}</span>}
              {group.archivo_origen && (
                <span style={{ display: 'block', fontSize: 11, color: 'var(--color-slate-gray)', marginTop: 2, fontWeight: 400, overflowWrap: 'anywhere' }}>
                  {group.archivo_origen}
                </span>
              )}
            </summary>
            <div style={{ maxWidth: 620, overflowWrap: 'anywhere', padding: '12px 0', fontSize: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {group.explicacion && (
                <div style={{ padding: 10, borderRadius: 10, background: 'var(--color-mist-gray)', border: '1px solid var(--color-border)' }}>
                  <p style={{ fontWeight: 600, color: 'var(--color-ink-black)', marginBottom: 4 }}>Por qué está aquí</p>
                  <p style={{ color: 'var(--color-slate-gray)' }}><strong>Regla:</strong> {group.explicacion.regla}</p>
                  <p style={{ color: 'var(--color-slate-gray)' }}><strong>Umbral / criterio:</strong> {group.explicacion.umbral}</p>
                  <p style={{ color: 'var(--color-slate-gray)' }}><strong>Valor de la fuente:</strong> {maskTexto(group.explicacion.valor_enmascarado || group.ejemplo || 'Sin valor')}</p>
                </div>
              )}
              <p style={{ color: 'var(--color-slate-gray)' }}>{maskTexto(group.ejemplo) || 'Sin ejemplo disponible'}</p>
            </div>
          </details>
        </td>
        <td>{group.n.toLocaleString('es-BO')}</td>
        <td><Button variant="ghost" disabled={busy} onClick={() => onVerIndividual(group.clave)}>Ver casos</Button>
          {!readOnly && group.accion_grupo !== 'MANUAL' && <Button variant="ghost" disabled={busy} isLoading={busy} onClick={() => group.accion_grupo === 'APROBAR' ? onResolver(group) : open(group)}>{group.accion_grupo === 'APROBAR' ? 'Aprobar grupo' : group.accion_grupo === 'CORREGIR_FECHA' ? 'Corregir fecha' : 'Revisar estado'}</Button>}</td>
      </tr>
        );
      })}</tbody>
    </table></div>}
    {dialog && <div className="floating-artifact" role="dialog" aria-label="Corregir grupo" style={{ padding: 20, marginTop: 16 }}>
      <p>La corrección se aplicará a los {dialog.n} casos del grupo.</p>
      {dialog.accion_grupo === 'CORREGIR_FECHA' ? <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        <label>Mes<input aria-label="Mes del grupo" className="dataops-input" type="number" min="1" max="12" value={mes} onChange={e => setMes(e.target.value)} /></label>
        <label>Gestión<input aria-label="Gestión del grupo" className="dataops-input" type="number" min="2000" max="2100" value={gestion} onChange={e => setGestion(e.target.value)} /></label>
      </div> : <><label>Estado correcto<input className="dataops-input" value={canonico} onChange={e => setCanonico(e.target.value)} maxLength={100} /></label><p style={{ fontSize: 12 }}>Indica el estado que corresponde antes de aprobar el grupo.</p></>}
      <div style={{ display: 'flex', gap: 12, marginTop: 12 }}><Button variant="ghost" onClick={() => setDialog(null)}>Cancelar</Button>
        <Button isLoading={busy} disabled={busy || (dialog.accion_grupo === 'CORREGIR_FECHA' ? !(Number(mes) >= 1 && Number(mes) <= 12 && Number(gestion) >= 2000 && Number(gestion) <= 2100) : !canonico.trim())} onClick={() => { onResolver(dialog, dialog.accion_grupo === 'CORREGIR_FECHA' ? { mes: Number(mes), gestion: Number(gestion) } : { canonico: canonico.trim() }); setDialog(null); }}>Programar corrección</Button></div>
    </div>}
  </>;
}
