import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Archive } from 'lucide-react';
import cmiApi from '../../../../api/cmiApi';
import { sileoToast } from '../../../../services/sileoToast';
import { errorUmbrales } from './PanelPerspectiva';

export default function ConfigKppTab({ perspectivas, medidas, kpisPersonalizados }) {
  const qc = useQueryClient();
  const [persp, setPersp] = useState(() => perspectivas[0]?.codigo || '');
  const medidasPersp = medidas.filter((m) => m.perspectiva === persp);
  const [medida, setMedida] = useState(() => medidasPersp[0]?.codigo || '');
  const [nombre, setNombre] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const medObj = medidas.find((m) => m.codigo === medida) || medidasPersp[0];
  const [agregacion, setAgregacion] = useState(() => medObj?.agregaciones_permitidas?.[0] || 'SUM');
  const [sentido, setSentido] = useState('MAX');
  const [meta, setMeta] = useState('');
  const [uv, setUv] = useState('');
  const [ua, setUa] = useState('');

  const agregacionActual = medObj?.agregaciones_permitidas?.includes(agregacion)
    ? agregacion
    : (medObj?.agregaciones_permitidas?.[0] || 'SUM');
  const errUmbral = errorUmbrales(
    sentido,
    uv === '' ? null : Number(uv),
    ua === '' ? null : Number(ua),
  );

  const crear = useMutation({
    mutationFn: () => cmiApi.createKpiPersonalizado({
      perspectiva: persp,
      nombre: nombre.trim(),
      descripcion: descripcion.trim() || null,
      medida_codigo: medObj?.codigo,
      agregacion: agregacionActual,
      sentido,
      meta: meta === '' ? null : Number(meta),
      umbral_verde: uv === '' ? null : Number(uv),
      umbral_ambar: ua === '' ? null : Number(ua),
      estado: 'ACTIVO',
    }),
    onSuccess: (cfg) => {
      qc.setQueryData(['cmi', 'config'], cfg);
      qc.invalidateQueries({ queryKey: ['cmi'] });
      setNombre('');
      setDescripcion('');
      sileoToast.success({ title: 'KPI personalizado creado' });
    },
    onError: (e) => sileoToast.error({ title: 'No se pudo crear', description: e?.response?.data?.detail || 'Error al guardar.' }),
  });

  const archivar = useMutation({
    mutationFn: (k) => cmiApi.updateKpiPersonalizado(k.codigo, { ...k, estado: k.estado === 'ACTIVO' ? 'ARCHIVADO' : 'ACTIVO' }),
    onSuccess: (cfg) => {
      qc.setQueryData(['cmi', 'config'], cfg);
      qc.invalidateQueries({ queryKey: ['cmi'] });
      sileoToast.success({ title: 'Estado de KPI personalizado actualizado' });
    },
  });

  return (
    <div className="space-y-6">
      <section className="cmi-card cmi-cfg-persp">
        <div className="cmi-eyebrow">Nuevo indicador personalizado (fuera de los 23 oficiales)</div>
        <h3 className="cmi-cfg-sub">Crear KPI personalizado</h3>
        <div className="cmi-cfg-form">
          <label className="cmi-field">
            Perspectiva
            <select
              className="cmi-input"
              value={persp}
              onChange={(e) => {
                const p = e.target.value;
                setPersp(p);
                const first = medidas.find((m) => m.perspectiva === p);
                if (first) {
                  setMedida(first.codigo);
                  setAgregacion(first.agregaciones_permitidas?.[0] || 'SUM');
                }
              }}
            >
              {perspectivas.map((p) => <option key={p.codigo} value={p.codigo}>{p.nombre}</option>)}
            </select>
          </label>
          <label className="cmi-field">
            Medida autorizada (sin PII)
            <select
              className="cmi-input"
              value={medObj?.codigo || ''}
              onChange={(e) => {
                setMedida(e.target.value);
                const m = medidas.find((x) => x.codigo === e.target.value);
                if (m?.agregaciones_permitidas?.length) setAgregacion(m.agregaciones_permitidas[0]);
              }}
            >
              {medidasPersp.map((m) => <option key={m.codigo} value={m.codigo}>{m.nombre}</option>)}
            </select>
          </label>
          <label className="cmi-field">
            Agregación
            <select className="cmi-input" value={agregacionActual} onChange={(e) => setAgregacion(e.target.value)}>
              {(medObj?.agregaciones_permitidas || ['SUM']).map((ag) => <option key={ag} value={ag}>{ag}</option>)}
            </select>
          </label>
          <label className="cmi-field wide">
            Nombre del indicador
            <input className="cmi-input" value={nombre} onChange={(e) => setNombre(e.target.value)} maxLength={120} placeholder="Ej. Inscripciones modalidad virtual" />
          </label>
          <label className="cmi-field">
            Sentido
            <select className="cmi-input" value={sentido} onChange={(e) => setSentido(e.target.value)}>
              <option value="MAX">↑ Más es mejor</option>
              <option value="MIN">↓ Menos es mejor</option>
            </select>
          </label>
          <label className="cmi-field">
            Meta
            <input className="cmi-input num" type="number" step="any" value={meta} onChange={(e) => setMeta(e.target.value)} />
          </label>
          <label className="cmi-field">
            Umbral verde
            <input className="cmi-input num" type="number" step="any" value={uv} onChange={(e) => setUv(e.target.value)} />
          </label>
          <label className="cmi-field">
            Umbral ámbar
            <input className="cmi-input num" type="number" step="any" value={ua} onChange={(e) => setUa(e.target.value)} />
          </label>
        </div>
        {errUmbral && <div className="cmi-row-err" role="alert" style={{ marginTop: 8 }}>{errUmbral}</div>}
        <div className="cmi-cfg-actions">
          <button
            type="button"
            className="cmi-btn cmi-btn-primary"
            disabled={nombre.trim().length < 3 || !medObj || !!errUmbral || crear.isPending}
            onClick={() => crear.mutate()}
          >
            <Plus size={14} aria-hidden="true" />
            <span>{crear.isPending ? 'Creando...' : 'Crear KPI personalizado'}</span>
          </button>
        </div>
      </section>

      <section className="cmi-card cmi-cfg-persp">
        <h3 className="cmi-cfg-sub">KPI personalizados registrados ({kpisPersonalizados.length})</h3>
        {kpisPersonalizados.length === 0 ? (
          <div className="cmi-empty">Aún no hay KPI personalizados en tus perspectivas visibles.</div>
        ) : (
          <div className="cmi-table-wrap">
            <table className="cmi-table">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Nombre</th>
                  <th>Medida</th>
                  <th>Estado</th>
                  <th>Auditoría</th>
                  <th style={{ textAlign: 'right' }}>Acción</th>
                </tr>
              </thead>
              <tbody>
                {kpisPersonalizados.map((k) => (
                  <tr key={k.codigo} data-inactivo={k.estado !== 'ACTIVO'}>
                    <td><span className="cmi-kpi-code">{k.codigo}</span></td>
                    <td>{k.nombre}</td>
                    <td>{k.medida_codigo} ({k.agregacion})</td>
                    <td>{k.estado}</td>
                    <td>{k.actualizado_por || k.creado_por}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button type="button" className="cmi-btn" onClick={() => archivar.mutate(k)}>
                        <Archive size={13} aria-hidden="true" />
                        <span>{k.estado === 'ACTIVO' ? 'Archivar' : 'Reactivar'}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
