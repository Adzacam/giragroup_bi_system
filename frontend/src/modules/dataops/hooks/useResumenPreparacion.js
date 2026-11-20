// Cálculo común de las tres cifras de resumen del texto preparado
// (usado por Carga de archivos y por la pestaña "Texto preparado").
export function resumenPreparacion(kpis) {
  if (!kpis) return null;
  return [
    ['Registros preparados', kpis.filas_leidas],
    ['Campos por fila, máximo', kpis.columnas_detectadas],
    ['Filas con observaciones', kpis.total_alertas],
  ];
}

export default function useResumenPreparacion(data) {
  return resumenPreparacion(data?.kpis);
}
