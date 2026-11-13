import { test } from 'node:test';
import assert from 'node:assert/strict';
import { crearColaRevision } from '../../frontend/src/modules/dataops/hooks/colaRevision.mjs';

test('la espera de una operación no bloquea programar la siguiente; cada una se envía a sus diez segundos', t => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  const enviadas = [];
  let lista = [];
  const cola = crearColaRevision(l => { lista = l; }, op => enviadas.push(op.title));
  assert.equal(cola.schedule('Aprobar grupo A', () => {}), 1);
  t.mock.timers.tick(4000);
  assert.equal(cola.schedule('Aprobar grupo B', () => {}), 2);
  assert.deepEqual(lista.map(o => o.title), ['Aprobar grupo A', 'Aprobar grupo B']);
  t.mock.timers.tick(6000);
  assert.deepEqual(enviadas, ['Aprobar grupo A']);
  assert.deepEqual(lista.map(o => o.title), ['Aprobar grupo B']);
  t.mock.timers.tick(4000);
  assert.deepEqual(enviadas, ['Aprobar grupo A', 'Aprobar grupo B']);
  assert.equal(cola.size(), 0);
});

test('la misma operación no se programa dos veces y Deshacer cancela solo la elegida', t => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  const enviadas = [];
  const cola = crearColaRevision(() => {}, op => enviadas.push(op.title));
  const a = cola.schedule('Aprobar caso 7', () => {});
  assert.equal(cola.schedule('Aprobar caso 7', () => {}), null);
  cola.schedule('Aprobar caso 8', () => {});
  assert.equal(cola.cancel(a), true);
  assert.equal(cola.cancel(a), false);
  t.mock.timers.tick(10000);
  assert.deepEqual(enviadas, ['Aprobar caso 8']);
});

test('salir de la pantalla cancela todas las esperas sin enviar nada', t => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  let enviadas = 0;
  const cola = crearColaRevision(() => {}, () => enviadas++);
  cola.schedule('Uno', () => {});
  cola.schedule('Dos', () => {});
  cola.cancelAll();
  t.mock.timers.tick(30000);
  assert.equal(enviadas, 0);
  assert.equal(cola.size(), 0);
});
