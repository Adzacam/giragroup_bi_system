import client from './client';

// Cuadro de Mando Integral sobre la capa semántica bi (la misma que consume Power BI)
const cmiApi = {
  getScorecard: (gestion) =>
    client.get('/api/v1/cmi/scorecard', { params: gestion ? { gestion } : {} }).then((r) => r.data),
  getHistorialKpi: (codigo) => client.get(`/api/v1/cmi/kpis/${codigo}/historial`).then((r) => r.data),
  getConfig: () => client.get('/api/v1/cmi/config').then((r) => r.data),
  updatePerspectiva: (codigo, body) =>
    client.put(`/api/v1/cmi/config/perspectivas/${codigo}`, body).then((r) => r.data),
  updateKpi: (codigo, body) =>
    client.put(`/api/v1/cmi/config/kpis/${codigo}`, body).then((r) => r.data),
};

export default cmiApi;
