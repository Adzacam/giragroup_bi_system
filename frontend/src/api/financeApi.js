export const getForecastMetas = async (granularidad, horizonte) => {
  const response = await fetch(`/api/v1/forecast/metas?granularidad=${encodeURIComponent(granularidad)}&horizonte=${encodeURIComponent(horizonte)}`);
  return response.json();
};
