import { QueryClient } from '@tanstack/react-query';

/* React Query Client optimizado para navegación instantánea (compartido por App y por el logout) */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 300_000,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      retry: 1,
    },
  },
});

/** Prefijo de las queries del flujo DataOps; se invalidan sin refetch inmediato tras una mutación. */
export const DATAOPS_QUERY_KEY = ['dataops'];
