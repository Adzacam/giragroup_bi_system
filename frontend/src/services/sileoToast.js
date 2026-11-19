import { sileo } from 'sileo';

const DEFAULT_OPTIONS = {
  position: 'top-center',
  fill: '#0C1E33',
  roundness: 16,
  styles: {
    title: 'sileo-title',
    description: 'sileo-desc',
    badge: 'sileo-badge',
    button: 'sileo-btn',
  },
};

export const MAX_VISIBLE_TOASTS = 3;

let nextToastId = 0;
const activeVisibleIds = [];
const overflowQueue = [];
let overflowSummaryToastId = null;
let overflowSummaryTimer = null;
const dismissTimers = new Map();
const taskToastMap = new Map(); // tarea_id -> { toastId, type, title, etapa, porcentaje }

let bulkDeleteCount = 0;
let bulkDeleteTimer = null;

const clearDismissTimer = (id) => {
  const timer = dismissTimers.get(id);
  if (timer) {
    clearTimeout(timer);
    dismissTimers.delete(id);
  }
};

const removeVisibleId = (id) => {
  clearDismissTimer(id);
  const idx = activeVisibleIds.indexOf(id);
  if (idx !== -1) activeVisibleIds.splice(idx, 1);
  for (const [k, v] of taskToastMap.entries()) {
    if (v.toastId === id) taskToastMap.delete(k);
  }
};

const resolveToastFill = () => {
  if (typeof document === 'undefined') return DEFAULT_OPTIONS.fill;
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const cssFill = getComputedStyle(document.documentElement).getPropertyValue('--color-toast-background').trim();
  if (cssFill) return cssFill;
  return isDark ? '#161920' : '#0C1E33';
};

const mergeOptions = (opts = {}) => {
  const { styles, ...rest } = opts;
  return {
    ...DEFAULT_OPTIONS,
    id: opts.id || `gira-aviso-${Date.now()}-${++nextToastId}`,
    fill: resolveToastFill(),
    ...rest,
    styles: {
      ...DEFAULT_OPTIONS.styles,
      ...(styles || {}),
    },
  };
};

const updateOverflowSummaryToast = (position = DEFAULT_OPTIONS.position) => {
  if (overflowSummaryTimer) {
    clearTimeout(overflowSummaryTimer);
    overflowSummaryTimer = null;
  }
  if (overflowSummaryToastId) {
    sileo.dismiss(overflowSummaryToastId);
    overflowSummaryToastId = null;
  }
  if (overflowQueue.length > 0) {
    const n = overflowQueue.length;
    const last = overflowQueue[overflowQueue.length - 1];
    overflowSummaryToastId = sileo.info(
      mergeOptions({
        position,
        title: `+${n} más`,
        description: last?.title ? `Último aviso: ${last.title}` : `${n} notificaciones agrupadas.`,
        duration: 4500,
      })
    );
    overflowSummaryTimer = setTimeout(() => {
      overflowSummaryTimer = null;
      overflowSummaryToastId = null;
      overflowQueue.length = 0;
    }, 4600);
  }
};

const showManaged = (method, opts = {}) => {
  const merged = mergeOptions(opts);
  if (activeVisibleIds.length >= MAX_VISIBLE_TOASTS) {
    overflowQueue.push({ title: merged.title, description: merged.description, method });
    updateOverflowSummaryToast(merged.position);
    return overflowSummaryToastId;
  }
  const sileoId = sileo[method](merged);
  activeVisibleIds.push(sileoId);
  const effectiveDuration = merged.duration === undefined ? 6000 : merged.duration;
  if (typeof effectiveDuration === 'number' && effectiveDuration > 0) {
    const timer = setTimeout(() => {
      removeVisibleId(sileoId);
    }, effectiveDuration + 100);
    dismissTimers.set(sileoId, timer);
  }
  return sileoId;
};

const formatTaskDescription = ({ etapa, porcentaje, description }) => {
  const pctNum = porcentaje != null && Number.isFinite(Number(porcentaje)) ? Math.round(Number(porcentaje)) : null;
  const stageText = etapa || '';
  if (pctNum != null && stageText) {
    return `${pctNum} % · ${stageText}`;
  }
  if (pctNum != null) {
    return `${pctNum} % completado`;
  }
  return stageText || description || 'Procesando…';
};

