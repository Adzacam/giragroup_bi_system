import { useCallback, useState } from 'react';
import { dataopsApi } from '../../../api/dataopsApi';
import { mensajeError } from '../../../utils/mensajeError';
import { sileoToast } from '../../../services/sileoToast';

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
        title: err.response?.status === 403 ? 'Permiso denegado (RBAC)' : 'No se pudo revelar el CI',
        description: mensajeError(err, 'Se requiere rol ADMIN o AUDITOR_CALIDAD para revelar datos personales.'),
      });
    }
  }, [revealedCis, onReveal]);

  return [revealedCis, toggleCi];
}
