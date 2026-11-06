import { useQuery } from '@tanstack/react-query';
import { catalogApi } from '../api/catalogApi';

/**
 * Número de programas registrados en giragroup_catalog_db.
 * Devuelve null mientras carga o si el catálogo no responde (la UI muestra "—").
 */
export function useCatalogProgramCount() {
  const { data } = useQuery({
    queryKey: ['catalog', 'institutional-summary'],
    queryFn: () => catalogApi.getInstitutionalSummary(),
    staleTime: 5 * 60_000,
  });
  return data?.status === 'success' ? data.total_programas_activos ?? null : null;
}
