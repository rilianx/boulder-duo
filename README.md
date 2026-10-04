# Boulder Dúo

Juego estilo Boulder Dash para el navegador, con gráficos al estilo C64 y pantalla dividida para dos jugadores en un mismo teclado.

Abre `index.html` en un navegador. No necesita instalar nada.

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

## Puntero Dúo (piloto)

[`puntero-duo/index.html`](puntero-duo/index.html) es un juego hermano, todavía en borrador, sobre listas enlazadas. Tiene estética de cuaderno dibujado a mano. Cada jugador es un puntero (`p` y `q`): toma flechas de los nodos y las engancha en otro nodo. El vacío solo se cruza saltando por una flecha (`p = p.next`), y para volver se usa una pila de pasos. Además, un recolector de basura borra cualquier nodo que se quede 5 segundos sin que nada lo apunte. Trae 6 niveles: buscar, insertar, borrar, push en una pila, cola con head y tail, e invertir una lista.

### Puntero C (versión táctil)

[`puntero-duo/tactil.html`](puntero-duo/tactil.html) es la versión para celular, de un jugador, con el código en C escribiéndose al lado. Cada línea se arma con dos toques: primero lo que va a la izquierda del `=` (una variable, `x->next`, una declaración `Nodo *sig` o una acción como `free(_)`, `if (_->value == 7)` o `return`), y después lo que va a la derecha (`NULL`, una variable, `x->next`, `x->next->next`, `x->prev` o `crearNodo(v)`). Las piezas salen del estado actual, así que el alumno puede declarar punteros, crear nodos, avanzar y conectar con libertad. Se parte solo con `l->head`. Lo que en C no compila o se cae (variable sin declarar, `->prev`, segfault, uso después de free, double free) no se ejecuta y se explica. Una fuga sí se ejecuta: el nodo queda en su lugar, transparente y marcado «sin acceso», y se puede deshacer. Todo lo que es C válido se dibuja tal cual, incluso `p->next = p` (una flecha que vuelve al mismo nodo). Cada nivel solo define el punto de partida y el estado que gana, y al terminar muestra una solución de referencia. En las búsquedas los datos están ocultos, y cada `if` falso cambia el `?` del nodo por `≠7`.

### Puntero C: motor (modo libre)

[`puntero-duo/motor.html`](puntero-duo/motor.html) es el motor gráfico, sin ejercicios: la memoria parte vacía y se arma con líneas de C. Arriba va el dibujo apaisado (las listas corren de izquierda a derecha), debajo el programa y abajo el menú.
- **Memoria:** variables en el stack y nodos con dirección en el heap. Un puntero vale un nodo, `NULL` o basura.
- **Intérprete:** ejecuta un subconjunto de C. Comandos simples: `Nodo *x = …;`, `x = …;`, `x->next = …;`, `x->value = n;`, `malloc(sizeof(Nodo))` (con campos basura), `free`, `if (x->value == n)`, `if (x == NULL)` y `printf`. Bloquea los errores de compilación, los segfault, el uso después de `free` y el *double free*, y marca las fugas.
- **Funciones compuestas** (`crearNodo`, `insertarInicio`, `insertarDespues`, `eliminarSiguiente`): están escritas con los mismos comandos simples y se desbloquean al hacer a mano lo mismo que hacen. Al llamarlas se ve su marco en el stack, con los parámetros copiados, y en el código se puede abrir la línea para ver cada paso.
- **Tocar el dibujo:** tocar un post-it, la casilla `next` de un nodo o el cuerpo de un nodo pone su expresión en la línea que se está armando (`head`, `head->next`, o el nombre más corto del nodo). Si no hay ninguna línea en curso, empieza su asignación.
- **Herramientas:** deshacer, ordenar el dibujo y exportar el programa completo como un `.c` que compila.
