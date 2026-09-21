export const getForecastAlumnos = async (tipo, horizonte) => {
  const response = await fetch(`/api/v1/forecast/alumnos?tipo=${encodeURIComponent(tipo)}&horizonte=${encodeURIComponent(horizonte)}`);
  return response.json();
};

export const getRiesgoCruzado = async (limiteNota, minCuotas) => {
  const response = await fetch(`/api/v1/riesgos/cruzado?limite_nota=${encodeURIComponent(limiteNota)}&min_cuotas=${encodeURIComponent(minCuotas)}`);
  return response.json();
};
