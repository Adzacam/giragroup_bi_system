import client from './client';

export const catalogApi = {
  // Docentes
  getDocentes: async (params = {}) => {
    try {
      const res = await client.get('/api/v1/docentes', { params });
      return res.data;
    } catch (err) {
      console.warn('Fallback docentes:', err.message);
      return { status: 'success', total: 0, data: [] };
    }
  },

  // Módulos
  getModulos: async (params = {}) => {
    try {
      const res = await client.get('/api/v1/modulos', { params });
      return res.data;
    } catch (err) {
      console.warn('Fallback modulos:', err.message);
      return { status: 'success', total: 0, data: [] };
    }
  },

  createModulo: async (data) => {
    const res = await client.post('/api/v1/modulos', data);
    return res.data;
  },

  deleteModulo: async (id) => {
    const res = await client.delete(`/api/v1/modulos/${id}`);
    return res.data;
  },

  // Catálogos Financieros
  getFinancialConcepts: async (params = {}) =>
    (await client.get('/api/v1/catalogs/financial/concepts', { params })).data,

  matchFinancialConcept: async (data) => {
    const res = await client.post('/api/v1/catalogs/financial/match', data);
    return res.data;
  },

  validateFinancialTransaction: async (data) => {
    const res = await client.post('/api/v1/catalogs/financial/validate-transaction', data);
    return res.data;
  },

  validateFinancialGoal: async (data) => {
    const res = await client.post('/api/v1/catalogs/financial/validate-goal', data);
    return res.data;
  },

  resolveStudentIdentity: async (data) => {
    const res = await client.post('/api/v1/catalogs/financial/resolve-student', data);
    return res.data;
  },

  checkCrossSourceStudent: async (id) => {
    const res = await client.get(`/api/v1/catalogs/financial/cross-source-check/${id}`);
    return res.data;
  },

  auditCrossSourceBatch: async (params = {}) => {
    const res = await client.get('/api/v1/catalogs/financial/cross-source-audit', { params });
    return res.data;
  },

  evaluateFinancialRisk: async (data) => {
    const res = await client.post('/api/v1/catalogs/financial/evaluate-risk', data);
    return res.data;
  },

  detectFinancialAnomalies: async (data) => {
    const res = await client.post('/api/v1/catalogs/financial/detect-anomalies', data);
    return res.data;
  },

  // Resumen del Catálogo Maestro Institucional Estático (18 Programas Activos, Cero PII)
  getInstitutionalSummary: async () => {
    try {
      const res = await client.get('/api/v1/catalogs/institutional-summary');
      return res.data;
    } catch (err) {
      console.warn('Fallback institutional summary:', err.message);
      return { status: 'error', total_programas_activos: 0, sin_pii: true, programas: [] };
    }
  }
};
