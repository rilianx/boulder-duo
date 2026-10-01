# Prueba en juegos no vistos: protocolo registrado antes de correr

- **Código congelado:** rama `congelado-prueba`, que contiene este archivo. Después de registrar esto no se cambia nada del agente para estos juegos.
- **Sorteo:**
  - Universo: los juegos de `examples/gridphysics` de GVGAI que tienen los niveles 0–4.
  - Se excluyen los 10 de desarrollo (aliens, boulderdash, butterflies, chase, frogs, missilecommand, portals, sokoban, survivezombies, zelda) y las variantes `_ggame`/`_glvl`. Quedan 108 juegos.
  - Se eligen 10 con `random.Random(20261001).sample(pool, 10)`.
- **Juegos sorteados:** doorkoban, flower, grow, ikaruga, pacman, racebet2, run, themole, whackamole, zenpuzzle.
- **Nuestro agente:** `budget.py <juego> --budget 300 --out heldout --eval --seeds 15`.
  - Aprende desde cero, en 5 minutos de reloj y un proceso, en los niveles 0–2, sin simulador.
  - Se evalúa en los niveles 3–4 con 15 semillas: 30 partidas.
- **Referencias:** YOLOBOT y OLETS en los mismos niveles 3–4 con 15 semillas, de a una partida (`gvgai_baselines.py --procs 1`).
- **Regla de fallas:** si un juego hace fallar a un agente, cuenta como 0 % y no se reemplaza.
- **Se reporta todo,** incluidos los juegos donde nos va mal.
