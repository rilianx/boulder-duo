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

La antigua versión táctil por niveles (`puntero-duo/tactil.html`) se retiró: sus ideas quedaron en el motor, y el archivo sigue en el historial de git.

### Puntero C: motor (modo libre)

[`puntero-duo/motor.html`](puntero-duo/motor.html) es el motor gráfico, sin ejercicios: la memoria parte vacía y se arma con líneas de C. El cuaderno ocupa la pantalla y las listas corren de izquierda a derecha.
- **Pantalla:** en el celular hay dos pestañas, **Cuaderno** y **Código**. Sobre el campo para escribir, las últimas 4 líneas del programa se ven **escritas a mano en el cuaderno** (con su número; errores en rojo, fugas en ámbar, salidas en verde). Se quedan abajo y se ocultan mientras están abiertas las opciones o un aviso. Se desplazan arrastrándolas hacia arriba o abajo, con la rueda o con ▲ ▼; al viajar en el tiempo o ver un caso, siguen la línea actual (subrayada). La tira muestra solo la línea que se está armando. Al tocar la tira se abre el código. La tira y el campo para escribir van dentro del mismo cuaderno, abajo, así que el dibujo nunca se achica. El alto del cuaderno se adapta a la pantalla, y el orden automático deja los nodos en la parte de arriba, donde la bandeja no los tapa. En pantallas anchas (900 px o más) el cuaderno y el código van lado a lado. Exportar el programa, el registro para consultas y «Empezar de cero» están en la pestaña Código.
- **Elegir opciones (por defecto):** cada línea se arma eligiendo, sin escribir. Abajo, sobre el mismo cuaderno y semitransparente, hay una fila de pestañas (Variables, Campos, Memoria, Consultas, Funciones, Atajos); al tocar una se despliegan sus líneas y tocarla de nuevo las pliega. Mientras nada está desplegado se ve el código escrito a mano. Tocar el dibujo abre las opciones de ese puntero (post-it), de su `next` o de su `value` (solo lo que se hace con un valor: `p->value = _;`, `if (p->value == _)`, `printf`). Los huecos se llenan con piezas o tocando el dibujo. En un hueco de puntero, el primer toque a un post-it lo marca y **tocarlo de nuevo** (o tocar el nodo marcado) lo usa; si no hay flecha que seguir (NULL o basura), basta un toque.
- **Teclado (opcional):** la pestaña ⌨ cambia a escribir la línea en C (tolerante con los espacios, ⏎ ejecuta, ↑ repite, sugerencias mientras se escribe); ☷ vuelve a las opciones. La elección se recuerda.

