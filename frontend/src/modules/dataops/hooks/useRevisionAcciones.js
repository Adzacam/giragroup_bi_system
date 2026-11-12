import { useEffect, useRef, useState } from 'react';
import { sileoToast } from '../../../services/sileoToast';
import { mensajeError } from '../../../utils/mensajeError';
import { queryClient, DATAOPS_QUERY_KEY } from '../../../api/queryClient';
import { crearEsperaRevision } from './esperaRevision.mjs';
import { useNotifications } from '../../../context/NotificationContext';

/** Una operación pendiente por vista. Al desmontarse se cancela la espera, nunca se adelanta el envío. */
export default function useRevisionAcciones() {
  const { refreshNotifications } = useNotifications();
  const [pending, setPending] = useState(null);
  const [sending, setSending] = useState(false);
  const current = useRef(null);
  const mounted = useRef(true);
  const cancel = () => {
    const op = current.current;
    if (!op || op.started) return;
    op.wait.cancel();
    sileoToast.dismiss(op.toast);
    current.current = null;
    if (mounted.current) setPending(null);
  };
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; cancel(); };
  }, []);
  const schedule = (title, execute) => {
    if (current.current) return false;
    const op = { title, seconds: 10, started: false };
    current.current = op;
    setPending({ title, seconds: 10 });
    op.toast = sileoToast.action({ title: 'Cambio pendiente', description: `${title}. Se enviará en 10 segundos.`, duration: 10000, button: { title: 'Deshacer', onClick: cancel } });
    op.wait = crearEsperaRevision(seconds => {
      if (mounted.current) setPending({ title, seconds: Math.max(0, seconds) });
    }, async () => {
      op.started = true;
      sileoToast.dismiss(op.toast);
      setPending(null);
      setSending(true);
      try {
        const result = await execute();
        if (result?.status === 'error') throw new Error(result.message || 'No se pudo guardar.');
        if (result?.status !== 'accepted') sileoToast.success({ title: 'Cambio guardado', description: result?.message || 'La bandeja se actualizará con los resultados guardados.' });
        await refreshNotifications();
        await queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
      } catch (error) {
        sileoToast.error({ title: 'No se pudo completar el cambio', description: mensajeError(error) });
        await queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
      } finally {
        current.current = null;
        if (mounted.current) setSending(false);
      }
    });
    op.wait.start();
    return true;
  };
  return { pending, sending, busy: !!pending || sending, cancel, schedule };
}
