import { useQuery } from '@tanstack/react-query';
import { dataopsApi } from '../../../api/dataopsApi';
import { DATAOPS_QUERY_KEY } from '../../../api/queryClient';

export default function useLecturaBeto(batchId, filters, enabled) {
  return useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'beto-reading', String(batchId), filters],
    queryFn: () => dataopsApi.getLoteBetoReading(batchId, {
      docId: filters.docId, area: filters.area, filtroGlobal: filters.condition,
      tipoEntidad: filters.entity, search: filters.search, page: filters.page,
    }),
    enabled: !!batchId && enabled,
    placeholderData: previous => previous,
    refetchInterval: query => query.state.data?.status === 'processing' ? 2000 : false,
  });
}
