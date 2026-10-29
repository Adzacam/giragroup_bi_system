import client from './client';

export const reportesApi = {
  /**
   * Descarga un reporte oficial institucional (kpis, alertas, cierre) en formato xlsx o pdf.
   * @param {{ tipo: 'kpis'|'alertas'|'cierre', formato?: 'xlsx'|'pdf', gestion?: string, programa?: string }} params
   */
  exportarReporte: async ({ tipo = 'kpis', formato = 'xlsx', gestion = '', programa = '' }) => {
    const params = { tipo, formato };
    if (gestion && gestion !== 'TODOS' && gestion !== 'ALL') params.gestion = gestion;
    if (programa && programa !== 'TODOS' && programa !== 'ALL') params.programa = programa;

    const response = await client.get('/api/v1/reportes/export', {
      params,
      responseType: 'blob',
    });

    let filename = `reporte_${tipo}_${new Date().toISOString().slice(0, 10)}.${formato}`;
    const disposition = response.headers?.['content-disposition'];
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1];
    }

    const blob = new Blob([response.data], {
      type: formato === 'xlsx'
        ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        : 'application/pdf',
    });

    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    return { success: true, filename };
  },

  /**
   * Obtiene el historial de exportaciones auditadas registradas en log_pipeline_ingesta.
   * @param {number} limit
   */
  getHistorial: async (limit = 20) => {
    const response = await client.get('/api/v1/reportes/historial', {
      params: { limit },
    });
    return response.data;
  },
};

export default reportesApi;
