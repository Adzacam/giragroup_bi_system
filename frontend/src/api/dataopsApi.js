import client from './client';
import { UMBRAL_INDICE_REGISTRO_DEC } from '../constants/dataopsConfig';

const BASE_URL = '/api/v1/dataops';

export const dataopsApi = {
  /**
   * Obtiene la lista de fuentes documentales y métricas KPI de ingesta
   */
  getSources: async () => {
    try {
      const res = await client.get(`${BASE_URL}/sources`);
      return res.data;
    } catch (err) {
      console.warn('Backend dataops/sources no disponible:', err.message);
      return {
        status: 'success',
        total: 0,
        kpis: {
          total_fuentes: 0,
          registros_detectados: 0,
          archivos_advertencias: 0,
          ultima_sincronizacion: 'Sin sincronización previa'
        },
        data: []
      };
    }
  },

  /**
   * Obtiene el detalle de una fuente específica
   */
  getSourceDetail: async (id) => {
    const res = await client.get(`${BASE_URL}/sources/${id}`);
    return res.data;
  },

  /**
   * Elimina una fuente documental individual por su ID
   */
  deleteSource: async (id) => {
    const res = await client.delete(`${BASE_URL}/sources/${id}`);
    return res.data;
  },

  /**
   * Elimina un conjunto de fuentes documentales por sus IDs
   */
  deleteBatch: async (ids) => {
    const res = await client.post(`${BASE_URL}/sources/delete-batch`, { ids });
    return res.data;
  },

  /**
   * Limpia todas las fuentes procesadas
   */
  clearCompleted: async () => {
    const res = await client.delete(`${BASE_URL}/sources/clear-completed`);
    return res.data;
  },

  /**
   * Sube un nuevo archivo fuente individual con tracking de progreso
   */
  uploadFile: async (file, sourceType = 'ACTA', tipoEscala = null, onProgress = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (sourceType) formData.append('source_type', sourceType);
    if (tipoEscala) formData.append('tipo_escala', tipoEscala);

    const res = await client.post(`${BASE_URL}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      }
    });
    return res.data;
  },

  /**
   * Sube un lote de 1 a 10 archivos simultáneos con tipos documentales y escala por archivo (#16, #17, #18)
   * @param {Array<{ file: File, sourceType: string, tipoEscala?: string|null }>} filesWithTypes
   * @param {Function} onProgress
   */
  uploadBatch: async (filesWithTypes, onProgress = null, batchMeta = {}) => {
    const formData = new FormData();
    filesWithTypes.forEach(({ file, sourceType, tipoEscala }) => {
      formData.append('files', file);
      formData.append('source_types', sourceType || '');
      formData.append('tipos_fuente', sourceType || '');
      formData.append('tipos_escala', tipoEscala || '');
    });
    if (batchMeta?.institucion) {
      formData.append('institucion', batchMeta.institucion);
    }
    if (batchMeta?.periodo) {
      formData.append('periodo', batchMeta.periodo);
    }

    const res = await client.post(`${BASE_URL}/upload-batch`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      }
    });
    return res.data;
  },

  /**
   * Ejecuta o re-procesa el pipeline sobre un lote
   */
  processBatch: async (docId = null) => {
    const res = docId
      ? await client.post(`${BASE_URL}/process/${docId}`)
      : await client.post(`${BASE_URL}/process-batch`);
    return res.data;
  },

  /**
   * Obtiene la bitácora técnica de logs para un documento
   */
  getLogs: async (docId) => {
    try {
      const res = await client.get(`${BASE_URL}/logs/${docId}`);
      return res.data;
    } catch (err) {
      console.warn('Backend dataops/logs no disponible:', err.message);
      return { status: 'success', data: [] };
    }
  },

  /**
   * Alias de getLogs para obtener la bitácora técnica y reporte Markdown de un documento
   */
  getDocumentLogs: async (docId) => {
    try {
      const res = await client.get(`${BASE_URL}/logs/${docId}`);
      return res.data;
    } catch (err) {
      console.warn('Backend dataops/logs no disponible:', err.message);
      return { status: 'success', data: [] };
    }
  },

  /**
   * Obtiene la matriz de normalización canónica
   */
  getNormalizationMatrix: async (docId) => {
    try {
      const res = await client.get(`${BASE_URL}/normalization-matrix/${docId}`);
      return res.data;
    } catch (err) {
      console.warn('Backend dataops/normalization-matrix no disponible:', err.message);
      return { status: 'success', data: [] };
    }
  },

  /**
   * Obtiene resumen agregado y KPIs server-side de un lote (#1, #2)
   */
  getLoteResumen: async (idLote = 'latest') => {
    const res = await client.get(`${BASE_URL}/lote/${idLote}/resumen`);
    return res.data;
  },

  /**
   * Obtiene la cabecera contextual y lista de archivos de un lote (#17)
   */
  getLoteContext: async (idLote) => {
    const res = await client.get(`${BASE_URL}/lote/${idLote}/context`);
    return res.data;
  },

  /**
   * Paso ②: Obtiene el mapeo fila origen vs oración que lee BETO (#17)
   */
  getLoteRawVsText: async (idLote, docId = null) => {
    const params = docId ? { doc_id: docId } : {};
    const res = await client.get(`${BASE_URL}/lote/${idLote}/raw-vs-text`, { params });
    return res.data;
  },

  /**
   * Paso ③: Obtiene la lectura estructurada de BETO (Capas A, B y C) con filtro opcional por archivo y paginación (#13, #17)
   */
  getLoteBetoReading: async (idLote, options = {}) => {
    const params = {};
    if (options.docId) params.doc_id = options.docId;
    if (options.page) params.page = options.page;
    if (options.pageSize) params.page_size = options.pageSize;
    if (options.search) params.search = options.search;
    const estadoVal = options.estado || options.filtroEstado;
    if (estadoVal && estadoVal !== 'ALL') params.estado = estadoVal;
    if (options.motivo && options.motivo !== 'ALL') params.motivo = options.motivo;
    const res = await client.get(`${BASE_URL}/lote/${idLote}/beto-reading`, { params });
    return res.data;
  },

  /**
   * Paso ④: Obtiene los casos derivados a la bandeja de revisión humana (#12, #17)
   */
  getReviewTray: async (idLote = null, options = {}) => {
    const params = {};
    if (idLote) {
      params.id_lote = idLote;
    }
    if (options.docId) {
      params.doc_id = options.docId;
    }
    if (options.motivo && options.motivo !== 'ALL') params.motivo = options.motivo;
    if (options.estado && options.estado !== 'ALL') params.estado = options.estado;
    if (options.page) params.page = options.page;
    if (options.pageSize) params.page_size = options.pageSize;
    const res = await client.get(`${BASE_URL}/review-tray`, { params });
    return res.data;
  },

  /**
   * Revela el CI completo de un registro bajo demanda con auditoría (#13)
   */
  revelarCi: async (registroId) => {
    const res = await client.get(`${BASE_URL}/registro/${registroId}/revelar-ci`);
    return res.data;
  },

  /**
   * Compara texto libre contra catálogo oficial con RapidFuzz real en backend (#7)
   */
  compareRapidFuzz: async (inputText, catalogType = 'MODULO', threshold = 85.0) => {
    const safeText = String(inputText || '').slice(0, 200);
    const res = await client.post(`${BASE_URL}/rapidfuzz-compare`, {
      input_text: safeText,
      string_a: safeText,
      catalog_type: catalogType,
      threshold
    });
    return res.data;
  },

  /**
   * Desvincula fuentes conciliadas
   */
  unlinkSources: async (data) => {
    const res = await client.post(`${BASE_URL}/unlink`, data);
    return res.data;
  },

  /**
   * Resuelve y confirma un registro individual de la bandeja de revisión humana
   */
  resolveReviewItem: async (itemId, payload = {}) => {
    const res = await client.post(`${BASE_URL}/review-tray/${itemId}/resolve`, payload);
    return res.data;
  },

  /**
   * Desvincula / rechaza un registro de la bandeja de revisión
   */
  unlinkReviewItem: async (itemId) => {
    const res = await client.post(`${BASE_URL}/review-tray/${itemId}/unlink`);
    return res.data;
  },

  /**
   * Resuelve en lote múltiples registros de revisión humana
   */
  batchResolveReviewItems: async (payload = {}) => {
    const res = await client.post(`${BASE_URL}/review-tray/batch-resolve`, payload);
    return res.data;
  },

  /**
   * Obtiene entidades no resueltas
   */
  getUnresolvedEntities: async () => {
    try {
      const res = await client.get(`${BASE_URL}/entities/unresolved`);
      return res.data;
    } catch (err) {
      return { status: 'success', data: [] };
    }
  },

  /**
   * Vincula una entidad detectada con el catálogo maestro
   */
  linkEntity: async (id, payload = {}) => {
    const res = await client.post(`${BASE_URL}/entities/${id}/link`, payload);
    return res.data;
  },

  /**
   * Obtiene métricas y rendimiento de telemetría IA (BETO + RapidFuzz)
   */
  getTelemetrySummary: async () => {
    const res = await client.get(`${BASE_URL}/telemetry/summary`);
    return res.data;
  },

  /**
   * Obtiene los registros de texto plano serializados del pipeline (Registros de Ingesta)
   */
  getPlainTextRecords: async (docIds = null) => {
    try {
      const params = docIds ? { doc_ids: docIds } : {};
      const res = await client.get(`${BASE_URL}/plain-text-records`, { params });
      return res.data;
    } catch (err) {
      console.warn('Backend plain-text-records no disponible:', err.message);
      return { status: 'success', data: [] };
    }
  },

  /**
   * Obtiene los catálogos maestros (Módulos, Docentes, Estudiantes) de PostgreSQL
   */
  getCatalogs: async () => {
    try {
      const res = await client.get(`${BASE_URL}/catalogs`);
      return res.data;
    } catch (err) {
      console.warn('Backend catalogs no disponible:', err.message);
      return { status: 'success', data: null };
    }
  },

  /**
   * Ejecuta inferencia BETO NER y matching sobre texto libre (#5, #6)
   */
  inferBeto: async (text, threshold = UMBRAL_INDICE_REGISTRO_DEC) => {
    try {
      const res = await client.post(`${BASE_URL}/infer-beto`, { text, threshold });
      return res.data;
    } catch (err) {
      console.warn('Backend infer-beto no disponible:', err.message);
      return null;
    }
  },

  /**
   * Confirma la inserción de registros al Data Warehouse enrutando por tipo_fuente (#8, #10)
   * o resuelve un caso individual si se provee resolved_item_id.
   */
  confirmDwInsert: async (payload = {}) => {
    if (payload && payload.resolved_item_id) {
      const res = await client.post(`${BASE_URL}/review-tray/${payload.resolved_item_id}/resolve`, {
        motivo: payload.motivo,
        accion: payload.accion,
        texto_editado: payload.nuevo_texto || null
      });
      return res.data;
    }
    const res = await client.post(`${BASE_URL}/confirm-dw-insert`, payload);
    return res.data;
  }
};
