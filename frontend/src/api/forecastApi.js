import client from './client';

/**
 * Servicio API para los modelos predictivos y analítica macro institucional (Vista 4).
 * Todos los endpoints consumen cálculos reales de time_series_extractor y Holt-Winters/OLS.
 */

export const getForecastAlumnos = async (tipo = 'GLOBAL', horizonte = 6) => {
  const res = await client.get(`/api/v1/forecast/alumnos?tipo=${encodeURIComponent(tipo)}&horizonte=${horizonte}`);
  return res.data;
};

export const getForecastMetas = async (granularidad = 'MENSUAL', horizonte = 6) => {
  const res = await client.get(`/api/v1/forecast/metas?granularidad=${encodeURIComponent(granularidad)}&horizonte=${horizonte}`);
  return res.data;
};

export const getAnaliticaPredictivaMacro = async (horizonte = 6) => {
  const res = await client.get(`/api/v1/forecast/analitica-macro?horizonte=${horizonte}`);
  return res.data;
};

export const getViabilidadProgramas = async (tipo = null) => {
  const url = tipo ? `/api/v1/forecast/viabilidad-programas?tipo=${encodeURIComponent(tipo)}` : '/api/v1/forecast/viabilidad-programas';
  const res = await client.get(url);
  return res.data;
};

export const forecastApi = {
  getForecastAlumnos,
  getForecastMetas,
  getAnaliticaPredictivaMacro,
  getViabilidadProgramas,
};

export default forecastApi;
