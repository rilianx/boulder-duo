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

[`puntero-duo/tactil.html`](puntero-duo/tactil.html) es la versión para celular, de un jugador. Cada paso es elegir la próxima línea de C entre varias candidatas, donde siempre hay algunas malas, y el código se va escribiendo al lado. Se parte solo con `l->head`, así que declarar punteros (`Nodo *p = l->head;`, `Nodo *sig = p->next;`) también es una decisión. Una línea mala se ejecuta para que se vea qué provoca (fuga, segfault, ciclo, error de compilación como `p->prev`), luego se explica y se deshace. En las búsquedas los datos están ocultos, y cada `if (p->value == 7)` falso cambia el `?` del nodo por `≠7`. Trae 8 niveles: está el 7, no está el 5, insertar, borrar con `free`, push, pop, encolar e invertir.
