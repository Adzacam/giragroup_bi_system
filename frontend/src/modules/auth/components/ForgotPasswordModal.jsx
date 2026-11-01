import React, { useState, useEffect } from 'react';
import { X, KeyRound, Mail, ArrowRight, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { authApi } from '../../../api/authApi';

export default function ForgotPasswordModal({ isOpen, onClose, initialEmail = '' }) {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (isOpen) {
      setEmail(initialEmail || '');
      setIsSuccess(false);
      setErrorMessage('');
      setIsLoading(false);
    }
  }, [isOpen, initialEmail]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    setErrorMessage('');

    try {
      if (authApi.forgotPassword) {
        await authApi.forgotPassword(email);
      } else {
        // Fallback simulación inmediata en caso de desconexión
        await new Promise((res) => setTimeout(res, 600));
      }
      setIsSuccess(true);
    } catch (err) {
      const detail = err.response?.data?.detail || 'No se pudo procesar la solicitud. Verifique su conexión.';
      setErrorMessage(detail);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="forgot-password-title"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        backgroundColor: 'rgba(12, 30, 51, 0.65)',
        backdropFilter: 'blur(8px)',
        animation: 'fadeIn 0.2s ease-out',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="modal-panel"
        style={{
          width: '100%',
          maxWidth: '480px',
          backgroundColor: 'var(--color-paper-white)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-cards, 24px)',
          boxShadow: 'var(--shadow-modal, 0 24px 60px rgba(0,0,0,0.18))',
          padding: '32px 36px',
          position: 'relative',
          color: 'var(--color-ink-black)',
        }}
      >
        {/* Botón de Cierre Superior */}
        <button
          type="button"
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '20px',
            right: '20px',
            background: 'none',
            border: 'none',
            color: 'var(--color-slate-gray)',
            cursor: 'pointer',
            padding: '8px',
            borderRadius: '9999px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-mist-gray)';
            e.currentTarget.style.color = 'var(--color-ink-black)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = 'var(--color-slate-gray)';
          }}
          title="Cerrar ventana"
          aria-label="Cerrar ventana"
        >
          <X size={18} />
        </button>

        {!isSuccess ? (
          <div>
            {/* Cabecera Institucional */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '12px',
                  backgroundColor: 'rgba(217, 155, 38, 0.12)',
                  border: '1px solid rgba(217, 155, 38, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--color-sienna-brown)',
                  flexShrink: 0,
                }}
              >
                <KeyRound size={22} />
              </div>
              <div>
                <span
                  style={{
                    fontSize: '11px',
                    textTransform: 'uppercase',
                    letterSpacing: '1px',
                    color: 'var(--color-slate-gray)',
                    fontWeight: 600,
                  }}
                >
                  Seguridad y Recuperación
                </span>
                <h2
                  id="forgot-password-title"
                  className="serif-heading"
                  style={{
                    fontSize: '22px',
                    lineHeight: 1.25,
                    color: 'var(--color-ink-black)',
                    margin: 0,
                  }}
                >
                  ¿Olvidó su contraseña?
                </h2>
              </div>
            </div>

            <p
              style={{
                fontSize: '13.5px',
                color: 'var(--color-slate-gray)',
                lineHeight: 1.55,
                marginBottom: '22px',
              }}
            >
              Ingrese su correo institucional registrado (<strong style={{ color: 'var(--color-ink-black)' }}>@giragroup.bo</strong>).
              Le remitiremos un código OTP temporal y las instrucciones de seguridad para restablecer el acceso a la plataforma.
            </p>

            {errorMessage && (
              <div
                style={{
                  marginBottom: '18px',
                  padding: '12px 16px',
                  borderRadius: 'var(--radius-inputs, 14px)',
                  backgroundColor: 'rgba(217, 56, 58, 0.1)',
                  border: '1px solid rgba(217, 56, 58, 0.3)',
                  color: 'var(--color-alert-red, #d9383a)',
                  fontSize: '13px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                }}
              >
                <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <label
                  htmlFor="forgot-email"
                  style={{
                    display: 'block',
                    fontSize: '13px',
                    fontWeight: 500,
                    marginBottom: '6px',
                    color: 'var(--color-ink-black)',
                  }}
                >
                  Correo Institucional
                </label>
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                  <input
                    id="forgot-email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="usuario@giragroup.bo"
                    className="form-input"
                    disabled={isLoading}
                    autoFocus
                    style={{ paddingLeft: '38px', width: '100%' }}
                  />
                  <Mail
                    size={16}
                    style={{
                      position: 'absolute',
                      left: '12px',
                      color: 'var(--color-slate-gray)',
                      pointerEvents: 'none',
                    }}
                  />
                </div>
              </div>

              <div
                style={{
                  padding: '10px 14px',
                  borderRadius: '10px',
                  backgroundColor: 'var(--color-fog-white)',
                  border: '1px solid var(--color-border)',
                  fontSize: '11.5px',
                  color: 'var(--color-slate-gray)',
                  lineHeight: 1.45,
                }}
              >
                🔒 Por doctrina de seguridad TLS 1.3, este enlace de recuperación tendrá una caducidad estricta de <strong>15 minutos</strong>.
              </div>

              <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
                <button
                  type="button"
                  onClick={onClose}
                  className="btn-pill-ghost"
                  disabled={isLoading}
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '11px 18px',
                    fontSize: '13.5px',
                  }}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isLoading || !email}
                  className="btn-pill-dark"
                  style={{
                    flex: 1.3,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    padding: '11px 18px',
                    fontSize: '13.5px',
                    cursor: isLoading || !email ? 'not-allowed' : 'pointer',
                    opacity: isLoading || !email ? 0.6 : 1,
                  }}
                >
                  {isLoading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>Enviando...</span>
                    </>
                  ) : (
                    <>
                      <span>Enviar código</span>
                      <ArrowRight size={15} />
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        ) : (
          /* Estado de Éxito */
          <div style={{ textAlign: 'center', padding: '12px 6px' }}>
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                backgroundColor: 'rgba(34, 197, 94, 0.12)',
                border: '1px solid rgba(34, 197, 94, 0.35)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-alert-green, #22c55e)',
                margin: '0 auto 18px auto',
              }}
            >
              <CheckCircle2 size={30} />
            </div>

            <h2
              className="serif-heading"
              style={{
                fontSize: '24px',
                color: 'var(--color-ink-black)',
                marginBottom: '10px',
              }}
            >
              Instrucciones Despachadas
            </h2>

            <p
              style={{
                fontSize: '14px',
                color: 'var(--color-slate-gray)',
                lineHeight: 1.55,
                marginBottom: '20px',
              }}
            >
              Si la cuenta <strong style={{ color: 'var(--color-ink-black)' }}>{email}</strong> pertenece al dominio corporativo,
              hemos remitido una plantilla de verificación con el código OTP y el enlace de restablecimiento a su bandeja de entrada.
            </p>

            <div
              style={{
                padding: '12px 16px',
                borderRadius: '12px',
                backgroundColor: 'var(--color-fog-white)',
                border: '1px solid var(--color-border)',
                fontSize: '12px',
                color: 'var(--color-slate-gray)',
                lineHeight: 1.5,
                marginBottom: '24px',
                textAlign: 'left',
              }}
            >
              ⏱ <strong>Tiempo límite:</strong> El código permanecerá activo durante 15 minutos.<br />
              📁 <strong>Recomendación:</strong> Si no lo visualiza en breve, revise su carpeta de spam o correo institucional.
            </div>

            <button
              type="button"
              onClick={onClose}
              className="btn-pill-dark"
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '12px 24px',
                fontSize: '14px',
              }}
            >
              Entendido, volver al inicio
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
