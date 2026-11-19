import { useEffect } from 'react';

const CARD_SELECTOR = '.v2-main-content .card, .v2-main-content .kpi-card, .v2-main-content .panel';

export function useScrollFlowV2(routeKey) {
  useEffect(() => {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;

    const cards = Array.from(document.querySelectorAll(CARD_SELECTOR));
    cards.forEach((el) => el.classList.add('v2-scroll-card'));

    const supportsViewTimeline =
      typeof CSS !== 'undefined' &&
      typeof CSS.supports === 'function' &&
      CSS.supports('(animation-timeline: view()) and (animation-range: entry)');

    const prefersNoReducedMotion =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: no-preference)').matches;

    if (supportsViewTimeline || !prefersNoReducedMotion || typeof IntersectionObserver === 'undefined') {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const ratio = entry.intersectionRatio;
          const opacity = 0.45 + ratio * 0.55;
          const scale = 0.985 + ratio * 0.015;
          entry.target.style.opacity = opacity.toFixed(3);
          entry.target.style.transform = `scale(${scale.toFixed(4)})`;
        }
      },
      {
        threshold: [0, 0.25, 0.5, 0.75, 1],
      }
    );

    cards.forEach((el) => observer.observe(el));

    return () => {
      observer.disconnect();
      cards.forEach((el) => {
        el.style.opacity = '';
        el.style.transform = '';
      });
    };
  }, [routeKey]);
}
