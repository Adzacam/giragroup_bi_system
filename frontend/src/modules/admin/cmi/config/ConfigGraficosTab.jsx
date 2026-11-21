import React, { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Eye, Plus, EyeOff } from 'lucide-react';
import cmiApi from '../../../../api/cmiApi';
import { sileoToast } from '../../../../services/sileoToast';
import { useTheme } from '../../../../context/ThemeContext';
import { getChartTokens, buildChartOptions } from '../chartTheme';
import GraficoPersonalizadoBody from '../scorecard/GraficoPersonalizadoBody';

export default function ConfigGraficosTab({ perspectivas, medidas, graficos }) {
  const qc = useQueryClient();
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const tokens = useMemo(() => getChartTokens(isDark), [isDark]);

  const [persp, setPersp] = useState(() => perspectivas[0]?.codigo || '');
  const medidasPersp = medidas.filter((m) => m.perspectiva === persp);
  const [medida, setMedida] = useState(() => medidasPersp[0]?.codigo || '');
  const medObj = medidas.find((m) => m.codigo === medida) || medidasPersp[0];
  const dims = medObj?.dimensiones_permitidas || [];

  const [dimension, setDimension] = useState(() => dims[0]?.codigo || '');
  const [agregacion, setAgregacion] = useState(() => medObj?.agregaciones_permitidas?.[0] || 'SUM');
  const [tipo, setTipo] = useState('bar');
  const [titulo, setTitulo] = useState('');
  const [preview, setPreview] = useState(null);

  const dimActual = dims.find((d) => d.codigo === dimension) ? dimension : (dims[0]?.codigo || '');

  const hacerPreview = useMutation({
    mutationFn: () => cmiApi.previewGrafico({
      medida_codigo: medObj.codigo,
      dimension_codigo: dimActual,
      agregacion,
    }),
    onSuccess: (res) => setPreview(res),
    onError: (e) => sileoToast.error({ title: 'No se pudo previsualizar', description: e?.response?.data?.detail || 'Error.' }),
  });

  const guardar = useMutation({
    mutationFn: () => cmiApi.createGrafico({
      perspectiva: persp,
      titulo: titulo.trim(),
      medida_codigo: medObj.codigo,
      dimension_codigo: dimActual,
      agregacion,
      tipo_grafico: tipo,
      orden: 10,
      visible: true,
    }),
    onSuccess: (cfg) => {
      qc.setQueryData(['cmi', 'config'], cfg);
      qc.invalidateQueries({ queryKey: ['cmi'] });
      setTitulo('');
      setPreview(null);
      sileoToast.success({ title: 'Gráfica personalizada guardada' });
    },
    onError: (e) => sileoToast.error({ title: 'No se pudo guardar', description: e?.response?.data?.detail || 'Error.' }),
  });

  const toggleVisible = useMutation({
    mutationFn: (g) => cmiApi.updateGrafico(g.id, { ...g, visible: !g.visible }),
    onSuccess: (cfg) => {
      qc.setQueryData(['cmi', 'config'], cfg);
      qc.invalidateQueries({ queryKey: ['cmi'] });
    },
  });

  const previewChartData = preview?.filas?.length ? preview.filas : null;

  const chartOpts = useMemo(() => buildChartOptions(isDark), [isDark]);

  return (
    <div className="space-y-6">
      <section className="cmi-card cmi-cfg-persp">
        <div className="cmi-eyebrow">Constructor seguro de gráficas (lista blanca sin PII)</div>
        <h3 className="cmi-cfg-sub">Nueva gráfica personalizada</h3>
        <div className="cmi-cfg-form">
          <label className="cmi-field">
            Perspectiva destino
            <select
              className="cmi-input"
              value={persp}
              onChange={(e) => {
                const p = e.target.value;
                setPersp(p);
                const first = medidas.find((m) => m.perspectiva === p);
                if (first) {
                  setMedida(first.codigo);
                  setDimension(first.dimensiones_permitidas?.[0]?.codigo || '');
                  setAgregacion(first.agregaciones_permitidas?.[0] || 'SUM');
                }
              }}
            >
              {perspectivas.map((p) => <option key={p.codigo} value={p.codigo}>{p.nombre}</option>)}
            </select>
          </label>
          <label className="cmi-field">
            Medida
            <select
              className="cmi-input"
              value={medObj?.codigo || ''}
              onChange={(e) => {
                setMedida(e.target.value);
                const m = medidas.find((x) => x.codigo === e.target.value);
                if (m) {
                  setDimension(m.dimensiones_permitidas?.[0]?.codigo || '');
                  setAgregacion(m.agregaciones_permitidas?.[0] || 'SUM');
                }
              }}
            >
              {medidasPersp.map((m) => <option key={m.codigo} value={m.codigo}>{m.nombre}</option>)}
            </select>
          </label>
          <label className="cmi-field">
            Dimensión
            <select className="cmi-input" value={dimActual} onChange={(e) => setDimension(e.target.value)}>
              {dims.map((d) => <option key={d.codigo} value={d.codigo}>{d.label}</option>)}
            </select>
          </label>
          <label className="cmi-field">
            Agregación
            <select className="cmi-input" value={agregacion} onChange={(e) => setAgregacion(e.target.value)}>
              {(medObj?.agregaciones_permitidas || ['SUM']).map((ag) => <option key={ag} value={ag}>{ag}</option>)}
            </select>
          </label>
          <label className="cmi-field">
            Tipo de gráfica
            <select className="cmi-input" value={tipo} onChange={(e) => setTipo(e.target.value)}>
              <option value="bar">Barras</option>
              <option value="line">Línea</option>
              <option value="area">Área</option>
              <option value="doughnut">Dona</option>
              <option value="table">Tabla</option>
            </select>
          </label>
          <label className="cmi-field wide">
            Título de la gráfica
            <input className="cmi-input" value={titulo} onChange={(e) => setTitulo(e.target.value)} maxLength={120} placeholder="Ej. Inscripciones por modalidad" />
          </label>
        </div>

        <div className="cmi-cfg-actions">
          <button type="button" className="cmi-btn" disabled={!medObj || !dimActual || hacerPreview.isPending} onClick={() => hacerPreview.mutate()}>
            <Eye size={14} aria-hidden="true" />
            <span>{hacerPreview.isPending ? 'Consultando...' : 'Vista previa'}</span>
          </button>
          <button type="button" className="cmi-btn cmi-btn-primary" disabled={titulo.trim().length < 3 || !medObj || !dimActual || guardar.isPending} onClick={() => guardar.mutate()}>
            <Plus size={14} aria-hidden="true" />
            <span>{guardar.isPending ? 'Guardando...' : 'Guardar gráfica'}</span>
          </button>
        </div>

        {previewChartData && (
          <div className="cmi-ov-chart" style={{ marginTop: 16 }}>
            <GraficoPersonalizadoBody
              tipo={tipo}
              titulo={titulo.trim() || `${preview.medida} (${preview.agregacion})`}
              filas={previewChartData}
              tokens={tokens}
              chartOpts={chartOpts}
            />
          </div>
        )}
      </section>

      <section className="cmi-card cmi-cfg-persp">
        <h3 className="cmi-cfg-sub">Gráficas personalizadas ({graficos.length})</h3>
        {graficos.length === 0 ? (
          <div className="cmi-empty">No hay gráficas personalizadas registradas.</div>
        ) : (
          <div className="cmi-table-wrap">
            <table className="cmi-table">
              <thead>
                <tr>
                  <th>Título</th>
                  <th>Perspectiva</th>
                  <th>Medida / Dimensión</th>
                  <th>Tipo</th>
                  <th style={{ textAlign: 'right' }}>Visibilidad</th>
                </tr>
              </thead>
              <tbody>
                {graficos.map((g) => (
                  <tr key={g.id} data-inactivo={!g.visible}>
                    <td>{g.titulo}</td>
                    <td>{g.perspectiva}</td>
                    <td>{g.medida_codigo} · {g.dimension_codigo} ({g.agregacion})</td>
                    <td>{g.tipo_grafico}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button type="button" className="cmi-btn" onClick={() => toggleVisible.mutate(g)}>
                        {g.visible ? <EyeOff size={13} aria-hidden="true" /> : <Eye size={13} aria-hidden="true" />}
                        <span>{g.visible ? 'Ocultar' : 'Mostrar'}</span>
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
