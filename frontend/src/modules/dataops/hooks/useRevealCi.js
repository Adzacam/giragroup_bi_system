import { useCallback, useState } from 'react';
import { dataopsApi } from '../../../api/dataopsApi';
import { mensajeError } from '../../../utils/mensajeError';
import { sileoToast } from '../../../services/sileoToast';

const ETIQUETAS = {
  ci: 'cédula',
  nombre: 'nombre',
  correo: 'correo',
};

/**
 * Revela u oculta un campo sensible (ci, nombre, correo) de un registro bajo demanda
 * (auditado en backend; solo ADMIN/AUDITOR_CALIDAD). Vive solo en memoria del componente.
 */
export function useRevealCampo(onReveal) {
  const [revealed, setRevealed] = useState({});

  const toggleCampo = useCallback(async (id, campo = 'ci') => {
    const key = `${id}:${campo}`;
    if (revealed[key]) {
      setRevealed((prev) => {
        const next = { ...prev };
        delete next[key];
        if (campo === 'nombre') {
          delete next[`${id}:sugerencia`];
          delete next[`${id}:raw`];
        }
        return next;
      });
      return;
    }
    try {
      const res = await dataopsApi.revelarCampo(id, campo);
      const val = res?.valor || res?.ci_real || res?.ci;
      if (val) {
        setRevealed((prev) => {
          const next = { ...prev, [key]: val };
          if (campo === 'nombre') {
            if (res?.sugerencia) next[`${id}:sugerencia`] = res.sugerencia;
            if (res?.raw) next[`${id}:raw`] = res.raw;
          }
          return next;
        });
        onReveal?.(val, campo);
      }
    } catch (err) {
      const label = ETIQUETAS[campo] || campo;
      sileoToast.error({
        title: err.response?.status === 403 ? `No tienes permiso para revelar el ${label}` : `No se pudo revelar el ${label}`,
        description: mensajeError(err, 'Esta consulta está disponible para Administrador y Auditor de calidad.'),
      });
    }
  }, [revealed, onReveal]);

  const getValor = useCallback((id, campo = 'ci') => revealed[`${id}:${campo}`] || null, [revealed]);

  return { revealed, toggleCampo, getValor };
}

/**
 * Revela u oculta el CI completo de un registro bajo demanda (auditado en backend; solo ADMIN/AUDITOR_CALIDAD).
 * El CI revelado vive solo en memoria del componente: nunca se persiste en borradores ni sessionStorage.
 * `onReveal(ci)` se llama tras revelar con éxito (p. ej. para rellenar el formulario).
 */
export function useRevealCi(onReveal) {
  const [revealedCis, setRevealedCis] = useState({});

  const toggleCi = useCallback(async (id) => {
    if (revealedCis[id]) {
      setRevealedCis(({ [id]: _oculto, ...resto }) => resto);
      return;
    }
    try {
      const res = await dataopsApi.revelarCi(id);
      const ci = res?.ci_real || res?.ci;
      if (ci) {
        setRevealedCis((prev) => ({ ...prev, [id]: ci }));
        onReveal?.(ci);
      }
    } catch (err) {
      sileoToast.error({
        title: err.response?.status === 403 ? 'No tienes permiso para revelar la cédula' : 'No se pudo revelar la cédula',
        description: mensajeError(err, 'Esta consulta está disponible para Administrador y Auditor de calidad.'),
      });
    }
  }, [revealedCis, onReveal]);

  return [revealedCis, toggleCi];
}
