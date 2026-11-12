import { test } from 'node:test';
import assert from 'node:assert/strict';
import { crearEsperaRevision } from '../frontend/src/modules/dataops/hooks/esperaRevision.mjs';

test('no envía antes de diez segundos y bloquea un segundo inicio', t => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  let calls = 0;
  const espera = crearEsperaRevision(() => {}, () => calls++);
  assert.equal(espera.start(), true);
  assert.equal(espera.start(), false);
  t.mock.timers.tick(9999);
  assert.equal(calls, 0);
  t.mock.timers.tick(1);
  assert.equal(calls, 1);
  t.mock.timers.tick(20000);
  assert.equal(calls, 1);
  assert.equal(espera.cancel(), false);
});

test('deshacer o salir durante la espera evita cualquier envío', t => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  let calls = 0;
  const espera = crearEsperaRevision(() => {}, () => calls++);
  espera.start();
  t.mock.timers.tick(9000);
  assert.equal(espera.cancel(), true);
  t.mock.timers.tick(60000);
  assert.equal(calls, 0);
});
