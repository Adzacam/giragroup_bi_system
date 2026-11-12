import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Building2 } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import Button from '../../components/shared/Button';
import Paginacion from '../../components/shared/Paginacion';
import ResponsiveTable from '../../components/shared/ResponsiveTable';
import DataOpsTabs from './components/DataOpsTabs';
import { catalogApi } from '../../api/catalogApi';
import { dataopsApi } from '../../api/dataopsApi';
import { queryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';
import { confirmar, sileoToast } from '../../services/sileoToast';
import { mensajeError } from '../../utils/mensajeError';
import { useNotifications } from '../../context/NotificationContext';

const EMPTY = { nombre_modulo: '', nombre_institucion: '', programa: '', pos_code: '' };
const ESCALAS = { CENTESIMAL_100: 'Sobre 100', DECIMAL_10: 'Sobre 10', VIGESIMAL_20: 'Sobre 20' };
const tabs = [{ id: 'modulos', label: 'Módulos', icon: BookOpen }, { id: 'instituciones', label: 'Instituciones', icon: Building2 }];

export default function MasterDataView() {
  const { refreshNotifications } = useNotifications();
  const [tipo, setTipo] = useState('modulos');
  const [page, setPage] = useState(1);
  const [input, setInput] = useState('');
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const mutationLock = useRef(false);
  const busy = saving || deleting != null;
  useEffect(() => {
    if (!modal) return undefined;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const close = event => { if (event.key === 'Escape' && !saving) setModal(false); };
    window.addEventListener('keydown', close);
    return () => { document.body.style.overflow = overflow; window.removeEventListener('keydown', close); };
  }, [modal, saving]);
  const { data, error, isFetching, refetch } = useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'master-catalog', tipo, page, search],
    queryFn: () => dataopsApi.getCatalogs({ tipo, page, search }),
    placeholderData: previous => previous,
  });
  useEffect(() => { if (error) sileoToast.error({ title: 'No se pudo consultar el catálogo', description: mensajeError(error) }); }, [error]);
  useEffect(() => { if (!isFetching && data?.pagination && page > data.pagination.total_pages) setPage(data.pagination.total_pages); }, [data, page, isFetching]);
  const update = async () => {
    await queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    await queryClient.invalidateQueries({ queryKey: ['admin', 'catalogos-maestros'] });
    await refreshNotifications();
  };
  const create = async event => {
    event.preventDefault();
    if (mutationLock.current) return;
    mutationLock.current = true; setSaving(true);
    try {
      await catalogApi.createModulo(Object.fromEntries(Object.entries(form).map(([key,value]) => [key, value.trim() || null])));
      setModal(false); setForm(EMPTY);
      sileoToast.success({ title: 'Módulo registrado', description: 'El catálogo se actualizará con el registro guardado.' });
      await update();
    } catch (err) { sileoToast.error({ title: 'No se pudo guardar el módulo', description: mensajeError(err) }); }
    finally { mutationLock.current = false; setSaving(false); }
  };
  const remove = async record => {
    if (mutationLock.current) return;
    mutationLock.current = true; setDeleting(record.id);
    try {
      if (!await confirmar({ title: 'Eliminar módulo sin vínculos', description: `Módulo ${record.id}: ${record.nombre}. Se eliminará únicamente si no tiene datos vinculados.`, confirmText: 'Eliminar módulo' })) return;
      await catalogApi.deleteModulo(record.id);
      sileoToast.success({ title: 'Módulo eliminado', description: 'Se retiró el registro sin datos vinculados.' });
      await update();
    } catch (err) { sileoToast.error({ title: 'No se pudo eliminar el módulo', description: mensajeError(err) }); }
    finally { mutationLock.current = false; setDeleting(null); }
  };
  const refresh = async () => { const result = await refetch(); if (!result.error) sileoToast.success({ title: 'Catálogo actualizado', description: 'Se consultaron los registros guardados.' }); };
  const field = (key, label, required = false, maxLength = 200) => <label style={{ display: 'grid', gap: 6, fontSize: 13 }}>{label}<input className="dataops-input" value={form[key]} onChange={e => setForm(prev => ({ ...prev, [key]: e.target.value }))} required={required} maxLength={maxLength} disabled={saving} /></label>;
  return <div style={{ maxWidth: 1400, margin: '0 auto', paddingBottom: 40 }}>
    <PageHeader category="DATOS MAESTROS" title="Catálogo de referencia" subtitle="Consulta los módulos e instituciones que utiliza el sistema. Las tablas muestran cinco registros por página." action={<div style={{ display: 'flex', gap: 10 }}>
      <Button variant="ghost" isLoading={isFetching} loadingText="Consultando…" disabled={busy} onClick={refresh}>Actualizar</Button>
      {tipo === 'modulos' && <Button disabled={busy} onClick={() => { setForm(EMPTY); setModal(true); }}>Nuevo módulo</Button>}
    </div>} />
    <DataOpsTabs tabs={tabs} activeTab={tipo} disabled={busy} onChangeTab={value => { setTipo(value); setPage(1); setInput(''); setSearch(''); setModal(false); }} />
    <form onSubmit={event => { event.preventDefault(); setSearch(input.trim()); setPage(1); }} style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
      <input className="dataops-input" aria-label="Buscar en el catálogo" placeholder={tipo === 'modulos' ? 'Nombre, código, programa o institución' : 'Nombre o sigla de la institución'} value={input} onChange={e => setInput(e.target.value)} maxLength={100} disabled={busy} style={{ flex: 1 }} />
      <Button type="submit" disabled={busy || isFetching}>Buscar</Button>
      <Button variant="ghost" disabled={busy} onClick={() => { setInput(''); setSearch(''); setPage(1); }}>Limpiar búsqueda</Button>
    </form>
    {tipo === 'instituciones' && <p style={{ color: 'var(--color-slate-gray)', marginBottom: 16, fontSize: 13 }}>Instituciones registradas en el catálogo institucional. Esta vista es de consulta.</p>}
    <div className="floating-artifact" style={{ padding: 20 }} aria-busy={isFetching}>
      {error ? <p role="alert">No se pudo consultar el catálogo. Pulsa Actualizar para reintentarlo.</p> : isFetching || !data ? <p role="status">Consultando registros…</p> : <ResponsiveTable>
        <table className="dataops-table" style={{ width: '100%' }}><thead><tr><th>Registro</th><th>Nombre</th><th>{tipo === 'modulos' ? 'Código' : 'Sigla'}</th>{tipo === 'modulos' ? <><th>Programa</th><th>Institución</th><th>Acción</th></> : <th>Escala de referencia</th>}</tr></thead>
          <tbody>{data.data.map(row => <tr key={row.id}><td>{row.id}</td><td>{row.nombre || 'Sin dato'}</td><td>{row.codigo || 'Sin dato'}</td>{tipo === 'modulos' ? <><td>{row.programa || 'Sin dato'}</td><td>{row.institucion || 'Sin dato'}</td><td><Button variant="ghost" disabled={busy} isLoading={deleting === row.id} loadingText="Procesando…" onClick={() => remove(row)}>Eliminar</Button></td></> : <td>{ESCALAS[row.escala] || 'Sin dato'}</td>}</tr>)}</tbody></table>
        {!data.data.length && <p role="status" style={{ padding: 20 }}>No hay registros para esta búsqueda.</p>}
      </ResponsiveTable>}
      {!isFetching && !error && <Paginacion pagina={page} totalPaginas={data?.pagination?.total_pages || 1} total={data?.pagination?.total_items || 0} filasPorPagina={5} disabled={busy} onChange={setPage} />}
    </div>
    {modal && createPortal(<div className="modal-backdrop show" style={{ zIndex: 2000, padding: 16 }}><section className="modal-panel" role="dialog" aria-modal="true" aria-label="Nuevo módulo" style={{ maxWidth: 520 }}>
      <h2 className="serif-heading" style={{ marginBottom: 16 }}>Nuevo módulo</h2>
      <form onSubmit={create} style={{ display: 'grid', gap: 14 }}>{field('nombre_modulo', 'Nombre del módulo', true)}{field('nombre_institucion', 'Institución', true)}{field('programa', 'Programa (opcional)')}{field('pos_code', 'Código (opcional)', false, 50)}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'end' }}><Button variant="ghost" disabled={saving} onClick={() => setModal(false)}>Cancelar</Button><Button type="submit" isLoading={saving} loadingText="Guardando…">Guardar módulo</Button></div>
      </form>
    </section></div>, document.body)}
  </div>;
}
