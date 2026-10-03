# Plantillas de mecánicas

El conocimiento del agente sobre un juego se arma con **plantillas de mecánicas**. Cada plantilla es una hipótesis genérica sobre juegos de cuadrícula, por ejemplo "¿este tipo bloquea?", "¿esto se empuja?" o "¿se gana por sobrevivir?", y se llena contando lo vivido. Cada una es un archivo en `boulder/mecanicas/`, con una clase que hereda de `Mecanica`.

## Interfaz

```python
class MiMecanica(Mecanica):
    nombre = "mi_mecanica"
    nucleo = False                     # True: no se puede apagar (sin ella el agente no camina)
    prioridad = 50                     # orden en que reacciona a cada evento
    estado = {"mis_conteos": (dict, "I>v")}   # campo → (valor inicial, forma para guardar/fusionar)
    neutros = {"mi_consulta": None}    # qué devuelve cada consulta si se la apaga (ablación)
    orden_opcion = None                # o un número: propone órdenes al alto nivel

    def al_paso(self, st, d, mask, moved, salto, fuente, **_):   # observar un evento
        ...                                                     # actualizar self.K.mis_conteos

    def mi_consulta(self, t):          # lo que el agente le pregunta (queda como K.mi_consulta)
        ...

    def opcion(self, cmd, st, info, vals, targets):              # opcional: proponer (casilla, tiempo)
        ...
```

Para agregar una mecánica:
1. Escribir su archivo.
2. Sumar la clase a `REGISTRO` en `boulder/mecanicas/__init__.py`.

No hace falta tocar el navegador ni el alto nivel. Guardar, cargar y fusionar lo aprendido (entre procesos y tras la práctica) sale del `estado` declarado. Apagarla para una ablación es `--sin mi_mecanica` en `play_hl.py` y en `budget.py`.

**Eventos que emite el agente** (con `K.emitir`):

| Evento | Cuándo |
|---|---|
| `paso` | el avatar intentó moverse |
| `toque` | entró o chocó con una casilla |
| `objeto_movio` | lo ve el rastreador de objetos |
| `empuje` | resultado de un empuje |
| `sonda_usar` | se resolvió una sonda de usar |
| `mitad` | muestra a mitad de partida |
| `fin` | terminó la partida |

**Enganches de uso:** las consultas de cada mecánica las usan el A* y el oráculo (bloqueo, giro), el cubo de predicción (dirección de objetos, movimiento relativo) y el valor de cada meta (toque, fin por conteo). Las mecánicas con `orden_opcion` proponen órdenes cuando no hay nada valioso que tocar: apuntar para usar, entrar a un portal, abrir camino. El plan de empujes es una consulta de `empujar`.

**Verificación:** `golden.py` juega partidas deterministas con una compilación de GVGAI sin límite de tiempo (`gvgai/build_notime.sh`) y compara acciones y conocimiento contra una referencia grabada. La refactorización a este formato dejó los 10 juegos idénticos.

## Catálogo (generado con `python -m boulder.mecanicas --md`)

| Mecánica | Núcleo | Estado | Eventos | Consultas | Opción | Apagada devuelve |
|---|---|---|---|---|---|---|
| **tipos** | sí | floor, avatar_types | — | observe_types | — | (núcleo) |
| **bloqueo** | sí | passed, blocked, by_res | paso | is_blocking, blocking_bits, blocked_cells | — | (núcleo) |
| **giro** |  | turns | paso | turn_cost_value | — | turn_cost_value=0 |
| **teletransporte** |  | teleport | paso | teleport_exit | sí | teleport_exit=None |
| **toque** | sí | eff, term | paso, toque, fin | p_win, novelty, effect | — | (núcleo) |
| **movimiento** | sí | move_dirs | objeto_movio | — | sí | (núcleo) |
| **relativo** |  | rel | objeto_movio | attractor | — | attractor=None |
| **usar** |  | use_kill, use_base, use_score | sonda_usar | use_lift, use_value, claves_usar, efecto_usar | sí | use_lift=0.0, use_value=0.0 |
| **empujar** |  | push, push_into | empuje | pushable, push_candidate, push_ok, push_value, plan_empujes | — | pushable=False, push_candidate=False, push_ok=False, push_value=(0.0, 0), plan_empujes=None |
| **fin_conteo** |  | ends | mitad, fin | despues_de_cargar, extinct_win, extinct_loss | — | extinct_win=False, extinct_loss=False |

**Umbrales** (los mismos en todos los juegos):

