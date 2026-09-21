// API Service for DataOps Module

const BASE_URL = '/api/v1/dataops';

// Mock delay to simulate network requests
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const dataopsApi = {
  /**
   * Obtiene la lista de fuentes documentales cargadas
   */
  getSources: async () => {
    // Return mock data since backend might not be ready
    await delay(500);
    return {
      status: 'success',
      data: [
        { id: '1', name: 'Acta_POS_2026_Modulo3.xlsx', type: 'Excel Acta', records: 342, date: '2026-09-20 10:15', status: 'completed' },
        { id: '2', name: 'Respuestas_Encuesta_M3.csv', type: 'Google Forms', records: 215, date: '2026-09-19 14:30', status: 'completed' },
        { id: '3', name: 'Moodle_Grades_Export.xml', type: 'Aula Moodle', records: 691, date: '2026-09-18 09:45', status: 'warning' }
      ]
    };
    /* Actual fetch implementation:
    const response = await fetch(`${BASE_URL}/sources`);
    if (!response.ok) throw new Error('Failed to fetch sources');
    return response.json();
    */
  },

  /**
   * Sube un nuevo archivo fuente
   * @param {FormData} formData 
   */
  uploadFile: async (formData) => {
    await delay(800);
    return { status: 'success', message: 'File uploaded and validated successfully' };
    /*
    const response = await fetch(`${BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error('Upload failed');
    return response.json();
    */
  },

  /**
   * Simula o ejecuta el procesamiento de batch
   */
  processBatch: async () => {
    await delay(1000);
    return { status: 'success', message: 'Batch processed successfully' };
    /*
    const response = await fetch(`${BASE_URL}/process-batch`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Processing failed');
    return response.json();
    */
  },

  /**
   * Obtiene la bandeja de revisión humana
   */
  getReviewTray: async () => {
    await delay(500);
    return { status: 'success', data: [] };
    /*
    const response = await fetch(`${BASE_URL}/review-tray`);
    if (!response.ok) throw new Error('Failed to fetch review tray');
    return response.json();
    */
  },

  /**
   * Desvincula fuentes conciliadas
   * @param {Object} data - IDs a desvincular
   */
  unlinkSources: async (data) => {
    await delay(600);
    return { status: 'success', message: 'Sources unlinked successfully' };
    /*
    const response = await fetch(`${BASE_URL}/unlink`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to unlink sources');
    return response.json();
    */
  }
};
