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
