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

## Resultados

Niveles 3–4, 15 semillas, 30 partidas por celda. Las referencias corrieron de a una partida. Ningún agente falló por error de ejecución.

| Juego | Nosotros (5 min, sin simulador) | YOLOBOT (simulador cada tick) | OLETS (simulador cada tick) |
|---|---|---|---|
| doorkoban | 0 % | **97 %** | 0 % |
| flower | **100 %** | 93 % | 87 % |
| grow | 0 % | 0 % | 0 % |
| ikaruga | 3 % | **53 %** | 50 % |
| pacman | 0 % | 0 % | 7 % |
| racebet2 | 0 % | **67 %** | 27 % |
| run | 3 % | 3 % | 0 % |
| themole | 0 % | 0 % | 0 % |
| whackamole | 50 % | 80 % | **97 %** |
| zenpuzzle | 0 % | 50 % | 50 % |
| **Promedio** | **16 %** | **44 %** | **32 %** |

**Lectura:** en juegos que nadie de este trabajo había mirado, el agente queda muy por debajo de los que consultan el simulador en cada tick (16 % contra 44 % y 32 %).
- **Donde el juego es moverse, recoger y esquivar,** se iguala o se supera a las referencias: flower 100 %.
- **Donde hacen falta cadenas de efectos que ninguna plantilla representa,** el agente se queda en 0 % o casi:
  - en doorkoban, llenar un hoyo abre una puerta;
  - en racebet2, apostar al camello que va a ganar;
  - en zenpuzzle, pisar cada casilla una sola vez.

  Ahí el simulador de las referencias encuentra la secuencia por búsqueda.
- **En 4 juegos nadie gana:** grow, pacman, run y themole.
- **La diferencia contra los 10 juegos de desarrollo** (61 % contra 57 % y 56 %) mide cuánto del resultado anterior venía de haber diseñado las plantillas mirando esos juegos.

## Después de la prueba: efectos causales y el límite de tiempo (no registrado de antemano)

Doorkoban se miró para diseñar estos cambios, así que este resultado **ya no es una prueba en juegos no vistos**: sirve para ver cuánto cambia, no como afirmación de generalización. Para eso hará falta un sorteo nuevo.

Cambios:
- plantilla `efectos`: qué desaparece cuando desaparece otra cosa, con medios y fines hacia atrás;
- `budget.py`: perder en un tick final ya visto antes es el límite de tiempo, no una muerte.

Mismo protocolo: 5 minutos, niveles 3–4, 15 semillas.

| Juego | Antes | Con efectos causales y el arreglo del tiempo | Muertes etiquetadas (antes → ahora) |
|---|---|---|---|
| doorkoban | 0 % | **100 %** | (51 → 0 en la prueba de desarrollo) |
| flower | 100 % | 100 % | |
| grow | 0 % | 0 % | |
| ikaruga | 3 % | 0 % | |
| pacman | 0 % | 0 % | |
| racebet2 | 0 % | **50 %** (nivel 3: 15/15, nivel 4: 0/15) | 321 → 141 |
| run | 3 % | 0 % | |
| themole | 0 % | 0 % | |
| whackamole | 50 % | 70 % | 379 → 286 |
| zenpuzzle | 0 % | 0 % | |
| **Promedio** | **16 %** | **32 %** | |

Referencias: YOLOBOT 44 %, OLETS 32 %.

En racebet2 y whackamole la mejora viene sobre todo de no aprender muertes falsas. Racebet2 se pierde por tiempo, igual que doorkoban. Racebet2 no se miró al diseñar los cambios.