export const sileoToast = {
  success: ({ title, description, ...opts } = {}) => showManaged('success', { title, description, ...opts }),
  error: ({ title, description, ...opts } = {}) => showManaged('error', { title, description, ...opts }),
  warning: ({ title, description, ...opts } = {}) => showManaged('warning', { title, description, ...opts }),
  info: ({ title, description, ...opts } = {}) => showManaged('info', { title, description, ...opts }),
  action: ({ title, description, button, ...opts } = {}) => showManaged('action', { title, description, button, ...opts }),
  icon: ({ title, description, icon, ...opts } = {}) => showManaged('show', { title, description, icon, ...opts }),

  /**
   * Un único toast por `tarea_id`: actualiza porcentaje y etapa sin apilar toasts.
   */
  upsertTask: (tareaId, { type = 'show', title, etapa, porcentaje, description, ...opts } = {}) => {
    const key = String(tareaId);
    const existing = taskToastMap.get(key);
    const resolvedDesc = description ?? formatTaskDescription({ etapa, porcentaje });
    const method = ['success', 'error', 'warning', 'info', 'action'].includes(type) ? type : 'show';

    if (existing?.toastId && existing.toastId !== overflowSummaryToastId) {
      removeVisibleId(existing.toastId);
      sileo.dismiss(existing.toastId);
    }

    const toastId = showManaged(method, {
      id: `dataops-tarea-${key}`,
      title,
      description: resolvedDesc,
      ...opts,
    });

    const entry = { toastId, type: method, title, etapa, porcentaje, description: resolvedDesc };
    if (method === 'success' || method === 'error') {
      taskToastMap.delete(key);
    } else {
      taskToastMap.set(key, entry);
    }
    return toastId;
  },

  /**
   * Resume eliminaciones en bloque en un solo toast ("N lotes eliminados").
   */
  bulkDeleteSummary: (count, { entity = 'lote', plural = 'lotes', description = 'El historial se ha actualizado.', ...opts } = {}) => {
    const n = Math.max(1, Number(count) || 1);
    const label = n === 1 ? `${n} ${entity} eliminado` : `${n} ${plural} eliminados`;
    return showManaged('success', {
      title: label,
      description,
      ...opts,
    });
  },

  queueBulkDelete: (opts = {}) => {
    bulkDeleteCount += 1;
    if (bulkDeleteTimer) clearTimeout(bulkDeleteTimer);
    bulkDeleteTimer = setTimeout(() => {
      const total = bulkDeleteCount;
      bulkDeleteCount = 0;
      bulkDeleteTimer = null;
      sileoToast.bulkDeleteSummary(total, opts);
    }, 50);
  },

  promise: (promise, { loading, success, error, action, ...opts } = {}) => {
    const wrapHandler = (target) => {
      if (!target) return target;
      if (typeof target === 'function') {
        return (data) => mergeOptions(target(data));
      }
      return mergeOptions(target);
    };

    return sileo.promise(promise, {
      position: opts.position || DEFAULT_OPTIONS.position,
      ...opts,
      loading: mergeOptions(loading),
      success: wrapHandler(success),
      error: wrapHandler(error),
      ...(action ? { action: wrapHandler(action) } : {}),
    });
  },

  dismiss: (id) => {
    if (!id) return;
    removeVisibleId(id);
    if (id === overflowSummaryToastId) {
      if (overflowSummaryTimer) {
        clearTimeout(overflowSummaryTimer);
        overflowSummaryTimer = null;
      }
      overflowSummaryToastId = null;
      overflowQueue.length = 0;
    }
    sileo.dismiss(id);
  },

  clear: (position) => {
    activeVisibleIds.length = 0;
    overflowQueue.length = 0;
    if (overflowSummaryTimer) {
      clearTimeout(overflowSummaryTimer);
      overflowSummaryTimer = null;
    }
    overflowSummaryToastId = null;
    for (const timer of dismissTimers.values()) {
      clearTimeout(timer);
    }
    dismissTimers.clear();
    taskToastMap.clear();
    if (bulkDeleteTimer) {
      clearTimeout(bulkDeleteTimer);
      bulkDeleteTimer = null;
    }
    bulkDeleteCount = 0;
    sileo.clear(position);
  },

  getActiveToastsState: () => ({
    visibleCount: activeVisibleIds.length,
    overflowCount: overflowQueue.length,
    taskCount: taskToastMap.size,
    tasks: Array.from(taskToastMap.entries()).map(([id, v]) => ({ tarea_id: id, ...v })),
  }),
};

export const confirmar = ({ title, description, confirmText = 'Confirmar' } = {}) =>
  new Promise((resolve) => {
    let resuelto = false;
    const fin = (v) => { if (!resuelto) { resuelto = true; resolve(v); } };
    sileo.action(mergeOptions({
      title, description, duration: 15000,
      button: { title: confirmText, onClick: () => fin(true) },
    }));
    setTimeout(() => fin(false), 15500);
  });

export { sileo };
export default sileoToast;
