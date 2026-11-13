import { useEffect, useRef, useState } from 'react';
import { sileoToast } from '../../../services/sileoToast';
import { mensajeError } from '../../../utils/mensajeError';
import { queryClient, DATAOPS_QUERY_KEY } from '../../../api/queryClient';
import { crearColaRevision } from './colaRevision.mjs';
import { useNotifications } from '../../../context/NotificationContext';

/**
 * Operaciones pendientes de la vista, cada una con su cuenta de diez segundos y su Deshacer. Programar una no espera
 * a que termine la anterior. Al desmontarse se cancelan las esperas; nunca se adelanta un envío.
 */
export default function useRevisionAcciones() {
  const { refreshNotifications } = useNotifications();
  const [pending, setPending] = useState([]);
  const [sending, setSending] = useState(0);
  const cola = useRef(null);
  const mounted = useRef(true);
  const toasts = useRef(new Map());
  if (!cola.current) {
    cola.current = crearColaRevision(lista => {
      if (mounted.current) setPending(lista);
    }, async op => {
      sileoToast.dismiss(toasts.current.get(op.id));
      toasts.current.delete(op.id);
      if (mounted.current) setSending(n => n + 1);
      try {
        const result = await op.execute();
        if (result?.status === 'error') throw new Error(result.message || 'No se pudo guardar.');
        if (result?.status !== 'accepted') sileoToast.success({ title: 'Cambio guardado', description: result?.message || 'La bandeja se actualizará con los resultados guardados.' });
        await refreshNotifications();
        await queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
      } catch (error) {
        sileoToast.error({ title: 'No se pudo completar el cambio', description: mensajeError(error) });
        await queryClient.invalidateQueries({ queryKey: DATAOPS_QUERY_KEY });
      } finally {
        if (mounted.current) setSending(n => Math.max(0, n - 1));
      }
    });
  }
  const cancel = id => {
    if (!cola.current.cancel(id)) return;
    sileoToast.dismiss(toasts.current.get(id));
    toasts.current.delete(id);
  };
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      cola.current.cancelAll();
      toasts.current.forEach(toast => sileoToast.dismiss(toast));
      toasts.current.clear();
    };
  }, []);
  const schedule = (title, execute) => {
    const id = cola.current.schedule(title, execute);
    if (id === null) return false;
    toasts.current.set(id, sileoToast.action({ title: 'Cambio pendiente', description: `${title}. Se enviará en 10 segundos.`, duration: 10000, button: { title: 'Deshacer', onClick: () => cancel(id) } }));
    return true;
  };
  return { pending, sending: sending > 0, busy: sending > 0, cancel, schedule };
}
