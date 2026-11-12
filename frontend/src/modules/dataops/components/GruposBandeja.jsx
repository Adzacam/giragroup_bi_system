import React, { useState } from 'react';
import Button from '../../../components/shared/Button';
import { textoMotivo } from '../../../constants/motivosBandeja';

export default function GruposBandeja({ data, readOnly, busy, onVerIndividual, onResolver }) {
  const [dialog, setDialog] = useState(null);
  const [mes, setMes] = useState('');
  const [gestion, setGestion] = useState('');
  const [canonico, setCanonico] = useState('');
  const open = group => { setMes(''); setGestion(''); setCanonico(''); setDialog(group); };
  return <>
    {!data?.grupos?.length ? <p role="status">No hay grupos para esta selección.</p> : <div style={{ overflowX: 'auto' }}><table className="dataops-table" style={{ width: '100%' }}>
      <thead><tr><th>Motivo</th><th>Casos</th><th>Revisión</th></tr></thead>
      <tbody>{data.grupos.map(group => <tr key={group.clave}>
        <td><details><summary style={{ cursor: 'pointer', color: 'var(--dataops-info-text)' }}>{textoMotivo(group.motivo, group.titulo)}</summary><p style={{ maxWidth: 580, overflowWrap: 'anywhere', padding: '12px 0', fontSize: 12 }}>{group.ejemplo || 'Sin ejemplo disponible'}</p></details></td>
        <td>{group.n.toLocaleString('es-BO')}</td>
        <td><Button variant="ghost" disabled={busy} onClick={() => onVerIndividual(group.clave)}>Ver casos</Button>
          {!readOnly && group.accion_grupo !== 'MANUAL' && <Button variant="ghost" disabled={busy} onClick={() => group.accion_grupo === 'APROBAR' ? onResolver(group) : open(group)}>{group.accion_grupo === 'APROBAR' ? 'Aprobar grupo' : group.accion_grupo === 'CORREGIR_FECHA' ? 'Corregir fecha' : 'Revisar estado'}</Button>}</td>
      </tr>)}</tbody>
    </table></div>}
    {dialog && <div className="floating-artifact" role="dialog" aria-label="Corregir grupo" style={{ padding: 20, marginTop: 16 }}>
      <p>La corrección se aplicará a los {dialog.n} casos del grupo.</p>
      {dialog.accion_grupo === 'CORREGIR_FECHA' ? <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        <label>Mes<input aria-label="Mes del grupo" className="dataops-input" type="number" min="1" max="12" value={mes} onChange={e => setMes(e.target.value)} /></label>
        <label>Gestión<input aria-label="Gestión del grupo" className="dataops-input" type="number" min="2000" max="2100" value={gestion} onChange={e => setGestion(e.target.value)} /></label>
      </div> : <><label>Estado correcto<input className="dataops-input" value={canonico} onChange={e => setCanonico(e.target.value)} maxLength={100} /></label><p style={{ fontSize: 12 }}>Indica el estado que corresponde antes de aprobar el grupo.</p></>}
      <div style={{ display: 'flex', gap: 12, marginTop: 12 }}><Button variant="ghost" onClick={() => setDialog(null)}>Cancelar</Button>
        <Button disabled={busy || (dialog.accion_grupo === 'CORREGIR_FECHA' ? !(Number(mes) >= 1 && Number(mes) <= 12 && Number(gestion) >= 2000 && Number(gestion) <= 2100) : !canonico.trim())} onClick={() => { onResolver(dialog, dialog.accion_grupo === 'CORREGIR_FECHA' ? { mes: Number(mes), gestion: Number(gestion) } : { canonico: canonico.trim() }); setDialog(null); }}>Programar corrección</Button></div>
    </div>}
  </>;
}
