import { queryClient as defaultQueryClient, DATAOPS_QUERY_KEY } from '../../api/queryClient';
import cmiApi from '../../api/cmiApi';
import { getKpisGeneral, getKpisAcademico, getKpisFinanciero, getKpisPipeline } from '../../api/kpiApi';
import { getAlertasTempranas } from '../../api/academicApi';
import { getForecastAlumnos, getForecastMetas, getAnaliticaPredictivaMacro, getViabilidadProgramas } from '../../api/forecastApi';
import { dataopsApi } from '../../api/dataopsApi';
import { catalogApi } from '../../api/catalogApi';
import { auditApi } from '../../api/auditApi';
import { getUsers } from '../../api/usersApi';
import { reportesApi } from '../../api/reportesApi';
import { notificationsApi } from '../../api/notificationsApi';
import { toV1Path } from '../utils/v2Routes';

export const V2_ROUTE_MANIFEST = {
  '/dashboard': {
    loadChunk: () => import('../../modules/admin/CuadroMandoIntegral'),
    prefetch: (qc) => [
      qc.prefetchQuery({ queryKey: ['cmi', 'scorecard', null], queryFn: () => cmiApi.getScorecard(null), staleTime: 60_000 }),
      qc.prefetchQuery({ queryKey: ['kpis', 'general'], queryFn: () => getKpisGeneral(), staleTime: 60_000 }),
    ],
  },
  '/cmi': {
    loadChunk: () => import('../../modules/admin/CuadroMandoIntegral'),
    prefetch: (qc) => [
      qc.prefetchQuery({ queryKey: ['cmi', 'scorecard', null], queryFn: () => cmiApi.getScorecard(null), staleTime: 60_000 }),
      qc.prefetchQuery({ queryKey: ['analiticaPredictivaMacro', 6], queryFn: () => getAnaliticaPredictivaMacro(6), staleTime: 60_000 }),
    ],
  },
  '/dataops/ingesta': {
    loadChunk: () => import('../../modules/dataops/IngestView'),
    prefetch: (qc) => [
      dataopsApi.getLotes ? qc.prefetchQuery({ queryKey: [...DATAOPS_QUERY_KEY, 'lotes'], queryFn: () => dataopsApi.getLotes(), staleTime: 30_000 }) : Promise.resolve(),
      qc.prefetchQuery({ queryKey: ['kpis', 'pipeline'], queryFn: () => getKpisPipeline(), staleTime: 30_000 }),
    ],
  },
  '/dataops/beto': {
    loadChunk: () => import('../../modules/dataops/BetoReadingFlowView'),
    prefetch: (qc) => [
      dataopsApi.getLotes ? qc.prefetchQuery({ queryKey: [...DATAOPS_QUERY_KEY, 'lotes'], queryFn: () => dataopsApi.getLotes(), staleTime: 30_000 }) : Promise.resolve(),
    ],
  },
  '/dataops/revision': {
    loadChunk: () => import('../../modules/dataops/HumanReviewFlowView'),
    prefetch: (qc) => [
      dataopsApi.getLotes ? qc.prefetchQuery({ queryKey: [...DATAOPS_QUERY_KEY, 'lotes'], queryFn: () => dataopsApi.getLotes(), staleTime: 30_000 }) : Promise.resolve(),
    ],
  },
  '/dataops/datos-maestros': {
    loadChunk: () => import('../../modules/dataops/MasterDataView'),
    prefetch: (qc) => [
      dataopsApi.getCatalogs
        ? qc.prefetchQuery({ queryKey: [...DATAOPS_QUERY_KEY, 'master-catalog', 'modulos', 1, ''], queryFn: () => dataopsApi.getCatalogs({ tipo: 'modulos', page: 1, search: '' }), staleTime: 60_000 })
        : Promise.resolve(),
    ],
  },
  '/academico/rendimiento': {
    loadChunk: () => import('../../modules/academic/RendimientoAlertas'),
    prefetch: (qc) => [
      qc.prefetchQuery({ queryKey: ['alertasTempranas'], queryFn: () => getAlertasTempranas(), staleTime: 60_000 }),
      qc.prefetchQuery({ queryKey: ['kpis', 'academico'], queryFn: () => getKpisAcademico(), staleTime: 60_000 }),
    ],
  },
  '/academico/alertas': {
    loadChunk: () => import('../../modules/academic/RendimientoAlertas'),
    prefetch: (qc) => [
      qc.prefetchQuery({ queryKey: ['alertasTempranas'], queryFn: () => getAlertasTempranas(), staleTime: 60_000 }),
    ],
  },
  '/alertas-tempranas': {
    loadChunk: () => import('../../modules/academic/RendimientoAlertas'),
    prefetch: (qc) => [
      qc.prefetchQuery({ queryKey: ['alertasTempranas'], queryFn: () => getAlertasTempranas(), staleTime: 60_000 }),
    ],
  },
  '/academico/docente': {
    loadChunk: () => import('../../modules/academic/DesempenoDocente'),
    prefetch: (qc) => [
      qc.prefetchQuery({ queryKey: ['kpis', 'academico'], queryFn: () => getKpisAcademico(), staleTime: 60_000 }),
    ],
  },
  '/academico/catalogo': {
    loadChunk: () => import('../../modules/academic/CatalogoCurricular'),
    prefetch: (qc) => [
      catalogApi.getProgramas ? qc.prefetchQuery({ queryKey: ['catalog', 'programas'], queryFn: () => catalogApi.getProgramas(), staleTime: 60_000 }) : Promise.resolve(),
    ],
  },
  '/academico/programas': {
    loadChunk: () => import('../../modules/academic/CatalogoCurricular'),
    prefetch: (qc) => [
      catalogApi.getProgramas ? qc.prefetchQuery({ queryKey: ['catalog', 'programas'], queryFn: () => catalogApi.getProgramas(), staleTime: 60_000 }) : Promise.resolve(),
    ],
  },
  '/academico/proyeccion': {
    loadChunk: () => import('../../modules/academic/ProyeccionAlumnos'),
    prefetch: (qc) => [
      qc.prefetchQuery({ queryKey: ['forecast', 'alumnos'], queryFn: () => getForecastAlumnos(), staleTime: 60_000 }),
      qc.prefetchQuery({ queryKey: ['forecast', 'viabilidad'], queryFn: () => getViabilidadProgramas(), staleTime: 60_000 }),
    ],
  },
  '/financiero/recaudacion': {
    loadChunk: () => import('../../modules/finance/RecaudacionCobranzas'),
    prefetch: (qc) => [
      qc.prefetchQuery({ queryKey: ['finance', 'recaudacion-cobranzas'], queryFn: () => getKpisFinanciero(), staleTime: 60_000 }),
    ],
  },
  '/financiero/cartera': {
    loadChunk: () => import('../../modules/finance/CarteraMora'),
    prefetch: (qc) => [
      qc.prefetchQuery({ queryKey: ['finance', 'cartera-mora'], queryFn: () => getKpisFinanciero(), staleTime: 60_000 }),
    ],
  },
  '/financiero/metas': {
    loadChunk: () => import('../../modules/finance/MetasGestion'),
    prefetch: (qc) => [
      qc.prefetchQuery({ queryKey: ['finance', 'metas-gestion'], queryFn: () => getForecastMetas(), staleTime: 60_000 }),
    ],
  },
  '/financiero/proyeccion': {
    loadChunk: () => import('../../modules/finance/ProyeccionFinanciera'),
    prefetch: (qc) => [
      qc.prefetchQuery({ queryKey: ['finance', 'proyeccion-financiera', 6, 'mensual'], queryFn: () => getAnaliticaPredictivaMacro(6), staleTime: 60_000 }),
    ],
  },
  '/admin/usuarios': {
    loadChunk: () => import('../../modules/admin/GestionUsuarios'),
    prefetch: (qc) => [
      qc.prefetchQuery({ queryKey: ['admin', 'users'], queryFn: () => getUsers(), staleTime: 60_000 }),
    ],
  },
  '/admin/catalogos': {
    loadChunk: () => import('../../modules/admin/CatalogosMaestros'),
    prefetch: (qc) => [
      catalogApi.getFinancialConcepts ? qc.prefetchQuery({ queryKey: ['admin', 'conceptos-financieros'], queryFn: () => catalogApi.getFinancialConcepts(), staleTime: 60_000 }) : Promise.resolve(),
    ],
  },
  '/admin/auditoria': {
    loadChunk: () => import('../../modules/admin/AuditoriaSistema'),
    prefetch: (qc) => [
      auditApi.getLogs ? qc.prefetchQuery({ queryKey: ['admin', 'audit'], queryFn: () => auditApi.getLogs(), staleTime: 30_000 }) : Promise.resolve(),
    ],
  },
  '/reportes': {
    loadChunk: () => import('../../modules/reports/CentroReportes'),
    prefetch: (qc) => [
      reportesApi.getHistorial ? qc.prefetchQuery({ queryKey: ['reportes', 'historial'], queryFn: () => reportesApi.getHistorial(15), staleTime: 60_000 }) : Promise.resolve(),
    ],
  },
  '/notificaciones': {
    loadChunk: () => import('../../modules/notifications/NotificationsPage'),
    prefetch: (qc) => [
      notificationsApi.getNotifications ? qc.prefetchQuery({ queryKey: ['notifications'], queryFn: () => notificationsApi.getNotifications(), staleTime: 30_000 }) : Promise.resolve(),
    ],
  },
  '/ajustes': {
    loadChunk: () => import('../../modules/settings/AjustesSistema'),
    prefetch: () => [],
  },
};

