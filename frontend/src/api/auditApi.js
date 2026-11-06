import client from './client';

const BASE_URL = '/api/v1/audit';

export const auditApi = {
  /**
   * Obtiene la bitácora consolidada de auditoría del sistema con filtros y KPIs
   * @param {Object} params - { modulo, severidad, busqueda, limit, offset }
   */
  getLogs: async (params = {}) => {
    try {
      const res = await client.get(`${BASE_URL}/logs`, { params });
      return res.data;
    } catch (err) {
      console.warn('Backend audit/logs no disponible, usando fallback local:', err.message);
      return {
        status: 'success',
        kpis: {
          total_eventos: 0,
          eventos_seguridad: 0,
          ingestas_dataops: 0,
          alertas_criticas: 0,
        },
        total: 0,
        data: [],
      };
    }
  },

  /**
   * Dispara la ejecución del pipeline integral bajo demanda (Ingesta, NLP, Calidad y Carga DW)
   * @param {Object} options - { file?: File, docId?: number|string }
   */
  triggerManualPipeline: async ({ file, docId } = {}) => {
    const formData = new FormData();
    if (file) {
      formData.append('file', file);
    }
    if (docId !== undefined && docId !== null && docId !== '') {
      formData.append('doc_id', docId);
    }

    try {
      const res = await client.post('/api/v1/pipeline/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return res.data;
    } catch (err) {
      // Fallback a /pipeline/process en caso de que el proxy o gateway apunte al alias raíz
      if (err.response?.status === 404 || err.response?.status === 403) {
        try {
          const resFallback = await client.post('/pipeline/process', formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          });
          return resFallback.data;
        } catch (fallbackErr) {
          throw fallbackErr;
        }
      }
      throw err;
    }
  },
};
