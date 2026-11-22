import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import fs from 'node:fs';
import path from 'node:path';

import { UiVersionProvider, useUiVersion } from '../context/UiVersionContext';
import { AuthProvider } from '../../context/AuthContext';
import { NotificationProvider } from '../../context/NotificationContext';
import TareasSegundoPlano from '../../components/shared/TareasSegundoPlano';
import { dataopsApi } from '../../api/dataopsApi';

describe('V2 como vista principal y prevención de 401 en login', () => {
  beforeEach(() => {
    const store = {};
    globalThis.localStorage = {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
      clear: () => {},
    };
  });

  it('UiVersionProvider expone uiVersion="v2" por defecto', () => {
    let captured = null;
    function Probe() {
      captured = useUiVersion();
      return null;
    }
    renderToStaticMarkup(
      <UiVersionProvider>
        <Probe />
      </UiVersionProvider>
    );
    expect(captured?.uiVersion).toBe('v2');
  });

  it('TareasSegundoPlano no dispara getTareasActivas sin sesión o en rutas de login', () => {
    const spy = vi.spyOn(dataopsApi, 'getTareasActivas').mockResolvedValue([]);
    renderToStaticMarkup(
      <MemoryRouter initialEntries={['/v2/login']}>
        <AuthProvider>
          <NotificationProvider>
            <TareasSegundoPlano role="ADMIN" />
          </NotificationProvider>
        </AuthProvider>
      </MemoryRouter>
    );
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it('App.jsx, LoginPage.jsx y client.js dirigen a /v2/* por defecto', () => {
    const appSrc = fs.readFileSync(path.resolve(__dirname, '../../App.jsx'), 'utf8');
    expect(appSrc).toContain("V2_ROLE_REDIRECTS[role] || '/v2/dashboard'");
    expect(appSrc).toContain("isExplicitV1 ? '/login' : '/v2/login'");

    const loginSrc = fs.readFileSync(path.resolve(__dirname, '../../modules/auth/LoginPage.jsx'), 'utf8');
    expect(loginSrc).toContain("V2_ROLE_REDIRECTS[userData?.role] || '/v2/dashboard'");

    const clientSrc = fs.readFileSync(path.resolve(__dirname, '../../api/client.js'), 'utf8');
    expect(clientSrc).toContain("window.location.pathname === '/v2/login'");
    expect(clientSrc).toContain("window.location.href = '/v2/login'");
  });
});
