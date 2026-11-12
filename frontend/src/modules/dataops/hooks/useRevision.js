import { useQuery } from '@tanstack/react-query';
import { DATAOPS_QUERY_KEY } from '../../../api/queryClient';
import { dataopsApi } from '../../../api/dataopsApi';

export default function useRevision(batchId, filters, enabled) {
  return useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'revision-v4', String(batchId), filters],
    queryFn: () => filters.vista === 'GRUPOS'
      ? dataopsApi.getGruposBandeja({ idLote: batchId, docId: filters.docId, page: filters.page, search: filters.search })
      : dataopsApi.getReviewTray(batchId, filters),
    enabled: !!batchId && enabled,
    placeholderData: previous => previous,
  });
}
