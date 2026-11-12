import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import MasterDataView from '../dataops/MasterDataView';
import PageHeader from '../../components/shared/PageHeader';
import Button from '../../components/shared/Button';
import Paginacion from '../../components/shared/Paginacion';
import usePaginacion from '../../hooks/usePaginacion';
import { catalogApi } from '../../api/catalogApi';
import { sileoToast } from '../../services/sileoToast';

function ConceptosFinancieros() {
  const [search, setSearch] = useState('');
  const { data, error, isFetching, refetch } = useQuery({ queryKey: ['admin', 'conceptos-financieros'], queryFn: () => catalogApi.getFinancialConcepts() });
  const rows = useMemo(() => (Array.isArray(data) ? data : data?.data || []).filter(row => [row.codigo_canonico, row.nombre_canonico, row.tipo_movimiento, row.categoria_contable].some(value => String(value || '').toLowerCase().includes(search.toLowerCase()))), [data, search]);
  const pag = usePaginacion(rows);
  return <>
    <PageHeader category="DATOS MAESTROS" title="Conceptos financieros" subtitle="Conceptos registrados para clasificar los movimientos financieros." action={<Button variant="ghost" isLoading={isFetching} loadingText="Consultando…" onClick={async () => { const res = await refetch(); if (res.error) sileoToast.error({ title: 'No se pudo consultar el catálogo' }); else sileoToast.success({ title: 'Catálogo actualizado' }); }}>Actualizar</Button>} />
    <input className="dataops-input" aria-label="Buscar conceptos financieros" placeholder="Código, concepto o categoría" value={search} onChange={e => { setSearch(e.target.value); pag.setPagina(1); }} maxLength={100} style={{ marginBottom: 20 }} />
    <div className="floating-artifact" style={{ padding: 20 }}>{error ? <p role="alert">No se pudo consultar el catálogo. Pulsa Actualizar para reintentarlo.</p> : isFetching ? <p role="status">Consultando conceptos…</p> : <div style={{ overflowX: 'auto' }}><table className="dataops-table" style={{ width: '100%' }}><thead><tr><th>Código</th><th>Concepto</th><th>Movimiento</th><th>Categoría</th></tr></thead><tbody>{pag.visibles.map(row => <tr key={row.id_concepto}><td>{row.codigo_canonico || 'Sin dato'}</td><td>{row.nombre_canonico || 'Sin dato'}</td><td>{row.tipo_movimiento || 'Sin dato'}</td><td>{row.categoria_contable || 'Sin dato'}</td></tr>)}</tbody></table>{!rows.length && <p>No hay conceptos para esta búsqueda.</p>}</div>}
      <Paginacion pagina={pag.pagina} totalPaginas={pag.totalPaginas} total={rows.length} filasPorPagina={5} disabled={isFetching} onChange={pag.setPagina} />
    </div>
  </>;
}

export default function CatalogosMaestros() {
  const [tab, setTab] = useState('referencia');
  return <div style={{ maxWidth: 1400, margin: '0 auto' }}>
    <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}><Button variant={tab === 'referencia' ? 'dark' : 'ghost'} onClick={() => setTab('referencia')}>Módulos e instituciones</Button><Button variant={tab === 'finanzas' ? 'dark' : 'ghost'} onClick={() => setTab('finanzas')}>Conceptos financieros</Button></div>
    {tab === 'referencia' ? <MasterDataView /> : <ConceptosFinancieros />}
  </div>;
}
