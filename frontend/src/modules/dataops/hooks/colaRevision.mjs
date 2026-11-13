import { crearEsperaRevision } from './esperaRevision.mjs';

/**
 * Varias operaciones pendientes a la vez, cada una con su propia cuenta reversible de diez segundos.
 * La espera de una no bloquea programar la siguiente; la misma operación (mismo título) no se programa dos veces.
 * onChange recibe la lista pendiente [{id, title, seconds}]; onSend(op) se llama cuando una cuenta termina.
 */
export function crearColaRevision(onChange, onSend) {
  let seq = 0;
  const ops = [];
  const emit = () => onChange(ops.map(op => ({ id: op.id, title: op.title, seconds: op.seconds })));
  const quitar = op => {
    const i = ops.indexOf(op);
    if (i >= 0) ops.splice(i, 1);
  };
  return {
    schedule(title, execute) {
      if (ops.some(op => op.title === title)) return null;
      const op = { id: ++seq, title, seconds: 10, execute };
      op.wait = crearEsperaRevision(seconds => {
        op.seconds = Math.max(0, seconds);
        emit();
      }, () => {
        quitar(op);
        emit();
        onSend(op);
      });
      ops.push(op);
      op.wait.start();
      emit();
      return op.id;
    },
    cancel(id) {
      const op = ops.find(o => o.id === id);
      if (!op) return false;
      op.wait.cancel();
      quitar(op);
      emit();
      return true;
    },
    cancelAll() {
      ops.splice(0).forEach(op => op.wait.cancel());
      emit();
    },
    size() {
      return ops.length;
    },
  };
}
