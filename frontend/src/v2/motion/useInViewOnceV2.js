import { useEffect, useState } from 'react';

/**
 * Observa cuándo un elemento entra en pantalla (viewport) una sola vez.
 * En SSR o entornos sin IntersectionObserver devuelve `true` inmediatamente.
 */
export function useInViewOnceV2(ref, { threshold = 0.12, rootMargin = '0px 0px -32px 0px', enabled = true } = {}) {
  const canObserve = typeof window !== 'undefined' && typeof IntersectionObserver !== 'undefined';
  const [inView, setInView] = useState(() => !canObserve || !enabled);

  useEffect(() => {
    if (!enabled) {
      setInView(false);
      return undefined;
    }
    if (!canObserve) {
      setInView(true);
      return undefined;
    }
    if (inView) return undefined;

    const node = ref?.current;
    if (!node) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting || entry.intersectionRatio > 0) {
            setInView(true);
            observer.disconnect();
            break;
          }
        }
      },
      { threshold, rootMargin }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [ref, threshold, rootMargin, enabled, canObserve, inView]);

  return inView;
}
