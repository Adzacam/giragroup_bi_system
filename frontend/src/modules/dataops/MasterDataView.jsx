import React, { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Building2, Filter, Sparkles, Trash2 } from 'lucide-react';
import PageHeader from '../../components/shared/PageHeader';
import Button from '../../components/shared/Button';
import Paginacion from '../../components/shared/Paginacion';
import DataOpsTabs from './components/DataOpsTabs';
import { catalogApi } from '../../api/catalogApi';
import { dataopsApi } from '../../api/dataopsApi';
import { queryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';
import { confirmar, sileoToast } from '../../services/sileoToast';
import { mensajeError } from '../../utils/mensajeError';
import { useNotifications } from '../../context/NotificationContext';
import { useAuth } from '../../context/AuthContext';
import { useParentChildTransitionV2 } from '../../v2/transitions/useParentChildTransitionV2';
import './MasterDataView.css';

const EMPTY = { nombre_modulo: '', nombre_institucion: 'GiraGroup Posgrado', programa: '', pos_code: '' };
const ESCALAS = { CENTESIMAL_100: 'Sobre 100', DECIMAL_10: 'Sobre 10', VIGESIMAL_20: 'Sobre 20' };
const tabs = [
  { id: 'modulos', label: 'Módulos', icon: BookOpen },
  { id: 'instituciones', label: 'Instituciones', icon: Building2 },
];

export default function MasterDataView() {
  const { refreshNotifications } = useNotifications();
  const { role } = useAuth();
  const isAdmin = String(role || '').toUpperCase() === 'ADMIN';
  const { triggerParentChild } = useParentChildTransitionV2();

  const [tipo, setTipo] = useState('modulos');
  const [page, setPage] = useState(1);
  const [input, setInput] = useState('');
  const [search, setSearch] = useState('');

  // CAT-L5 filters for modulos
  const [soloGenericos, setSoloGenericos] = useState(false);
  const [sinPrograma, setSinPrograma] = useState(false);
  const [uso, setUso] = useState('todos');

  // CAT-L7 filter for instituciones
  const [grupo, setGrupo] = useState('todos');

  // Modals (native <dialog>)
  const createDialogRef = useRef(null);
  const cleanupDialogRef = useRef(null);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(null);

  const [cleanupOpen, setCleanupOpen] = useState(false);
  const [cleanupPreview, setCleanupPreview] = useState(null);
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [cleanupRunning, setCleanupRunning] = useState(false);

  const mutationLock = useRef(false);
  const busy = saving || deleting != null || cleanupRunning;

  useEffect(() => {
    const dlg = createDialogRef.current;
    if (!dlg) return;
    if (modal && !dlg.open) dlg.showModal();
    else if (!modal && dlg.open) dlg.close();
  }, [modal]);

  useEffect(() => {
    const dlg = cleanupDialogRef.current;
    if (!dlg) return;
    if (cleanupOpen && !dlg.open) dlg.showModal();
    else if (!cleanupOpen && dlg.open) dlg.close();
  }, [cleanupOpen]);

  const { data, error, isFetching, refetch } = useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'master-catalog', tipo, page, search, soloGenericos, sinPrograma, uso, grupo],
    queryFn: () =>
      dataopsApi.getCatalogs({
        tipo,
        page,
        search,
        solo_genericos: soloGenericos,
        sin_programa: sinPrograma,
        uso,
        grupo,
      }),
    placeholderData: previous => previous,
  });

  useEffect(() => {
    if (error) sileoToast.error({ title: 'No se pudo consultar el catálogo', description: mensajeError(error) });
  }, [error]);

  useEffect(() => {
    if (!isFetching && data?.pagination && page > data.pagination.total_pages) {
      setPage(data.pagination.total_pages);
    }
  }, [data, page, isFetching]);

  const update = async () => {
    await queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
    await queryClient.invalidateQueries({ queryKey: ['admin', 'catalogos-maestros'] });
    await refreshNotifications();
  };

  const create = async event => {
    event.preventDefault();
    if (mutationLock.current) return;
    mutationLock.current = true;
    setSaving(true);
    try {
      await catalogApi.createModulo(
        Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value.trim() || null])),
      );
      setModal(false);
      setForm(EMPTY);
      sileoToast.success({ title: 'Módulo registrado', description: 'El catálogo se actualizará con el registro guardado.' });
      await update();
    } catch (err) {
      sileoToast.error({ title: 'No se pudo guardar el módulo', description: mensajeError(err) });
    } finally {
      mutationLock.current = false;
      setSaving(false);
    }
  };

  const remove = async record => {
    if (mutationLock.current || Number(record.en_uso) > 0) return;
    mutationLock.current = true;
    setDeleting(record.id);
    try {
      const ok = await confirmar({
        title: 'Eliminar módulo sin vínculos',
        description: `Módulo ${record.id}: ${record.nombre}. Se eliminará únicamente porque no tiene hechos vinculados.`,
        confirmText: 'Eliminar módulo',
      });
      if (!ok) return;
      await catalogApi.deleteModulo(record.id);
      sileoToast.success({ title: 'Módulo eliminado', description: 'Se retiró el registro sin datos vinculados.' });
      await update();
    } catch (err) {
      sileoToast.error({ title: 'No se pudo eliminar el módulo', description: mensajeError(err) });
    } finally {
      mutationLock.current = false;
      setDeleting(null);
    }
  };

  const openCleanupPreview = async () => {
    setCleanupOpen(true);
    setCleanupLoading(true);
    setCleanupPreview(null);
    try {
      const prev = await dataopsApi.previewLimpiarModulosSinUso();
      setCleanupPreview(prev);
    } catch (err) {
      sileoToast.error({ title: 'No se pudo cargar la vista previa', description: mensajeError(err) });
      setCleanupOpen(false);
    } finally {
      setCleanupLoading(false);
    }
  };

  const confirmCleanup = async () => {
    if (mutationLock.current) return;
    mutationLock.current = true;
    setCleanupRunning(true);
    try {
      const res = await dataopsApi.limpiarModulosSinUso();
      setCleanupOpen(false);
      sileoToast.success({
        title: 'Limpieza completada',
        description: `Se eliminaron ${res.eliminados} módulo(s) sin uso.`,
      });
      await update();
    } catch (err) {
      sileoToast.error({ title: 'No se pudo completar la limpieza', description: mensajeError(err) });
    } finally {
      mutationLock.current = false;
      setCleanupRunning(false);
    }
  };

  const refresh = async () => {
    const result = await refetch();
    if (!result.error) sileoToast.success({ title: 'Catálogo actualizado', description: 'Se consultaron los registros guardados.' });
  };

  const totalSinUso = data?.resumen?.total_sin_uso ?? 0;
  const pageSize = data?.pagination?.page_size || 20;
  const gruposInst = data?.grupos || { propia: 0, convenio: 0 };

  const field = (key, label, required = false, maxLength = 200, autoFocus = false) => (
    <label style={{ display: 'grid', gap: 6, fontSize: 13 }}>
      {label}
      <input
        className="dataops-input"
        value={form[key]}
        onChange={e => setForm(prev => ({ ...prev, [key]: e.target.value }))}
        required={required}
        maxLength={maxLength}
        disabled={saving}
        autoFocus={autoFocus}
      />
    </label>
  );

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', paddingBottom: 40 }}>
      <PageHeader
        category="DATOS MAESTROS"
        title="Catálogo de referencia"
        subtitle="Consulta los módulos e instituciones que utiliza el sistema. Las tablas muestran veinte registros por página."
        action={
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            <Button variant="ghost" isLoading={isFetching} loadingText="Consultando…" disabled={busy} onClick={refresh}>
              Actualizar
            </Button>
            {tipo === 'modulos' && isAdmin && totalSinUso > 0 && (
              <Button variant="ghost" disabled={busy} onClick={openCleanupPreview}>
                <Trash2 size={15} aria-hidden="true" style={{ marginRight: 6 }} />
                Limpiar módulos sin uso ({totalSinUso})
              </Button>
            )}
            {tipo === 'modulos' && (
              <Button disabled={busy} onClick={() => { setForm(EMPTY); setModal(true); }}>
                Nuevo módulo
              </Button>
            )}
          </div>
        }
      />

      <DataOpsTabs
        tabs={tabs}
        activeTab={tipo}
        disabled={busy}
        onChangeTab={(value, sourceEl) =>
          triggerParentChild(sourceEl, () => {
            setTipo(value);
            setPage(1);
            setInput('');
            setSearch('');
            setSoloGenericos(false);
            setSinPrograma(false);
            setUso('todos');
            setGrupo('todos');
            setModal(false);
          })
        }
      />

      <form
        onSubmit={event => {
          event.preventDefault();
          setSearch(input.trim());
          setPage(1);
        }}
        className="cat-ref-toolbar"
      >
        <div className="cat-ref-search">
          <input
            className="dataops-input"
            aria-label="Buscar en el catálogo"
            placeholder={
              tipo === 'modulos'
                ? 'Nombre, código POS, programa o institución'
                : 'Nombre, sigla o variante de la institución'
            }
            value={input}
            onChange={e => setInput(e.target.value)}
            maxLength={100}
            disabled={busy}
            style={{ flex: 1, minWidth: 0 }}
          />
          <Button type="submit" disabled={busy || isFetching}>
            Buscar
          </Button>
          <Button
            type="button"
            variant="ghost"
            disabled={busy}
            onClick={() => {
              setInput('');
              setSearch('');
              setPage(1);
            }}
          >
            Limpiar
          </Button>
        </div>
      </form>

      {tipo === 'modulos' ? (
        <div className="cat-ref-filters" role="group" aria-label="Filtros de módulos">
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12, color: 'var(--color-slate-gray)', marginRight: 4 }}>
            <Filter size={13} aria-hidden="true" /> Filtros:
          </span>
          <button
            type="button"
            className="cat-chip-btn"
            aria-pressed={soloGenericos}
            disabled={busy}
            onClick={() => { setSoloGenericos(v => !v); setPage(1); }}
          >
            <Sparkles size={13} aria-hidden="true" /> Solo genéricos
          </button>
          <button
            type="button"
            className="cat-chip-btn"
            aria-pressed={sinPrograma}
            disabled={busy}
            onClick={() => { setSinPrograma(v => !v); setPage(1); }}
          >
            Sin programa
          </button>
          <select
            aria-label="Filtrar por uso en hechos"
            className="dataops-input"
            style={{ width: 'auto', minWidth: 165, padding: '6px 10px', fontSize: 13 }}
            value={uso}
            disabled={busy}
            onChange={e => { setUso(e.target.value); setPage(1); }}
          >
            <option value="todos">Todos (en uso y sin uso)</option>
            <option value="en_uso">Solo en uso</option>
            <option value="sin_uso">Solo sin uso</option>
          </select>
        </div>
      ) : (
        <div className="cat-ref-filters" role="group" aria-label="Grupos de instituciones">
          <button
            type="button"
            className="cat-chip-btn"
            aria-pressed={grupo === 'todos'}
            disabled={busy}
            onClick={() => { setGrupo('todos'); setPage(1); }}
          >
            Todas ({gruposInst.propia + gruposInst.convenio})
          </button>
          <button
            type="button"
            className="cat-chip-btn"
            aria-pressed={grupo === 'propia'}
            disabled={busy}
            onClick={() => { setGrupo('propia'); setPage(1); }}
          >
            Propia ({gruposInst.propia})
          </button>
          <button
            type="button"
            className="cat-chip-btn"
            aria-pressed={grupo === 'convenio'}
            disabled={busy}
            onClick={() => { setGrupo('convenio'); setPage(1); }}
          >
            Convenio ({gruposInst.convenio})
          </button>
        </div>
      )}

      <div className="floating-artifact v2-parent-child-panel" style={{ padding: 20 }} aria-busy={isFetching}>
        {error ? (
          <p role="alert">No se pudo consultar el catálogo. Pulsa Actualizar para reintentarlo.</p>
        ) : isFetching || !data ? (
          <p role="status">Consultando registros…</p>
        ) : (
          <div className="cat-table-region" tabIndex={0} role="region" aria-label={tipo === 'modulos' ? 'Tabla de módulos' : 'Tabla de instituciones'}>
            <table className="dataops-table">
              <thead>
                {tipo === 'modulos' ? (
                  <tr>
                    <th>Registro</th>
                    <th>Nombre</th>
                    <th>Código</th>
                    <th>Programa</th>
                    <th>Institución</th>
                    <th>En uso</th>
                    <th>Acción</th>
                  </tr>
                ) : (
                  <tr>
                    <th>Grupo</th>
                    <th>Nombre</th>
                    <th>Sigla</th>
                    <th>Programas</th>
                    <th>Inscritos</th>
                    <th>Años con techo / Escala</th>
                  </tr>
                )}
              </thead>
              <tbody>
                {data.data.map((row, idx) =>
                  tipo === 'modulos' ? (
                    <tr key={row.id} className="cat-row-enter" style={{ animationDelay: `${Math.min(idx, 10) * 18}ms` }}>
                      <td data-label="Registro">{row.id}</td>
                      <td data-label="Nombre">{row.nombre || 'Sin dato'}</td>
                      <td data-label="Código">{row.codigo || 'Sin dato'}</td>
                      <td data-label="Programa">{row.programa || 'Sin dato'}</td>
                      <td data-label="Institución">{row.institucion || 'Sin dato'}</td>
                      <td data-label="En uso">
                        <span className={`cat-badge ${Number(row.en_uso) > 0 ? 'cat-badge--en-uso' : 'cat-badge--sin-uso'}`}>
                          {Number(row.en_uso) > 0 ? `${row.en_uso} hecho(s)` : 'Sin uso (0)'}
                        </span>
                      </td>
                      <td data-label="Acción">
                        <Button
                          variant="ghost"
                          disabled={busy || Number(row.en_uso) > 0}
                          title={Number(row.en_uso) > 0 ? 'Tiene hechos vinculados; no se puede eliminar' : 'Eliminar módulo sin referencias'}
                          isLoading={deleting === row.id}
                          loadingText="Procesando…"
                          onClick={() => remove(row)}
                        >
                          Eliminar
                        </Button>
                      </td>
                    </tr>
                  ) : (
                    <tr key={row.id} className="cat-row-enter" style={{ animationDelay: `${Math.min(idx, 10) * 18}ms` }}>
                      <td data-label="Grupo">
                        <span className={`cat-badge ${row.grupo === 'propia' ? 'cat-badge--propia' : 'cat-badge--convenio'}`}>
                          {row.grupo === 'propia' ? 'Propia' : 'Convenio'}
                        </span>
                      </td>
                      <td data-label="Nombre">{row.nombre || 'Sin dato'}</td>
                      <td data-label="Sigla">{row.codigo || '—'}</td>
                      <td data-label="Programas">{row.n_programas ?? 0}</td>
                      <td data-label="Inscritos">{row.n_inscritos ?? 0}</td>
                      <td data-label="Años con techo / Escala">
                        {row.grupo === 'propia'
                          ? ESCALAS[row.escala] || 'Sobre 100'
                          : row.anios?.length
                            ? row.anios.join(', ')
                            : 'Sin techo cargado'}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
            {!data.data.length && <p role="status" style={{ padding: 20 }}>No hay registros para esta búsqueda.</p>}
          </div>
        )}
        {!isFetching && !error && (
          <Paginacion
            pagina={page}
            totalPaginas={data?.pagination?.total_pages || 1}
            total={data?.pagination?.total_items || 0}
            filasPorPagina={pageSize}
            disabled={busy}
            onChange={setPage}
          />
        )}
      </div>

      {/* Diálogo nativo: Nuevo módulo */}
      <dialog
        ref={createDialogRef}
        className="cat-native-dialog"
        aria-labelledby="cat-new-mod-title"
        onClose={() => { if (!saving) setModal(false); }}
      >
        <h2 id="cat-new-mod-title" className="serif-heading" style={{ marginBottom: 16 }}>
          Nuevo módulo
        </h2>
        <form onSubmit={create} style={{ display: 'grid', gap: 14 }}>
          {field('nombre_modulo', 'Nombre del módulo', true, 200, true)}
          {field('nombre_institucion', 'Institución', true)}
          {field('programa', 'Programa (opcional)')}
          {field('pos_code', 'Código POS (ej. POS-5072)', false, 50)}
          <div style={{ display: 'flex', gap: 12, justifyContent: 'end', marginTop: 8 }}>
            <Button type="button" variant="ghost" disabled={saving} onClick={() => setModal(false)}>
              Cancelar
            </Button>
            <Button type="submit" isLoading={saving} loadingText="Guardando…">
              Guardar módulo
            </Button>
          </div>
        </form>
      </dialog>

      {/* Diálogo nativo: Vista previa limpieza de módulos sin uso (ADMIN) */}
      <dialog
        ref={cleanupDialogRef}
        className="cat-native-dialog"
        aria-labelledby="cat-cleanup-title"
        onClose={() => { if (!cleanupRunning) setCleanupOpen(false); }}
      >
        <h2 id="cat-cleanup-title" className="serif-heading" style={{ marginBottom: 10 }}>
          Limpiar módulos sin uso
        </h2>
        {cleanupLoading ? (
          <p role="status">Calculando módulos sin referencias…</p>
        ) : cleanupPreview ? (
          <div style={{ display: 'grid', gap: 12 }}>
            <p style={{ fontSize: 14, color: 'var(--color-slate-gray)' }}>
              Se encontraron <strong>{cleanupPreview.total_sin_uso}</strong> módulo(s) sin ninguna referencia en tablas de hechos ni staging.
              Esta acción eliminará únicamente los módulos sin uso.
            </p>
            {cleanupPreview.muestra?.length > 0 && (
              <div style={{ maxHeight: 220, overflow: 'auto', border: '1px solid var(--color-border, #e2e8f0)', borderRadius: 8, padding: 8 }}>
                <table className="dataops-table" style={{ width: '100%', fontSize: 12 }}>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Código</th>
                      <th>Nombre</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cleanupPreview.muestra.map(m => (
                      <tr key={m.id}>
                        <td>{m.id}</td>
                        <td>{m.codigo || '—'}</td>
                        <td>{m.nombre}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'end', marginTop: 6 }}>
              <Button type="button" variant="ghost" autoFocus disabled={cleanupRunning} onClick={() => setCleanupOpen(false)}>
                Cancelar
              </Button>
              <Button
                type="button"
                disabled={cleanupRunning || !cleanupPreview.total_sin_uso}
                isLoading={cleanupRunning}
                loadingText="Limpiando…"
                onClick={confirmCleanup}
              >
                Eliminar {cleanupPreview.total_sin_uso} módulos sin uso
              </Button>
            </div>
          </div>
        ) : null}
      </dialog>
    </div>
  );
}
