import { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { toV2Path } from '../utils/v2Routes';
import { prefetchRouteAndData } from './routeDataPrefetcherV2';

export function useSynchronizedNavigationV2() {
  const navigate = useNavigate();
  const location = useLocation();
  const { role } = useAuth();

  const [isNavigating, setIsNavigating] = useState(false);
  const [topProgress, setTopProgress] = useState(0);
  const activeNavIdRef = useRef(0);
  const resetTimerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (resetTimerRef.current) clearTimeout(resetTimerRef.current);
    };
  }, []);

  const prefetchOnIntent = useCallback(
    (targetPath) => {
      if (!targetPath) return;
      const v2Target = toV2Path(targetPath);
      prefetchRouteAndData(v2Target, role, { timeoutMs: 1500 });
    },
    [role]
  );

  const navigateV2 = useCallback(
    async (targetPath, { direction = null, replace = false, state = undefined } = {}) => {
      const v2Target = toV2Path(targetPath);
      if (v2Target === location.pathname && !state) {
        return;
      }

      if (resetTimerRef.current) clearTimeout(resetTimerRef.current);
      const navId = ++activeNavIdRef.current;

      setIsNavigating(true);
      setTopProgress(75);

      await prefetchRouteAndData(v2Target, role, { timeoutMs: 1200 });

      if (navId !== activeNavIdRef.current) return;

      const performSwap = () => {
        navigate(v2Target, { replace, state });
        setTopProgress(100);
        window.scrollTo({ top: 0, behavior: 'auto' });
      };

      if (typeof document !== 'undefined' && typeof document.startViewTransition === 'function') {
        const types = direction ? [direction] : undefined;
        try {
          const transition = types
            ? document.startViewTransition({ update: performSwap, types })
            : document.startViewTransition(performSwap);
          transition?.finished?.finally(() => {
            if (navId === activeNavIdRef.current) {
              setIsNavigating(false);
            }
          });
        } catch {
          performSwap();
        }
      } else {
        performSwap();
      }

      resetTimerRef.current = setTimeout(() => {
        if (navId === activeNavIdRef.current) {
          setIsNavigating(false);
          setTopProgress(0);
        }
      }, 220);
    },
    [location.pathname, navigate, role]
  );

  return {
    navigateV2,
    prefetchOnIntent,
    isNavigating,
    topProgress,
  };
}
