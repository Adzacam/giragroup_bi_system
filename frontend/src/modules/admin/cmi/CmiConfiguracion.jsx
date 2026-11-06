import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Save, RotateCcw } from 'lucide-react';
import cmiApi from '../../../api/cmiApi';
import { sileoToast } from '../../../services/sileoToast';
import { UNIDAD } from './cmiFormat';
import './cmi.css';

const COLORES_PERSPECTIVA = ['#0C1E33', '#D99B26', '#1b8754', '#5b6b8c'];

const aNumero = (v) => (v === '' || v === null || v === undefined ? null : Number(v));
const aTexto = (v) => (v === null || v === undefined ? '' : String(v));

const mensajeError = (err) => {
  const d = err?.response?.data?.detail;
  if (Array.isArray(d)) return d.map((e) => e.msg?.replace(/^Value error, /, '')).join(' ');
  return d || 'No se pudo guardar el cambio.';
};

// Regla de coherencia de umbrales (la misma que valida el backend)
function errorUmbrales(sentido, verde, ambar) {
  if (ambar !== null && verde === null) return 'El umbral ámbar requiere un umbral verde.';
  if (verde === null || ambar === null) return null;
  if (sentido === 'MAX' && ambar > verde) return 'Ámbar debe ser ≤ verde (más es mejor).';
  if (sentido === 'MIN' && ambar < verde) return 'Ámbar debe ser ≥ verde (menos es mejor).';
  return null;
}

function useInvalidarCmi() {
  const qc = useQueryClient();
  return (config) => {
    if (config) qc.setQueryData(['cmi', 'config'], config);
    qc.invalidateQueries({ queryKey: ['cmi', 'scorecard'] });
  };
}

