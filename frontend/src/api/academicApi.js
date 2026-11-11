import client from './client';

/**
 * Obtiene alertas de riesgo multidimensional cruzado (académico + mora)
 * @param {number} limiteNota - Umbral máximo de nota (default: 70.0)
 * @param {number} minCuotas - Mínimo de cuotas impagas (default: 2)
 */
export const getRiesgoCruzado = async (limiteNota = 70.0, minCuotas = 2) => {
  const res = await client.get('/api/v1/riesgos/cruzado', {
    params: {
      limite_nota: limiteNota,
      min_cuotas: minCuotas,
    },
  });
  return res.data;
};

/**
 * Vista 3: Evalúa el Motor Determinístico de Reglas Fijas (IF/THEN) de Alertas Tempranas
 * sobre fact_rendimiento_academico y fact_situacion_financiera.
 * @param {Object} params - { periodo, programa, modulo, docente, regla_filtro, busqueda }
 */
export const getAlertasTempranas = async (params = {}) => {
  const cleanParams = {};
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '' && v !== 'TODOS') {
      cleanParams[k] = v;
    }
  });
  const res = await client.get('/api/v1/riesgos/alertas-tempranas', {
    params: cleanParams,
  });
  return res.data;
};

/**
 * Obtiene la Ficha Cruzada Académico-Financiera consolidada de un estudiante
 * @param {number} idEstudiante - ID en dim_estudiante
 */
export const getFichaCruzadaEstudiante = async (idEstudiante) => {
  const res = await client.get(`/api/v1/riesgos/ficha-estudiante/${idEstudiante}`);
  return res.data;
};

export const academicApi = {
  getRiesgoCruzado,
  getAlertasTempranas,
  getFichaCruzadaEstudiante,
};

export default academicApi;
