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
| `quieto` | esperó sobre algo |
| `toque` | entró o chocó con una casilla |
| `objeto_movio`, `objeto_avance` | los ve el rastreador de objetos |
| `empuje` | resultado de un empuje |
| `sonda_usar` | se resolvió una sonda de usar |
| `mitad` | muestra a mitad de partida |
| `fin` | terminó la partida |

**Enganches de uso:** las consultas de cada mecánica las usan el A* y el oráculo (bloqueo, direcciones, giro, arrastre), el cubo de predicción (dirección de objetos, caída, movimiento relativo), el riesgo (letalidad) y el valor de cada meta (toque, fin por conteo). Las mecánicas con `orden_opcion` proponen órdenes cuando no hay nada valioso que tocar: apuntar para usar, entrar a un portal, abrir camino, sobrevivir. El plan de empujes es una consulta de `empujar`.

**Verificación:** `golden.py` juega partidas deterministas con una compilación de GVGAI sin límite de tiempo (`gvgai/build_notime.sh`) y compara acciones y conocimiento contra una referencia grabada. La refactorización a este formato dejó los 10 juegos idénticos.

## Catálogo (generado con `python -m boulder.mecanicas --md`)

| Mecánica | Núcleo | Estado | Eventos | Consultas | Opción | Apagada devuelve |
|---|---|---|---|---|---|---|
| **tipos** | sí | floor, avatar_types | — | observe_types | — | (núcleo) |
| **bloqueo** | sí | passed, blocked, by_res | paso | is_blocking, blocking_bits, blocked_cells | — | (núcleo) |
| **direcciones** |  | dir_moves | paso | dir_ok | — | dir_ok=True |
| **giro** |  | turns | paso | turn_cost_value | — | turn_cost_value=0 |
| **arrastre** |  | carry | quieto | carriers | — | carriers=set() |
| **teletransporte** |  | teleport | paso | teleport_exit | sí | teleport_exit=None |
| **toque** | sí | eff, term | paso, toque, fin | p_win, novelty, effect | — | (núcleo) |
| **letalidad** |  | — | — | lethality | — | lethality=0.0 |
| **consumo** |  | consumed | toque | is_consumed | — | is_consumed=False |
| **movimiento** | sí | move_dirs | objeto_movio | — | — | (núcleo) |
| **caida** |  | fall | objeto_avance | p_move_into | sí | p_move_into=0.0 |
| **relativo** |  | rel | objeto_movio | attractor | — | attractor=None |
| **usar** |  | use_kill, use_base, use_score | sonda_usar | use_lift, use_value, claves_usar, efecto_usar | sí | use_lift=0.0, use_value=0.0 |
| **empujar** |  | push, push_into | empuje | pushable, push_candidate, push_ok, push_value, plan_empujes | — | pushable=False, push_candidate=False, push_ok=False, push_value=(0.0, 0), plan_empujes=None |
| **fin_conteo** |  | ends | mitad, fin | despues_de_cargar, extinct_win, extinct_loss | — | extinct_win=False, extinct_loss=False |
| **fin_tiempo** |  | end_ticks | fin | time_limit | sí | time_limit=None |

**Umbrales** (los mismos en todos los juegos):

| Valor | Dónde se usa |
|---|---|
| 3 observaciones como mínimo | consumo, caída, usar, letalidad (3 muertes), fin por conteo al ganar o perder |
| 2 observaciones | portales; empujable si se desplazó ≥ 2 veces |
| 5 observaciones | arrastre; fin por conteo a mitad de partida |
| 10 observaciones | movimiento relativo |
| 15 intentos | direcciones (éxito ≤ 5 % la descarta) |
| 20 intentos | giro |
| 50 % | consumo, arrastre, giro, empujar, letalidad |
| 75 % | movimiento relativo |
| 80 % | dirección principal de un objeto; fin por conteo al ganar |
| "Chocó > 2 × pasó + 1" | bloqueo |