function FilaKpi({ kpi }) {
  const inicial = useMemo(() => ({
    nombre: kpi.nombre,
    descripcion: aTexto(kpi.descripcion),
    meta: aTexto(kpi.meta),
    umbral_verde: aTexto(kpi.umbral_verde),
    umbral_ambar: aTexto(kpi.umbral_ambar),
    peso: aTexto(kpi.peso),
    activo: kpi.activo,
  }), [kpi]);
  const [f, setF] = useState(inicial);
  useEffect(() => setF(inicial), [inicial]);
  const invalidar = useInvalidarCmi();

  const sucio = JSON.stringify(f) !== JSON.stringify(inicial);
  const err = errorUmbrales(kpi.sentido, aNumero(f.umbral_verde), aNumero(f.umbral_ambar))
    || (f.nombre.trim().length < 3 ? 'El nombre necesita al menos 3 caracteres.' : null)
    || (f.peso === '' || Number(f.peso) < 0 ? 'El peso debe ser 0 o mayor.' : null);

  const guardar = useMutation({
    mutationFn: () => cmiApi.updateKpi(kpi.codigo, {
      nombre: f.nombre.trim(),
      descripcion: f.descripcion.trim() || null,
      meta: aNumero(f.meta),
      umbral_verde: aNumero(f.umbral_verde),
      umbral_ambar: aNumero(f.umbral_ambar),
      peso: Number(f.peso),
      activo: f.activo,
    }),
    onSuccess: (config) => { invalidar(config); sileoToast.success({ title: 'Indicador actualizado', description: `${kpi.codigo} · ${f.nombre.trim()}` }); },
    onError: (e) => sileoToast.error({ title: 'No se guardó el cambio', description: mensajeError(e) }),
  });

  const set = (campo) => (e) => setF((prev) => ({ ...prev, [campo]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));
  const num = (campo, label) => (
    <td className="num-col">
      <input className="cmi-input num" type="number" step="any" inputMode="decimal" aria-label={`${label} de ${kpi.nombre}`}
             value={f[campo]} onChange={set(campo)}
             aria-invalid={campo.startsWith('umbral') && !!errorUmbrales(kpi.sentido, aNumero(f.umbral_verde), aNumero(f.umbral_ambar))} />
    </td>
  );

  return (
    <tr data-inactivo={!f.activo}>
      <td style={{ whiteSpace: 'nowrap' }}><span className="cmi-kpi-code">{kpi.codigo}</span></td>
      <td style={{ minWidth: 220 }}>
        <input className="cmi-input" aria-label={`Nombre de ${kpi.codigo}`} value={f.nombre} onChange={set('nombre')} maxLength={120} />
        {err && <div className="cmi-row-err" role="alert">{err}</div>}
      </td>
      <td className="sentido">{kpi.sentido === 'MAX' ? '↑ Más es mejor' : '↓ Menos es mejor'}<br />{UNIDAD[kpi.unidad]}</td>
      {num('meta', 'Meta')}
      {num('umbral_verde', 'Umbral verde')}
      {num('umbral_ambar', 'Umbral ámbar')}
      <td className="num-col peso">
        <input className="cmi-input num" type="number" min="0" step="0.5" aria-label={`Peso de ${kpi.nombre}`} value={f.peso} onChange={set('peso')} />
      </td>
      <td style={{ textAlign: 'center' }}>
        <input type="checkbox" aria-label={`${kpi.nombre} activo`} checked={f.activo} onChange={set('activo')} />
      </td>
      <td style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
        {sucio && <span className="cmi-dirty" title="Cambios sin guardar" style={{ marginRight: 8 }} />}
        <button className="cmi-btn" type="button" title="Descartar" aria-label={`Descartar cambios de ${kpi.codigo}`}
                disabled={!sucio || guardar.isPending} onClick={() => setF(inicial)} style={{ padding: '6px 9px', marginRight: 6 }}>
          <RotateCcw size={13} />
        </button>
        <button className="cmi-btn cmi-btn-primary" type="button" aria-label={`Guardar ${kpi.codigo}`}
                disabled={!sucio || !!err || guardar.isPending} onClick={() => guardar.mutate()} style={{ padding: '6px 11px' }}>
          <Save size={13} />{guardar.isPending ? 'Guardando' : 'Guardar'}
        </button>
      </td>
    </tr>
  );
}

function PanelPerspectiva({ p, color }) {
  const inicial = useMemo(() => ({
    nombre: p.nombre, objetivo: p.objetivo, pregunta: p.pregunta, peso: aTexto(p.peso), activa: p.activa,
  }), [p]);
  const [f, setF] = useState(inicial);
  useEffect(() => setF(inicial), [inicial]);
  const invalidar = useInvalidarCmi();
  const sucio = JSON.stringify(f) !== JSON.stringify(inicial);
  const peso = Number(f.peso);
  const err = f.nombre.trim().length < 3 ? 'El nombre necesita al menos 3 caracteres.'
    : f.objetivo.trim().length < 10 ? 'Describe el objetivo estratégico (10 caracteres o más).'
    : f.pregunta.trim().length < 5 ? 'Escribe la pregunta estratégica.'
    : (f.peso === '' || peso < 0 || peso > 100) ? 'El peso debe estar entre 0 y 100.' : null;

  const guardar = useMutation({
    mutationFn: () => cmiApi.updatePerspectiva(p.codigo, {
      nombre: f.nombre.trim(), objetivo: f.objetivo.trim(), pregunta: f.pregunta.trim(), peso, activa: f.activa,
    }),
    onSuccess: (config) => { invalidar(config); sileoToast.success({ title: 'Perspectiva actualizada', description: f.nombre.trim() }); },
    onError: (e) => sileoToast.error({ title: 'No se guardó el cambio', description: mensajeError(e) }),
  });
  const set = (campo) => (e) => setF((prev) => ({ ...prev, [campo]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

  return (
    <section className="cmi-card cmi-cfg-persp" aria-labelledby={`cfg-${p.codigo}`} style={{ borderTop: `4px solid ${color}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginBottom: 14 }}>
        <div>
          <div className="cmi-eyebrow">Perspectiva {p.orden}</div>
          <h3 id={`cfg-${p.codigo}`} style={{ fontFamily: 'var(--font-signifier)', fontWeight: 400, fontSize: 22, margin: '2px 0 0' }}>
            {p.nombre}
          </h3>
          {p.actualizado_por && (
            <div style={{ fontSize: 11.5, color: 'var(--color-slate-gray)', marginTop: 4 }}>
              Última edición: {p.actualizado_por} · {new Date(p.actualizado_en).toLocaleString('es-BO')}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label className="cmi-check">
            <input type="checkbox" checked={f.activa} onChange={set('activa')} /> Visible en el CMI
          </label>
          <button className="cmi-btn" type="button" disabled={!sucio || guardar.isPending} onClick={() => setF(inicial)}>
            <RotateCcw size={13} /> Descartar
          </button>
          <button className="cmi-btn cmi-btn-primary" type="button" disabled={!sucio || !!err || guardar.isPending} onClick={() => guardar.mutate()}>
            <Save size={13} /> {guardar.isPending ? 'Guardando' : 'Guardar perspectiva'}
          </button>
        </div>
      </div>

      <div className="cmi-cfg-grid">
        <label className="cmi-field">Nombre
          <input className="cmi-input" value={f.nombre} onChange={set('nombre')} maxLength={80} />
        </label>
        <label className="cmi-field">Peso en el índice global (%)
          <input className="cmi-input num" type="number" min="0" max="100" step="1" value={f.peso} onChange={set('peso')} />
        </label>
        <label className="cmi-field wide">Objetivo estratégico
          <textarea className="cmi-input" rows={2} value={f.objetivo} onChange={set('objetivo')} maxLength={300} style={{ resize: 'vertical' }} />
        </label>
        <label className="cmi-field wide">Pregunta estratégica
          <input className="cmi-input" value={f.pregunta} onChange={set('pregunta')} maxLength={200} />
        </label>
      </div>
      {err && sucio && <div className="cmi-row-err" role="alert" style={{ marginTop: 8 }}>{err}</div>}

      <div className="cmi-table-wrap">
        <table className="cmi-table">
          <caption className="sr-only" style={{ position: 'absolute', left: -9999 }}>Indicadores de {p.nombre}</caption>
          <thead>
            <tr>
              <th scope="col">Código</th>
              <th scope="col">Indicador</th>
              <th scope="col">Sentido</th>
              <th scope="col">Meta</th>
              <th scope="col">Verde</th>
              <th scope="col">Ámbar</th>
              <th scope="col">Peso</th>
              <th scope="col">Activo</th>
              <th scope="col"><span style={{ position: 'absolute', left: -9999 }}>Acciones</span></th>
            </tr>
          </thead>
          <tbody>{p.kpis.map((k) => <FilaKpi key={k.codigo} kpi={k} />)}</tbody>
        </table>
      </div>
    </section>
  );
}

export default function CmiConfiguracion() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['cmi', 'config'],
    queryFn: cmiApi.getConfig,
    staleTime: 30_000,
  });

  if (isLoading) return <div className="cmi"><div className="cmi-skeleton" style={{ height: 420 }} /></div>;
  if (isError) {
    return (
      <div className="cmi">
        <div className="cmi-card cmi-error" role="alert">
          No se pudo cargar la configuración del CMI.{' '}
          <button className="cmi-btn" onClick={() => refetch()}>Reintentar</button>
        </div>
      </div>
    );
  }

  const perspectivas = data.perspectivas;
  const activas = perspectivas.filter((p) => p.activa);
  const sumaPesos = activas.reduce((s, p) => s + Number(p.peso), 0);

  return (
    <div className="cmi">
      <div className="cmi-card cmi-cfg-intro">
        <p>
          Define el objetivo de cada perspectiva, su peso en el índice global y la meta y los umbrales de semáforo de cada
          indicador. Los cambios se aplican al CMI de la web y al informe de Power BI en su próxima actualización: ambos leen
          esta misma configuración. Un indicador sin umbral verde se muestra, pero no puntúa.
        </p>
        <div className="cmi-weights" aria-label="Distribución de pesos entre perspectivas activas">
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
            <span className="cmi-eyebrow">Pesos de perspectivas</span>
            <strong style={{ color: Math.round(sumaPesos) === 100 ? 'var(--cmi-ok)' : 'var(--cmi-warn)' }}>{sumaPesos} %</strong>
          </div>
          <div className="cmi-stack">
            {activas.map((p) => (
              <i key={p.codigo} title={`${p.nombre}: ${p.peso} %`}
                 style={{ width: `${sumaPesos ? (p.peso / sumaPesos) * 100 : 0}%`, background: COLORES_PERSPECTIVA[(p.orden - 1) % 4] }} />
            ))}
          </div>
          {Math.round(sumaPesos) !== 100 && (
            <span style={{ fontSize: 11.5, color: 'var(--color-slate-gray)' }}>
              Los pesos no suman 100 %; el índice se normaliza sobre {sumaPesos} %.
            </span>
          )}
        </div>
      </div>
      {perspectivas.map((p) => <PanelPerspectiva key={p.codigo} p={p} color={COLORES_PERSPECTIVA[(p.orden - 1) % 4]} />)}
    </div>
  );
}