| Valor | Dónde se usa |
|---|---|
| 3 observaciones como mínimo | usar; fin por conteo al ganar o perder |
| 2 observaciones | portales; empujable si se desplazó ≥ 2 veces |
| 5 observaciones | fin por conteo a mitad de partida |
| 10 observaciones | movimiento relativo |
| 20 intentos | giro |
| 50 % | giro, empujar |
| 75 % | movimiento relativo |
| 80 % | dirección principal de un objeto; fin por conteo al ganar |
| "Chocó > 2 × pasó + 1" | bloqueo |

## Ablaciones (cuánto aporta cada plantilla)

En los 10 juegos de desarrollo: Sokoban, Aliens, Butterflies, Missilecommand, Portals, Chase, Survivezombies, Frogs, Zelda y Boulder Dash.
- Se apaga una mecánica al **jugar** (`--sin`), con el conocimiento de la práctica completa.
- Se usan 15 semillas: 30 partidas por juego, 75 en Frogs, Zelda y Boulder Dash.
- Margen aproximado: ±15 puntos con 30 partidas.
- En negrita, los cambios de 20 puntos o más.

| Apagada | Sok | Ali | But | Mis | Por | Cha | SZ | Fro | Zel | BD | Promedio | Δ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — (completa) | 100 | 100 | 100 | 83 | 27 | 13 | 0 | 91 | 84 | 55 | 65 |  |
| direcciones | 100 | 90 | 100 | 83 | 27 | 13 | 0 | 99 | 84 | 56 | 65 | -0 |
| giro | 100 | 100 | 100 | 70 | 27 | 10 | 0 | 97 | 75 | 51 | 63 | -2 |
| arrastre | 100 | 100 | 100 | 83 | 27 | 10 | 0 | 99 | 84 | 56 | 66 | +1 |
| teletransporte | 100 | 100 | 100 | 83 | **0** | 13 | 0 | 88 | 81 | 55 | 62 | -3 |
| letalidad | 100 | 100 | 100 | 83 | 27 | 13 | 0 | 89 | 83 | 55 | 65 | -0 |
| consumo | 100 | 100 | 100 | 83 | 27 | 10 | 0 | 95 | 85 | 56 | 66 | +0 |
| caida | 100 | 100 | 100 | 83 | 27 | 10 | 0 | 96 | 83 | 57 | 66 | +0 |
| relativo | 100 | 100 | 100 | 67 | 23 | 3 | 0 | 96 | 85 | 55 | 63 | -2 |
| usar | 100 | **0** | 100 | **50** | 27 | 10 | 0 | 93 | 87 | 57 | 52 | -13 |
| empujar | **0** | 100 | 100 | 83 | 27 | 13 | 0 | 87 | 84 | 57 | 55 | -10 |
| fin_conteo | 100 | 100 | 100 | 67 | 23 | 13 | 0 | 88 | 84 | 56 | 63 | -2 |
| fin_tiempo | 100 | 100 | 100 | 83 | 27 | 13 | 0 | 95 | 83 | 56 | 66 | +0 |

**Lectura:**
- **Tres plantillas deciden juegos enteros:**
  - **usar:** Aliens de 100 a 0 %, Missilecommand de 83 a 50 %;
  - **empujar:** Sokoban de 100 a 0 %;
  - **teletransporte:** Portals de 27 a 0 %.

  Cada una es necesaria en su familia de juegos y no interfiere en las demás.
- **Efectos chicos, dentro del margen:**
  - **relativo** en Chase (13 → 3 %) y Missilecommand;
  - **giro** en Zelda (84 → 75 %);
  - **fin_conteo** en Missilecommand.
- **Sin efecto medible en estos juegos:** direcciones, arrastre, letalidad, consumo, caída y fin_tiempo. Hay que leerlo con cuidado:
  - **Direcciones y letalidad** se agregaron por Ikaruga, que no está entre estos 10.
  - **Arrastre, caída y consumo** pesan en otro momento: apagadas solo al jugar, el resto de lo aprendido (el riesgo, por ejemplo) ya compensa. Apagarlas también durante la práctica mediría mejor su aporte. Esa es la ablación pendiente.
- **La configuración completa da 65 % de promedio en esta corrida.** Missilecommand dio 83 % (antes 60 %) y Aliens 100 %. Esa variación entre corridas es justamente el ruido que hay que reportar.

### Ablación también durante la práctica

Para las 6 plantillas sin efecto al apagarlas solo al jugar, se las apagó también en la práctica de 40 partidas: desde `knowledge.json`, con la mecánica apagada, y después se evaluó igual. Para comparar en las mismas condiciones, la configuración completa también se practicó de nuevo con el código actual.

