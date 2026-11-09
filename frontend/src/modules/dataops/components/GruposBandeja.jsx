import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { dataopsApi } from '../../../api/dataopsApi';
import { sileoToast } from '../../../services/sileoToast';
import { describirGrupo, ESTADOS_VINCULO, textoAccion, textoMotivo } from '../../../constants/motivosBandeja';

const accionDe = (g) => g.accion_grupo || 'APROBAR';

/**
 * Bandeja por grupos: casos pendientes agrupados por (motivo, valor normalizado). Cada grupo se resuelve con una sola acción:
 * Aprobar grupo (APROBAR), Mapear a estado canónico (MAPEAR_ESTADO) o Corregir fecha (CORREGIR_FECHA); los MANUAL se revisan en la vista individual.
 */
export default function GruposBandeja({ docId = null, onVerIndividual, onCambio }) {
  const [data, setData] = useState({ total_casos: 0, total_grupos: 0, grupos: [] });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [enCurso, setEnCurso] = useState(null);
  const [dialogo, setDialogo] = useState(null); // { tipo: 'MAPEAR_ESTADO' | 'CORREGIR_FECHA', grupo }
  const [canonico, setCanonico] = useState('');
  const [mes, setMes] = useState(String(new Date().getMonth() + 1));
  const [gestion, setGestion] = useState(String(new Date().getFullYear()));

  const cargar = useCallback(async () => {
    try {
      setCargando(true);
      setError('');
      setData(await dataopsApi.getGruposBandeja({ docId }));
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'No se pudieron cargar los grupos.');
    } finally {
      setCargando(false);
    }
  }, [docId]);

  useEffect(() => { cargar(); }, [cargar]);

  // Casos que se resuelven en bloque: todos los grupos con una acción de grupo (no los MANUAL)
  const resumen = useMemo(() => {
    const enBloque = data.grupos.filter((g) => accionDe(g) !== 'MANUAL');
    return { casosEnBloque: enBloque.reduce((s, g) => s + g.n, 0), gruposEnBloque: enBloque.length };
  }, [data]);

  const ejecutar = async (g, extra = {}) => {
    try {
      setEnCurso(g.clave);
      const accion = accionDe(g);
      const res = await dataopsApi.aprobarGrupo({ clave: g.clave, accion: accion === 'MAPEAR_ESTADO' ? 'MAPEAR_ESTADO' : null, docIds: docId ? [docId] : null, ...extra });
      if (res.status === 'error') {
        sileoToast.error({ title: 'No se pudo resolver el grupo', description: res.message });
      } else {
        sileoToast.success({ title: 'Grupo resuelto', description: `${res.resolved_count ?? 0} casos resueltos (${textoAccion(accion).toLowerCase()}).` });
      }
      setDialogo(null);
      setCanonico('');
      await cargar();
      if (onCambio) onCambio();
    } catch (e) {
      sileoToast.error({ title: 'No se pudo resolver el grupo', description: e.response?.data?.detail || e.message });
    } finally {
      setEnCurso(null);
    }
  };

  const abrirDialogo = (tipo, grupo) => { setCanonico(''); setDialogo({ tipo, grupo }); };

  const confirmarDialogo = () => {
    if (!dialogo) return;
    if (dialogo.tipo === 'MAPEAR_ESTADO') ejecutar(dialogo.grupo, { canonico: canonico.trim() || null });
    else ejecutar(dialogo.grupo, { mes: Number(mes), gestion: Number(gestion) });
  };

  const botonAccion = (g) => {
    const accion = accionDe(g);
    const ocupado = enCurso === g.clave;
    if (accion === 'MANUAL') {
      return (
        <button type="button" className="pill-filter" data-testid="grupo-manual" onClick={() => onVerIndividual && onVerIndividual()}>
          {textoAccion('MANUAL')}
        </button>
      );
    }
    if (accion === 'MAPEAR_ESTADO' || accion === 'CORREGIR_FECHA') {
      return (
        <button type="button" className="btn-pill-gold" style={{ padding: '5px 12px', fontSize: '12px' }} disabled={ocupado} data-testid={`grupo-${accion.toLowerCase()}`}
          onClick={() => abrirDialogo(accion, g)}>
          {ocupado ? 'Aplicando…' : `${textoAccion(accion)}…`}
        </button>
      );
    }
    return (
      <button type="button" className="btn-pill-gold" style={{ padding: '5px 12px', fontSize: '12px' }} disabled={ocupado} data-testid="grupo-aprobar" onClick={() => ejecutar(g)}>
        {ocupado ? 'Aprobando…' : textoAccion('APROBAR')}
      </button>
    );
  };

  if (cargando) {
    return <div className="floating-artifact" style={{ padding: '48px', textAlign: 'center', color: 'var(--color-slate-gray)' }}>Cargando grupos de la bandeja…</div>;
  }
  if (error) {
    return <div className="floating-artifact" role="alert" style={{ padding: '24px', color: '#D9383A' }}>{error} <button type="button" className="pill-filter" onClick={cargar}>Reintentar</button></div>;
  }

  return (
    <div data-testid="bandeja-grupos">
      <div className="floating-artifact" style={{ padding: '12px 16px', marginBottom: '12px', display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center' }}>
        <span data-testid="grupos-total"><strong>{data.total_casos}</strong> casos en <strong>{data.total_grupos}</strong> grupos</span>
        <span data-testid="grupos-en-bloque">Aprobables en bloque: <strong>{resumen.casosEnBloque}</strong> casos en <strong>{resumen.gruposEnBloque}</strong> grupos</span>
        <span style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)' }} title="fk_estado: vínculo del estudiante con la dimensión">
          {ESTADOS_VINCULO.map((e) => e.texto).join('  ·  ')}
        </span>
      </div>

      {data.grupos.length === 0 ? (
        <div className="floating-artifact" style={{ padding: '36px', textAlign: 'center' }} data-testid="grupos-vacio">No hay casos pendientes.</div>
      ) : (
        <div className="floating-artifact" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="dataops-table">
            <thead>
              <tr><th>Motivo</th><th>Valor normalizado</th><th style={{ textAlign: 'right' }}>Casos</th><th>Acción</th></tr>
            </thead>
            <tbody>
              {data.grupos.map((g) => (
                <tr key={g.clave} data-testid="fila-grupo">
                  <td>{textoMotivo(g.motivo)}</td>
                  <td style={{ maxWidth: '420px', overflowWrap: 'anywhere' }} title={g.ejemplo}>{describirGrupo(g)}</td>
                  <td style={{ textAlign: 'right', fontWeight: 700 }}>{g.n}</td>
                  <td>{botonAccion(g)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dialogo && (
        <div role="dialog" aria-modal="true" aria-label={textoAccion(dialogo.tipo)} data-testid="dialogo-grupo"
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="floating-artifact" style={{ padding: '22px', width: 'min(480px, 92vw)', background: 'var(--color-paper-white, #fff)' }}>
            <h4 className="serif-heading" style={{ margin: '0 0 8px 0' }}>{textoAccion(dialogo.tipo)}</h4>
            <p style={{ fontSize: '12.5px', color: 'var(--color-slate-gray)', margin: '0 0 12px 0' }}>
              {describirGrupo(dialogo.grupo)} — {dialogo.grupo.n} casos.
            </p>
            {dialogo.tipo === 'MAPEAR_ESTADO' ? (
              <>
                <label style={{ fontSize: '12px', fontWeight: 600 }} htmlFor="canonico-estado">Estado canónico (opcional)</label>
                <input id="canonico-estado" className="dataops-input" value={canonico} onChange={(e) => setCanonico(e.target.value)} placeholder="Ej.: Deserción" />
                <p style={{ fontSize: '11.5px', color: 'var(--color-slate-gray)' }}>
                  Con estado canónico, el valor fuera de catálogo se reescribe a ese estado. Sin él, una combinación no admitida se agrega al catálogo
                  de combinaciones y un estado desconocido se agrega al catálogo de estados.
                </p>
              </>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600 }} htmlFor="fecha-mes">Mes</label>
                  <input id="fecha-mes" type="number" min="1" max="12" className="dataops-input" value={mes} onChange={(e) => setMes(e.target.value)} />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600 }} htmlFor="fecha-gestion">Gestión</label>
                  <input id="fecha-gestion" type="number" min="2000" max="2100" className="dataops-input" value={gestion} onChange={(e) => setGestion(e.target.value)} />
                </div>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
              <button type="button" className="pill-filter" onClick={() => setDialogo(null)}>Cancelar</button>
              <button type="button" className="btn-pill-gold" data-testid="dialogo-confirmar" onClick={confirmarDialogo} disabled={enCurso !== null}>Aplicar a {dialogo.grupo.n} casos</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
