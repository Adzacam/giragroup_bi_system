import { useCallback, useEffect, useState } from 'react';
import { academicApi } from '../api/academicApi';

/**
 * Revelación auditada de nombre o CI en Cartera y Alertas (DD3).
 * Los valores revelados viven solo en memoria local y caducan al desmontar la pantalla.
 */
export default function useRevealEstudiante() {
  const [revelados, setRevelados] = useState({});

  useEffect(() => {
    return () => setRevelados({});
  }, []);

  const toggle = useCallback(async (idEstudiante, campo = 'nombre') => {
    const key = `${idEstudiante}:${campo}`;
    if (revelados[key]) {
      setRevelados((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
      return;
    }
    const res = await academicApi.revelarEstudianteCampo(idEstudiante, campo);
    if (res?.valor != null) {
      setRevelados((prev) => ({ ...prev, [key]: res.valor }));
    }
  }, [revelados]);

  const getValor = useCallback((idEstudiante, campo = 'nombre') => revelados[`${idEstudiante}:${campo}`] || null, [revelados]);

  return { toggle, getValor };
}