| Apagada (práctica y juego) | Sok | Ali | But | Mis | Por | Cha | SZ | Fro | Zel | BD | Promedio | Δ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — (completa, practicada de nuevo) | 100 | 97 | 100 | 50 | 23 | 10 | 0 | 92 | 85 | 56 | 61 |  |
| direcciones | 100 | 97 | 100 | 57 | 27 | 7 | 0 | 92 | 85 | 56 | 62 | +1 |
| arrastre | 100 | 100 | 100 | 50 | 27 | 10 | 0 | 93 | 83 | 56 | 62 | +1 |
| letalidad | 100 | 93 | 100 | 53 | 27 | 13 | 0 | 92 | 85 | 56 | 62 | +1 |
| consumo | 100 | 93 | 100 | 53 | 27 | 7 | 0 | 99 | 84 | 56 | 62 | +1 |
| caida | 100 | 93 | 100 | 50 | 27 | 13 | 0 | 96 | 84 | 55 | 62 | +0 |
| fin_tiempo | 100 | 97 | 100 | 50 | 23 | 20 | 0 | 100 | 84 | 55 | 63 | +2 |

**Lectura:**
- **Ninguna de las 6 cambia el resultado en estos 10 juegos**, ni siquiera apagada desde la práctica.
- Ahí lo cubren otras partes del agente:
  - el riesgo aprendido ya sabe que el agua con tronco es segura (arrastre);
  - el cubo ya predice las rocas que caen (caída);
  - la exploración encuentra lo que se consume (consumo).
- **Direcciones y letalidad** se agregaron por Ikaruga, que no está en este conjunto.
- **Fin por tiempo** solo actúa en Survivezombies, que nadie gana.
- **Para el artículo:** de las 12 plantillas que se pueden apagar, 3 son decisivas en su familia (usar, empujar, teletransporte), 3 tienen efectos chicos (relativo, giro, fin por conteo) y 6 son redundantes en los juegos de desarrollo. Las 6 redundantes hay que justificarlas con juegos donde importen, o declarar que no aportan.
- **El ruido entre corridas es grande en Missilecommand:** la configuración completa dio 83 % en la tabla anterior y 50 % aquí. El nivel 3 alterna entre ganarse a veces y casi nunca.

## Simplificación: de 16 a 10 plantillas

Se quitaron las 6 plantillas que no aportaban en los juegos de desarrollo: direcciones, arrastre, letalidad, consumo, caída y fin por tiempo.
- "Abrir camino" pasó a `movimiento`, del núcleo, porque solo usa hacia dónde se mueve cada tipo.
- La "imaginación" de trampas, que dependía de consumo y caída, se quitó. Entre metas de igual puntaje se conserva el desempate por la de más abajo y a la derecha, que era todo su aporte en Boulder Dash.

Comparación con práctica nueva y la misma evaluación (15 semillas):

| | Sok | Ali | But | Mis | Por | Cha | SZ | Fro | Zel | BD | Prom. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 16 plantillas | 100 | 97 | 100 | 50 | 23 | 10 | 0 | 92 | 85 | 56 | 61 |
| 10 plantillas | 100 | 90 | 100 | 50 | 27 | 17 | 0 | 95 | 84 | 57 | 62 |

Igual rendimiento con un agente más simple. Las 6 quitadas siguen en la rama `modular` antes del commit de esta simplificación, por si algún juego futuro las necesita.
- **Direcciones y letalidad** se habían agregado por Ikaruga (juego no visto, a posteriori): en Ikaruga bajaban los plazos agotados, pero no las derrotas.
- La prueba en juegos no vistos (`PRUEBA_NO_VISTOS.md`) se corrió con el código congelado anterior a todo esto.

## Prueba: decisiones con probabilidades en vez de umbrales (rama `bayes`)

Cada "sí/no" contado es una tasa con previo Beta(1, 1). Una plantilla concluye cuando P(tasa > nivel) ≥ C, con C = 0,8 (`MECANICAS_CONF`). Por ejemplo:
- "bloquea" = P(chocar > 1/2) ≥ C;
- "persigue" = P(acercarse > 0,7) ≥ C;
- "se pierde si se extingue" = P(extinto al perder > 1/2) ≥ C y P(extinto a mitad de partida < 1/2) ≥ C.

Esto reemplaza los mínimos de observaciones y los porcentajes de bloqueo, giro, movimiento relativo, usar, empujar y fin por conteo. Quedan dos constantes globales: el previo y C.

Comparación con práctica nueva y la misma evaluación (15 semillas):

