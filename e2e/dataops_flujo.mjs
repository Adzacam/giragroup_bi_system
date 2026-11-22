// Verificación E2E en Chrome real vía CDP (sin depender de paquetes externos).
// Cubre DF-L9: ① Carga -> ② BETO -> ③ Revisión + Auditoría + Rendimiento en 1440/768/375 px (claro y oscuro).
import { execSync, spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const URL_APP = process.env.E2E_URL || 'http://localhost:5173';
const OUT_DIR = 'docs/mediciones/df_l9_capturas';
fs.mkdirSync(OUT_DIR, { recursive: true });

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].filter(Boolean);

const CHROME_BIN = CHROME_CANDIDATES.find((p) => fs.existsSync(p));
if (!CHROME_BIN) {
  throw new Error('No se encontró Chrome ni Edge en el sistema.');
}

const RUTAS = [
  ['p1_ingesta', '/v2/dataops/ingesta', true],
  ['p2_beto', '/v2/dataops/lote/46/beto', true],
  ['p3_revision', '/v2/dataops/lote/46/revision', true],
  ['p4_auditoria', '/v2/admin/auditoria', false],
  ['p5_rendimiento', '/v2/academico/rendimiento', false],
];

const VIEWPORTS = [
  ['1440', { width: 1440, height: 900 }],
  ['768', { width: 768, height: 1024 }],
  ['375', { width: 375, height: 812 }],
];

function obtenerSesionE2E() {
  if (process.env.E2E_TOKEN && process.env.E2E_USER) {
    return { token: process.env.E2E_TOKEN, user: JSON.parse(process.env.E2E_USER) };
  }
  const raw = execSync(
    'docker exec giragroup_api python -c "import json; from core.database import SessionLocal; from models.user import User; from core.security import create_access_token; db=SessionLocal(); u=db.query(User).filter(User.role==\'ADMIN\').first(); tok=create_access_token({\'sub\': u.username, \'role\': u.role, \'id\': u.id}); print(json.dumps({\'token\': tok, \'user\': {\'id\': u.id, \'username\': u.username, \'email\': getattr(u, \'email\', u.username), \'role\': u.role}}))"',
    { encoding: 'utf8' }
  ).trim();
  return JSON.parse(raw);
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.seq = 1;
    this.pending = new Map();
    this.events = [];
    this.ready = new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, { once: true });
      this.ws.addEventListener('error', reject, { once: true });
    });
    this.ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message || JSON.stringify(msg.error)));
        else resolve(msg.result);
      } else if (msg.method) {
        this.events.push(msg);
      }
    });
  }

  async send(method, params = {}) {
    await this.ready;
    const id = this.seq++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    try { this.ws.close(); } catch {}
  }
}

async function esperar(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function run() {
  const sesion = obtenerSesionE2E();
  const port = 9229;
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'gira-cdp-'));
  const chrome = spawn(CHROME_BIN, [
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    'about:blank',
  ], { stdio: 'ignore' });

  let client;
  const consoleErrors = [];
  const overflowIssues = [];
  const taskLeakIssues = [];

  try {
    let targets = null;
    for (let i = 0; i < 30; i++) {
      try {
        const res = await fetch(`http://127.0.0.1:${port}/json/list`);
        if (res.ok) {
          targets = await res.json();
          if (targets.length > 0) break;
        }
      } catch {}
      await esperar(250);
    }
    if (!targets || !targets.length) throw new Error('Chrome CDP no respondió a tiempo.');
    const pageTarget = targets.find((t) => t.type === 'page') || targets[0];
    client = new CDPClient(pageTarget.webSocketDebuggerUrl);

    await client.send('Page.enable');
    await client.send('Runtime.enable');
    await client.send('Log.enable');

    // Inyectar sesión en localStorage sobre el origen de la app
    await client.send('Page.navigate', { url: `${URL_APP}/login` });
    await esperar(1200);
    await client.send('Runtime.evaluate', {
      expression: `
        localStorage.setItem('gira_token', ${JSON.stringify(sesion.token)});
        localStorage.setItem('gira_user', ${JSON.stringify(JSON.stringify(sesion.user))});
      `,
    });

    for (const theme of ['light', 'dark']) {
      for (const [nombre, ruta, esDataops] of RUTAS) {
        for (const [vpName, vp] of VIEWPORTS) {
          await client.send('Emulation.setDeviceMetricsOverride', {
            width: vp.width,
            height: vp.height,
            deviceScaleFactor: 1,
            mobile: vp.width <= 768,
          });

          const evStart = client.events.length;
          await client.send('Page.navigate', { url: `${URL_APP}${ruta}` });
          await esperar(1800);

          await client.send('Runtime.evaluate', {
            expression: theme === 'dark'
              ? `document.documentElement.classList.add('dark'); localStorage.setItem('gira_theme', 'dark');`
              : `document.documentElement.classList.remove('dark'); localStorage.setItem('gira_theme', 'light');`,
          });
          await esperar(350);

          const checkRes = await client.send('Runtime.evaluate', {
            returnByValue: true,
            expression: `(() => {
              const sw = document.documentElement.scrollWidth;
              const cw = document.documentElement.clientWidth;
              const text = document.body ? document.body.innerText : '';
              const tareaMatch = text.match(/tarea\\s*\\d+/gi) || [];
              return { scrollWidth: sw, clientWidth: cw, tareaMatches: tareaMatch.slice(0, 5) };
            })()`,
          });

          const metrics = checkRes?.result?.value || {};
          if (metrics.scrollWidth > metrics.clientWidth + 2) {
            overflowIssues.push(`${nombre}_${vpName}_${theme}: scrollWidth=${metrics.scrollWidth} > clientWidth=${metrics.clientWidth}`);
          }
          if (esDataops && metrics.tareaMatches?.length) {
            taskLeakIssues.push(`${nombre}_${vpName}_${theme}: ${metrics.tareaMatches.join(', ')}`);
          }

          for (const ev of client.events.slice(evStart)) {
            if (ev.method === 'Runtime.exceptionThrown') {
              consoleErrors.push(`${nombre}_${vpName}_${theme}: ${ev.params?.exceptionDetails?.text || 'Exception'}`);
            } else if (ev.method === 'Runtime.consoleAPICalled' && ev.params?.type === 'error') {
              const txt = (ev.params.args || []).map((a) => a.value ?? a.description ?? '').join(' ');
              consoleErrors.push(`${nombre}_${vpName}_${theme}: ${txt}`);
            } else if (ev.method === 'Log.entryAdded' && ev.params?.entry?.level === 'error') {
              consoleErrors.push(`${nombre}_${vpName}_${theme}: ${ev.params.entry.text}`);
            }
          }

          if (vpName === '1440' || theme === 'light') {
            const shot = await client.send('Page.captureScreenshot', { format: 'png' });
            fs.writeFileSync(
              path.join(OUT_DIR, `${nombre}_${vpName}_${theme}.png`),
              Buffer.from(shot.data, 'base64')
            );
          }
        }
      }
    }

    const report = {
      ok: consoleErrors.length === 0 && taskLeakIssues.length === 0,
      consoleErrors,
      overflowIssues,
      taskLeakIssues,
      screenshotsDir: OUT_DIR,
    };
    console.log(JSON.stringify(report, null, 2));
    if (!report.ok) {
      process.exitCode = 1;
    }
  } finally {
    if (client) client.close();
    try { chrome.kill('SIGKILL'); } catch {}
    try { fs.rmSync(userDataDir, { recursive: true, force: true }); } catch {}
  }
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
