import { useQuery } from '@tanstack/react-query';
import { dataopsApi } from '../../../api/dataopsApi';

export const loteContextKey = (idLote) => ['dataops', 'lote-context', String(idLote)];

const ESCALA_LABEL = {
  DECIMAL_10: 'Sobre 10',
  VIGESIMAL_20: 'Sobre 20',
  CENTESIMAL_100: 'Sobre 100',
};

/** Carga el contexto del lote (con fallback a 'latest' en 404 y a /sources si el contexto no viene). */
export async function fetchLoteContext(batchId) {
  let res;
  try {
    res = await dataopsApi.getLoteContext(batchId);
  } catch (errApi) {
    if (errApi.response?.status === 404 && batchId !== 'latest') {
      res = await dataopsApi.getLoteContext('latest');
    } else {
      throw errApi;
    }
  }
  if (res && res.status === 'success') {
    try { localStorage.setItem('last_active_batch_id', String(res.id_lote || batchId)); } catch { /* sin storage */ }
    return res;
  }
  const sources = await dataopsApi.getSources();
  const found = sources?.data?.find(
    (s) => s.id === Number(batchId) || s.id_documento === Number(batchId) || s.id_lote === Number(batchId)
  );
  if (!found) return null;
  const idDoc = found.id_documento || found.id || Number(batchId);
  const nombre = found.nombre_archivo || `Lote_${batchId}.xlsx`;
  const registros = found.total_registros || found.registros_detectados || 0;
  return {
    id_lote: found.id_lote || batchId,
    id_documento: idDoc,
    nombre_archivo: nombre,
    institucion: found.institucion || '—',
    tipo_fuente: found.tipo_fuente || found.tipo_documento || 'ACTA',
    tipo_escala: found.tipo_escala || null,
    escala_label: ESCALA_LABEL[found.tipo_escala] || 'No aplica',
    periodo: found.periodo || 'Por detectar',
    total_archivos: 1,
    total_registros: registros,
    pendientes_revision: found.inconsistencias || 0,
    estado_flujo: 'EN_CURSO',
    archivos: [{
      id_documento: idDoc,
      nombre_archivo: nombre,
      tipo_fuente: found.tipo_fuente || 'ACTA',
      tipo_escala: found.tipo_escala || null,
      total_registros: registros,
      pendientes_revision: found.inconsistencias || 0,
    }],
  };
}

/** Contexto del lote vía React Query: comparte caché entre los pasos y se invalida al mutar. */
export function useLoteContext(idLote) {
  return useQuery({
    queryKey: loteContextKey(idLote),
    queryFn: () => fetchLoteContext(idLote),
    enabled: !!idLote,
    refetchOnMount: true, // respeta staleTime (60 s) pero refetchea si una mutación lo invalidó
  });
}
