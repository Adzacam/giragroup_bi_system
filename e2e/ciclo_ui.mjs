// E2E de la UI real: login (con 2FA) -> carga de los 10 archivos del ciclo -> bandeja por grupos -> aprobar los grupos -> CMI.
// Uso: E2E_PASSWORD=... node e2e/ciclo_ui.mjs   (Playwright instalado fuera del repo: NODE_PATH)
import { chromium } from 'playwright';
import fs from 'node:fs';
import { execSync } from 'node:child_process';
import path from 'node:path';
import { URL_APP, EMAIL, PASSWORD, SALIDA, paso, pasos, otpDelLog } from './lib.mjs';

const CARPETA = process.env.E2E_ARCHIVOS;
const archivos = fs.readdirSync(CARPETA).filter((f) => f.endsWith('.xlsx')).map((f) => path.join(CARPETA, f));
const tiempos = { grupos: [] };
console.log('salida:', SALIDA);
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
page.setDefaultTimeout(120000);
let sesionDesde;
try {
  await paso('login: credenciales + OTP', async () => {
    await page.goto(`${URL_APP}/login`);
    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    sesionDesde = new Date(Date.now() - 2000).toISOString();
    await page.click('button:has-text("Iniciar sesión")');
    let otp = null;
    for (let i = 0; i < 20 && !otp; i++) { await page.waitForTimeout(500); otp = otpDelLog(sesionDesde); }
    if (!otp) throw new Error('no se encontró el OTP en el log del auth-service');
    await page.locator('input[maxlength="1"]').first().click();
    await page.keyboard.type(otp, { delay: 30 });
    await page.click('button:has-text("Verificar y Acceder")');
    await page.waitForURL((u) => !u.pathname.includes('login'));
  });
  await page.screenshot({ path: `${SALIDA}/00_post_login.png` });
  await paso('ingesta: abrir pantalla', async () => { await page.goto(`${URL_APP}/dataops/ingesta`); await page.waitForSelector('#file-upload-input', { state: 'attached' }); });
  await paso(`ingesta: seleccionar ${archivos.length} archivos`, async () => { await page.setInputFiles('#file-upload-input', archivos); await page.waitForTimeout(1500); });
  await page.screenshot({ path: `${SALIDA}/01_ingesta_cola.png`, fullPage: true });
  await paso('ingesta: procesar lote de 10 archivos (hasta pre-etiquetado)', async () => {
    await page.click('button:has-text("Procesar Lote e Inspeccionar")');
    await page.waitForFunction(() => document.body.innerText.includes('Pre-etiquetado'), null, { timeout: 1500000 });
  });
  await page.screenshot({ path: `${SALIDA}/02_ingesta_procesada.png`, fullPage: true });
  const lote = await page.evaluate(() => localStorage.getItem('last_active_batch_id'));
  await paso('BETO: abrir lectura del lote', async () => {
    await page.goto(`${URL_APP}/dataops/lote/${lote}/beto`);
    await page.waitForSelector('button:has-text("Consolidar lote al DW")');
    await page.waitForFunction(() => { const b = [...document.querySelectorAll('button')].find((x) => x.innerText.includes('Consolidar lote al DW')); return b && !b.disabled; }, null, { timeout: 2400000 });
  });
  await page.screenshot({ path: `${SALIDA}/03_beto_lectura.png`, fullPage: false });
  await paso('DW: consolidar el lote (carga al DW)', async () => {
    await page.click('button:has-text("Consolidar lote al DW")');
    await page.click('button:has-text("Confirmar e Insertar")');
    await page.waitForFunction(() => document.body.innerText.includes('Lote consolidado'), null, { timeout: 1500000 });
  });
  // Caso de prueba en el clon: un hecho ya cargado con una combinación de estados no admitida (Aprobado / Tutoria / Titulado) para ejercitar 'Mapear a estado canónico'
  execSync(`docker exec giragroup_db psql -U giragroup_user -d giragroup_e2e -c "UPDATE fact_rendimiento_academico SET estado_academico='Aprobado', estado_tutoria='Tutoria', estado_arca='Titulado', requiere_revision=TRUE WHERE id_hecho_aca IN (SELECT id_hecho_aca FROM fact_rendimiento_academico WHERE id_documento > (SELECT max(id_documento)-10 FROM dim_origen_documental) AND nota_final IS NOT NULL ORDER BY id_hecho_aca LIMIT 3)"`);
  await paso('bandeja: abrir revisión por grupos', async () => {
    await page.goto(`${URL_APP}/dataops/lote/${lote}/revision`);
    await page.waitForSelector('[data-testid="bandeja-grupos"]');
    await page.waitForSelector('[data-testid="fila-grupo"], [data-testid="grupos-vacio"]');
  });
  const resumenGrupos = await page.locator('[data-testid="grupos-total"]').innerText();
  const enBloque = await page.locator('[data-testid="grupos-en-bloque"]').innerText();
  tiempos.bandeja = { total: resumenGrupos, en_bloque: enBloque };
  console.log('bandeja:', resumenGrupos, '|', enBloque);
  await page.screenshot({ path: `${SALIDA}/04_bandeja_por_grupos.png`, fullPage: false });
  let capturaDialogo = false, n = 0;
  while (true) {
    await page.waitForSelector('[data-testid="fila-grupo"], [data-testid="grupos-vacio"]');
    if ((await page.locator('[data-testid="fila-grupo"]').count()) === 0) break;
    const fila = page.locator('[data-testid="fila-grupo"]').first();
    const boton = fila.locator('button').first();
    const texto = (await boton.innerText()).trim();
    const casos = Number((await fila.locator('td').nth(2).innerText()).trim());
    const motivo = (await fila.locator('td').nth(0).innerText()).trim();
    const valor = (await fila.locator('td').nth(1).innerText()).trim();
    const accion = texto.startsWith('Mapear') ? 'MAPEAR_ESTADO' : texto.startsWith('Corregir') ? 'CORREGIR_FECHA' : texto.startsWith('Revisar') ? 'MANUAL' : 'APROBAR';
    if (accion === 'MANUAL') { console.log('grupo manual: queda para la vista caso por caso'); break; }
    const filasAntes = await page.locator('[data-testid="fila-grupo"]').count();
    const t0 = performance.now();
    await boton.click();
    if (accion !== 'APROBAR') {
      await page.waitForSelector('[data-testid="dialogo-grupo"]');
      if (accion === 'MAPEAR_ESTADO' && !capturaDialogo) { await page.screenshot({ path: `${SALIDA}/05_dialogo_mapear_estado.png` }); capturaDialogo = true; }
      if (accion === 'CORREGIR_FECHA') { await page.fill('#fecha-mes', '3'); await page.fill('#fecha-gestion', '2026'); }
      await page.click('[data-testid="dialogo-confirmar"]');
    }
    await page.waitForFunction((k) => document.querySelectorAll('[data-testid="fila-grupo"]').length < k || !!document.querySelector('[data-testid="grupos-vacio"]'), filasAntes, { timeout: 120000 });
    const ms = Math.round(performance.now() - t0);
    n += 1;
    tiempos.grupos.push({ orden: n, motivo, valor: valor.slice(0, 100), accion, n_casos: casos, ms_ui_medido: ms });
    console.log(`grupo ${n} ${accion} (${casos} casos): ${ms} ms`);
  }
  pasos.push({ paso: `bandeja: aprobar ${n} grupos (suma de la UI)`, segundos: Math.round(tiempos.grupos.reduce((a, g) => a + g.ms_ui_medido, 0)) / 1000, ok: true, error: null });
  await page.screenshot({ path: `${SALIDA}/06_bandeja_resuelta.png` });
  await paso('CMI: abrir el cuadro de mando actualizado', async () => {
    await page.goto(`${URL_APP}/cmi`);
    await page.waitForFunction(() => document.body.innerText.includes('Confianza media de extracción'), null, { timeout: 120000 });
  });
  await page.screenshot({ path: `${SALIDA}/07_cmi.png`, fullPage: true });
  fs.writeFileSync(`${SALIDA}/tiempos_ui.json`, JSON.stringify({ pasos, ...tiempos }, null, 1));
} catch (e) {
  await page.screenshot({ path: `${SALIDA}/error.png`, fullPage: true }).catch(() => {});
  throw e;
} finally {
  await browser.close();
}
