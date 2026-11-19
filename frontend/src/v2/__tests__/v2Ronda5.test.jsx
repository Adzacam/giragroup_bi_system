import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import fs from 'node:fs';
import path from 'node:path';

import LoginHeroPane from '../../modules/auth/components/LoginHeroPane';
import OtpInputForm from '../../modules/auth/components/OtpInputForm';
import ForgotPasswordModal from '../../modules/auth/components/ForgotPasswordModal';
import ProfileModal from '../../components/profile/ProfileModal';
import IsometricCanvasBackground from '../../components/canvas3d/IsometricCanvasBackground';
import LoginPage from '../../modules/auth/LoginPage';
import { AuthProvider } from '../../context/AuthContext';
import { NotificationProvider } from '../../context/NotificationContext';
import { UiVersionProvider } from '../context/UiVersionContext';

// Mock ThemeContext so IsometricCanvasBackground can test canvasEnabled=true
vi.mock('../../context/ThemeContext', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useTheme: () => ({
      theme: 'dark',
      isDark: true,
      toggleTheme: () => {},
      canvasEnabled: true,
    }),
  };
});

describe('Ronda 5 (L1-R5 y L2-R5: Login, OTP, Modales y Hero Pane Obsidiana)', () => {
  beforeEach(() => {
    const store = {};
    globalThis.localStorage = {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
      clear: () => {},
    };
  });

  it('L2-R5: LoginHeroPane renderiza lienzo obsidiana, nubes plata esmerilada, 2 líneas curvas 90°, grano y 2 cards ejecutivas sin partículas', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/login']}>
        <LoginHeroPane />
      </MemoryRouter>
    );
    expect(html).toContain('v2-hero-obsidian-canvas');
    expect(html).toContain('v2-cloud-bottom-left');
    expect(html).toContain('v2-cloud-top-right');
    expect(html).toContain('v2-hero-curved-lines-svg');
    expect(html).toContain('M 620 44 L 860 44 Q 956 44 956 140 L 956 380');
    expect(html).toContain('M 380 956 L 140 956 Q 44 956 44 860 L 44 620');
    expect(html).toContain('v2-hero-film-grain');
    expect(html).toContain('feTurbulence');
    expect(html).toContain('v2-hero-card-a');
    expect(html).toContain('v2-hero-card-b');
    expect(html).toContain('RESOLUCIÓN DE IDENTIDAD · CASCADA 5 ETAPAS');
    expect(html).toContain('BETO NER + RAPIDFUZZ');
    expect(html).toContain('INTELIGENCIA EJECUTIVA · CMI &amp; ANALÍTICA PREDICTIVA');
    expect(html).toContain('22 KPIS · m=12');
    expect(html).not.toContain('login-hero-glow');
  });

  it('L2-R5: IsometricCanvasBackground suprime partículas en /login y /v2/login, y las permite en /v2/dashboard', () => {
    const loginHtml = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/login']}>
        <IsometricCanvasBackground />
      </MemoryRouter>
    );
    expect(loginHtml).toBe('');

    const v2LoginHtml = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/v2/login']}>
        <IsometricCanvasBackground />
      </MemoryRouter>
    );
    expect(v2LoginHtml).toBe('');

    const dashHtml = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/v2/dashboard']}>
        <IsometricCanvasBackground />
      </MemoryRouter>
    );
    expect(dashHtml).toContain('id="bg-3d-canvas"');
  });

  it('L1-R5: OtpInputForm renderiza 6 casillas escalonadas, sacudida en error y estado isEnteringSystem', () => {
    const html = renderToStaticMarkup(
      <OtpInputForm
        email="dazaadriano12@gmail.com"
        otp={['1', '2', '3', '4', '5', '6']}
        onOtpChange={() => {}}
        onOtpKeyDown={() => {}}
        onOtpPaste={() => {}}
        otpRefs={{ current: [] }}
        onSubmit={() => {}}
        onBack={() => {}}
        otpTimeLeft={240}
        resendCooldown={30}
        onResend={() => {}}
        isLoading={false}
        formatTime={(s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`}
        error="Código inválido"
        isEnteringSystem={true}
      />
    );
    expect(html).toContain('v2-otp-grid has-error');
    expect(html).toContain('--otp-idx:0');
    expect(html).toContain('--otp-idx:5');
    expect(html).toContain('v2-login-submit-btn is-entering');
    expect(html).toContain('Entrando al sistema...');
  });

  it('L1-R5: ForgotPasswordModal y ProfileModal renderizan clases animadas al abrir y nada cuando isOpen=false', () => {
    const closedForgot = renderToStaticMarkup(
      <ForgotPasswordModal isOpen={false} onClose={() => {}} />
    );
    expect(closedForgot).toBe('');

    const openForgot = renderToStaticMarkup(
      <ForgotPasswordModal isOpen={true} onClose={() => {}} initialEmail="test@giragroup.bo" />
    );
    expect(openForgot).toContain('v2-modal-backdrop');
    expect(openForgot).toContain('v2-modal-card');
    expect(openForgot).toContain('v2-modal-step-enter');

    const closedProfile = renderToStaticMarkup(
      <AuthProvider>
        <NotificationProvider>
          <ProfileModal isOpen={false} onClose={() => {}} />
        </NotificationProvider>
      </AuthProvider>
    );
    expect(closedProfile).toBe('');

    const openProfile = renderToStaticMarkup(
      <AuthProvider>
        <NotificationProvider>
          <ProfileModal isOpen={true} onClose={() => {}} />
        </NotificationProvider>
      </AuthProvider>
    );
    expect(openProfile).toContain('v2-modal-backdrop');
    expect(openProfile).toContain('v2-modal-card');
  });

  it('L1-R5: LoginPage renderiza en /v2/login con panel de transición direccional y Hero Pane', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={['/v2/login']}>
        <AuthProvider>
          <UiVersionProvider>
            <LoginPage />
          </UiVersionProvider>
        </AuthProvider>
      </MemoryRouter>
    );
    expect(html).toContain('login-split-layout');
    expect(html).toContain('v2-auth-step-panel');
    expect(html).toContain('v2-hero-obsidian-canvas');
    expect(html).toContain('Iniciar sesión');
  });

  it('L1-R5 y L2-R5: v2-login.css respeta prefers-reduced-motion: reduce', () => {
    const cssPath = path.resolve(__dirname, '../../styles/v2-login.css');
    const css = fs.readFileSync(cssPath, 'utf-8');
    expect(css).toContain('prefers-reduced-motion: reduce');
    expect(css).toContain('prefers-reduced-motion: no-preference');
    expect(css).toContain('v2-hero-float-card-a');
    expect(css).toContain('v2-silver-line-flow');
    expect(css).toContain('::view-transition-old(v2-auth-step)');
    expect(css).toContain('::view-transition-new(v2-auth-step)');
    expect(css).toContain('animation-duration: 280ms;');
  });
});
