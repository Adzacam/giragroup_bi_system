// E2E del diálogo "Mapear a estado canónico": un grupo con estado fuera de catálogo se resuelve desde la UI (tiempo medido y capturas).
import { chromium } from 'playwright';
import fs from 'node:fs';
import { URL_APP, EMAIL, PASSWORD, SALIDA, otpDelLog } from './lib.mjs';
const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } }); const page = await ctx.newPage(); page.setDefaultTimeout(60000);
await page.goto(`${URL_APP}/login`); await page.fill('input[type="email"]', EMAIL); await page.fill('input[type="password"]', PASSWORD);
const d = new Date(Date.now() - 2000).toISOString(); await page.click('button:has-text("Iniciar sesión")');
let otp = null; for (let i = 0; i < 20 && !otp; i++) { await page.waitForTimeout(500); otp = otpDelLog(d); }
await page.locator('input[maxlength="1"]').first().click(); await page.keyboard.type(otp, { delay: 30 }); await page.click('button:has-text("Verificar y Acceder")');
await page.waitForURL((u) => !u.pathname.includes('login'));
await page.goto(`${URL_APP}/dataops/lote/${process.env.E2E_LOTE || 2}/revision`);
await page.waitForSelector('[data-testid="grupo-mapear_estado"]');
await page.screenshot({ path: `${SALIDA}/04b_bandeja_con_grupo_de_estado.png` });
const fila = page.locator('[data-testid="fila-grupo"]', { has: page.locator('[data-testid="grupo-mapear_estado"]') }).first();
const casos = Number((await fila.locator('td').nth(2).innerText()).trim());
const antes = await page.locator('[data-testid="fila-grupo"]').count();
const t0 = performance.now();
await fila.locator('[data-testid="grupo-mapear_estado"]').click();
await page.waitForSelector('[data-testid="dialogo-grupo"]');
await page.fill('#canonico-estado', 'Deserción');
await page.screenshot({ path: `${SALIDA}/05_dialogo_mapear_estado.png` });
await page.click('[data-testid="dialogo-confirmar"]');
await page.waitForFunction((k) => document.querySelectorAll('[data-testid="fila-grupo"]').length < k || !!document.querySelector('[data-testid="grupos-vacio"]'), antes);
const ms = Math.round(performance.now() - t0);
console.log(JSON.stringify({ accion: 'MAPEAR_ESTADO', n_casos: casos, ms_ui_medido: ms }));
fs.writeFileSync(`${SALIDA}/tiempo_mapeo_ui.json`, JSON.stringify({ accion: 'MAPEAR_ESTADO', n_casos: casos, ms_ui_medido: ms, nota: 'incluye abrir el diálogo, escribir el estado canónico y aplicar' }, null, 1));
await b.close();
