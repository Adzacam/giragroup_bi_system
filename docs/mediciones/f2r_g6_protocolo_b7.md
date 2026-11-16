# Protocolo de medición de tiempos para B-7 (F3)

## 1. Hallazgos de G-6 que justifican el protocolo
- `lectura_beto_s` permanece estable entre `125.9 s` y `135.4 s`; la variación ocurre casi exclusivamente en `consolidacion_s` (`627.6 s` en D3B r1, `731–732 s` en F2-6 c1/c2, `1,068.1 s` en F2-6 c3).
- En la corrida 3 de F2-6 (`1,203.36 s`), `recursos_corrida_3.json` registró contención externa de CPU en el host (`host_cpu_pct` promedio `56.0%`, pico `97.1%`, RAM pico `28,687.8 MB`) frente al rango base de las corridas 1 y 2 (`30.4%–32.3%` promedio).

## 2. Reglas obligatorias para ejecutar B-7 en F3
1. **Contenedores permitidos:** únicamente la pila Docker del proyecto (`9` servicios `giragroup_*`) más `beto_pg_tmpfs`. Sin `frontend` dev server (`vite`), sin `pytest`, sin notebooks ni procesos de entrenamiento/inferencia paralelos.
2. **Plan de energía y equipo:** equipo conectado a corriente AC, plan de energía en **Alto rendimiento / Máximo rendimiento**, sin suspensión ni ahorro de batería.
3. **Calentamiento (warm-up) y reposo:** verificar `docker stats --no-stream` antes de iniciar; esperar `30 s` de reposo entre corridas para estabilizar temperatura y caché de SO.
4. **Orden de ejecución:** 3 corridas consecutivas sobre clones `tmpfs` limpios (`dw_vacio` + migración `016`, `CACHE_VACIA=1`, 4 flags `False`, `beto-v2`), muestreando `psutil` + `docker stats` cada `5 s`.
5. **Criterio de descarte de corrida:** se descarta y repite una corrida únicamente si ocurre contención externa comprobada (`host_cpu_pct` promedio `> 45%` ajeno a Docker o pico `>= 95%` sostenido) o error de infraestructura, dejando constancia explícita en `corridas.json`.
6. **Reporte:** informar media, desviación estándar muestral ($n-1$), mínimo y máximo de `tiempo_maquina_s` (solo máquina) y `tiempo_maquina + KLM` (con $W=10\text{ s}$ y $W=0\text{ s}$) usando la fórmula canónica de `scripts/agregar_flujo_repetido.py::klm`.
