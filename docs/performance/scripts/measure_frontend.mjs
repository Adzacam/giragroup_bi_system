#!/usr/bin/env node
/**
 * Script de medición reproducible de Frontend (Bundle + Web Vitals / Transiciones)
 * Sistema BI GiraGroup - Auditoría de Rendimiento
 *
 * Uso:
 *   1) Solo análisis de bundle estático (no requiere Docker activo):
 *      node docs/performance/scripts/measure_frontend.mjs --build-only
 *
 *   2) Análisis completo (Bundle + Playwright LCP/TTI/TBT/CLS y transiciones SPA):
 *      node docs/performance/scripts/measure_frontend.mjs --url http://localhost
 */

import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import zlib from 'node:zlib';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const FRONTEND_DIR = path.join(REPO_ROOT, 'frontend');

const args = process.argv.slice(2);
const buildOnly = args.includes('--build-only');
const urlIdx = args.indexOf('--url');
const BASE_URL = urlIdx !== -1 && args[urlIdx + 1] ? args[urlIdx + 1] : 'http://localhost';

function analyzeViteBundle() {
  console.log('=== [1/2] Analizando Bundle de Producción (vite build) ===');
  const tmpOutDir = fs.mkdtempSync(path.join(os.tmpdir(), 'gira-vite-bench-'));
  const t0 = performance.now();
  try {
    const out = execSync(`npx vite build --outDir "${tmpOutDir}"`, {
      cwd: FRONTEND_DIR,
      encoding: 'utf-8',
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    const elapsedMs = Math.round(performance.now() - t0);

    const assetsDir = path.join(tmpOutDir, 'assets');
    const files = fs.existsSync(assetsDir) ? fs.readdirSync(assetsDir) : [];
    const stats = files.map((file) => {
      const fullPath = path.join(assetsDir, file);
      const buf = fs.readFileSync(fullPath);
      const sizeBytes = buf.length;
      const gzipBytes = zlib.gzipSync(buf, { level: 9 }).length;
      return {
        file,
        type: path.extname(file).replace('.', '') || 'other',
        sizeKiB: Number((sizeBytes / 1024).toFixed(2)),
        gzipKiB: Number((gzipBytes / 1024).toFixed(2)),
      };
    });

    stats.sort((a, b) => b.sizeKiB - a.sizeKiB);
    const jsChunks = stats.filter((s) => s.type === 'js');
    const cssChunks = stats.filter((s) => s.type === 'css');
    const totalJS = jsChunks.reduce((acc, s) => acc + s.sizeKiB, 0);
    const totalJSGzip = jsChunks.reduce((acc, s) => acc + s.gzipKiB, 0);
    const totalCSS = cssChunks.reduce((acc, s) => acc + s.sizeKiB, 0);
    const totalCSSGzip = cssChunks.reduce((acc, s) => acc + s.gzipKiB, 0);

    console.log(`Build completado en ${elapsedMs} ms`);
    console.log(
      `Total JS: ${totalJS.toFixed(2)} KiB bruto / ${totalJSGzip.toFixed(2)} KiB gzip (${jsChunks.length} chunks)`
    );
    console.log(
      `Total CSS: ${totalCSS.toFixed(2)} KiB bruto / ${totalCSSGzip.toFixed(2)} KiB gzip (${cssChunks.length} archivo)`
    );
    console.log(
      `Total Bundle (JS + CSS): ${(totalJS + totalCSS).toFixed(2)} KiB bruto / ${(totalJSGzip + totalCSSGzip).toFixed(2)} KiB gzip`
    );
    console.log('\nTop 12 Chunks más pesados:');
    console.table(stats.slice(0, 12));

    return {
      elapsedMs,
      jsChunksCount: jsChunks.length,
      totalJS: Number(totalJS.toFixed(2)),
      totalJSGzip: Number(totalJSGzip.toFixed(2)),
      totalCSS: Number(totalCSS.toFixed(2)),
      totalCSSGzip: Number(totalCSSGzip.toFixed(2)),
      topChunks: stats.slice(0, 12),
      rawOutput: out,
    };
  } finally {
    fs.rmSync(tmpOutDir, { recursive: true, force: true });
  }
}

async function measureRuntimeWithPlaywright(baseUrl) {
  console.log(`\n=== [2/2] Midiendo Carga Inicial (LCP/FCP/CLS/TBT) y Navegación SPA en ${baseUrl} ===`);
  let chromium;
  try {
    const pw = await import('playwright');
    chromium = pw.chromium;
  } catch {
    console.warn(
      '[AVISO] Playwright no está instalado en el entorno local. Ejecute `pnpm add -D playwright` o use `--build-only`.'
    );
    return null;
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  await page.addInitScript(() => {
    window.__perfMetrics = { lcpMs: null, cls: 0, tbtMs: 0 };
    try {
      new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          window.__perfMetrics.lcpMs = Math.round(entry.startTime);
        }
      }).observe({ type: 'largest-contentful-paint', buffered: true });

      new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          if (!entry.hadRecentInput) {
            window.__perfMetrics.cls += entry.value;
          }
        }
      }).observe({ type: 'layout-shift', buffered: true });

      new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          const blocking = entry.duration - 50;
          if (blocking > 0) {
            window.__perfMetrics.tbtMs += Math.round(blocking);
          }
        }
      }).observe({ type: 'longtask', buffered: true });
    } catch {
      // Observers opcionales según soporte del navegador headless
    }
  });

  const requestLog = [];
  page.on('requestfinished', async (req) => {
    const timing = req.timing();
    requestLog.push({
      url: req.url(),
      method: req.method(),
      resourceType: req.resourceType(),
      durationMs: timing.responseEnd > 0 ? Math.round(timing.responseEnd - timing.startTime) : -1,
    });
  });

  try {
    const tStart = performance.now();
    await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle', timeout: 30000 });
    const initialLoadMs = Math.round(performance.now() - tStart);

    const navMetrics = await page.evaluate(() => {
      const nav = performance.getEntriesByType('navigation')[0];
      const paints = Object.fromEntries(
        performance.getEntriesByType('paint').map((p) => [p.name, Math.round(p.startTime)])
      );
      const obs = window.__perfMetrics || {};
      return {
        ttfbMs: nav ? Math.round(nav.responseStart - nav.requestStart) : null,
        fcpMs: paints['first-contentful-paint'] ?? null,
        lcpMs: obs.lcpMs ?? paints['first-contentful-paint'] ?? null,
        domInteractiveMs: nav ? Math.round(nav.domInteractive) : null,
        domCompleteMs: nav ? Math.round(nav.domComplete) : null,
        tbtMs: obs.tbtMs ?? 0,
        cls: Number((obs.cls ?? 0).toFixed(4)),
        resourcesCount: performance.getEntriesByType('resource').length,
      };
    });

    console.log('Métricas de Carga Inicial (/login):');
    console.table([{ initialLoadMs, ...navMetrics, totalRequests: requestLog.length }]);

    // Rutas reales definidas en frontend/src/App.jsx:377-543
    const routesToMeasure = [
      '/dashboard',
      '/alertas-tempranas',
      '/academico/docente',
      '/academico/catalogo',
      '/academico/proyeccion',
      '/financiero/recaudacion',
      '/financiero/cartera',
      '/financiero/metas',
      '/financiero/proyeccion',
      '/dataops/ingesta',
      '/dataops/texto',
      '/dataops/beto',
      '/dataops/revision',
      '/admin/auditoria',
    ];

    const routeResults = [];
    for (const route of routesToMeasure) {
      requestLog.length = 0;
      const tRoute = performance.now();
      await page.goto(`${baseUrl}${route}`, { waitUntil: 'networkidle', timeout: 30000 });
      const routeMs = Math.round(performance.now() - tRoute);
      const apiCalls = requestLog.filter((r) => r.url.includes('/api/v1/'));
      routeResults.push({
        route,
        networkIdleMs: routeMs,
        totalRequests: requestLog.length,
        apiCallsCount: apiCalls.length,
        slowestApiMs: apiCalls.length ? Math.max(...apiCalls.map((a) => a.durationMs)) : 0,
      });
    }

    console.log('\nMétricas por Ruta:');
    console.table(routeResults);
    return { navMetrics, routeResults };
  } catch (err) {
    console.error(`[ERROR] No se pudo conectar a ${baseUrl}: ${err.message}`);
    return null;
  } finally {
    await browser.close();
  }
}

async function main() {
  analyzeViteBundle();
  if (!buildOnly) {
    await measureRuntimeWithPlaywright(BASE_URL);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
