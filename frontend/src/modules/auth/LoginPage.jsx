import React, { useState, useEffect, useRef } from 'react';
import { ArrowRight, ShieldCheck, Sun, Moon, Eye, EyeOff, Lock } from 'lucide-react';
import { authApi } from '../../api/authApi';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { useNavigate } from 'react-router-dom';
import { sileoToast } from '../../services/sileoToast';
import { notificationService } from '../../services/notificationService';
import GiraLogo from '../../components/common/GiraLogo';
import DemoAccountsSelector from './components/DemoAccountsSelector';
import OtpInputForm from './components/OtpInputForm';
import LoginHeroPane from './components/LoginHeroPane';
import ForgotPasswordModal from './components/ForgotPasswordModal';

export default function LoginPage() {
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberDevice, setRememberDevice] = useState(true);
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [tempToken, setTempToken] = useState('');
  const [isForgotPasswordOpen, setIsForgotPasswordOpen] = useState(false);
  
  const [error, setError] = useState('');
  const [isLocked, setIsLocked] = useState(false);
  const [lockTimeLeft, setLockTimeLeft] = useState(0);
  
  const [otpTimeLeft, setOtpTimeLeft] = useState(300); // 5 mins
  const [resendCooldown, setResendCooldown] = useState(60);
  const [isLoading, setIsLoading] = useState(false);
  
  const { login } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const otpRefs = useRef([]);

  // Dynamic greeting based on time of day and returning status
  const getGreetingData = () => {
    const todayStr = new Date().toISOString().split('T')[0];
    const lastLoginDate = localStorage.getItem('gira_last_login_date');
    const isFirstVisitToday = lastLoginDate !== todayStr;
    const hour = new Date().getHours();

    let timeSalutation = 'Bienvenido';
    if (hour >= 5 && hour < 12) {
      timeSalutation = 'Buenos días';
    } else if (hour >= 12 && hour < 19) {
      timeSalutation = 'Buenas tardes';
    } else {
      timeSalutation = 'Buenas noches';
    }

    if (isFirstVisitToday) {
      return {
        prefix: `${timeSalutation}, bienvenido`,
        title: 'al Sistema BI',
        subtitle: 'Ingrese sus credenciales institucionales para acceder a los tableros de control y gobierno de datos.'
      };
    } else {
      return {
        prefix: `${timeSalutation}, bienvenido de vuelta`,
        title: 'al Sistema BI',
        subtitle: 'Retoma tus tareas de auditoría de calidad, control de retención o análisis financiero.'
      };
    }
  };

  const greeting = getGreetingData();

  // Lockout timer
  useEffect(() => {
    let timer;
    if (isLocked && lockTimeLeft > 0) {
      timer = setInterval(() => setLockTimeLeft(prev => prev - 1), 1000);
    } else if (isLocked && lockTimeLeft <= 0) {
      setIsLocked(false);
      setError('');
    }
    return () => clearInterval(timer);
  }, [isLocked, lockTimeLeft]);

  // OTP expiration timer
  useEffect(() => {
    let timer;
    if (step === 2 && otpTimeLeft > 0) {
      timer = setInterval(() => setOtpTimeLeft(prev => prev - 1), 1000);
    }
    return () => clearInterval(timer);
  }, [step, otpTimeLeft]);

  // Resend cooldown timer
  useEffect(() => {
    let timer;
    if (step === 2 && resendCooldown > 0) {
      timer = setInterval(() => setResendCooldown(prev => prev - 1), 1000);
    }
    return () => clearInterval(timer);
  }, [step, resendCooldown]);

  const handleStep1Submit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const normalizedEmail = email.trim().toLowerCase();
      const savedDeviceToken = localStorage.getItem(`gira_trusted_device_${normalizedEmail}`) || localStorage.getItem(`gira_trusted_device_${email}`);
      const res = await authApi.loginStep1(email, password, savedDeviceToken, rememberDevice);

      // Si el dispositivo ya es de confianza para esta cuenta, ingresa directamente
      if (res.mfa_required === false && res.access_token) {
        if (res.device_token) {
          localStorage.setItem(`gira_trusted_device_${normalizedEmail}`, res.device_token);
          localStorage.setItem(`gira_trusted_device_${email}`, res.device_token);
        }
        const todayStr = new Date().toISOString().split('T')[0];
        localStorage.setItem('gira_last_login_date', todayStr);
        notificationService.notifyPendingOnLogin(res.user.role, navigate);
        login(res.user, res.access_token);
        navigate('/');
        return;
      }

      // Si requiere doble factor (primera vez o cuenta distinta)
      setTempToken(res.temp_token);
      setOtp(['', '', '', '', '', '']);
      setStep(2);
      setOtpTimeLeft(300);
      setResendCooldown(60);
      setTimeout(() => otpRefs.current[0]?.focus(), 100);
    } catch (err) {
      sileoToast.error({
        title: 'Acceso Denegado',
        description: 'Credenciales inválidas o cuenta bloqueada por exceso de intentos.'
      });
      if (err.response?.status === 423) {
        setIsLocked(true);
        setLockTimeLeft(300);
        setError('Cuenta bloqueada temporalmente por exceso de intentos fallidos (15 min).');
      } else if (err.response?.status === 401) {
        setError('Credenciales incorrectas. Verifique correo institucional y contraseña.');
      } else {
        setError('Error al comunicarse con el servidor. Intente nuevamente.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleOtpPaste = (e) => {
    e.preventDefault();
    const clipboardText = e.clipboardData?.getData('text') || '';
    const cleanDigits = clipboardText.replace(/\D/g, '').slice(0, 6);
    if (!cleanDigits) return;

    const newOtp = ['', '', '', '', '', ''];
    for (let i = 0; i < cleanDigits.length; i++) {
      newOtp[i] = cleanDigits[i];
    }
    setOtp(newOtp);

    const targetFocus = Math.min(cleanDigits.length, 5);
    otpRefs.current[targetFocus]?.focus();
  };

  const handleOtpChange = (index, value) => {
    const cleanDigits = value.replace(/\D/g, '');
    if (cleanDigits.length > 1) {
      const newOtp = [...otp];
      for (let i = 0; i < cleanDigits.length && (index + i) < 6; i++) {
        newOtp[index + i] = cleanDigits[i];
      }
      setOtp(newOtp);
      const nextFocus = Math.min(index + cleanDigits.length, 5);
      otpRefs.current[nextFocus]?.focus();
      return;
    }

    if (!/^\d*$/.test(value)) return;
    
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    if (value && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
  };

  const handleStep2Submit = async (e) => {
    e.preventDefault();
    const code = otp.join('');
    if (code.length !== 6) {
      setError('Por favor, ingrese el código completo de 6 dígitos.');
      return;
    }

    setError('');
    setIsLoading(true);

    try {
      const res = await authApi.verifyOTP(tempToken, code, rememberDevice);
      sileoToast.icon({
        title: 'Identidad Verificada',
        description: 'Código 2FA validado mediante canal seguro.',
        icon: <ShieldCheck size={16} color="#60a5fa" />
      });
      if (res.device_token) {
        const normalizedEmail = email.trim().toLowerCase();
        localStorage.setItem(`gira_trusted_device_${normalizedEmail}`, res.device_token);
        localStorage.setItem(`gira_trusted_device_${email}`, res.device_token);
      }
      const todayStr = new Date().toISOString().split('T')[0];
      localStorage.setItem('gira_last_login_date', todayStr);

      const token = res.access_token || res.token;
      notificationService.notifyPendingOnLogin(res.user.role, navigate);
      login(res.user, token);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Código OTP inválido o expirado.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0) return;
    setIsLoading(true);
    try {
      await authApi.resendOTP(tempToken);
      setResendCooldown(60);
      setOtpTimeLeft(300);
      setError('');
    } catch (err) {
      setError('Error al reenviar el código. Intente nuevamente en unos instantes.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSelectAccount = (selectedEmail, selectedPassword) => {
    setEmail(selectedEmail);
    setPassword(selectedPassword);
    setError('');
    if (step === 2) {
      setStep(1);
    }
  };

  return (
    <div className="view-content-layer">
      <section className="login-split-grid">
        {/* ── Panel Izquierdo: Formulario Institucional ──────────────── */}
        <div
          className="login-left-pane"
          style={{
            padding: 'clamp(28px, 5vw, 64px)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            alignItems: 'center',
            minHeight: '100vh',
            zIndex: 2,
            overflowY: 'auto',
          }}
        >
          {/* Header Superior con Logo Institucional y Conmutador de Modo Oscuro */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              width: '100%',
              maxWidth: '440px',
              gap: '12px',
            }}
          >
            <GiraLogo size={44} showText={true} />
            <button
              type="button"
              onClick={toggleTheme}
              className="btn-pill-ghost"
              style={{
                padding: '7px 14px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '7px',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--color-ink-black)',
                border: '1px solid var(--color-border)',
                borderRadius: '9999px',
                cursor: 'pointer',
                backgroundColor: 'var(--color-paper-white)',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-mist-gray)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-paper-white)'; }}
              title={theme === 'dark' ? 'Cambiar a Modo Claro' : 'Cambiar a Modo Oscuro'}
              aria-label="Conmutador de Tema Claro u Oscuro"
            >
              {theme === 'dark' ? (
                <>
                  <Sun size={15} color="var(--color-sienna-brown, #F1B844)" />
                  <span>Claro</span>
                </>
              ) : (
                <>
                  <Moon size={15} color="var(--color-ink-black)" />
                  <span>Oscuro</span>
                </>
              )}
            </button>
          </div>

          {/* Área Central: Saludo Institucional y Formulario Limpio */}
          <div style={{ maxWidth: '440px', width: '100%', margin: '28px 0' }}>
            <span
              style={{
                fontSize: '12px',
                textTransform: 'uppercase',
                letterSpacing: '1.2px',
                color: 'var(--color-slate-gray)',
                fontWeight: 600,
              }}
            >
              Plataforma Institucional
            </span>

            <h1
              className="serif-display"
              style={{
                fontSize: 'clamp(32px, 3.6vw, 44px)',
                margin: '8px 0 14px 0',
                lineHeight: 1.15,
                color: 'var(--color-ink-black)',
              }}
            >
              {greeting.prefix} <span style={{ display: 'block' }}>{greeting.title}</span>
            </h1>

            <p
              style={{
                color: 'var(--color-slate-gray)',
                fontSize: '14.5px',
                marginBottom: '26px',
                lineHeight: 1.5,
              }}
            >
              {step === 1 ? greeting.subtitle : 'Ingresa el código de 6 dígitos emitido por el sistema para tu cuenta institucional.'}
            </p>

            {error && (
              <div
                style={{
                  marginBottom: '20px',
                  padding: '14px 18px',
                  borderRadius: 'var(--radius-inputs, 16px)',
                  backgroundColor: 'rgba(217, 56, 58, 0.12)',
                  border: '1px solid rgba(217, 56, 58, 0.28)',
                  color: 'var(--color-alert-red, #d9383a)',
                  fontSize: '13.5px',
                }}
              >
                <p style={{ fontWeight: 500 }}>{error}</p>
                {isLocked && (
                  <p style={{ marginTop: '6px', fontFamily: 'var(--font-mono)', fontSize: '12.5px' }}>
                    Tiempo de espera: {formatTime(lockTimeLeft)}
                  </p>
                )}
              </div>
            )}

            {step === 1 ? (
              <form onSubmit={handleStep1Submit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                <div>
                  <label
                    htmlFor="login-email"
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
                  <input
                    id="login-email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="usuario@giragroup.bo"
                    className="form-input"
                    autoComplete="username"
                    disabled={isLocked || isLoading}
                    style={{ width: '100%' }}
                  />
                </div>

                <div>
                  <label
                    htmlFor="login-password"
                    style={{
                      display: 'block',
                      fontSize: '13px',
                      fontWeight: 500,
                      marginBottom: '6px',
                      color: 'var(--color-ink-black)',
                    }}
                  >
                    Contraseña de Acceso
                  </label>
                  <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                    <input
                      id="login-password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••••••"
                      className="form-input"
                      autoComplete="current-password"
                      disabled={isLocked || isLoading}
                      style={{ paddingRight: '44px', width: '100%' }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((prev) => !prev)}
                      disabled={isLocked || isLoading}
                      style={{
                        position: 'absolute',
                        right: '10px',
                        background: 'none',
                        border: 'none',
                        padding: '6px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--color-slate-gray)',
                        cursor: isLocked || isLoading ? 'not-allowed' : 'pointer',
                        borderRadius: '6px',
                        transition: 'color 0.2s, background-color 0.2s',
                      }}
                      onMouseEnter={(e) => {
                        if (!isLocked && !isLoading) {
                          e.currentTarget.style.color = 'var(--color-ink-black)';
                          e.currentTarget.style.backgroundColor = 'var(--color-mist-gray)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.color = 'var(--color-slate-gray)';
                        e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                      title={showPassword ? 'Ocultar contraseña' : 'Ver contraseña'}
                      aria-label={showPassword ? 'Ocultar contraseña' : 'Ver contraseña'}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: '13px',
                  }}
                >
                  <label
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      color: 'var(--color-slate-gray)',
                      cursor: 'pointer',
                    }}
                  >
                    <input 
                      type="checkbox" 
                      checked={rememberDevice}
                      onChange={(e) => setRememberDevice(e.target.checked)}
                      style={{
                        accentColor: 'var(--color-gira-gold, #D99B26)',
                        width: '16px',
                        height: '16px',
                        cursor: 'pointer',
                      }} 
                    />
                    <span>Recordar este equipo</span>
                  </label>

                  <a 
                    href="#forgot" 
                    onClick={(e) => {
                      e.preventDefault();
                      setIsForgotPasswordOpen(true);
                    }}
                    style={{
                      color: 'var(--color-slate-gray)',
                      textDecoration: 'none',
                      fontSize: '13px',
                      fontWeight: 500,
                      cursor: 'pointer',
                      transition: 'color 0.2s',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-sienna-brown, #D99B26)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--color-slate-gray)'; }}
                  >
                    ¿Olvidó su clave?
                  </a>
                </div>

                <button
                  type="submit"
                  disabled={isLocked || isLoading || !email || !password}
                  className="btn-pill-dark"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    width: '100%',
                    padding: '13px 24px',
                    marginTop: '6px',
                    fontSize: '15px',
                    cursor: isLocked || isLoading || !email || !password ? 'not-allowed' : 'pointer',
                    opacity: isLocked || isLoading || !email || !password ? 0.6 : 1,
                  }}
                >
                  {isLoading ? 'Verificando credenciales...' : 'Iniciar sesión'}
                  {!isLoading && <ArrowRight size={16} />}
                </button>
              </form>
            ) : (
              <OtpInputForm
                email={email}
                otp={otp}
                onOtpChange={handleOtpChange}
                onOtpKeyDown={handleOtpKeyDown}
                onOtpPaste={handleOtpPaste}
                otpRefs={otpRefs}
                onSubmit={handleStep2Submit}
                onBack={() => setStep(1)}
                otpTimeLeft={otpTimeLeft}
                resendCooldown={resendCooldown}
                onResend={handleResend}
                isLoading={isLoading}
                formatTime={formatTime}
                rememberDevice={rememberDevice}
                onRememberDeviceChange={setRememberDevice}
              />
            )}
          </div>

          {/* ── Pie de Página y Auditoría de Seguridad al Fondo Absoluto ──────────────── */}
          <div style={{ marginTop: '24px', width: '100%', maxWidth: '440px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '11.5px',
                color: 'var(--color-slate-gray)',
                marginBottom: '6px',
              }}
            >
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                <Lock size={12} color="var(--color-sienna-brown, #D99B26)" />
                Conexión Segura TLS 1.3 · SHA-256
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                Versión v1.0.4 · Docker Cloud
              </span>
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '11.5px',
                color: 'var(--color-ash-gray)',
                paddingBottom: '10px',
                borderBottom: '1px solid var(--color-border)',
              }}
            >
              <span>© 2026 GIRAGROUP S.A. Todos los derechos reservados.</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--color-alert-green, #22c55e)',
                    boxShadow: '0 0 6px rgba(34, 197, 94, 0.45)',
                  }}
                />
                Servicios Operativos
              </span>
            </div>

            {/* [▾] Rol de Acceso (Validado) Acordeón al Fondo Absoluto */}
            {/* Cuentas de demostración solo en desarrollo: nunca en el build de producción */}
            {import.meta.env.DEV && (
              <DemoAccountsSelector
                currentEmail={email}
                onSelectAccount={handleSelectAccount}
                defaultOpen={false}
              />
            )}
          </div>
        </div>

        {/* ── Panel Derecho Hero con Cards Animadas y Repulsión Confinada (Modular) ─────── */}
        <LoginHeroPane />
      </section>

      {/* Modal Institucional ¿Olvidó su clave? */}
      <ForgotPasswordModal
        isOpen={isForgotPasswordOpen}
        onClose={() => setIsForgotPasswordOpen(false)}
        initialEmail={email}
      />
    </div>
  );
}
