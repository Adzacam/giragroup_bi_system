import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { Outlet, useParams, useSearchParams } from 'react-router-dom';
import { useLoteContext } from '../hooks/useLoteContext';

/**
 * Estado de UI y borradores del flujo de lote (filtros, caso seleccionado, vista, inputs sin guardar).
 * NO guarda datos del servidor (eso es React Query). Persiste en sessionStorage por id_lote y
 * sobrevive al desmontaje de cada paso (/texto, /beto, /revision) y a F5.
 */
const LoteFlowContext = createContext(null);
const SESSION_PREFIX = 'lote_flow_';

const leerSesion = (idLote) => {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_PREFIX + idLote) || '{}') || {};
  } catch {
    return {};
  }
};

/** Borra los borradores del flujo (logout o lote consolidado). Sin id borra todos. */
export function clearLoteFlowSession(idLote = null) {
  try {
    if (idLote) {
      sessionStorage.removeItem(SESSION_PREFIX + idLote);
      return;
    }
    Object.keys(sessionStorage)
      .filter((k) => k.startsWith(SESSION_PREFIX))
      .forEach((k) => sessionStorage.removeItem(k));
  } catch { /* sin storage */ }
}

export function LoteFlowProvider({ children }) {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  let ultimoActivo = null;
  try { ultimoActivo = localStorage.getItem('last_active_batch_id'); } catch { /* sin storage */ }
  const idLote = id || searchParams.get('lote') || ultimoActivo || null;

  const { data: contexto } = useLoteContext(idLote);
  const readOnly = contexto?.estado_flujo === 'CONSOLIDADO';

  const borradores = useRef({ id: null, data: {} });
  const cargar = useCallback(() => {
    const clave = String(idLote);
    if (borradores.current.id !== clave) borradores.current = { id: clave, data: leerSesion(clave) };
    return borradores.current;
  }, [idLote]);

  const getDraft = useCallback((key) => cargar().data[key], [cargar]);
  const setDraft = useCallback((key, value) => {
    const b = cargar();
    b.data[key] = value;
    try { sessionStorage.setItem(SESSION_PREFIX + b.id, JSON.stringify(b.data)); } catch { /* cuota/sin storage */ }
  }, [cargar]);

  const value = useMemo(
    () => ({ idLote, contexto, readOnly, getDraft, setDraft }),
    [idLote, contexto, readOnly, getDraft, setDraft]
  );
  return <LoteFlowContext.Provider value={value}>{children}</LoteFlowContext.Provider>;
}

/** Ruta-layout: envuelve los pasos ②③④ para que compartan borradores y estado de solo lectura. */
export function LoteFlowRoute() {
  return (
    <LoteFlowProvider>
      <Outlet />
    </LoteFlowProvider>
  );
}

const SIN_PROVIDER = { idLote: null, contexto: null, readOnly: false, getDraft: () => undefined, setDraft: () => {} };
export const useLoteFlow = () => useContext(LoteFlowContext) || SIN_PROVIDER;

/** Igual que useState, pero el valor sobrevive a cambiar de paso y a recargar (por lote). */
export function useDraftState(key, initial) {
  const { getDraft, setDraft } = useLoteFlow();
  const [value, setValue] = useState(() => {
    const guardado = getDraft(key);
    return guardado === undefined ? initial : guardado;
  });
  useEffect(() => { setDraft(key, value); }, [key, value, setDraft]);
  return [value, setValue];
}
