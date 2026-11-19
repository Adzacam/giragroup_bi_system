import React, { useState, useEffect } from 'react';
import { ArrowLeft, ArrowRight, Loader2 } from 'lucide-react';

export default function OtpInputForm({
  email,
  otp,
  onOtpChange,
  onOtpKeyDown,
  onOtpPaste,
  otpRefs,
  onSubmit,
  onBack,
  otpTimeLeft,
  resendCooldown,
  onResend,
  isLoading,
  formatTime,
  rememberDevice = true,
  onRememberDeviceChange,
  error = '',
  isEnteringSystem = false,
}) {
  const [pulsedIndex, setPulsedIndex] = useState(null);

  useEffect(() => {
    if (pulsedIndex === null) return undefined;
    const t = setTimeout(() => setPulsedIndex(null), 240);
    return () => clearTimeout(t);
  }, [pulsedIndex]);

  const handleDigitChange = (index, value) => {
    if (/^\d$/.test(value)) {
      setPulsedIndex(index);
    }
    onOtpChange(index, value);
  };

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
            padding: '4px',
            borderRadius: '6px',
            transition: 'background-color 0.2s',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-mist-gray)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
          title="Volver al inicio de sesión"
          aria-label="Volver al inicio de sesión"
        >
          <ArrowLeft size={16} />
        </button>
        <span>Verificación 2FA para <strong style={{ color: 'var(--color-ink-black)' }}>{email}</strong></span>
      </div>

      <div className={`v2-otp-grid${error ? ' has-error' : ''}`}>
        {otp.map((digit, i) => (
          <input
            key={i}
            ref={(el) => (otpRefs.current[i] = el)}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={digit}
            aria-label={`Dígito OTP ${i + 1}`}
            className={`v2-otp-box${pulsedIndex === i ? ' is-pulsing' : ''}`}
            data-filled={digit ? 'true' : 'false'}
            onChange={(e) => handleDigitChange(i, e.target.value)}
            onKeyDown={(e) => onOtpKeyDown(i, e)}
            onPaste={onOtpPaste}
            onFocus={(e) => {
              e.target.style.borderColor = 'var(--color-gira-gold, #D99B26)';
              e.target.style.boxShadow = '0 0 0 3px rgba(217, 155, 38, 0.2)';
            }}
            onBlur={(e) => {
              e.target.style.boxShadow = 'none';
              if (!digit) e.target.style.borderColor = 'var(--color-border)';
            }}
            style={{
              '--otp-idx': i,
              width: '52px',
              height: '60px',
              textAlign: 'center',
              fontSize: '26px',
              fontFamily: 'var(--font-mono)',
              borderRadius: 'var(--radius-inputs, 16px)',
              border: digit ? '1.5px solid var(--color-gira-gold, #D99B26)' : '1px solid var(--color-border)',
              background: 'var(--color-fog-white)',
              color: 'var(--color-ink-black)',
              outline: 'none',
            }}
            disabled={isLoading || otpTimeLeft <= 0 || isEnteringSystem}
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
          disabled={resendCooldown > 0 || isLoading || isEnteringSystem}
          style={{
            background: 'none',
            border: 'none',
            color: resendCooldown > 0 ? 'var(--color-ash-gray)' : 'var(--color-sienna-brown, #D99B26)',
            cursor: resendCooldown > 0 ? 'not-allowed' : 'pointer',
            textDecoration: 'underline',
            fontSize: '12.5px',
            fontWeight: 500,
          }}
        >
          {resendCooldown > 0 ? `Reenviar en ${resendCooldown}s` : 'Reenviar código'}
        </button>
      </div>

      <label
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '13px',
          color: 'var(--color-slate-gray)',
          cursor: 'pointer',
          userSelect: 'none',
          marginTop: '-6px',
        }}
      >
        <input
          type="checkbox"
          checked={rememberDevice}
          onChange={(e) => onRememberDeviceChange?.(e.target.checked)}
          style={{
            accentColor: 'var(--color-gira-gold, #D99B26)',
            width: '16px',
            height: '16px',
            cursor: 'pointer',
          }}
        />
        <span>Recordar este equipo por 30 días</span>
      </label>

      <div
        style={{
          backgroundColor: 'rgba(217, 155, 38, 0.08)',
          border: '1px solid rgba(217, 155, 38, 0.25)',
          borderRadius: '10px',
          padding: '10px 14px',
          fontSize: '12px',
          color: 'var(--color-slate-gray)',
          lineHeight: 1.45,
        }}
      >
        📩 Si no visualizas el correo en tu bandeja principal, por favor revisa tu carpeta de <strong>Spam</strong> o <strong>Correo no deseado</strong>.
      </div>

      <button
        type="submit"
        disabled={isLoading || isEnteringSystem || otp.some((d) => !d) || otpTimeLeft <= 0}
        className={`btn-pill-dark v2-login-submit-btn${isEnteringSystem ? ' is-entering' : ''}`}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          width: '100%',
          padding: '13px 24px',
          fontSize: '15px',
          cursor: isLoading || isEnteringSystem || otp.some((d) => !d) || otpTimeLeft <= 0 ? 'not-allowed' : 'pointer',
          opacity: isLoading || otp.some((d) => !d) || otpTimeLeft <= 0 ? 0.6 : 1,
        }}
      >
        {isEnteringSystem ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            <span>Entrando al sistema...</span>
          </>
        ) : isLoading ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            <span>Comprobando OTP...</span>
          </>
        ) : (
          <>
            <span>Verificar e Ingresar</span>
            <ArrowRight size={16} />
          </>
        )}
      </button>
    </form>
  );
}
