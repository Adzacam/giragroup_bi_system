import client from './client';

export const powerbiApi = {
  getEmbedConfig: async (reportId = null) => {
    const params = reportId ? { report_id: reportId } : {};
    const res = await client.get('/api/v1/powerbi/embed-token', { params });
    return res.data;
  }
};
