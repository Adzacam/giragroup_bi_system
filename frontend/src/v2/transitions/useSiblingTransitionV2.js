import { useCallback } from 'react';

export function useSiblingTransitionV2() {
  const transitionSibling = useCallback((fromIdx, toIdx, updateDOM) => {
    if (typeof updateDOM !== 'function') return;

    if (typeof document === 'undefined' || typeof document.startViewTransition !== 'function') {
      updateDOM();
      return;
    }

    const direction = toIdx >= fromIdx ? 'sibling-forward' : 'sibling-backward';
    try {
      document.startViewTransition({
        update: updateDOM,
        types: [direction],
      });
    } catch {
      updateDOM();
    }
  }, []);

  return { transitionSibling };
}
