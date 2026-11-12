/** Cuenta reversible: un único envío, cancelable hasta que comiencen los diez segundos completos. */
export function crearEsperaRevision(onTick, onSend) {
  let timer;
  let tick;
  let active = false;
  let started = false;
  return {
    start() {
      if (active || started) return false;
      active = true;
      let seconds = 10;
      tick = setInterval(() => onTick(--seconds), 1000);
      timer = setTimeout(() => {
        if (!active) return;
        started = true;
        active = false;
        clearInterval(tick);
        onSend();
      }, 10000);
      return true;
    },
    cancel() {
      if (started) return false;
      active = false;
      clearTimeout(timer);
      clearInterval(tick);
      return true;
    },
  };
}
