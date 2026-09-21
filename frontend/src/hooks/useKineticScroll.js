import { useEffect } from 'react';

/**
 * useKineticScroll hook
 * Observes elements with `.kinetic-card` or custom selector.
 * Adds `.in-view` when entering viewport and `.out-view` when exiting,
 * producing smooth orchestrated card entrance as the user scrolls.
 */
export function useKineticScroll(selector = '.kinetic-card', threshold = 0.12) {
  useEffect(() => {
    const elements = document.querySelectorAll(selector);
    if (!elements || elements.length === 0) return;

    // Set initial out-view state if not already in-view
    elements.forEach((el) => {
      if (!el.classList.contains('in-view')) {
        el.classList.add('out-view');
      }
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.remove('out-view');
            entry.target.classList.add('in-view');
          } else {
            // Optional: reset for re-animation on scroll up
            if (entry.boundingClientRect.top > 0) {
              entry.target.classList.remove('in-view');
              entry.target.classList.add('out-view');
            }
          }
        });
      },
      {
        threshold,
        rootMargin: '0px 0px -40px 0px',
      }
    );

    elements.forEach((el) => observer.observe(el));

    return () => {
      elements.forEach((el) => observer.unobserve(el));
      observer.disconnect();
    };
  }, [selector, threshold]);
}

export default useKineticScroll;
