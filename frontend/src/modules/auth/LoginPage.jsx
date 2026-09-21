import React, { useState, useEffect, useRef } from 'react';
import { ArrowRight, ArrowLeft } from 'lucide-react';
import { authApi } from '../../api/authApi';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const GiraLogo = () => (
  <div className="w-12 h-12 rounded-[12px] bg-[#0c2340] flex items-center justify-center shadow-md mb-6">
    <svg width="24" height="24" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M 50 18 L 74 42 C 77 45 77 50 74 53 L 50 77 C 47 80 42 80 39 77 L 15 53 C 12 50 12 45 15 42 L 39 18 C 42 15 47 15 50 18 Z" fill="#ffffff" />
      <path d="M 50 35 L 62 47 C 64 49 64 52 62 54 L 50 66 C 48 68 45 68 43 66 L 31 54 C 29 52 29 49 31 47 L 43 35 C 45 33 48 33 50 35 Z" fill="#4ade80" />
    </svg>
  </div>
);

const LoginPage = () => {
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
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

  const handleDemoSelect = (e) => {
    const roles = {
      'Auditor de Calidad': 'auditor@giragroup.bo',
      'Director Académico': 'director@giragroup.bo',
      'Analista Financiero': 'analista@giragroup.bo',
      'Administrador del Sistema': 'admin@giragroup.bo'
    };
    setEmail(roles[e.target.value] || '');
    setPassword('demo123');
  };

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

  useEffect(() => {
    let timer;
    if (step === 2 && otpTimeLeft > 0) {
      timer = setInterval(() => setOtpTimeLeft(prev => prev - 1), 1000);
    }
    return () => clearInterval(timer);
  }, [step, otpTimeLeft]);

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

    if (email.includes('@giragroup.bo') && password === 'demo123') {
      login({ email, name: email.split('@')[0], role: 'Demo User' }, 'demo_token');
      navigate('/');
      return;
    }

    try {
      if (authApi && authApi.loginStep1) {
        const res = await authApi.loginStep1(email, password);
        setTempToken(res.temp_token);
        setStep(2);
        setOtpTimeLeft(300);
        setResendCooldown(60);
      } else {
        setTempToken('temp_123');
        setStep(2);
      }
    } catch (err) {
      if (err.response?.status === 423) {
        setIsLocked(true);
        setLockTimeLeft(300);
        setError('Cuenta bloqueada temporalmente por exceso de intentos fallidos');
      } else {
        setError('Credenciales incorrectas. Por favor, intente nuevamente.');
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
      otpRefs.current[index + 1].focus();
    }
  };

  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      otpRefs.current[index - 1].focus();
    }
  };

  const handleStep2Submit = async (e) => {
    e.preventDefault();
    const code = otp.join('');
    if (code.length !== 6) {
      setError('Por favor, ingrese el código completo.');
      return;
    }

    setError('');
    setIsLoading(true);

    try {
      if (authApi && authApi.verifyOTP) {
        const res = await authApi.verifyOTP(tempToken, code);
        login(res.user, res.token);
        navigate('/');
      } else {
        login({ email, name: 'Demo User' }, 'final_token');
        navigate('/');
      }
    } catch (err) {
      setError('Código inválido o expirado.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (resendCooldown > 0) return;
    setIsLoading(true);
    try {
      if (authApi && authApi.resendOTP) {
        await authApi.resendOTP(tempToken);
      }
      setResendCooldown(60);
      setOtpTimeLeft(300);
      setError('');
    } catch (err) {
      setError('Error al reenviar el código. Intente más tarde.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen flex bg-paper-white">
      <div className="flex-1 flex flex-col justify-center px-8 sm:px-12 md:px-16 lg:px-24">
        <div className="max-w-md w-full mx-auto">
          <GiraLogo />
          
          <div className="mb-8">
            <span className="text-xs font-bold text-slate-gray uppercase tracking-widest mb-2 block">
              BI & Analytics Governance
            </span>
            <span className="text-sm font-semibold text-ink-black uppercase tracking-[1.2px] mb-2 block">
              Plataforma Institucional
            </span>
            <h1 className="serif-display text-ink-black mb-4 leading-tight" style={{ fontSize: 'clamp(36px, 3.8vw, 48px)' }}>
              Bienvenido al <em>Sistema BI</em>
            </h1>
            {step === 1 ? (
              <p className="text-slate-gray text-base leading-relaxed">
                Ingrese sus credenciales institucionales para acceder a los tableros de control y reportes gerenciales.
              </p>
            ) : (
              <p className="text-slate-gray text-base leading-relaxed">
                Hemos enviado un código de verificación de 6 dígitos a su correo institucional.
              </p>
            )}
          </div>

          {error && (
            <div className={`mb-6 p-4 rounded-[16px] border ${isLocked ? 'bg-red-50 border-red-200 text-red-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
              <p className="text-sm font-medium">{error}</p>
              {isLocked && (
                <p className="text-sm mt-2 font-mono">
                  Desbloqueo en: {formatTime(lockTimeLeft)}
                </p>
              )}
            </div>
          )}

          {step === 1 ? (
            <form onSubmit={handleStep1Submit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-ink-black mb-2">Correo Institucional</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="usuario@giragroup.bo"
                  className="w-full px-4 py-3 rounded-[16px] border border-mist-gray bg-paper-white focus:outline-none focus:ring-2 focus:ring-ink-black transition-shadow form-input"
                  required
                  disabled={isLocked || isLoading}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-black mb-2">Contraseña de Acceso</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-3 rounded-[16px] border border-mist-gray bg-paper-white focus:outline-none focus:ring-2 focus:ring-ink-black transition-shadow form-input"
                  required
                  disabled={isLocked || isLoading}
                />
              </div>
              
              <div className="flex items-center justify-between">
                <label className="flex items-center">
                  <input type="checkbox" className="w-4 h-4 rounded border-mist-gray text-ink-black focus:ring-ink-black" />
                  <span className="ml-2 text-sm text-slate-gray">Mantener sesión</span>
                </label>
                <a href="#" className="text-sm font-medium text-ink-black hover:underline">
                  ¿Olvidó su clave?
                </a>
              </div>

              <button
                type="submit"
                disabled={isLocked || isLoading || !email || !password}
                className="w-full btn-pill-dark py-4 text-base font-semibold flex items-center justify-center gap-2 group disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Iniciando...' : 'Acceder al Sistema'}
                {!isLoading && <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />}
              </button>
            </form>
          ) : (
            <form onSubmit={handleStep2Submit} className="space-y-8">
              <div className="flex items-center text-sm text-slate-gray mb-4">
                <button type="button" onClick={() => setStep(1)} className="mr-2 hover:text-ink-black">
                  <ArrowLeft size={16} />
                </button>
                <span>Código enviado a {email.substring(0, 1)}****@{email.split('@')[1]}</span>
              </div>

              <div className="flex justify-between gap-2">
                {otp.map((digit, index) => (
                  <input
                    key={index}
                    ref={el => otpRefs.current[index] = el}
                    type="text"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(index, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(index, e)}
                    className="w-[52px] h-[60px] text-center text-[28px] font-mono rounded-[16px] border border-mist-gray focus:outline-none focus:ring-2 focus:ring-ink-black transition-shadow"
                    disabled={isLoading || otpTimeLeft <= 0}
                  />
                ))}
              </div>

              <div className="flex flex-col items-center gap-4">
                <span className={`text-sm font-mono ${otpTimeLeft < 60 ? 'text-red-500' : 'text-slate-gray'}`}>
                  Código válido por: {formatTime(otpTimeLeft)}
                </span>
                
                <button
                  type="button"
                  onClick={handleResendOtp}
                  disabled={resendCooldown > 0 || isLoading}
                  className="text-sm font-medium text-ink-black hover:underline disabled:text-slate-gray disabled:no-underline disabled:cursor-not-allowed transition-colors"
                >
                  {resendCooldown > 0 
                    ? `Reenviar código en ${resendCooldown}s` 
                    : 'Reenviar código'}
                </button>
              </div>

              <button
                type="submit"
                disabled={isLoading || otpTimeLeft <= 0 || otp.some(d => !d)}
                className="w-full btn-pill-dark py-4 text-base font-semibold flex items-center justify-center gap-2 group disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Verificando...' : 'Verificar e Ingresar'}
                {!isLoading && <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />}
              </button>
            </form>
          )}

          <div className="mt-12 pt-6 border-t border-mist-gray flex items-center justify-between text-xs text-slate-gray">
            <span>© 2026 GIRAGROUP S.A.</span>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-green-500"></div>
              <span>Pipeline Operativo</span>
            </div>
          </div>

          <div className="mt-8">
            <details className="text-xs text-slate-gray cursor-pointer">
              <summary className="hover:text-ink-black transition-colors select-none">
                [Herramientas de Desarrollador — Selección de Perfil Demo]
              </summary>
              <div className="mt-3 p-4 bg-mist-gray/30 rounded-[12px]">
                <label className="block mb-2 font-medium">Seleccionar Perfil:</label>
                <select 
                  onChange={handleDemoSelect} 
                  className="w-full p-2 rounded-[8px] border border-mist-gray text-ink-black bg-paper-white"
                  defaultValue=""
                >
                  <option value="" disabled>-- Seleccione un rol --</option>
                  <option value="Auditor de Calidad">Auditor de Calidad</option>
                  <option value="Director Académico">Director Académico</option>
                  <option value="Analista Financiero">Analista Financiero</option>
                  <option value="Administrador del Sistema">Administrador del Sistema</option>
                </select>
                <p className="mt-2 opacity-75">Seleccionar un perfil pre-llenará el correo e ingresará una contraseña demo. Use el botón de inicio de sesión para aplicar bypass de cliente.</p>
              </div>
            </details>
          </div>
        </div>
      </div>

      <div className="hidden lg:flex flex-1 relative bg-mist-gray/20 overflow-hidden items-center justify-center p-12">
        <div className="absolute inset-0 bg-[rgba(250,250,251,0.75)] backdrop-blur-[10px] z-0"></div>
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full bg-blue-100/40 blur-[100px] animate-[floatAmbientA_6.5s_ease-in-out_infinite_alternate] z-0"></div>
        <div className="absolute bottom-[-10%] left-[-10%] w-[600px] h-[600px] rounded-full bg-orange-100/40 blur-[120px] animate-[floatAmbientB_7.5s_ease-in-out_infinite_alternate] z-0"></div>

        <div className="relative z-10 w-full max-w-lg space-y-6">
          <div className="floating-artifact p-8 kinetic-card">
            <div className="inline-block px-3 py-1 bg-ink-black text-paper-white text-[10px] font-bold uppercase tracking-wider rounded-full mb-4">
              DataOps Core
            </div>
            <h3 className="serif-display text-2xl text-ink-black mb-3">Fase 2: Procesamiento & Normalización</h3>
            <p className="text-slate-gray text-sm leading-relaxed">
              El sistema se encarga de extraer, transformar y cargar datos desde múltiples fuentes (SIGAA, Excel, APIs externas) aplicando reglas de negocio estrictas para garantizar la calidad del dato.
            </p>
          </div>

          <div className="card-peach-accent p-8 rounded-[24px] kinetic-card" style={{ transform: 'rotate(2deg)' }}>
            <h3 className="serif-display text-2xl text-ink-black mb-3">De la planilla Excel caótica al modelo dimensional canónico</h3>
            <p className="text-ink-black/80 text-sm leading-relaxed font-medium">
              Gobierno de datos en acción. Reduzca la latencia de decisiones y elimine la ambigüedad en los reportes gerenciales con una única fuente de verdad.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