| | Sok | Ali | But | Mis | Por | Cha | SZ | Fro | Zel | BD | Prom. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| umbrales a mano | 100 | 90 | 100 | 50 | 27 | 17 | 0 | 95 | 84 | 57 | 62 |
| probabilidades (C = 0,8) | 100 | 93 | 100 | 53 | 23 | 13 | 0 | 89 | 84 | 55 | 61 |

Mismo rendimiento, dentro del ruido. El sistema queda descrito como un modelo bayesiano factorizado con una sola regla de decisión.

Siguen fuera de esta regla:
- los umbrales del rastreador de objetos: dirección principal ≥ 80 %, "al azar" si cambia de dirección > 25 %;
- el "≥ 2 saltos" de teletransporte, que es una regla de existencia y no de proporción.

**Sensibilidad al nivel de confianza C** (práctica nueva y evaluación con 15 semillas para cada valor):

| | Sok | Ali | But | Mis | Por | Cha | SZ | Fro | Zel | BD | Prom. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| umbrales a mano | 100 | 90 | 100 | 50 | 27 | 17 | 0 | 95 | 84 | 57 | 62 |
| C = 0,7 | 100 | 77 | 100 | 53 | 27 | 10 | 0 | 93 | 84 | 55 | 60 |
| C = 0,8 | 100 | 93 | 100 | 53 | 23 | 13 | 0 | 89 | 84 | 55 | 61 |
| C = 0,9 | 100 | 90 | 100 | 70 | 27 | 10 | 0 | 95 | 83 | 56 | 63 |

El resultado no depende finamente de C: entre 0,7 y 0,9 el promedio va de 60 a 63 %, y las diferencias por juego están dentro del ruido (±15 puntos con 30 partidas). Se deja C = 0,8, el valor central elegido antes de ver estos resultados.

## Efectos causales y medios y fines (rama `estrategias`)

Plantilla nueva `efectos`: cada tick compara cuántas casillas tiene cada tipo. Aprende "si X desaparece, Y desaparece" (y "si el avatar toca X, Y desaparece") cuando casi siempre que X desaparece también lo hace Y, e Y casi nunca desaparece solo. Con eso, el alto nivel razona hacia atrás: si lo valioso (o terreno nunca pisado) queda tapado por un bloqueo D que se sabe quitar, la causa de D vale lo tapado, encadenando hasta tres pasos con descuento 0,9. El plan de empujes lleva la causa adonde desaparece junto con su compañero (la caja a su hoyo).

Arreglo genérico en `budget.py`: una derrota en un tick final ya visto antes es el límite de tiempo del juego, no una muerte (en Doorkoban nada mata y se aprendían 51 muertes falsas que paralizaban al navegador).

Doorkoban (no visto antes, 5 minutos de entrenamiento, niveles 3–4, 15 semillas): base 0 % (puntaje 0,9) → solo efectos 3 % (puntaje 15,5: abre las cuatro puertas pero no sale) → con el arreglo del tiempo **100 %**.

Regresión en los 10 juegos de desarrollo (práctica de 40 partidas desde cero, 15 semillas):

| versión | Sokoban | Aliens | Butterflies | Missilecommand | Portals | Chase | Survivezombies | Frogs | Zelda | Boulder Dash | prom. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| probabilidades (C = 0,8) | 100 | 93 | 100 | 53 | 23 | 13 | 0 | 89 | 84 | 55 | 61 |
| + efectos causales | 100 | 100 | 100 | 63 | 27 | 17 | 0 | 95 | 83 | 57 | 64 |
| + encuentros y «dejar caer» | 100 | 93 | 100 | 50 | 23 | 17 | 0 | 97 | 87 | 59 | 63 |

### Encuentros e imaginación

Plantilla `encuentros`: por par de tipos (a, b) y por lado de b (encima, arriba, derecha, abajo, izquierda) cuenta cuántas veces estuvieron juntos sin pasar nada y cuántas a desapareció (con el Δpuntaje). "b mata a a desde ese lado" si P(tasa > 0,2) ≥ C.

Imaginar: un par que casi no se probó desde un lado es una hipótesis. Probarla vale según cuánto importa b (mata, bloquea o vale). Eso lo usan:
- la curiosidad del plan de empujes;
- el medio «dejar caer»: cavar lo que sostiene un objeto que siempre cae en una dirección, cuando en su línea de caída hay algo con que encontrarse.

En la variante `boulderdash_roca` (la roca que cae desde arriba mata a la mariposa, +2) se aprende "roca desde arriba mata mariposa" en 120 s de entrenamiento: 8 de 29 encuentros desde arriba, 0 de 1124 desde abajo. En los 10 juegos de desarrollo no cambia el promedio (63 % contra 64 %, dentro del ruido).
