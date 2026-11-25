import { useEffect, useMemo, useRef, useState } from 'react';

export const MOTION_DURATION_MS = 900;
export const MOTION_EASING_CSS = 'cubic-bezier(0.22, 1, 0.36, 1)';

/**
 * Curva de desaceleración suave equivalente a cubic-bezier(0.22, 1, 0.36, 1).
 */
export function easeOutQuintic(t) {
  const clamped = Math.max(0, Math.min(1, t));
  return 1 - Math.pow(1 - clamped, 4);
}

export function prefersReducedMotion() {
  if (typeof window === 'undefined') return true;
  if (typeof window.matchMedia !== 'function') return true;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Extrae prefijo, signo, valor numérico, separadores, decimales y sufijo
 * de una métrica formateada (e.g. 'Bs 1.234', 'Bs. 45,2 mil', '24,5 %', '+2,1 pp', '72.5%').
 */
export function parseFormattedMetric(input) {
  if (input === null || input === undefined) {
    return { isNumeric: false, raw: input, prefix: '', value: null, decimals: 0, decimalSep: ',', thousandSep: '', suffix: '', sign: '' };
  }

  if (typeof input === 'number') {
    if (!Number.isFinite(input)) {
      return { isNumeric: false, raw: String(input), prefix: '', value: null, decimals: 0, decimalSep: '.', thousandSep: '', suffix: '', sign: '' };
    }
    const str = String(input);
    const dotIdx = str.indexOf('.');
    const decimals = dotIdx >= 0 ? str.length - dotIdx - 1 : 0;
    return {
      isNumeric: true,
      raw: str,
      prefix: '',
      value: input,
      decimals,
      decimalSep: '.',
      thousandSep: '',
      suffix: '',
      sign: input < 0 ? '-' : '',
    };
  }

  const raw = String(input);
  const trimmed = raw.trim();
  if (!trimmed || trimmed === '—' || trimmed === '-' || trimmed === 'N/A' || trimmed === 'Sin dato') {
    return { isNumeric: false, raw, prefix: '', value: null, decimals: 0, decimalSep: ',', thousandSep: '', suffix: '', sign: '' };
  }

  // Captura el primer bloque numérico con signo opcional (+, -, −)
  const match = raw.match(/^([^0-9+\-−]*?)([+\-−]?)(\d[\d.,]*)(.*)$/);
  if (!match) {
    return { isNumeric: false, raw, prefix: '', value: null, decimals: 0, decimalSep: ',', thousandSep: '', suffix: '', sign: '' };
  }

  const [, prefix, signChar, numToken, suffix] = match;
  const hasComma = numToken.includes(',');
  const hasDot = numToken.includes('.');

  let thousandSep = '';
  let decimalSep = ',';
  let decimals = 0;
  let normalized = numToken;

  if (hasComma && hasDot) {
    const lastComma = numToken.lastIndexOf(',');
    const lastDot = numToken.lastIndexOf('.');
    if (lastComma > lastDot) {
      // Formato es-BO: 1.234,56
      thousandSep = '.';
      decimalSep = ',';
      decimals = numToken.length - lastComma - 1;
      normalized = numToken.replace(/\./g, '').replace(',', '.');
    } else {
      // Formato en-US: 1,234.56
      thousandSep = ',';
      decimalSep = '.';
      decimals = numToken.length - lastDot - 1;
      normalized = numToken.replace(/,/g, '');
    }
  } else if (hasComma) {
    const commaCount = (numToken.match(/,/g) || []).length;
    if (commaCount > 1) {
      thousandSep = ',';
      decimals = 0;
      normalized = numToken.replace(/,/g, '');
    } else {
      const parts = numToken.split(',');
      decimalSep = ',';
      decimals = parts[1].length;
      normalized = `${parts[0]}.${parts[1]}`;
    }
  } else if (hasDot) {
    const dotCount = (numToken.match(/\./g) || []).length;
    if (dotCount > 1) {
      thousandSep = '.';
      decimals = 0;
      normalized = numToken.replace(/\./g, '');
    } else {
      const parts = numToken.split('.');
      // En es-BO, un único punto con exactamente 3 dígitos después (y parte entera != '0') suele ser separador de miles (ej. '1.234')
      if (parts[1].length === 3 && parts[0] !== '0' && parts[0].length <= 3) {
        thousandSep = '.';
        decimals = 0;
        normalized = parts[0] + parts[1];
      } else {
        decimalSep = '.';
        decimals = parts[1].length;
        normalized = numToken;
      }
    }
  }

  const absValue = Number(normalized);
  if (!Number.isFinite(absValue)) {
    return { isNumeric: false, raw, prefix: '', value: null, decimals: 0, decimalSep: ',', thousandSep: '', suffix: '', sign: '' };
  }

  const isNegative = signChar === '-' || signChar === '−';
  const signedValue = isNegative ? -absValue : absValue;

  return {
    isNumeric: true,
    raw,
    prefix,
    value: signedValue,
    decimals,
    decimalSep,
    thousandSep,
    suffix,
    sign: signChar,
  };
}

/**
 * Formatea un valor numérico intermedio usando la estructura extraída por parseFormattedMetric.
 */
export function formatParsedMetric(currentValue, parsed) {
  if (!parsed?.isNumeric) return parsed?.raw ?? '—';

  const absVal = Math.abs(currentValue);
  const fixed = absVal.toFixed(parsed.decimals);
  const [intPart, fracPart] = fixed.split('.');

  const groupedInt = parsed.thousandSep
    ? intPart.replace(/\B(?=(\d{3})+(?!\d))/g, parsed.thousandSep)
    : intPart;

  const formattedNumber = parsed.decimals > 0
    ? `${groupedInt}${parsed.decimalSep}${fracPart}`
    : groupedInt;

  let signPrefix = '';
  if (currentValue < 0) {
    signPrefix = parsed.sign === '−' ? '−' : '-';
  } else if (parsed.sign === '+' && currentValue > 0) {
    signPrefix = '+';
  }

  return `${parsed.prefix}${signPrefix}${formattedNumber}${parsed.suffix}`;
}

const _ANIMATED_KEYS = new Map();

/**
 * Hook de conteo progresivo 0 -> N en 900ms.
 * - Enteros pequeños (<= 60): cuentan paso a paso (1, 2, 3... -> N).
 * - Cifras grandes o con decimales: interpolación suave a 60fps.
 * - En `prefers-reduced-motion: reduce`, SSR o tests síncronos devuelve el valor final exacto.
 * - Con `animateOnceKey` no repite 0 -> N al cambiar de pestaña o re-renderizar.
 */
export function useCountUpV2(target, { duration = MOTION_DURATION_MS, enabled = true, active = true, animateOnceKey = null } = {}) {
  const parsed = useMemo(() => parseFormattedMetric(target), [target]);
  const finalDisplay = useMemo(() => {
    if (target === null || target === undefined) return '—';
    return typeof target === 'number' ? String(target) : String(target);
  }, [target]);

  const yaAnimado = Boolean(animateOnceKey && _ANIMATED_KEYS.get(animateOnceKey) === finalDisplay);
  const shouldSkipAnimation = !enabled || yaAnimado || !parsed.isNumeric || parsed.value === 0 || prefersReducedMotion() || typeof requestAnimationFrame === 'undefined';

  const [display, setDisplay] = useState(() => (shouldSkipAnimation ? finalDisplay : formatParsedMetric(0, parsed)));
  const rafRef = useRef(null);

  useEffect(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }

    if (shouldSkipAnimation) {
      setDisplay(finalDisplay);
      return undefined;
    }

    if (!active) {
      setDisplay(formatParsedMetric(0, parsed));
      return undefined;
    }

    const targetVal = parsed.value;
    const isSmallInteger = parsed.decimals === 0 && Math.abs(targetVal) <= 60;
    const startTime = performance.now();

    const tick = (now) => {
      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / duration);
      if (t >= 1) {
        if (animateOnceKey) {
          if (_ANIMATED_KEYS.size >= 500) _ANIMATED_KEYS.clear();
          _ANIMATED_KEYS.set(animateOnceKey, finalDisplay);
        }
        setDisplay(finalDisplay);
        rafRef.current = null;
        return;
      }

      const eased = easeOutQuintic(t);
      let current = targetVal * eased;

      if (isSmallInteger) {
        current = targetVal >= 0 ? Math.floor(current) : Math.ceil(current);
      }

      setDisplay(formatParsedMetric(current, parsed));
      rafRef.current = requestAnimationFrame(tick);
    };

    setDisplay(formatParsedMetric(0, parsed));
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [finalDisplay, parsed, duration, shouldSkipAnimation, active]);

  return shouldSkipAnimation ? finalDisplay : display;
}

export default useCountUpV2;
