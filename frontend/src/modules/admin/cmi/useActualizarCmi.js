import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { sileoToast } from '../../../services/sileoToast';

function extraerMensajeError(err) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg || '').filter(Boolean).join(' ');
  return err?.message || 'No se pudo actualizar el Cuadro de Mando.';
}

function formatearHace(timestamp) {
  if (!timestamp) return null;
  const mins = Math.floor((Date.now() - timestamp) / 60_000);
  if (mins < 1) return 'Actualizado ahora';
  return `Actualizado hace ${mins} min`;
}

export default function useActualizarCmi({ activeMode, refetchMacro }) {
  const queryClient = useQueryClient();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null);
  const [nowTick, setNowTick] = useState(0);
  const inFlightRef = useRef(false);

  useEffect(() => {
    if (!lastUpdatedAt) return undefined;
    const id = setInterval(() => setNowTick((t) => t + 1), 30_000);
    return () => clearInterval(id);
  }, [lastUpdatedAt]);

  const actualizar = useCallback(async () => {
    if (inFlightRef.current) return null;
    inFlightRef.current = true;
    setIsRefreshing(true);

    const run = async () => {
      await queryClient.invalidateQueries({ queryKey: ['cmi'] });
      if (activeMode === 'B') {
        await queryClient.invalidateQueries({ queryKey: ['analiticaPredictivaMacro'] });
        if (refetchMacro) await refetchMacro();
      }
      const ahora = new Date();
      const hhmm = ahora.toLocaleTimeString('es-BO', { hour: '2-digit', minute: '2-digit', hour12: false });
      setLastUpdatedAt(Date.now());
      return hhmm;
    };

    try {
      return await sileoToast.promise(run(), {
        loading: { title: 'Actualizando CMI…' },
        success: (hhmm) => ({
          title: `CMI actualizado · 23 indicadores · ${hhmm}`,
        }),
        error: (err) => ({
          title: 'Error al actualizar CMI',
          description: extraerMensajeError(err),
        }),
      });
    } finally {
      inFlightRef.current = false;
      setIsRefreshing(false);
    }
  }, [queryClient, activeMode, refetchMacro]);

  const lastUpdatedLabel = nowTick >= 0 ? formatearHace(lastUpdatedAt) : null;

  return { isRefreshing, lastUpdatedLabel, actualizar };
}
