# Generador de cuevas cooperativas

Herramientas con las que se hicieron las [10 cuevas cooperativas](../../docs/cuevas-cooperativas.md).

- `python3 run.py N [intentos]`: genera la cueva N (0 a 9) según su especificación en `run.py`, la resuelve con `gen.py` y la guarda en `cN.json` (mapa, letras propias, solución y posiciones).
- `gen.py`: el modelo (salas, puertas, placas, palancas, relojes, barreras), el resolvedor (búsqueda en anchura sobre los dos niños) y el dibujo del mapa de 40 × 22.
- `python3 mkdbg.py ../../index.html DIR` hace una copia del juego con un acceso para pruebas, y `node replay.mjs DIR DIR_DE_LOS_JSON` juega cada solución en el juego de verdad (necesita Playwright).
