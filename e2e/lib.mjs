// Utilidades del E2E (Playwright): temporizador por paso, OTP desde el log del auth-service y capturas.
import { execSync } from 'node:child_process';
import fs from 'node:fs';

export const URL_APP = process.env.E2E_URL || 'http://localhost:5173';
export const EMAIL = process.env.E2E_EMAIL || 'e2e.admin@giragroup.test';
export const PASSWORD = process.env.E2E_PASSWORD; // contraseña de prueba del usuario e2e (semilla del proyecto)
export const SALIDA = process.env.E2E_SALIDA || 'docs/evidencias/e2e';
fs.mkdirSync(SALIDA, { recursive: true });

export const pasos = [];
export async function paso(nombre, fn) {
  const t0 = performance.now();
  let error = null;
  try { await fn(); } catch (e) { error = String(e.message || e).split('\n')[0]; }
  const seg = Math.round((performance.now() - t0)) / 1000;
  pasos.push({ paso: nombre, segundos: seg, ok: !error, error });
  console.log(`${error ? 'FALLO' : 'ok   '} ${nombre}: ${seg} s${error ? ' — ' + error : ''}`);
  if (error) throw new Error(`${nombre}: ${error}`);
}

export function otpDelLog(desde) {
  const log = execSync(`docker logs --since ${desde} giragroup_auth_svc 2>&1`, { encoding: 'utf8' });
  const m = [...log.matchAll(/CÓDIGO OTP PARA e2e\.admin@giragroup\.test: (\d{6})/g)].pop();
  return m ? m[1] : null;
}
