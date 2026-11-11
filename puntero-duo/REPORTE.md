# Puntero C: un cuaderno para aprender listas enlazadas en C

## Qué es

Puntero C es un juego educativo para celular (también funciona en computador) que enseña **listas enlazadas en C** de manera visual. El estudiante arma un programa línea a línea y ve, en un cuaderno cuadriculado dibujado a mano, qué le pasa a la memoria con cada instrucción: qué variables existen, a qué nodo apunta cada puntero y qué nodos quedaron perdidos.

Todo el juego es un único archivo HTML (`puntero-duo/motor.html`) que no necesita instalación ni servidor: basta abrirlo en el navegador.

## El problema que ataca

Las listas enlazadas suelen ser el primer tema en que los estudiantes de programación chocan con los punteros. Los errores típicos son siempre los mismos:

- perder el resto de la lista por cambiar `head` antes de enlazar el nodo nuevo (una **fuga**);
- usar un puntero que vale `NULL` (un **segfault**);
- leer un campo que nunca recibió valor (**basura**);
- usar un nodo después de liberarlo, o liberarlo dos veces.

En papel o en un compilador, estos errores son invisibles o aparecen como un mensaje críptico. Puntero C los muestra en el dibujo en el momento en que ocurren y explica por qué pasaron.

## Cómo se ve

La pantalla es un cuaderno que ocupa todo el celular:

- **El margen (stack):** las variables son post-its amarillos con su nombre (`p`, `q`, `nuevo`…). De cada post-it sale una flecha hacia el nodo al que apunta, o una raya si vale `NULL`.
- **La hoja (heap):** cada nodo es una caja `[value | next]` con su dirección de memoria debajo (`0x3b8`). Bajo cada nodo aparecen en chico los nombres de los punteros que lo apuntan, como `(p, q)`.
- **La Lista:** es una caja verde aparte, arriba de los nodos, con la casilla de su puntero `head` y la etiqueta `(l->head)`.
- **Estados especiales:** un nodo sin ninguna flecha que lo alcance queda transparente con la marca «sin acceso». Uno liberado aparece en rojo, y un campo sin inicializar se ve como `¿?`.

Abajo, escritas a mano sobre el cuaderno, se ven las últimas líneas del programa. Se pueden desplazar hacia arriba y abajo. El programa completo está en la pestaña **Código**, y en pantallas anchas cuaderno y código se ven lado a lado.

## Cómo se juega

El estudiante **no escribe código: lo arma eligiendo**. Sobre el cuaderno hay una fila de pestañas semitransparentes (Variables, Campos, Memoria, Consultas, Funciones, Atajos). Al tocar una aparecen las líneas posibles con huecos, por ejemplo `Nodo *p = _;` o `_->next = _;`. Los huecos se llenan con piezas o tocando el dibujo.

Lo central es que **a la memoria se llega por los punteros**, como en C:

- Tocar un post-it marca el nodo al que apunta. Tocar de nuevo el post-it, o el nodo marcado, lo usa en el hueco.
- Tocar la casilla `next` del nodo marcado sigue la flecha (`p` → `p->next`).
- En un nodo que tiene nombre, sus casillas se tocan directamente: `value` ofrece `p->value = _;`, `if (p->value == _)` y `printf`. `next` ofrece las opciones de `p->next`.
- Si dos punteros apuntan al mismo nodo, el juego pregunta por cuál se quiere llegar, porque el código resultante es distinto.
- Un nodo sin nombre no se puede tocar directamente: hay que llegar a él siguiendo flechas.

Para quien lo prefiera existe un modo **teclado** (pestaña ⌨). En él se escribe la línea en C con tolerancia a los espacios, con sugerencias, y con taps en el dibujo que completan el lado izquierdo o derecho del `=`.

## Qué hace el motor

Detrás del dibujo hay un **intérprete de un subconjunto de C** que ejecuta de verdad cada línea:

- declaraciones y asignaciones de punteros, `x->next = …`, `x->value = …`;
- `malloc(sizeof(Nodo))`, que crea un nodo con campos basura, y `free`;
- `if (x->value == n)`, `if (x == NULL)` y `printf`;
- llamadas a funciones con su propio marco en el stack y parámetros copiados.

