# Boulder Dúo

Juego estilo Boulder Dash para el navegador, con gráficos al estilo C64 y pantalla dividida para dos jugadores en un mismo teclado.

Abre `index.html` en un navegador. No necesita instalar nada.

## Jugar con celular

Al abrirlo en un celular o tablet, el juego pregunta si quieres jugar con celular. Si dices que sí, te mueves **deslizando el dedo sobre tu propio tablero**: lo apoyas en cualquier parte y lo arrastras hacia abajo, la izquierda, arriba o la derecha; mientras no lo levantes el minero sigue caminando, y para girar basta con arrastrar hacia el otro lado. Un círculo marca dónde pusiste el dedo y la flecha, la dirección. El botón **TÁCTIL** de arriba lo activa o desactiva y la elección se recuerda.

Se juega en **horizontal**: J1 desliza en el tablero de la izquierda y J2 en el de la derecha; contra el PC sirven los dos tableros para J1. Si el celular está en vertical, el juego pide girarlo.

**Pantalla completa:** botón **PANT. COMPLETA** arriba (Android y computador). En iPhone, Safari no lo permite en páginas: hay que agregar el juego a la pantalla de inicio (Compartir → Agregar a inicio) y abrirlo desde ahí, y se abre sin barras.

La salida está escondida en la fila de abajo del mapa y aparece al juntar las gemas necesarias: suena una fanfarria, sale el aviso «¡SALIDA ABIERTA!» y, si no está en pantalla, una flecha en el borde del tablero apunta hacia ella.

Las rocas y gemas quietas esperan un tick antes de empezar a caer cuando les quitan el piso, así alcanzas a salir de debajo.

## Modos

- **Cooperativo:** los dos juntan gemas para el equipo y salen por la puerta.
- **Versus:** cada uno junta sus gemas y gana el primero en salir.
- **Contra PC:** el rival aprende con Q(λ) mientras juegas.
- **Entrenar PC:** el PC juega solo. Se puede acelerar (x1, x10, x100 y MÁX) o usar **TURBO SIN PANTALLA**, que entrena sin dibujar y muestra solo parámetros y curvas de aprendizaje.

## Controles

| Jugador 1 | Jugador 2 | Partida |
|---|---|---|
| `W` `A` `S` `D` | Flechas | `Enter` seguir · `P` pausa · `R` reiniciar · `M` sonido · `C` CRT |

## El agente

- **Algoritmo:** Q(λ) de Watkins con trazas reemplazantes. Por defecto α = 0,15, γ = 0,93, λ = 0,3 y exploración ε-greedy con decaimiento.
- **Estado:** resume su pantalla de 17×12 casillas. Incluye qué hay en cada dirección y el tipo de peligro, el peligro en su propia casilla, el primer paso de la ruta segura más corta (BFS) hacia la gema o la salida más cercana con su distancia, el enemigo más cercano, si le cae una roca encima y cuántas gemas tiene a la vista.
- **Recompensas:** +5 por gema, +60 por salir, −40 por morir, −0,05 por paso, −0,3 por chocar con algo, y +0,4 por cada casilla que se acerca al objetivo.
- **Guardado:** lo aprendido se guarda en IndexedDB del navegador cada 15 segundos, con localStorage como respaldo.

## Entrenamiento fuera del navegador

`rl/` tiene lo necesario para entrenar al rival fuera del navegador:
- una copia en Python de la simulación, verificada tick a tick contra este `index.html`,
- un tokenizador de entidades,
- un transformer con PPO,
- un baseline con A\*.

Ver [`rl/README.md`](rl/README.md).
