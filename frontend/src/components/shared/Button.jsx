import React from 'react';
import { Loader2 } from 'lucide-react';

const VARIANTES = { dark: 'btn-pill-dark', ghost: 'btn-pill-ghost' };

export default function Button({
  variant = 'dark', isLoading = false, disabled = false, loadingText,
  className = '', children, type = 'button', onClick, ...rest
}) {
  const bloqueado = disabled || isLoading;
  return (
    <button
      type={type}
      className={`btn-base ${VARIANTES[variant] || ''} ${className}`.trim()}
      disabled={bloqueado}
      aria-busy={isLoading}
      onClick={(e) => { if (!bloqueado && onClick) onClick(e); }}
      {...rest}
    >
      {isLoading && <Loader2 size={14} className="btn-spinner" aria-hidden="true" />}
      <span>{isLoading && loadingText ? loadingText : children}</span>
    </button>
  );
}
