// Correcciones F3W: imports, 3 pasos en V1/V2 y barra superior a 375 px (inspección de fuentes).
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const SRC = path.resolve(__dirname, '../../..');
const read = (p) => fs.readFileSync(path.join(SRC, p), 'utf8');
const walk = (dir) => fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
  const full = path.join(dir, e.name);
  if (e.isDirectory()) return e.name === '__tests__' ? [] : walk(full);
  return /\.(jsx?|css)$/.test(e.name) ? [full] : [];
});

describe('F3W correcciones de frontend', () => {
  it('todo archivo que usa toDataopsPath lo importa o lo define', () => {
    const malos = walk(SRC).filter((f) => {
      const t = fs.readFileSync(f, 'utf8');
      return /toDataopsPath\(/.test(t) && !/import\s*\{[^}]*toDataopsPath[^}]*\}/.test(t) && !/function toDataopsPath/.test(t);
    });
    expect(malos).toEqual([]);
  });

  it('el menú lateral V2 del flujo DataOps tiene exactamente 3 pasos numerados', () => {
    const t = read('v2/layout/SidebarV2.jsx');
    const pasos = t.match(/'[①②③④⑤] [^']+'/g) || [];
    expect(new Set(pasos.map((p) => p[1]))).toEqual(new Set(['①', '②', '③']));
    expect(t).not.toMatch(/④/);
  });

  it('ninguna referencia visible a 4 pasos', () => {
    const hallazgos = walk(SRC).filter((f) => /cuatro pasos|4 pasos|de 4 pasos/i.test(fs.readFileSync(f, 'utf8')));
    expect(hallazgos).toEqual([]);
  });

  it('la barra superior V1 oculta la etiqueta "Versión 2" a <=480 px', () => {
    expect(read('components/layout/Navbar.jsx')).toContain('navbar-v2-label');
    const css = read('styles/tokens.css');
    const bloque = css.slice(css.indexOf('@media (max-width: 480px)'));
    expect(bloque).toMatch(/\.navbar-v2-label\s*\{\s*display:\s*none/);
  });
});
