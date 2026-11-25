# F10-4: Estabilidad de Animaciones, Scroll y Gráficas

- `useCountUpV2.js` y `AnimatedNumberV2.jsx`: soporte de `animateOnceKey` con caché en módulo (`_ANIMATED_KEYS`) para no reiniciar `0 → N` al cambiar de pestaña o re-renderizar en `BetoReadingFlowView.jsx` y `HumanReviewFlowView.jsx`.
- `chartAnimationsV2.js` y `BetoMetricasModal.jsx`: bandera `$v2InitialAnimDone`, `transitions.active.animation.duration = 0` y `useMemo` en `curvaData`/`curvaOptions` para evitar que el hover reinicie la animación de Chart.js.
