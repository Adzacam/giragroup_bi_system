// Verificación E2E de PLAN_DATAOPS_FLUJO (DF-L9): ① Carga -> ② BETO -> ③ Revisión + Auditoría + Rendimiento.
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { URL_APP, EMAIL, PASSWORD, paso } from './lib.mjs';

const OUT_DIR = 'docs/mediciones/df_l9_capturas';
fs.mkdirSync(OUT_DIR, { recursive: true });

const RUTAS = [
  ['p1_ingesta', '/v2/dataops/ingesta'],
  ['p2_beto', '/v2/dataops/lote/46/beto'],
  ['p3_revision', '/v2/dataops/lote/46/revision'],
  ['p4_auditoria', '/v2/admin/auditoria'],
  ['p5_rendimiento', '/v2/academico/rendimiento'],
];

const VIEWPORTS = [
  ['1440', { width: 1440, height: 900 }],
  ['768', { width: 768, height: 1024 }],
  ['375', { width: 375, height: 812 }],
];

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(String(err)));

  await paso('login_admin', async () => {
    await page.goto(`${URL_APP}/login`, { waitUntil: 'networkidle' });
    await page.fill('input[type="email"], input[name="email"], input[name="username"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD || '');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1500);
  });

  for (const [nombre, ruta] of RUTAS) {
    for (const [vpName, vp] of VIEWPORTS) {
      await paso(`${nombre}_${vpName}`, async () => {
        await page.setViewportSize(vp);
        await page.goto(`${URL_APP}${ruta}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(600);
        await page.screenshot({ path: path.join(OUT_DIR, `${nombre}_${vpName}_light.png`), fullPage: false });
      });
    }
  }

  if (consoleErrors.length > 0) {
    throw new Error(`Errores de consola detectados: ${consoleErrors.join(' | ')}`);
  }
  await browser.close();
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