- **Memoria:** variables en el stack y nodos con dirección en el heap. Un puntero vale un nodo, `NULL` o basura.
- **Intérprete:** ejecuta un subconjunto de C. Comandos simples: `Nodo *x = …;`, `x = …;`, `x->next = …;`, `x->value = n;`, `malloc(sizeof(Nodo))` (con campos basura), `free`, `if (x->value == n)`, `if (x == NULL)` y `printf`. Bloquea los errores de compilación, los segfault, el uso después de `free` y el *double free*, y marca las fugas.
- **Lista:** `Lista *l = crearLista();` crea una caja `Lista` (un rectángulo con su nombre y solo la casilla del puntero `head`, con `(l->head)` en chico arriba), dibujada en su propio nivel arriba de los nodos. Bajo los nodos se muestran solo las variables que los apuntan; `l->head` se ve sobre la casilla de la Lista. Al primer nodo se llega con `l->head` (también siguiendo punteros en el dibujo: post-it `l` → casilla `head` → casillas `next`).
- **Funciones compuestas:** están escritas con los mismos comandos simples. `crearNodo` y el atajo `p = p->next` se desbloquean al hacerlos a mano. Las operaciones de lista (`insertarInicio(Lista *l, int v)` y las que vendrán) se desbloquean **al completar su ejercicio**.
- **Ejercicios (menú ☰):** se escribe el cuerpo de la función dentro de su marco, donde se ven los parámetros como copias. Las mismas líneas se prueban con **▶ Probar** sobre varios casos: lista vacía, un nodo, tres nodos y un caso oculto. Cada caso se revisa por separado (errores, fugas, lista esperada, que los nodos originales se reusen y no se copien) y se puede ver correr paso a paso. El primero es «Insertar al inicio». Al llamarlas se ve su marco en el stack, con los parámetros copiados, y en el código se puede abrir la línea para ver cada paso.
- **La línea se arma a la vista:** mientras eliges las piezas, la línea en construcción aparece en la tira bajo el dibujo (y al final del código), con el hueco que falta resaltado.
- **Declarar en un toque:** la pestaña Variables muestra directamente `Nodo *p = _;` para cada nombre libre y `p = _;` para cada variable declarada.
- **Atajos:** `p = p->next;` se desbloquea la primera vez que el alumno avanza un puntero a mano. Desde ahí, avanzar cualquier puntero es un toque en la pestaña «Atajos».
- **Advertencia de saltos:** antes de ejecutar una línea con dos o más `->next` seguidos (por ejemplo `head->next->next`), el motor avisa y deja escribirla igual o cancelar.
- **Opciones al seleccionar un puntero:** al tocar un post-it (y seguir flechas si se quiere) aparecen todos los componentes del nodo: `p = _;`, `p->value = _;`, `p->next = _;`, `if (p->value == _)`, `printf`, `free(p)` e `if (p == NULL)`. Para una Lista aparece `l->head = _;`. Los `int` (como el parámetro `v`) se tocan para llenar huecos numéricos.
- **Llegar a un nodo por sus punteros:** como en C, un nodo no se toca directamente. Se parte tocando el post-it de una variable (el nodo al que apunta queda marcado) y se avanza tocando la casilla `next` del nodo marcado (`p` → `p->next` → `p->next->next`). En el nodo marcado, su casilla value termina el camino en su valor (`p->next->value`), también cuando el hueco pide un número. Después se confirma con «✓ usar» o se borra el último paso con «⌫». Si no hay ninguna línea en curso, el camino ofrece `p->next = _;` o `p->next->value = _;`. Las casillas de un nodo **con nombre** (lo apunta una variable o el `head` de una lista) se tocan directo: value escribe `p->value` y next escribe `p->next`; para el nodo entero se toca su post-it. Donde va un puntero (la derecha de `p = `, `p->next = `, `free(`, o un hueco de puntero), tocar el cuerpo del nodo escribe su nombre (`q`) en vez de `q->value`. Bajo cada nodo con nombre se ve su referencia en chico, como `(p)` o `(q, aux)`. Si dos punteros apuntan al mismo nodo, un globo pregunta por cuál. Un nodo sin nombre explica que hay que llegar siguiendo flechas. `x->value` también sirve donde va un número (`nuevo->value = p->value;`).
- **Volver a una línea:** tocar una línea del código restaura la memoria de justo antes y deja todo en pausa. Desde ahí se puede avanzar paso a paso (también dentro de las funciones, incluidas las anidadas), reproducir, saltar al final o «escribir desde aquí», que descarta lo que venía después. Tocar un paso dentro de una función expandida lleva directo a ese paso.
- **Ordenar a mano:** los nodos y las cajas `Lista` se arrastran por el cuaderno. Las posiciones elegidas se mantienen al deshacer, al volver a una línea y al probar los casos (⇅ vuelve al orden automático).
- **Herramientas:** deshacer, ordenar el dibujo y exportar el programa completo como un `.c` que compila. Desde la misma tarjeta se puede copiar un **registro para consultas**: todas las líneas (también las que fallaron, con su mensaje), los pasos dentro de cada función y cómo quedó la memoria.
- **Flechas:** todas nacen del punto de su casilla (`next` o post-it) y se dibujan encima de los nodos. Hacia otra fila bajan o suben desde el punto y cruzan por el pasillo entre filas. Si una flecha pasaría por encima de otro nodo (por ejemplo `p->next = aux->next` en una misma fila), se dibuja como un arco por arriba.
