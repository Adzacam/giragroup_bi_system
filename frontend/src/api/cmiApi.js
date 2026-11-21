import client from './client';

// Cuadro de Mando Integral sobre la capa semántica bi
const cmiApi = {
  getScorecard: (gestion) =>
    client.get('/api/v1/cmi/scorecard', { params: gestion ? { gestion } : {} }).then((r) => r.data),
  getResumen: () => client.get('/api/v1/cmi/resumen').then((r) => r.data),
  getDetallePerspectiva: (codigo, gestion) =>
    client.get(`/api/v1/cmi/perspectivas/${codigo}/detalle`, { params: gestion ? { gestion } : {} }).then((r) => r.data),
  getHistorialKpi: (codigo) => client.get(`/api/v1/cmi/kpis/${codigo}/historial`).then((r) => r.data),
  getConfig: () => client.get('/api/v1/cmi/config').then((r) => r.data),
  updatePerspectiva: (codigo, body) =>
    client.put(`/api/v1/cmi/config/perspectivas/${codigo}`, body).then((r) => r.data),
  updateKpi: (codigo, body) =>
    client.put(`/api/v1/cmi/config/kpis/${codigo}`, body).then((r) => r.data),
  createKpiPersonalizado: (body) =>
    client.post('/api/v1/cmi/config/kpis-personalizados', body).then((r) => r.data),
  updateKpiPersonalizado: (codigo, body) =>
    client.put(`/api/v1/cmi/config/kpis-personalizados/${codigo}`, body).then((r) => r.data),
  previewGrafico: (body) =>
    client.post('/api/v1/cmi/config/graficos/preview', body).then((r) => r.data),
  createGrafico: (body) =>
    client.post('/api/v1/cmi/config/graficos', body).then((r) => r.data),
  updateGrafico: (id, body) =>
    client.put(`/api/v1/cmi/config/graficos/${id}`, body).then((r) => r.data),
};

export default cmiApi;
