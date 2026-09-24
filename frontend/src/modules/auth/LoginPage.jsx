import React, { useState, useEffect, useRef } from 'react';
import { ArrowRight } from 'lucide-react';
import { authApi } from '../../api/authApi';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import GiraLogo from '../../components/common/GiraLogo';
import DemoAccountsSelector from './components/DemoAccountsSelector';
import OtpInputForm from './components/OtpInputForm';
import LoginHeroPane from './components/LoginHeroPane';

export default function LoginPage() {
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('giragroup2026');
  const [rememberDevice, setRememberDevice] = useState(true);
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [tempToken, setTempToken] = useState('');
  
  const [error, setError] = useState('');
  const [isLocked, setIsLocked] = useState(false);
  const [lockTimeLeft, setLockTimeLeft] = useState(0);
  
  const [otpTimeLeft, setOtpTimeLeft] = useState(300); // 5 mins
  const [resendCooldown, setResendCooldown] = useState(60);
  const [isLoading, setIsLoading] = useState(false);
  
  const { login } = useAuth();
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
        prefix: `${timeSalutation} al`,
        title: 'Sistema BI',
        subtitle: 'Ingrese sus credenciales institucionales para acceder a los tableros de control y gobierno de datos.'
      };
    } else {
      return {
        prefix: 'Bienvenido de vuelta al',
        title: 'Sistema BI',
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
      const savedDeviceToken = localStorage.getItem(`gira_trusted_device_${email}`);
      const res = await authApi.loginStep1(email, password, savedDeviceToken, rememberDevice);

      // Si el dispositivo ya es de confianza para esta cuenta, ingresa directamente
      if (res.mfa_required === false && res.access_token) {
        if (res.device_token && rememberDevice) {
          localStorage.setItem(`gira_trusted_device_${email}`, res.device_token);
        }
        const todayStr = new Date().toISOString().split('T')[0];
        localStorage.setItem('gira_last_login_date', todayStr);
        login(res.user, res.access_token);
        navigate('/');
        return;
      }

      // Si requiere doble factor (primera vez o cuenta distinta)
      setTempToken(res.temp_token);
      setStep(2);
      setOtpTimeLeft(300);
      setResendCooldown(60);
    } catch (err) {
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

  const handleOtpChange = (index, value) => {
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
      if (res.device_token && rememberDevice) {
        localStorage.setItem(`gira_trusted_device_${email}`, res.device_token);
      }
      const todayStr = new Date().toISOString().split('T')[0];
      localStorage.setItem('gira_last_login_date', todayStr);

      const token = res.access_token || res.token;
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
  };

  return (
    <div className="view-content-layer">
      <section className="login-split-grid">
        {/* ── Panel Izquierdo: Formulario Institucional ──────────────── */}
        <div className="login-left-pane" style={{
          padding: 'clamp(32px, 6vw, 80px)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          zIndex: 2,
        }}>
          <GiraLogo />

          <div style={{ maxWidth: '440px', width: '100%', margin: '36px 0' }}>
            <span style={{
              fontSize: '12px',
              textTransform: 'uppercase',
              letterSpacing: '1.2px',
              color: 'var(--color-slate-gray)',
              fontWeight: 600,
            }}>
              Plataforma Institucional
            </span>

            <h1 className="serif-display" style={{
              fontSize: 'clamp(34px, 3.8vw, 46px)',
              margin: '8px 0 16px 0',
              lineHeight: 1.15,
            }}>
              {greeting.prefix} <em>{greeting.title}</em>
            </h1>

            <p style={{
              color: 'var(--color-slate-gray)',
              fontSize: '14.5px',
              marginBottom: '28px',
              lineHeight: 1.5,
            }}>
              {step === 1 ? greeting.subtitle : 'Ingresa el código de 6 dígitos emitido por el sistema para tu cuenta institucional.'}
            </p>

            {error && (
              <div style={{
                marginBottom: '20px',
                padding: '14px 18px',
                borderRadius: 'var(--radius-inputs)',
                backgroundColor: 'rgba(217, 56, 58, 0.12)',
                border: '1px solid rgba(217, 56, 58, 0.28)',
                color: 'var(--color-alert-red)',
                fontSize: '13.5px',
              }}>
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
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                    Correo Institucional
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="usuario@giragroup.bo"
                    className="form-input"
                    disabled={isLocked || isLoading}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                    Contraseña de Acceso
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••••••"
                    className="form-input"
                    disabled={isLocked || isLoading}
                  />
                </div>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '13px',
                }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-slate-gray)', cursor: 'pointer' }}>
                    <input 
                      type="checkbox" 
                      checked={rememberDevice}
                      onChange={(e) => setRememberDevice(e.target.checked)}
                      style={{ accentColor: 'var(--color-ink-black)', width: '16px', height: '16px' }} 
                    />
                    <span>Recordar este equipo (Evitar 2FA reiterado)</span>
                  </label>
                  <a 
                    href="#forgot" 
                    onClick={(e) => { e.preventDefault(); alert('Por motivos de seguridad institucional, contacte al Administrador del Sistema para restablecer su clave.'); }}
                    style={{ color: 'var(--color-slate-gray)', textDecoration: 'none', fontSize: '13px' }}
                  >
                    ¿Olvidó su clave?
                  </a>
                </div>

                <button
                  type="submit"
                  disabled={isLocked || isLoading || !email || !password}
                  className="btn-pill-dark"
                  style={{
                    justifyContent: 'center',
                    padding: '13px 24px',
                    marginTop: '8px',
                    fontSize: '15px',
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
                otpRefs={otpRefs}
                onSubmit={handleStep2Submit}
                onBack={() => setStep(1)}
                otpTimeLeft={otpTimeLeft}
                resendCooldown={resendCooldown}
                onResend={handleResend}
                isLoading={isLoading}
                formatTime={formatTime}
              />
            )}

            {/* ── Demo Accounts Quick Selector (Modular) ── */}
            <DemoAccountsSelector 
              currentEmail={email}
              onSelectAccount={handleSelectAccount}
            />
          </div>

          <div style={{ fontSize: '12px', color: 'var(--color-ash-gray)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>© 2026 GIRAGROUP S.A. Todos los derechos reservados.</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: 'var(--color-alert-green)' }} />
              Servicios Operativos
            </span>
          </div>
        </div>

        {/* ── Panel Derecho Hero con Cards Animadas y Repulsión Confinada (Modular) ─────── */}
        <LoginHeroPane />
      </section>
    </div>
  );
}
