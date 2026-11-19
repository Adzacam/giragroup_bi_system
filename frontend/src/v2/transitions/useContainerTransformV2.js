import { useCallback, useRef } from 'react';

function clearActiveTransitionClasses() {
  if (typeof document === 'undefined') return;
  document.querySelectorAll('.v2-vt-expand-source').forEach((el) => {
    el.classList.remove('v2-vt-expand-source');
  });
  document.querySelectorAll('.v2-vt-expand-title').forEach((el) => {
    el.classList.remove('v2-vt-expand-title');
  });
}

export function useContainerTransformV2() {
  const lastSourceRef = useRef(null);

  const triggerContainerExpand = useCallback((sourceEl, updateDOM, { focusTargetId } = {}) => {
    clearActiveTransitionClasses();

    if (sourceEl && sourceEl.classList) {
      lastSourceRef.current = sourceEl;
      sourceEl.classList.add('v2-vt-expand-source');
      const titleEl = sourceEl.querySelector('[data-v2-card-title], h2, h3, .kpi-title');
      if (titleEl) titleEl.classList.add('v2-vt-expand-title');
    }

    const focusDestination = () => {
      if (!focusTargetId || typeof document === 'undefined') return;
      const target = document.getElementById(focusTargetId);
      if (target && typeof target.focus === 'function') {
        if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
        target.focus({ preventScroll: true });
      }
    };

    if (typeof document === 'undefined' || typeof document.startViewTransition !== 'function') {
      updateDOM();
      focusDestination();
      clearActiveTransitionClasses();
      return;
    }

    const transition = document.startViewTransition(() => {
      updateDOM();
    });

    transition.finished.finally(() => {
      clearActiveTransitionClasses();
      focusDestination();
    });
  }, []);

  const triggerContainerCollapse = useCallback((updateDOM) => {
    const restoreFocus = () => {
      const el = lastSourceRef.current;
      if (el && typeof el.focus === 'function') {
        el.focus({ preventScroll: true });
      }
      lastSourceRef.current = null;
    };

    if (typeof document === 'undefined' || typeof document.startViewTransition !== 'function') {
      updateDOM();
      clearActiveTransitionClasses();
      restoreFocus();
      return;
    }

    const transition = document.startViewTransition(() => {
      updateDOM();
    });

    transition.finished.finally(() => {
      clearActiveTransitionClasses();
      restoreFocus();
    });
  }, []);

  return {
    triggerContainerExpand,
    triggerContainerCollapse,
  };
}
