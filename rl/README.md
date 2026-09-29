# Entrenar al PC con un transformer

Esta carpeta tiene lo necesario para entrenar al rival de Boulder Dúo con RL profundo, en vez de la tabla Q(λ) que corre dentro de `index.html`:
- una copia en Python de la simulación del juego,
- un tokenizador de entidades,
- un transformer entrenado con PPO.

```
cd rl
pip install -r requirements.txt
python -m pytest -q                                   # paridad con el juego + tokenizador
python train_ppo.py --name base --steps 2000000       # entrenar (Ctrl-C guarda y sale)
python train_ppo.py --name base --steps 4000000 --resume
python export_onnx.py --name base                     # → runs/base/policy.onnx
python baseline.py --lives 300                        # baseline con A*
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `boulder/sim.py` | Copia de la física de `index.html` (modo "Entrenar PC"): generación de niveles con el mismo mulberry32, caídas, rodado, empuje, enemigos, explosiones, reaparición y reloj. |
| `boulder/env.py` | Entorno con API estilo Gymnasium. Un episodio es una vida del PC. |
| `boulder/tokens.py` | Convierte el estado en tokens de entidades con datos locales. |
| `boulder/model.py` | Transformer (d = 64, 3 capas, 4 cabezas, unos 107.000 parámetros). |
| `boulder/vec.py` | Entornos en varios procesos. |
| `train_ppo.py` | PPO con GAE. Guarda `runs/<nombre>/ckpt.pt` y `metrics.csv`. |
| `export_onnx.py` | Exporta la política para correrla en el navegador con onnxruntime-web. |
| `boulder/astar.py` | Dijkstra/A\* desde el PC hasta el objetivo más barato, con costos de peligro. |
| `baseline.py` | Política trivial con A\*: ir a la gema más barata y, con la cuota cumplida, a la salida. |
| `tests/` | Tests de paridad con el juego y del tokenizador. |

## Paridad con el juego

`tests/fixtures/js_traces.json` se genera con el juego real. `gen_js_traces.cjs` abre `index.html` en Chromium headless y lo maneja con el hook `window.__sim`. Son 6 niveles con 500 acciones cada uno, y se guarda un hash de la grilla y del agente en cada tick. `test_parity.py` exige que la versión Python dé los mismos hashes en los 3.000 ticks.

Si cambias la física en `index.html`, regenera las trazas y corre los tests:

```
NODE_PATH=$(npm root -g) node tests/gen_js_traces.cjs   # requiere el paquete playwright
python -m pytest -q
```

## Observación: tokens de entidades con datos locales

No hay tokens de terreno. El terreno entra como vecindario local de cada entidad, y así la observación queda en **32 tokens × 91 características**:

- **Token 0, el propio PC:** su vecindario y los datos globales (gemas respecto a la cuota, si la salida está abierta, tiempo restante, si es inmune, si viene una roca cayendo por su columna, el contador de empuje y las gemas a la vista).
- **Entidades de su pantalla (17×12),** ordenadas por cercanía: rocas, gemas, luciérnagas, mariposas, explosiones y la salida.
- **Fuera de pantalla:** hasta 4 gemas y la salida, marcadas como "fuera de vista".

Cada token de entidad lleva:
- su tipo,
- Δx y Δy con signo respecto al PC,
- la distancia Manhattan y la distancia BFS por casillas transitables,
- si está cayendo,
- hacia dónde se mueve (en el caso de los enemigos),
- si se puede empujar a la izquierda o a la derecha,
- las 8 casillas que lo rodean y la casilla 2 más abajo, en 7 clases: vacío, tierra, sólido, roca, gema, enemigo y jugador.

Ese vecindario es lo que permite distinguir una roca apoyada en tierra (inofensiva) de una roca sobre un hueco (va a caer). El detalle de cada columna está en `boulder/tokens.py`.

## Recompensas

Son las mismas del Q(λ) del juego, para poder comparar:

| Evento | Recompensa |
|---|---|
| Gema | +5 |
| Salir | +60 |
| Morir | −40 |
| Cada paso | −0,05 |
| Chocar con algo | −0,3 |
| Acercarse al objetivo | +0,4 por casilla |

"Acercarse al objetivo" se mide por la ruta segura más corta dentro de la pantalla hacia la gema más cercana, o hacia la salida si ya está abierta.

## Rendimiento en CPU (4 núcleos, sin GPU)

- **El entorno solo:** unos 1.900 pasos por segundo por proceso.
- **El entrenamiento completo:** unos 780 pasos por segundo, con 3 procesos de entornos × 8 entornos, 64 pasos por rollout, 4 épocas y minibatch de 512. Durante la actualización la red usa todos los núcleos.
- **Qué lo frena:** la mayor parte del tiempo se va en el backward del transformer. Con GPU o menos épocas debería subir bastante.

## Resultados hasta ahora

Todas las cifras usan la misma definición: un episodio es una vida del PC, en niveles del 1 al 12.

| Agente | Gemas por vida | Llega a la salida | Muere | Se le acaba el tiempo |
|---|---|---|---|---|
| PPO + transformer, 1,1 M de pasos (25 min en CPU) | 2,2 | 0 % | 14 % | 86 % |
| Q(λ) tabular del juego (λ = 0,3), unas 20.000 vidas | 10,4 | 18,5 % | 45 % | 36 % |
| **A\* trivial, peligro = 25** | **13,7** | **85 %** | **15 %** | **0 %** |
| A\* trivial, peligro = ∞ (prohibido) | 14,3 | 79 % | 7 % | 14 % |
| A\* trivial, peligro = 5 | 10,6 | 63 % | 30 % | 7 % |
| A\* trivial, peligro = 0 (lo ignora) | 7,1 | 34 % | 53 % | 13 % |

Cada fila de A\* promedia 300 vidas.

- **PPO con una acción por tick se vuelve pasivo:** aprende a no morir, pero junta pocas gemas y nunca sale.
- **El A\* sin nada aprendido supera por mucho al Q(λ).** Eso respalda cambiar el espacio de acciones: que la red elija un destino (un token) y A\* se encargue de llegar.
- **Qué aporta cada nivel de peligro:**
  - **Ignorarlo** mata al PC la mitad de las veces.
  - **Prohibirlo** lo deja atascado cuando la única ruta es riesgosa.
  - **Un costo alto (25)** equilibra las dos cosas.

Siguiente paso: acciones de alto nivel. La red apunta a un token (gema, salida, lado de una roca empujable, casilla de refugio o esperar), A\* con costos de peligro recalcula la ruta en cada tick, la acción termina al llegar, al desaparecer el destino o por peligro, y el entrenamiento es PPO semi-Markov. El baseline de A\* es la vara a superar.

## Destinos, CEM y predictor de muerte (nuestro juego)

Evaluación final: 800 vidas con semillas que no se usaron para ajustar.

| Agente | Gemas por vida | Salida | Muere | Se le acaba el tiempo |
|---|---|---|---|---|
| Red con destinos (PPO semi-Markov, unas 420.000 decisiones) | 16,9 | 68 % | 26 % | 6 % |
| A\* con reglas a mano | 12,1 | 74 % | 26 % | 0 % |
| A\* con reglas + CEM (`tune_astar.py`) | 20,1 | **100 %** | **0 %** | 0 % |
| A\* con predictor de muerte, sin CEM | 13,4 | 49 % | 0 % | 51 % |
| **A\* con predictor de muerte + CEM** | **29,2** | 93,5 % | **0 %** | 6,5 % |

- **El predictor de muerte** (`train_danger.py`) es una red que recibe un parche de 7×7 alrededor de la casilla. Sus etiquetas son contrafactuales, y salen de simular: "¿muere si entra ahí y se queda quieto 3 ticks?".
- **En niveles no vistos detecta más muertes que las reglas:** 87 % contra 70 % (F1 0,85 contra 0,75), con la misma precisión.

## GVGAI: el Boulder Dash de los papers

`gvgai/` conecta con el motor Java real de GVGAI (`bash gvgai/build.sh`) por medio de un puente: en cada tick, Python recibe el estado y devuelve la acción. También puede preguntarle al modelo del juego si una acción es mortal. Las reglas son las oficiales (`boulderdash.txt`):
- 1 vida,
- 9 diamantes y salir,
- 2.000 ticks,
- rocas que no ruedan,
- enemigos que se mueven al azar,
- 5 niveles de 26×13.

**Calibración** (`gvgai_baselines.py`, 25 partidas por agente con la máquina libre, 40 ms por acción):

| Agente | Nuestro montaje | Publicado ([GVGAI-LLM](https://arxiv.org/html/2508.08501v3)) |
|---|---|---|
| OLETS | 48 % | 56 % |
| sampleMCTS | 24 % | 28 % |

**Resultados** (`gvgai_eval.py` y `gvgai_danger.py eval`, 5 niveles × 20 semillas nuevas). El predictor y el CEM usaron solo los niveles 0 a 2; los niveles 3 y 4 son de prueba.

| Agente | Victorias | Por nivel (0 a 4) | Niveles no vistos (3 y 4) |
|---|---|---|---|
| OLETS (calibración) | 48 % | 1, 3, 1, 3, 4 de 5 | — |
| sampleMCTS (calibración) | 24 % | 0, 3, 1, 0, 2 de 5 | — |
| A\* sin costos de peligro | 17 % | 0, 8, 1, 0, 8 de 20 | — |
| **A\* con reglas de peligro a mano** | **90 %** | 17, 13, 20, 20, 20 de 20 | 100 % |
| A\* con predictor, sin CEM | 77 % | 0, 19, 18, 20, 20 de 20 | 100 % |
| A\* con predictor + CEM (niveles 0 a 2) | 88 % | 20, 17, 20, 20, 11 de 20 | 77,5 % |

**Cómo leerlo**
- **El A\* supera por mucho a OLETS y MCTS**, pero tiene una ventaja: ve el mapa entero y la política "gemas y después salida" es específica de Boulder Dash.
- **El predictor de muerte**, entrenado sin reglas escritas a mano, detecta el 46 % de las muertes en niveles no vistos, contra el 21 % de las reglas (F1 0,36 contra 0,08). Es más difícil que en nuestro juego porque los enemigos se mueven al azar.
- **El CEM sobreajusta** con solo 3 niveles de entrenamiento. Mejora los niveles 0 a 2, pero empeora el nivel 4. Para arreglarlo hay que ajustar sobre muchos niveles generados con el formato de GVGAI y dejar los 5 oficiales solo para la prueba.
