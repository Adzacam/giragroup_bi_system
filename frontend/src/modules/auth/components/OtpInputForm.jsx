import React from 'react';
import { ArrowLeft, ArrowRight } from 'lucide-react';

export default function OtpInputForm({
  email,
  otp,
  onOtpChange,
  onOtpKeyDown,
  otpRefs,
  onSubmit,
  onBack,
  otpTimeLeft,
  resendCooldown,
  onResend,
  isLoading,
  formatTime,
}) {
  return (
    <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13.5px', color: 'var(--color-slate-gray)' }}>
        <button
          type="button"
          onClick={onBack}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            color: 'var(--color-ink-black)',
          }}
          title="Regresar a credenciales"
        >
          <ArrowLeft size={16} />
        </button>
        <span>Verificación 2FA para <strong>{email}</strong></span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
        {otp.map((digit, i) => (
          <input
            key={i}
            ref={(el) => (otpRefs.current[i] = el)}
            type="text"
            maxLength={1}
            value={digit}
            onChange={(e) => onOtpChange(i, e.target.value)}
            onKeyDown={(e) => onOtpKeyDown(i, e)}
            style={{
              width: '52px',
              height: '60px',
              textAlign: 'center',
              fontSize: '26px',
              fontFamily: 'var(--font-mono)',
              borderRadius: 'var(--radius-inputs)',
              border: '1px solid var(--color-border)',
              background: 'var(--color-fog-white)',
              outline: 'none',
            }}
            disabled={isLoading || otpTimeLeft <= 0}
            autoFocus={i === 0}
          />
        ))}
      </div>

      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '12.5px',
        color: 'var(--color-slate-gray)'
      }}>
        <span style={{ fontFamily: 'var(--font-mono)' }}>
          {otpTimeLeft > 0 ? `Válido por: ${formatTime(otpTimeLeft)}` : 'Código expirado'}
        </span>
        <button
          type="button"
          onClick={onResend}
          disabled={resendCooldown > 0 || isLoading}
          style={{
            background: 'none',
            border: 'none',
            color: resendCooldown > 0 ? 'var(--color-ash-gray)' : 'var(--color-ink-black)',
            cursor: resendCooldown > 0 ? 'not-allowed' : 'pointer',
            textDecoration: 'underline',
            fontSize: '12.5px',
          }}
        >
          {resendCooldown > 0 ? `Reenviar en ${resendCooldown}s` : 'Reenviar código'}
        </button>
      </div>

      <button
        type="submit"
        disabled={isLoading || otp.some((d) => !d) || otpTimeLeft <= 0}
        className="btn-pill-dark"
        style={{
          justifyContent: 'center',
          padding: '13px 24px',
          fontSize: '15px',
          opacity: isLoading || otp.some((d) => !d) || otpTimeLeft <= 0 ? 0.6 : 1,
        }}
      >
        {isLoading ? 'Comprobando OTP...' : 'Verificar y Acceder'}
        {!isLoading && <ArrowRight size={16} />}
      </button>
    </form>
  );
}
