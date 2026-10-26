import client from './client';

/**
 * Obtiene el consolidado general de KPIs para el Cuadro de Mando Integral (CMI)
 */
export const getKpisGeneral = async () => {
  const res = await client.get('/api/v1/kpis');
  return res.data;
};

/**
 * Obtiene el feed unificado de alertas institucionales basadas en reglas de negocio
 */
export const getAlertas = async () => {
  const res = await client.get('/api/v1/alertas');
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
 * Obtiene las 4 Perspectivas Estratégicas Institucionales del CMI con drilldowns
 */
export const getCmiCompleto = async () => {
  const res = await client.get('/api/v1/kpis/cmi-completo');
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