Cada línea se anima en el cuaderno. Los errores se clasifican:

- **De compilación** (variable sin declarar, campo inexistente como `->prev`): no se ejecutan y se explican.
- **De ejecución** (segfault, uso después de `free`, doble `free`, leer basura): tampoco se ejecutan, y el aviso dice qué habría pasado.
- **Fugas:** se ejecutan, porque en C son legales, pero el nodo perdido queda marcado. Se puede deshacer con un toque.

Si una línea usa dos o más `->next` seguidos, el juego advierte antes de ejecutarla y sugiere avanzar un puntero paso a paso.

## Viaje en el tiempo

Tocar cualquier línea del programa devuelve la memoria al momento justo antes de esa línea. Desde ahí se puede avanzar paso a paso (incluso dentro de las funciones), reproducir hasta el final o **«escribir desde aquí»**, que descarta lo que venía después. Es útil para que el estudiante encuentre en qué línea exacta se rompió su lista.

## Funciones que se desbloquean

Las operaciones compuestas no están disponibles desde el principio: **se ganan**.

- `crearNodo(v)` se desbloquea la primera vez que el estudiante crea un nodo a mano (con `malloc`, `value` y `next`).
- El atajo `p = p->next;` se desbloquea la primera vez que avanza un puntero manualmente.
- Las operaciones de lista, como `insertarInicio(l, v)`, se desbloquean **al resolver su ejercicio**.

Una vez desbloqueada, una función se usa en una sola línea, y en el código se puede abrir para ver cada paso que ejecutó por dentro. La idea es que el estudiante solo use una abstracción después de haberla construido.

## Ejercicios

El primer ejercicio es **Insertar al inicio**. El estudiante escribe el cuerpo de `void insertarInicio(Lista *l, int v)` parado dentro de la función: ve en el stack sus parámetros `l` y `v` como copias de lo que le pasó `main`.

Al tocar **▶ Probar**, las mismas líneas se ejecutan sobre varios casos: lista vacía, un nodo, tres nodos y un caso oculto. Cada caso se revisa por separado:

1. que no haya errores de ejecución;
2. que no haya fugas;
3. que la lista final sea la esperada;
4. que los nodos originales se reusen y no se hayan copiado.

Cada caso fallido muestra un mensaje concreto. Por ejemplo, «El 5 quedó sin acceso (fuga). Además, al terminar la lista tiene un ciclo», o «un nodo quedó con su value basura (¿?)». Cualquier caso se puede ver correr paso a paso en el cuaderno.

Al resolver el ejercicio, el juego muestra una solución de referencia, da estrellas según la cantidad de líneas y desbloquea la función en el modo libre. Las estrellas no dependen de si se usó el teclado o las opciones.

## Para el profesor

- **Programa en C:** exporta lo que armó el estudiante como un archivo `.c` completo que compila con gcc.
- **Registro para consultas:** copia todas las líneas, incluidas las que fallaron y su mensaje, los pasos dentro de cada función y el estado final de la memoria. Sirve para que el estudiante pida ayuda mostrando exactamente qué hizo.
- En el menú hay una opción para desbloquear o volver a bloquear todo, útil para demostraciones en clase.

## Estado actual y próximos pasos

El motor libre y el primer ejercicio están completos y probados. Las pruebas automáticas recorren la app como lo haría un estudiante, en un celular simulado, y los programas exportados se verifican compilándolos con gcc.

Vienen a continuación:

- los ejercicios **Insertar después** y **Eliminar siguiente** (sus funciones ya existen en el motor y se desbloquearán con ellos);
- más adelante, **bucles**, para recorrer listas sin repetir líneas;
- otras estructuras (pilas, colas) con la misma lógica de cuaderno.

## Archivos

- `puntero-duo/motor.html`: el juego completo (un solo archivo).
- `puntero-duo/index.html`: el piloto original, un juego de dos jugadores con teclado del que nació la idea.
- `README.md`: la descripción técnica detallada de cada función.
