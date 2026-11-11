import { useEffect, useMemo, useState } from 'react';

export const FILAS_POR_PAGINA = 5;

export default function usePaginacion(items, filasPorPagina = FILAS_POR_PAGINA) {
  const [pagina, setPagina] = useState(1);
  const lista = items || [];
  const totalPaginas = Math.max(1, Math.ceil(lista.length / filasPorPagina));

  useEffect(() => {
    if (pagina > totalPaginas) setPagina(totalPaginas);
  }, [pagina, totalPaginas]);

  const visibles = useMemo(
    () => lista.slice((pagina - 1) * filasPorPagina, pagina * filasPorPagina),
    [lista, pagina, filasPorPagina],
  );

  return { visibles, pagina, setPagina, totalPaginas, total: lista.length, filasPorPagina };
}
