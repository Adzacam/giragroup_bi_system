import React, { useState, useEffect, useRef } from 'react';
import { ArrowRight, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { authApi } from '../../api/authApi';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const GiraLogo = () => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
    <svg 
      width="46" 
      height="46" 
      viewBox="0 0 100 100" 
      fill="none" 
      style={{
        borderRadius: '12px',
        background: '#0c2340',
        padding: '6px',
        boxShadow: '0 4px 12px rgba(12, 35, 64, 0.2)'
      }}
    >
      <path 
        d="M 50 18 L 74 42 C 77 45, 77 51, 74 54 L 54 74 C 51 77, 45 77, 42 74 L 26 58 C 23 55, 23 49, 26 46 L 44 28 C 46 26, 49 26, 51 28 L 56 33 C 57 34, 57 36, 56 37 L 42 51 C 41 52, 41 54, 42 55 L 48 61 C 49 62, 51 62, 52 61 L 63 50 C 64 49, 64 47, 63 46 L 46 29" 
        stroke="#ffffff" 
        strokeWidth="9" 
        strokeLinecap="round" 
        strokeLinejoin="round"
      />
      <text 
        x="50" 
        y="93" 
        textAnchor="middle" 
        fill="#d99b26" 
        fontFamily="'Inter', sans-serif" 
        fontSize="14" 
        fontWeight="700" 
        letterSpacing="1.5"
      >
        Group
      </text>
    </svg>
    <div>
      <div style={{ fontWeight: 700, letterSpacing: '1.5px', fontSize: '15px', color: 'var(--color-ink-black)' }}>
        GIRAGROUP
      </div>
      <div style={{ fontSize: '11px', color: 'var(--color-slate-gray)', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
        BI &amp; Analytics Governance
      </div>
    </div>
  </div>
);

const DEMO_ACCOUNTS = [
  { label: 'Administrador del Sistema', email: 'admin.general@giragroup.bo', role: 'ADMIN' },
  { label: 'Auditor de Calidad (DataOps)', email: 'auditor.dataops@giragroup.bo', role: 'AUDITOR_CALIDAD' },
  { label: 'Director Académico', email: 'direccion.academica@giragroup.bo', role: 'DIRECTOR_ACADEMICO' },
  { label: 'Analista Financiero', email: 'analista.finanzas@giragroup.bo', role: 'ANALISTA_FINANCIERO' },
];

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

  // Hero card repulsion and interactive background
  const heroRef = useRef(null);
  const card1Ref = useRef(null);
  const card2Ref = useRef(null);
  const [card1Offset, setCard1Offset] = useState({ x: 0, y: 0 });
  const [card2Offset, setCard2Offset] = useState({ x: 0, y: 0 });
  const [mousePos, setMousePos] = useState({ x: 340, y: 260 });

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

  // Mouse repulsion physics
  const handleHeroMouseMove = (e) => {
    if (!heroRef.current) return;
    const rect = heroRef.current.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    setMousePos({ x: mx, y: my });

    if (card1Ref.current) {
      const c1Rect = card1Ref.current.getBoundingClientRect();
      const c1x = c1Rect.left - rect.left + c1Rect.width / 2;
      const c1y = c1Rect.top - rect.top + c1Rect.height / 2;
      const dist1 = Math.hypot(mx - c1x, my - c1y);
      if (dist1 < 160) {
        const force = (160 - dist1) / 160;
        const angle = Math.atan2(c1y - my, c1x - mx);
        const ox = Math.max(-30, Math.min(30, Math.cos(angle) * force * 35));
        const oy = Math.max(-25, Math.min(25, Math.sin(angle) * force * 30));
        setCard1Offset({ x: ox, y: oy });
      } else {
        setCard1Offset({ x: 0, y: 0 });
      }
    }

    if (card2Ref.current) {
      const c2Rect = card2Ref.current.getBoundingClientRect();
      const c2x = c2Rect.left - rect.left + c2Rect.width / 2;
      const c2y = c2Rect.top - rect.top + c2Rect.height / 2;
      const dist2 = Math.hypot(mx - c2x, my - c2y);
      if (dist2 < 160) {
        const force = (160 - dist2) / 160;
        const angle = Math.atan2(c2y - my, c2x - mx);
        const ox = Math.max(-30, Math.min(30, Math.cos(angle) * force * 35));
        const oy = Math.max(-25, Math.min(25, Math.sin(angle) * force * 30));
        setCard2Offset({ x: ox, y: oy });
      } else {
        setCard2Offset({ x: 0, y: 0 });
      }
    }
  };

  const handleHeroMouseLeave = () => {
    setCard1Offset({ x: 0, y: 0 });
    setCard2Offset({ x: 0, y: 0 });
  };

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

  return (
    <div className="view-content-layer">
      <section className="login-split-grid">
        {/* ── Panel Izquierdo: Formulario Institucional ──────────────── */}
        <div style={{
          padding: 'clamp(32px, 6vw, 80px)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          zIndex: 2,
          background: 'rgba(255, 255, 255, 0.85)',
          backdropFilter: 'blur(12px)',
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
                backgroundColor: '#fef2f2',
                border: '1px solid #fecaca',
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
              <form onSubmit={handleStep2Submit} style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13.5px', color: 'var(--color-slate-gray)' }}>
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      color: 'var(--color-ink-black)',
                    }}
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
                      onChange={(e) => handleOtpChange(i, e.target.value)}
                      onKeyDown={(e) => handleOtpKeyDown(i, e)}
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
                    />
                  ))}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12.5px', color: 'var(--color-slate-gray)' }}>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>
                    {otpTimeLeft > 0 ? `Válido por: ${formatTime(otpTimeLeft)}` : 'Código expirado'}
                  </span>
                  <button
                    type="button"
                    onClick={handleResend}
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
            )}

            {/* ── Demo Accounts Quick Selector (Collapsible) ── */}
            <div style={{ marginTop: '32px', paddingTop: '20px', borderTop: '1px solid var(--color-border)' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-slate-gray)', fontWeight: 600, marginBottom: '10px' }}>
                Acceso Rápido de Demostración
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                {DEMO_ACCOUNTS.map((account) => (
                  <button
                    key={account.email}
                    type="button"
                    onClick={() => {
                      setEmail(account.email);
                      setPassword('giragroup2026');
                      setError('');
                    }}
                    style={{
                      padding: '8px 10px',
                      borderRadius: '10px',
                      border: email === account.email ? '1px solid var(--color-ink-black)' : '1px solid var(--color-border)',
                      background: email === account.email ? 'var(--color-mist-gray)' : 'var(--color-paper-white)',
                      textAlign: 'left',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                  >
                    <div style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--color-ink-black)' }}>{account.label}</div>
                    <div style={{ fontSize: '10px', color: 'var(--color-slate-gray)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{account.email}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div style={{ fontSize: '12px', color: 'var(--color-ash-gray)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>© 2026 GIRAGROUP S.A. Todos los derechos reservados.</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: 'var(--color-alert-green)' }} />
              Servicios Operativos
            </span>
          </div>
        </div>

        {/* ── Panel Derecho Hero con Cards Animadas y Repulsión Confinada ──────────────── */}
        <div 
          ref={heroRef}
          onMouseMove={handleHeroMouseMove}
          onMouseLeave={handleHeroMouseLeave}
          className="login-hero-pane" 
          style={{
            background: 'rgba(250, 250, 251, 0.65)',
            borderLeft: '1px solid var(--color-border)',
            padding: '60px 48px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            position: 'relative',
            overflow: 'hidden',
            backdropFilter: 'blur(10px)',
          }}
        >
          {/* Radial Peach Gradient Ambient Glow sensible al movimiento del mouse */}
          <div style={{
            position: 'absolute',
            left: `${mousePos.x - 300}px`,
            top: `${mousePos.y - 300}px`,
            width: '600px',
            height: '600px',
            background: 'radial-gradient(circle, rgba(251, 225, 209, 0.75) 0%, rgba(254, 238, 227, 0.4) 40%, rgba(250, 250, 251, 0) 75%)',
            pointerEvents: 'none',
            transition: 'left 0.12s ease-out, top 0.12s ease-out',
          }} />

          {/* Floating Card 1: Inferencia NLP */}
          <div 
            ref={card1Ref}
            className="floating-artifact kinetic-card in-view ambient-float-a"
            style={{
              padding: '24px 28px',
              maxWidth: '440px',
              marginBottom: '24px',
              zIndex: 2,
              boxShadow: 'var(--shadow-artifact)',
              transform: `translate3d(${card1Offset.x}px, ${card1Offset.y}px, 0)`,
              transition: 'transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <span style={{
                fontSize: '11px',
                textTransform: 'uppercase',
                fontWeight: 600,
                color: 'var(--color-ash-gray)',
                letterSpacing: '0.8px',
              }}>
                Inferencia NLP en Tiempo Real
              </span>
              <span style={{
                fontSize: '12px',
                color: 'var(--color-sienna-brown)',
                background: 'var(--color-blush-peach)',
                padding: '3px 10px',
                borderRadius: '9999px',
                fontWeight: 600,
              }}>
                BETO v2.4
              </span>
            </div>
            <div style={{
              fontFamily: 'var(--font-signifier)',
              fontSize: '22px',
              lineHeight: 1.3,
              color: 'var(--color-ink-black)',
            }}>
              "Doble validación de confianza: Extracción NER + RapidFuzz Cross-Source."
            </div>
            <div style={{
              marginTop: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '13px',
              color: 'var(--color-alert-green)',
            }}>
              <CheckCircle2 size={16} />
              <span>Alineado a Doctrina Kimball (Sin ambigüedades)</span>
            </div>
          </div>

          {/* Floating Card 2: Disparador Campo Crítico */}
          <div 
            ref={card2Ref}
            className="card-peach-accent kinetic-card in-view ambient-float-b"
            style={{
              maxWidth: '460px',
              marginLeft: '28px',
              boxShadow: '0 18px 40px rgba(93, 42, 26, 0.08)',
              zIndex: 3,
              transform: `translate3d(${card2Offset.x}px, ${card2Offset.y}px, 0)`,
              transition: 'transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease',
            }}
          >
            <span style={{
              fontSize: '11px',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.9px',
            }}>
              Disparador de Integridad de Datos
            </span>
            <h3 className="serif-heading" style={{ fontSize: '24px', margin: '8px 0 12px 0' }}>
              Si falta la Cédula de Identidad en cualquier fuente, la regla de validación fuerza revisión visual inmediata.
            </h3>
            <p style={{ fontSize: '13.5px', opacity: 0.9, lineHeight: 1.5 }}>
              Garantía de integridad referencial para las dimensiones de alumnos y docentes en PostgreSQL.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