export function normalizeV2RouteKey(pathname = '') {
  const v1 = toV1Path(pathname);
  if (/^\/dataops\/lote\/[^/]+\/texto/.test(v1)) return '/dataops/texto';
  if (/^\/dataops\/lote\/[^/]+\/beto/.test(v1)) return '/dataops/beto';
  if (/^\/dataops\/lote\/[^/]+\/revision/.test(v1)) return '/dataops/revision';
  return v1;
}

export async function prefetchRouteAndData(
  pathname,
  role = 'ADMIN',
  { queryClient = defaultQueryClient, timeoutMs = 1200, manifest = V2_ROUTE_MANIFEST } = {}
) {
  const key = normalizeV2RouteKey(pathname);
  const entry = manifest[key];
  if (!entry) {
    return { key, status: 'unmapped', timedOut: false };
  }

  const chunkPromise = Promise.resolve()
    .then(() => entry.loadChunk?.())
    .catch(() => null);

  const dataPromises = (entry.prefetch ? entry.prefetch(queryClient, role) : []).map((p) =>
    Promise.resolve(p).catch(() => null)
  );

  let timedOut = false;
  let timerId = null;

  const workPromise = Promise.all([chunkPromise, ...dataPromises]).then(() => {
    if (timerId) clearTimeout(timerId);
    return { key, status: 'ready', timedOut };
  });

  const timeoutPromise = new Promise((resolve) => {
    timerId = setTimeout(() => {
      timedOut = true;
      resolve({ key, status: 'timeout', timedOut: true });
    }, timeoutMs);
  });

  return Promise.race([workPromise, timeoutPromise]);
}
