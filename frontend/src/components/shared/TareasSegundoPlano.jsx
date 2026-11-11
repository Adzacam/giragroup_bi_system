import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, CheckCircle2, AlertTriangle, X } from 'lucide-react';
import { dataopsApi } from '../../api/dataopsApi';
import { sileoToast } from '../../services/sileoToast';
import { resumenConsolidacion } from '../../utils/resumenConsolidacion';
import { queryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';
import { fmtDuracion } from '../../modules/dataops/components/ProgresoTarea';

// Las páginas avisan aquí cuando lanzan una tarea larga, para empezar a seguirla al instante
const EVENTO = 'gira:tarea-iniciada';
export const avisarTareaIniciada = () => window.dispatchEvent(new Event(EVENTO));

const TITULO = {
  INGESTA: 'Ingesta de archivos',
  LECTURA_BETO: 'Análisis de BETO',
  CONSOLIDACION: 'Consolidación al DW',
};
const DESTINO = {
  INGESTA: (l) => `/dataops/lote/${l}/texto`,
  LECTURA_BETO: (l) => `/dataops/lote/${l}/beto`,
  CONSOLIDACION: (l) => `/dataops/lote/${l}/revision`,
};
const ROLES = ['ADMIN', 'AUDITOR_CALIDAD'];

function mensajeFinal(t) {
  const r = t.resultado || {};
  if (t.tipo === 'INGESTA') return `${r.exitosos ?? 0} archivo(s) procesados, ${r.total_registros ?? 0} registros. BETO empieza a analizarlos.`;
  if (t.tipo === 'LECTURA_BETO') return `${r.total_tuplas ?? t.total} registros analizados: el paso ③ ya muestra los resultados.`;
  const { total, detalle } = resumenConsolidacion(r);
  return `${total} registros consolidados. ${detalle}.`;
}

/**
 * Panel flotante con las tareas largas de DataOps (ingesta, análisis de BETO, consolidación). Sigue funcionando
 * al cambiar de página porque vive en el layout y lee el avance del servidor; avisa con un toast y, si la
 * pestaña está en segundo plano, con una notificación del navegador.
 */
export default function TareasSegundoPlano({ role }) {
  const navigate = useNavigate();
  const [tareas, setTareas] = useState([]);
  const [ocultas, setOcultas] = useState({});
  const conocidas = useRef({});  // id -> estado visto, para avisar una sola vez al terminar
  const habilitado = ROLES.includes(role);

  useEffect(() => {
    if (!habilitado) return undefined;
    let activo = true;
    let timer = null;

    const revisar = async () => {
      let lista = [];
      try { lista = await dataopsApi.getTareasActivas(); } catch { lista = []; }
      if (!activo) return;
      for (const t of lista) {
        const antes = conocidas.current[t.id];
        if (antes === 'EN_CURSO' && t.estado !== 'EN_CURSO') {
          const titulo = `${TITULO[t.tipo] || 'Tarea'} · Lote #${t.id_lote ?? '—'}`;
          if (t.estado === 'COMPLETADA') {
            sileoToast.success({ title: `${titulo} terminada`, description: mensajeFinal(t) });
            queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY }); // el lote pudo cambiar de estado
            if (document.hidden && 'Notification' in window && Notification.permission === 'granted') {
              new Notification(`${titulo} terminada`, { body: mensajeFinal(t) });
            }
          } else {
            sileoToast.error({ title: `${titulo} no terminó`, description: t.error || 'Revisa el registro del lote.' });
          }
        }
        conocidas.current[t.id] = t.estado;
      }
      setTareas(lista);
      // Cada 2 s mientras haya algo en curso; si no, cada 15 s
      timer = setTimeout(revisar, lista.some((t) => t.estado === 'EN_CURSO') ? 2000 : 15000);
    };

    const alIniciar = () => {
      if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission().catch(() => {});
      clearTimeout(timer);
      revisar();
    };
    window.addEventListener(EVENTO, alIniciar);
    revisar();
    return () => { activo = false; clearTimeout(timer); window.removeEventListener(EVENTO, alIniciar); };
  }, [habilitado]);

  const visibles = tareas.filter((t) => !ocultas[t.id]);
  if (!habilitado || visibles.length === 0) return null;

  return (
    <div aria-live="polite" style={{
      position: 'fixed', right: '16px', bottom: '84px', zIndex: 9000, width: 'min(340px, calc(100vw - 32px))',
      display: 'grid', gap: '8px',
    }}>
      {visibles.map((t) => {
        const enCurso = t.estado === 'EN_CURSO';
        const ok = t.estado === 'COMPLETADA';
        const pct = t.total ? t.porcentaje : null;
        return (
          <div key={t.id} style={{
            background: 'var(--color-paper-white, #fff)', border: '1px solid var(--color-border, #ececec)',
            borderRadius: '14px', boxShadow: '0 8px 24px rgba(12,30,51,.14)', padding: '12px 14px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 700, color: 'var(--color-ink-black)' }}>
              {enCurso ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite', color: '#B8801A' }} />
                : ok ? <CheckCircle2 size={14} color="#1B8754" /> : <AlertTriangle size={14} color="#D9383A" />}
              <span>{TITULO[t.tipo] || t.tipo} · Lote #{t.id_lote ?? '—'}</span>
              <button type="button" aria-label="Ocultar" onClick={() => setOcultas((o) => ({ ...o, [t.id]: true }))}
                style={{ marginLeft: 'auto', background: 'none', border: 0, cursor: 'pointer', color: 'var(--color-slate-gray)', padding: 2 }}>
                <X size={14} />
              </button>
            </div>
            {enCurso && (
              <div style={{ height: '6px', borderRadius: '999px', background: 'rgba(12,30,51,.08)', overflow: 'hidden', margin: '8px 0 6px' }}>
                <div style={{ height: '100%', background: '#D99B26', borderRadius: '999px', width: pct != null ? `${Math.max(2, pct)}%` : '35%', transition: 'width .6s ease' }} />
              </div>
            )}
            <div style={{ fontSize: '12px', color: 'var(--color-slate-gray)', display: 'flex', flexWrap: 'wrap', gap: '2px 10px', fontVariantNumeric: 'tabular-nums' }}>
              {enCurso ? (
                <>
                  {pct != null && <span>{pct.toFixed(0)} % · {(t.procesados || 0).toLocaleString('es-BO')} de {t.total.toLocaleString('es-BO')}</span>}
                  <span>{fmtDuracion(t.transcurrido_seg)}</span>
                  {t.restante_seg != null && <span>quedan ~{fmtDuracion(t.restante_seg)}</span>}
                </>
              ) : (
                <span>{ok ? mensajeFinal(t) : (t.error || 'No terminó.')}</span>
              )}
            </div>
            {!enCurso && ok && t.id_lote && DESTINO[t.tipo] && (
              <button type="button" className="btn-pill-secondary" style={{ marginTop: '8px', fontSize: '12px', padding: '5px 12px' }}
                onClick={() => { setOcultas((o) => ({ ...o, [t.id]: true })); navigate(DESTINO[t.tipo](t.id_lote)); }}>
                Ver resultados
              </button>
            )}
          </div>
        );
      })}
      <style>{'@keyframes spin{to{transform:rotate(360deg)}}'}</style>
    </div>
  );
}
