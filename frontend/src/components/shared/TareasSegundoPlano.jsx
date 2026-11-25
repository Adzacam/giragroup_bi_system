import React, { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { dataopsApi } from '../../api/dataopsApi';
import { sileoToast } from '../../services/sileoToast';
import { useNotifications } from '../../context/NotificationContext';
import { queryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';
import { fmtDuracion } from '../../modules/dataops/components/ProgresoTarea';
import { toDataopsPath } from '../../v2/utils/v2Routes';
import { useAuth } from '../../context/AuthContext';

const EVENTO = 'gira:tarea-iniciada';
const PROGRESO = 'gira:tarea-progreso';
export const avisarTareaIniciada = () => window.dispatchEvent(new Event(EVENTO));
const TITULO = { INGESTA: 'Carga de archivos', LECTURA_BETO: 'Lectura de BETO', CONSOLIDACION: 'Consolidación de registros' };
const DESTINO = { INGESTA: 'texto', LECTURA_BETO: 'beto', CONSOLIDACION: 'revision' };

function ProgresoAviso({ inicial }) {
  const [tarea, setTarea] = useState(inicial);
  useEffect(() => {
    const actualizar = (e) => { if (e.detail.id === inicial.id) setTarea(e.detail); };
    window.addEventListener(PROGRESO, actualizar);
    return () => window.removeEventListener(PROGRESO, actualizar);
  }, [inicial.id]);
  const pct = tarea.total > 0 ? tarea.porcentaje : null;
  return <div role="status" aria-live="polite">
    <p>{pct == null ? 'Procesando…' : `${pct.toFixed(0)} % · ${tarea.procesados} de ${tarea.total} ${tarea.tipo === 'INGESTA' ? 'archivos' : 'registros'}`}</p>
    <progress aria-label="Avance del proceso" max="100" {...(pct == null ? {} : { value: pct })} style={{ width: '100%', accentColor: 'var(--color-gira-gold)' }} />
    <p>{fmtDuracion(tarea.transcurrido_seg)}{tarea.restante_seg != null ? ` · Restante estimado: ${fmtDuracion(tarea.restante_seg)}` : ''}</p>
    <p>Puedes seguir usando el sistema.</p>
  </div>;
}

/** Un aviso persistente de Sileo por tarea; la campana lee los avisos guardados por el servidor. */
export default function TareasSegundoPlano({ role }) {
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;
  const location = useLocation();
  const pathnameRef = useRef(location.pathname);
  pathnameRef.current = location.pathname;
  const { refreshNotifications } = useNotifications();
  const refreshRef = useRef(refreshNotifications);
  refreshRef.current = refreshNotifications;
  const conocidas = useRef({});
  const avisos = useRef({});
  const { isAuthenticated, token } = useAuth();
  const enLogin = location.pathname === '/login' || location.pathname === '/v2/login';
  const habilitado = Boolean(
    isAuthenticated &&
    token &&
    !enLogin &&
    ['ADMIN', 'AUDITOR_CALIDAD'].includes(role)
  );
  useEffect(() => {
    if (!habilitado) return undefined;
    let activo = true;
    let timer;
    let consultando = false;
    const revisar = async () => {
      if (consultando || !activo) return;
      consultando = true;
      clearTimeout(timer);
      let lista = [];
      try {
        lista = await dataopsApi.getTareasActivas();
        if (!activo) return;
        let termino = false;
        for (const t of lista) {
          const antes = conocidas.current[t.id];
          const titulo = `${TITULO[t.tipo] || 'Procesamiento'} · Lote #${t.id_lote ?? 'Sin dato'}`;
          if (t.estado === 'EN_CURSO') {
            if (!avisos.current[t.id]) {
              avisos.current[t.id] = sileoToast.upsertTask(t.id, {
                type: 'show',
                title: titulo,
                etapa: t.etapa || TITULO[t.tipo] || 'Procesando',
                porcentaje: t.porcentaje,
                description: <ProgresoAviso inicial={t} />,
                icon: <Loader2 size={16} className="btn-spinner" />,
                duration: 0,
                autopilot: false,
              });
            }
            window.dispatchEvent(new CustomEvent(PROGRESO, { detail: t }));
          } else if (antes !== t.estado) {
            if (avisos.current[t.id]) sileoToast.dismiss(avisos.current[t.id]);
            delete avisos.current[t.id];
            termino = true;
            if (antes === 'EN_CURSO') {
              const ok = t.estado === 'COMPLETADA';
              sileoToast.upsertTask(t.id, {
                type: ok ? 'success' : 'error',
                title: `${titulo}: ${ok ? 'terminado' : 'interrumpido'}`,
                porcentaje: ok ? 100 : t.porcentaje,
                description: ok ? 'Los resultados están disponibles en el lote y en la campana.' : 'Revisa el historial para reintentarlo.',
                button: {
                  title: 'Ver lote',
                  onClick: () => navigateRef.current(
                    toDataopsPath(
                      ok && t.id_lote ? `/lote/${t.id_lote}/${DESTINO[t.tipo] || 'revision'}` : '/ingesta',
                      pathnameRef.current
                    )
                  ),
                },
              });
            }
          }
          conocidas.current[t.id] = t.estado;
        }
        for (const [id, aviso] of Object.entries(avisos.current)) {
          if (!lista.some(t => String(t.id) === id)) { sileoToast.dismiss(aviso); delete avisos.current[id]; }
        }
        if (termino) {
          queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
          refreshRef.current();
        }
      } catch { /* Se conserva el aviso y se reintenta la conexión. */ }
      finally {
        consultando = false;
        if (activo) timer = setTimeout(revisar, lista.some(t => t.estado === 'EN_CURSO') ? 2000 : 15000);
      }
    };
    window.addEventListener(EVENTO, revisar);
    revisar();
    return () => {
      activo = false;
      clearTimeout(timer);
      window.removeEventListener(EVENTO, revisar);
      Object.values(avisos.current).forEach(sileoToast.dismiss);
      avisos.current = {};
      conocidas.current = {};
    };
  }, [habilitado, role]);
  return null;
}
