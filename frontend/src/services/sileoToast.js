import { sileo } from 'sileo';

const DEFAULT_OPTIONS = {
  position: 'top-center',
  fill: '#17191c',
  roundness: 16,
  styles: {
    title: 'text-white font-sans text-sm font-semibold',
    description: 'text-slate-300 font-sans text-xs',
    badge: 'bg-white/10',
    button: 'bg-white/15 hover:bg-white/20 text-white font-medium text-xs rounded-full px-3 py-1',
  },
};

const mergeOptions = (opts = {}) => {
  const { styles, ...rest } = opts;
  return {
    ...DEFAULT_OPTIONS,
    ...rest,
    styles: {
      ...DEFAULT_OPTIONS.styles,
      ...(styles || {}),
    },
  };
};

export const sileoToast = {
  success: ({ title, description, ...opts } = {}) => {
    return sileo.success(mergeOptions({ title, description, ...opts }));
  },
  error: ({ title, description, ...opts } = {}) => {
    return sileo.error(mergeOptions({ title, description, ...opts }));
  },
  warning: ({ title, description, ...opts } = {}) => {
    return sileo.warning(mergeOptions({ title, description, ...opts }));
  },
  info: ({ title, description, ...opts } = {}) => {
    return sileo.info(mergeOptions({ title, description, ...opts }));
  },
  action: ({ title, description, button, ...opts } = {}) => {
    return sileo.action(mergeOptions({ title, description, button, ...opts }));
  },
  icon: ({ title, description, icon, ...opts } = {}) => {
    return sileo.show(mergeOptions({ title, description, icon, ...opts }));
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
  dismiss: (id) => sileo.dismiss(id),
  clear: (position) => sileo.clear(position),
};

export { sileo };
export default sileoToast;
