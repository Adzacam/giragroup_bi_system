import client from './client';

const kpiMemoryCache = new Map();
const KPI_CACHE_TTL = 45_000; // 45 segundos

/**
 * Obtiene el consolidado general de KPIs para el Cuadro de Mando Integral (CMI)
 */
export const getKpisGeneral = async (forceRefresh = false) => {
  const key = 'kpis_general';
  if (!forceRefresh && kpiMemoryCache.has(key)) {
    const entry = kpiMemoryCache.get(key);
    if (Date.now() < entry.expiry) return entry.data;
  }
  const res = await client.get('/api/v1/kpis');
  kpiMemoryCache.set(key, { data: res.data, expiry: Date.now() + KPI_CACHE_TTL });
  return res.data;
};

/**
 * Obtiene el feed unificado de alertas institucionales basadas en reglas de negocio
 */
export const getAlertas = async (forceRefresh = false) => {
  const key = 'kpis_alertas_feed';
  if (!forceRefresh && kpiMemoryCache.has(key)) {
    const entry = kpiMemoryCache.get(key);
    if (Date.now() < entry.expiry) return entry.data;
  }
  const res = await client.get('/api/v1/alertas');
  kpiMemoryCache.set(key, { data: res.data, expiry: Date.now() + KPI_CACHE_TTL });
  return res.data;
};

/**
 * Obtiene KPIs específicos de la perspectiva académica
 */
export const getKpisAcademico = async () => {
  const res = await client.get('/api/v1/kpis/academico');
  return res.data;
};

/**
 * Obtiene KPIs específicos de la perspectiva financiera y recaudación
 */
export const getKpisFinanciero = async () => {
  const res = await client.get('/api/v1/kpis/financiero');
  return res.data;
};

/**
 * Obtiene KPIs específicos de calidad del pipeline de ingesta y NLP DataOps
 */
export const getKpisPipeline = async () => {
  const res = await client.get('/api/v1/kpis/pipeline');
  return res.data;
};

/**
 * Obtiene las 4 Perspectivas Estratégicas Institucionales del CMI con drilldowns (con caché en memoria)
 */
export const getCmiCompleto = async (forceRefresh = false) => {
  const key = 'cmi_completo';
  if (!forceRefresh && kpiMemoryCache.has(key)) {
    const entry = kpiMemoryCache.get(key);
    if (Date.now() < entry.expiry) return entry.data;
  }
  const res = await client.get('/api/v1/kpis/cmi-completo');
  kpiMemoryCache.set(key, { data: res.data, expiry: Date.now() + KPI_CACHE_TTL });
  return res.data;
};

export const kpiApi = {
  getKpisGeneral,
  getAlertas,
  getKpisAcademico,
  getKpisFinanciero,
  getKpisPipeline,
  getCmiCompleto,
};

export default kpiApi;

