import { useCallback } from 'react';
import { flushSync } from 'react-dom';

function clearParentChildMarkers() {
  if (typeof document === 'undefined') return;
  document.querySelectorAll('.v2-vt-parent-child').forEach((el) => {
    el.classList.remove('v2-vt-parent-child');
  });
}

/**
 * Hook de transición Padre -> Hijo para los 6 selectores de V2.
 * Usa flushSync dentro de document.startViewTransition para que el navegador
 * capture el snapshot real del nuevo panel hijo mientras Topbar y Sidebar
 * permanecen congelados.
 */
export function useParentChildTransitionV2() {
  const triggerParentChild = useCallback((sourceEl, updateDOM, { focusTargetId } = {}) => {
    if (typeof updateDOM !== 'function') return;

    const isV2 =
      typeof document !== 'undefined' &&
      document.documentElement.getAttribute('data-ui-version') === 'v2';

    const focusChild = () => {
      if (!focusTargetId || typeof document === 'undefined') return;
      const target = document.getElementById(focusTargetId);
      if (target && typeof target.focus === 'function') {
        if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
        target.focus({ preventScroll: true });
      }
    };

    const runSyncUpdate = () => {
      try {
        flushSync(() => {
          updateDOM();
        });
      } catch {
        updateDOM();
      }
    };

    if (!isV2 || typeof document.startViewTransition !== 'function') {
      updateDOM();
      focusChild();
      return;
    }

    clearParentChildMarkers();
    if (sourceEl && sourceEl.classList) {
      sourceEl.classList.add('v2-vt-parent-child');
    }

    try {
      const transition = document.startViewTransition({
        update: () => {
          runSyncUpdate();
        },
        types: ['parent-child'],
      });

      transition.finished.finally(() => {
        clearParentChildMarkers();
        focusChild();
      });
    } catch {
      clearParentChildMarkers();
      runSyncUpdate();
      focusChild();
    }
  }, []);

  return { triggerParentChild };
}
