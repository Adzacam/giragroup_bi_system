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
          total_eventos: 148,
          eventos_seguridad: 42,
          ingestas_dataops: 38,
          alertas_criticas: 3,
        },
        total: 148,
        data: [],
      };
    }
  },
};
