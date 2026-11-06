import React, { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, Upload, RotateCcw, Copy, MonitorDown } from 'lucide-react';
import powerbiApi from '../../../api/powerbiApi';
import { sileoToast } from '../../../services/sileoToast';
import './cmi.css';

const fmtTamano = (b) => (b >= 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.round(b / 1024)} KB`);
const fmtFecha = (iso) =>
  new Date(iso).toLocaleString('es-BO', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

const mensajeError = async (err) => {
  let d = err?.response?.data;
  if (d instanceof Blob) {
    try { d = JSON.parse(await d.text()); } catch { d = null; }
  }
  const det = d?.detail;
  if (Array.isArray(det)) return det.map((e) => e.msg).join(' ');
  return det || 'No se pudo completar la operación.';
};

function DatoConexion({ etiqueta, valor }) {
  const copiar = () =>
    navigator.clipboard?.writeText(valor).then(() => sileoToast.success({ title: 'Copiado', description: valor }));
  return (
    <div className="cmi-pbi-dato">
      <span>{etiqueta}</span>
      <code>{valor}</code>
      <button className="cmi-btn cmi-btn-icon" type="button" onClick={copiar} aria-label={`Copiar ${etiqueta}`} title="Copiar">
        <Copy size={14} />
      </button>
    </div>
  );
}

function Versiones({ vigente }) {
  const qc = useQueryClient();
  const { data = [], isLoading } = useQuery({ queryKey: ['powerbi', 'versiones'], queryFn: powerbiApi.getVersiones });
  const restaurar = useMutation({
    mutationFn: powerbiApi.restaurar,
    onSuccess: (v) => {
      qc.invalidateQueries({ queryKey: ['powerbi'] });
      sileoToast.success({ title: 'Versión restaurada', description: `v${v.version} es ahora la vigente.` });
    },
    onError: async (e) => sileoToast.error({ title: 'No se restauró', description: await mensajeError(e) }),
  });
  const descargar = (v) =>
    powerbiApi.descargar(v).catch(async (e) => sileoToast.error({ title: 'No se descargó', description: await mensajeError(e) }));

  if (isLoading) return <div className="cmi-skeleton" style={{ height: 120 }} />;
  if (!data.length) return null;
  return (
    <section className="cmi-card cmi-pbi-bloque" aria-labelledby="pbi-versiones">
      <h3 id="pbi-versiones">Historial de versiones</h3>
      <div className="cmi-table-wrap">
        <table className="cmi-table" style={{ minWidth: 640 }}>
          <thead>
            <tr><th>Versión</th><th>Subida</th><th>Por</th><th>Nota</th><th>Tamaño</th><th aria-label="Acciones" /></tr>
          </thead>
          <tbody>
            {data.map((v) => (
              <tr key={v.version}>
                <td style={{ whiteSpace: 'nowrap' }}>
                  <b>v{v.version}</b>{v.vigente && <span className="cmi-pill cmi-pbi-vigente">Vigente</span>}
                </td>
                <td style={{ whiteSpace: 'nowrap' }}>{fmtFecha(v.subido_en)}</td>
                <td>{v.subido_por}</td>
                <td>{v.nota || <span style={{ color: 'var(--color-slate-gray)' }}>—</span>}</td>
                <td style={{ whiteSpace: 'nowrap' }}>{fmtTamano(v.tamano_bytes)}</td>
                <td style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
                  <button className="cmi-btn" type="button" onClick={() => descargar(v.version)} aria-label={`Descargar v${v.version}`}>
                    <Download size={14} />
                  </button>
                  {!v.vigente && (
                    <button className="cmi-btn" type="button" style={{ marginLeft: 6 }} disabled={restaurar.isPending}
                      onClick={() => restaurar.mutate(v.version)}>
                      <RotateCcw size={14} /> Restaurar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {vigente && <p className="cmi-pbi-nota">Restaurar no borra ninguna versión: sólo cambia cuál descargan los demás roles.</p>}
    </section>
  );
}

function SubirVersion() {
  const qc = useQueryClient();
  const input = useRef(null);
  const [archivo, setArchivo] = useState(null);
  const [nota, setNota] = useState('');
  const subir = useMutation({
    mutationFn: () => powerbiApi.subir(archivo, nota.trim()),
    onSuccess: (v) => {
      qc.invalidateQueries({ queryKey: ['powerbi'] });
      setArchivo(null);
      setNota('');
      if (input.current) input.current.value = '';
      sileoToast.success({ title: 'Nueva versión publicada', description: `v${v.version} es ahora la vigente.` });
    },
    onError: async (e) => sileoToast.error({ title: 'No se subió el informe', description: await mensajeError(e) }),
  });
  return (
    <section className="cmi-card cmi-pbi-bloque" aria-labelledby="pbi-subir">
      <h3 id="pbi-subir">Publicar una nueva versión</h3>
      <p className="cmi-pbi-nota">Edita el informe en Power BI Desktop, guárdalo y súbelo aquí. Se convierte en la versión que descargan los demás roles.</p>
      <div className="cmi-pbi-form">
        <label className="cmi-field">Archivo .pbix
          <input ref={input} className="cmi-input" type="file" accept=".pbix" onChange={(e) => setArchivo(e.target.files?.[0] || null)} />
        </label>
        <label className="cmi-field wide">Nota del cambio (opcional)
          <input className="cmi-input" value={nota} maxLength={300} onChange={(e) => setNota(e.target.value)}
            placeholder="Ej.: nuevo gráfico de matrícula por programa" />
        </label>
        <button className="cmi-btn cmi-btn-primary" type="button" disabled={!archivo || subir.isPending} onClick={() => subir.mutate()}>
          <Upload size={14} /> {subir.isPending ? 'Subiendo…' : 'Publicar versión'}
        </button>
      </div>
    </section>
  );
}

export default function CmiPowerBi() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['powerbi', 'informe'], queryFn: powerbiApi.getInforme });
  const [bajando, setBajando] = useState(false);

  if (isLoading) return <div className="cmi"><div className="cmi-skeleton" style={{ height: 220 }} /></div>;
  if (isError) return <div className="cmi"><div className="cmi-card cmi-error">No se pudo cargar el acceso a Power BI.</div></div>;

  const { vigente, conexion, puede_editar: puedeEditar } = data;
  const descargar = () => {
    setBajando(true);
    powerbiApi.descargar()
      .catch(async (e) => sileoToast.error({ title: 'No se descargó', description: await mensajeError(e) }))
      .finally(() => setBajando(false));
  };

  return (
    <div className="cmi">
      <section className="cmi-card cmi-pbi-hero" aria-labelledby="pbi-titulo">
        <div className="cmi-pbi-icono" aria-hidden="true"><MonitorDown size={26} /></div>
        <div className="cmi-pbi-texto">
          <div className="cmi-eyebrow">Power BI Desktop</div>
          <h2 id="pbi-titulo">Informe del Cuadro de Mando Integral</h2>
          <p>
            Las mismas perspectivas, metas y semáforos de esta página, en un informe de Power BI Desktop para análisis
            detallado. {puedeEditar ? 'Puedes editarlo y publicar nuevas versiones.' : 'Acceso de consulta: descarga la versión vigente.'}
          </p>
          {vigente ? (
            <div className="cmi-pbi-meta">
              <span className="cmi-pill cmi-pbi-vigente">v{vigente.version}</span>
              <span>Actualizado {fmtFecha(vigente.subido_en)} por {vigente.subido_por}</span>
              <span>{fmtTamano(vigente.tamano_bytes)}</span>
              {vigente.nota && <span>· {vigente.nota}</span>}
            </div>
          ) : (
            <div className="cmi-pbi-meta"><span>Aún no hay un informe publicado.</span></div>
          )}
        </div>
        <button className="cmi-btn cmi-btn-primary cmi-pbi-descargar" type="button" disabled={!vigente || bajando} onClick={descargar}>
          <Download size={16} /> {bajando ? 'Descargando…' : 'Descargar .pbix'}
        </button>
      </section>

      <div className="cmi-pbi-grid">
        <section className="cmi-card cmi-pbi-bloque" aria-labelledby="pbi-pasos">
          <h3 id="pbi-pasos">Cómo abrirlo</h3>
          <ol className="cmi-pbi-pasos">
            <li>Instala <b>Power BI Desktop</b> (gratuito, Microsoft Store) en Windows.</li>
            <li>Descarga el informe y ábrelo con doble clic.</li>
            <li>Pulsa <b>Inicio → Actualizar</b> para traer los datos del día. La primera vez pide la contraseña de <code>{conexion.usuario}</code>; solicítala al administrador.</li>
            <li>Sin actualizar, el informe muestra los datos de la última vez que se publicó.</li>
          </ol>
        </section>
        <section className="cmi-card cmi-pbi-bloque" aria-labelledby="pbi-conexion">
          <h3 id="pbi-conexion">Conexión de datos</h3>
          <DatoConexion etiqueta="Servidor" valor={conexion.servidor} />
          <DatoConexion etiqueta="Base de datos" valor={conexion.base_datos} />
          <DatoConexion etiqueta="Usuario" valor={conexion.usuario} />
          <p className="cmi-pbi-nota">
            Usuario de sólo lectura sobre la capa <code>{conexion.esquema}</code>, sin datos personales. El servidor sólo
            acepta conexiones desde el equipo donde corre el sistema.
          </p>
        </section>
      </div>

      {puedeEditar && <SubirVersion />}
      {puedeEditar && <Versiones vigente={vigente} />}
    </div>
  );
}
