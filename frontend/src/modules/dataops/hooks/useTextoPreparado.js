import { useQuery } from '@tanstack/react-query';
import { dataopsApi } from '../../../api/dataopsApi';
import { DATAOPS_QUERY_KEY } from '../../../api/queryClient';

export default function useTextoPreparado(batchId, docId, page, enabled = true) {
  return useQuery({
    queryKey: [...DATAOPS_QUERY_KEY, 'texto-preparado', String(batchId), docId, page],
    queryFn: () => dataopsApi.getLoteRawVsText(batchId, docId, page),
    enabled: !!batchId && enabled,
  });
}
