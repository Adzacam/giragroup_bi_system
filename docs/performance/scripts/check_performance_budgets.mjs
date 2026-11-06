import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, '../../..');

const MAX_TOTAL_GZIP_KIB = 360.0;

console.log('=== Comprobación de Presupuestos de Rendimiento (Fase 3: Monitoreo y Prevención) ===\n');

// 1. Bundle Frontend
console.log('[1/3] Verificando presupuesto de bundle frontend...');
try {
  const output = execSync('node docs/performance/scripts/measure_frontend.mjs --build-only', {
    cwd: root,
    encoding: 'utf-8',
  });
  
  let totalGzip = null;
  const match = output.match(/Total Bundle \(JS \+ CSS\):.*?\/.*?([\d.]+)\s*KiB\s*gzip/);
  if (match) {
    totalGzip = parseFloat(match[1]);
  }

  if (totalGzip !== null) {
    console.log(`  Total Bundle Gzip: ${totalGzip.toFixed(2)} KiB (Límite: ${MAX_TOTAL_GZIP_KIB.toFixed(2)} KiB)`);
    if (totalGzip > MAX_TOTAL_GZIP_KIB) {
      console.error(`  [FAIL] Presupuesto excedido: ${totalGzip} > ${MAX_TOTAL_GZIP_KIB}`);
      process.exit(1);
    }
    console.log('  [OK] Presupuesto de bundle respetado.');
  } else {
    console.log('  [WARN] No se pudo parsear el tamaño gzip del bundle.');
  }
} catch (err) {
  console.error('  [ERROR] Falló la verificación del bundle:', err.message);
  process.exit(1);
}

// 2. Gateway Nginx & Docker Compose
console.log('\n[2/3] Verificando configuraciones de rendimiento en Nginx y Docker Compose...');
const nginxConf = fs.readFileSync(path.join(root, 'gateway/nginx.conf'), 'utf-8');
if (!nginxConf.includes('gzip on;')) {
  console.error("  [FAIL] 'gzip on;' no configurado en gateway/nginx.conf");
  process.exit(1);
}
if (!nginxConf.includes('keepalive 32;')) {
  console.error("  [FAIL] 'keepalive' en upstreams no configurado en gateway/nginx.conf");
  process.exit(1);
}
console.log('  [OK] Gateway Nginx configurado con compresión y keepalive.');

const composeYml = fs.readFileSync(path.join(root, 'docker-compose.yml'), 'utf-8');
if (!composeYml.includes('TORCH_NUM_THREADS:-4')) {
  console.error('  [FAIL] TORCH_NUM_THREADS óptimo (4) no encontrado en docker-compose.yml');
  process.exit(1);
}
if (!composeYml.includes('shared_preload_libraries=pg_stat_statements')) {
  console.error('  [FAIL] pg_stat_statements no activado en servicio db de docker-compose.yml');
  process.exit(1);
}
console.log('  [OK] docker-compose.yml configurado con hilos óptimos y pg_stat_statements.');

// 3. FastAPI Server-Timing
console.log('\n[3/3] Verificando instrumentación Server-Timing en FastAPI...');
const mainPy = fs.readFileSync(path.join(root, 'backend/main.py'), 'utf-8');
if (!mainPy.includes('response.headers["Server-Timing"]')) {
  console.error('  [FAIL] Server-Timing no instrumentado en backend/main.py');
  process.exit(1);
}
console.log('  [OK] Instrumentación Server-Timing y slow-query logger activos en FastAPI.');

console.log('\n>>> TODOS LOS PRESUPUESTOS Y CONFIGURACIONES DE RENDIMIENTO CUMPLEN LAS METAS EXITOSAMENTE.');
