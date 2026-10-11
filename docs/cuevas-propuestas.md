# 10 cuevas nuevas (propuestas)

Ideas para cuevas con desafíos que no están en Boulder Dash 1 ni 2. Cada una toma algo de otro juego del género (o vecino) y lo adapta a este, que se juega solo o **de a dos**. Son propuestas: todavía no están en el juego.

Para cada cueva: **de dónde sale la idea**, **qué hay de nuevo**, un **boceto** del mapa, **el desafío**, **cómo se pasa**, **con dos jugadores** y **qué haría falta** en el motor.

Bocetos: misma notación que el [catálogo](catalogo-cuevas.md) (`#` acero · `W` ladrillo · `.` tierra · ` ` vacío · `o` roca · `*` diamante · `X` salida · `F` luciérnaga · `B` mariposa · `1` `2` los niños), más las letras nuevas que se explican en cada cueva. Los bocetos son más chicos que una cueva real: muestran la idea, no el mapa final.

| # | Cueva | Idea de | Desafío |
|---|---|---|---|
| 1 | [Nueces](#1-nueces) | Emerald Mine | Romper nueces dejándoles caer una roca encima |
| 2 | [Llaves que se gastan](#2-llaves-que-se-gastan) | Emerald Mine, Zelda | Decidir qué puertas abrir con pocas llaves |
| 3 | [Pasos de un sentido](#3-pasos-de-un-sentido) | Supaplex | Planear el orden: no hay vuelta atrás |
| 4 | [Barriles](#4-barriles) | Supaplex, Emerald Mine | Llevar explosivos que estallan al caer |
| 5 | [Placas](#5-placas) | Sokoban | Hacer caer rocas justo sobre las placas |
| 6 | [Inundación](#6-inundación) | Mr. Driller | Subir antes de que suba el agua |
| 7 | [El comelón](#7-el-comelón) | Emerald Mine, Rocks'n'Diamonds | Dejarlo comer y aplastarlo en el momento justo |
| 8 | [Tierra viva](#8-tierra-viva) | Lode Runner | Túneles que se cierran solos: trampas |
| 9 | [Cueva giratoria](#9-cueva-giratoria) | Supaplex, la gravedad oculta de este juego | Girar la gravedad para vaciar bolsillos |
| 10 | [Dos llaves, una puerta](#10-dos-llaves-una-puerta) | Fireboy & Watergirl, Portal 2 | Turnarse en las placas para abrirse paso |

---

## 1. Nueces

**De dónde sale:** las nueces de *Emerald Mine* (1987), que se rompen dejándoles caer una roca y sueltan una esmeralda.

**Qué hay de nuevo:** la **nuez** (`n`). Se comporta como una roca: cae, rueda y se empuja. Si le cae una roca encima se rompe y deja un diamante. Si cae sobre algo, no le pasa nada.

```
##############################
#12......o.....o.....o.......#
#........n.....n.....n.......#
#WWWWWW..W.....W.....W..WWWWW#
#......o.......o.............#
#....o.n.....o.n..B...o......#
#....WWWW....WWWW.....WWWW...#
#............................#
#..n.n.n.......F.......n.n.n.X
##############################
```

**El desafío:** no hay diamantes sueltos, solo nueces. Algunas tienen una roca encima, lista para caer. Otras están en el suelo, lejos de cualquier roca, y hay que llevarles una.

**Cómo se pasa:** cavar debajo de las nueces que tienen roca encima para que caigan juntas y la roca rompa la nuez. Para las del suelo, empujar rocas por las repisas y dejarlas caer justo encima. Las rocas son contadas: una que cae al lado de la nuez se pierde.

**Con dos jugadores:** uno deja caer la roca y el otro recoge el diamante antes de que ruede a otra parte.

**Qué haría falta:** un tipo de celda nuevo que use la física de la roca, y una regla en la caída: roca sobre nuez = diamante. Es fácil.

---

## 2. Llaves que se gastan

**De dónde sale:** las llaves y puertas de colores de *Emerald Mine*, y las llaves pequeñas de *Zelda*, que sirven para una sola puerta.

**Qué hay de nuevo:** la **llave** (`a`) y la **puerta** (`A`). La llave se recoge como un diamante (se ve en la barra) y se gasta al abrir una puerta.

```
########################################
#12...o....a.....o.....a..........o....#
#..o.....o.....o.....o.....o.....o.....#
#WWWWWAWWWWWWWWWWAWWWWWWWWWWWAWWWWWWWWW#
#..*.*.*.#..o.o.o.o..#...*...........X.#
#.*.*.*..#.o*o*o*o*..#..F...*....F.....#
#..*.*.*.#..o.o.o.o..#.......*.........#
########################################
```

**El desafío:** hay tres puertas y solo dos llaves. Detrás de una están la salida y dos luciérnagas; detrás de las otras, diamantes. Una sala los tiene fáciles de tomar; en la otra están entre rocas que se derrumban. Hay que elegir bien.

**Cómo se pasa:** mirar antes de abrir. La sala de la salida es obligatoria, y de las otras dos conviene la que da los diamantes que faltan con menos riesgo. En una versión más difícil, una roca mal soltada tapa una puerta y la llave ya no sirve.

**Con dos jugadores:** las llaves son del equipo, pero cada una la lleva quien la recogió. Hay que ponerse de acuerdo sobre quién abre qué.

**Qué haría falta:** dos tipos de celda (llave y puerta), un contador de llaves por niño y que la puerta deje pasar solo a quien tiene una llave.

---

## 3. Pasos de un sentido

**De dónde sale:** los puertos de *Supaplex* (1991), pasos que se cruzan solo en una dirección.

**Qué hay de nuevo:** el **paso** (`>` `<` `^` `v`), una celda que el niño cruza solo en el sentido de la flecha. Las rocas y los enemigos no pueden atravesarlo.

```
##############################
#12......>.........v.........#
#WWWWWWWWWWWWWWWWW.WWWWWWWWWW#
#..*..o..<....*....>...*..o..#
#WWWW^WWWWWWWWWWWWWWWWWWW.WWW#
#..*....o....>..*.....<...*..#
#WWWWWWWWWWWW.WWWWWWWWWWWWWWW#
#...*...>....*.....*.....<..X#
##############################
```

**El desafío:** hay diamantes en todos los pisos, y una vez que se cruza un paso no se puede volver por ahí. En el orden equivocado uno queda del lado malo con diamantes sin tomar.

**Cómo se pasa:** antes de moverse, seguir con la vista las flechas hasta la salida. En cada piso, tomar todo lo que queda a este lado de un paso antes de cruzarlo. Es una cueva de pensar más que de reflejos.

**Con dos jugadores:** cada uno puede ir por un camino distinto, porque los caminos no se juntan hasta abajo. Al repartirse los pisos, un niño que se queda atrás no puede alcanzar al otro.

**Qué haría falta:** un tipo de celda con dirección, y que el paso de un niño mire esa dirección. Es fácil.

---

## 4. Barriles

**De dónde sale:** los discos naranjos de *Supaplex*, que explotan al caer, y las bombas de *Emerald Mine*.

**Qué hay de nuevo:** el **barril** (`Q`). Se empuja como una roca. Si cae o le cae algo encima, explota en 3×3 como una luciérnaga: rompe ladrillo, tierra y diamantes, y mata.

```
########################################
#12..Q....WWWW..*.*.*..WWWW....Q.......#
#.........W..WWWWWWWWWWWW..W...........#
#..o..o...W..*.......*...W..o....o.....#
#.........WWWWWWWWWWWWWWWW.............#
#..WWWWWW......o....o.......WWWWWWW....#
#..W*.*W....F...............W*.*.*W....#
#..WWWWWW...................WWWWWWW...X#
########################################
```

**El desafío:** los diamantes están en salas de ladrillo cerradas, y solo hay dos barriles para abrir tres salas. Hay que llevarlos sin que caigan antes de tiempo: un barril empujado sobre un hueco cae y explota ahí mismo.

**Cómo se pasa:** dejar cada barril junto a una pared de modo que una explosión abra dos salas a la vez, y hacerlo estallar dejándole caer una roca encima desde lejos. La luciérnaga también sirve como tercera explosión, si se la atrae con cuidado.

**Con dos jugadores:** uno empuja el barril y el otro, desde lejos, suelta la roca encima. Ninguno debe estar a menos de un cuadro.

**Qué haría falta:** un tipo de celda con física de roca que llame a la explosión que ya existe al caer o al recibir un golpe. Es fácil.

---

## 5. Placas

**De dónde sale:** *Sokoban*, pero con gravedad: aquí las rocas no se dejan donde uno quiere, caen.

**Qué hay de nuevo:** la **placa** (`_`), una celda de suelo. Cuando hay una roca encima se ilumina. Con todas encendidas se abre la salida, y en esta cueva no hay diamantes que juntar.

```
##############################
#12.......................X..#
#.....o.....o.....o..........#
#WWW..WWWWW..WWWW..WWWWWW....#
#                            #
#   o                        #
#WWWW_WWWWWW_WWWWWWWWW_WWWWWW#
##############################
```

**El desafío:** las rocas solo se empujan de lado y, al quedar sobre un hueco, caen y ruedan si caen sobre otra roca. Hay que hacerlas caer exactamente sobre las placas.

**Cómo se pasa:** contar las celdas: empujar cada roca hasta quedar justo sobre la columna de la placa y entonces dejarla caer. Si una roca queda mal, cavar o empujarla de nuevo, siempre que no haya caído en un rincón del que no sale. Hay una roca de sobra para un error.

**Con dos jugadores:** uno empuja desde arriba y el otro, desde el pasillo de abajo, empuja la roca que cayó mal hacia su placa.

**Qué haría falta:** la placa como celda sólida, y que la salida mire si todas tienen una roca encima, en vez de contar diamantes. Es fácil.

---

## 6. Inundación

**De dónde sale:** el aire que se acaba de *Mr. Driller* y el agua que sube de tantos juegos de plataformas.

**Qué hay de nuevo:** el **agua** (`~`). Sube una fila cada algunos segundos desde abajo. Las rocas y los diamantes se hunden en ella. Un niño bajo el agua aguanta unos segundos (se ve una barra de aire) y después se ahoga.

```
########################################
#............X.........................#
#..o..*..o.....o...*...o.....*...o.....#
#.WWWW....WWWWWWW.....WWWW.....WWWWW...#
#....*..o.....*.....o....*..o......*...#
#..o.....WWWW....o.....WWWWWW....o.....#
#....*........*.......*.......*........#
#.12..o...o.....o..o.....o....o....o...#
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
########################################
```

**El desafío:** se parte abajo y la salida está arriba. Los diamantes están repartidos por todos los pisos, y el agua no deja volver a buscar los que quedaron abajo.

**Cómo se pasa:** juntar los diamantes de cada piso antes de subir, sin perder tiempo cavando de más. Cavar hacia arriba bajo una roca es peligroso (cae), así que hay que subir por los lados. Mirar el ritmo del agua y no quedarse atrás.

**Con dos jugadores:** uno va adelante abriendo camino y el otro limpia el piso. Si uno se queda bajo el agua, el otro puede cavarle una salida hacia arriba.

**Qué haría falta:** una fila de agua que sube con el tiempo, una barra de aire por niño y que el agua no mueva nada. Es mediano.

---

## 7. El comelón

**De dónde sale:** el *Yam-Yam* de *Emerald Mine* y *Rocks'n'Diamonds*, una bestia que se come lo que encuentra y explota soltando lo que tenía adentro.

**Qué hay de nuevo:** el **comelón** (`Y`). Avanza en línea recta por el espacio vacío y dobla al chocar. Se come los diamantes que encuentra y mata al tocar. Si le cae una roca encima explota, y deja **todos** los diamantes que se comió (más uno de propina) en los cuadros de alrededor.

```
##############################
#12.....*.*.*.*.*.*.*.*....X.#
#                            #
#..Y.......o......o......Y...#
#......WWWWWWWWWWWWWW........#
#..*.*.*.*.........*.*.*.*...#
##############################
```

**El desafío:** dos comelones recorren los pasillos llenos de diamantes. Si uno los toma primero, quedan pocos para pasar. Si se deja que los comelones coman, se llenan, y aplastados devuelven todo junto.

**Cómo se pasa:** dejarlos comer un rato y aplastarlos bajo las dos rocas del medio cuando pasen. Hay que medir el tiempo: muy pronto dan poco, y muy tarde se acaba el reloj o uno se cruza en su camino.

**Con dos jugadores:** uno distrae al comelón (se desvía para perseguirlo) mientras el otro suelta la roca.

**Qué haría falta:** un enemigo nuevo que se mueve en línea recta, con un contador de diamantes comidos y una explosión que los devuelve. Es mediano.

---

## 8. Tierra viva

**De dónde sale:** los hoyos de *Lode Runner* (1983), que se vuelven a llenar solos y atrapan a los guardias.

**Qué hay de nuevo:** la **tierra viva** (`:`). Se cava como la normal, pero el hoyo se vuelve a llenar a los 6 segundos. Si al llenarse hay un enemigo adentro, lo aplasta: una mariposa deja 9 diamantes y una luciérnaga nada. Nunca se cierra sobre un niño, pero sí puede dejarlo encerrado (basta con volver a cavar).

```
##############################
#12:::::::::::::::::::::::::X#
#::B::::::::::*::::::::::B:::#
#:::::::*::::::::::*:::::::::#
#::*::::::::::F:::::::::::*::#
##############################
```

**El desafío:** las mariposas solo se mueven por el espacio vacío, así que salen únicamente por los túneles que uno abre, y esos túneles se cierran detrás. Se necesitan los diamantes de dos mariposas.

**Cómo se pasa:** abrir un túnel hasta una mariposa, dejar que lo siga y alejarse. Cuando la tierra se cierre con la mariposa adentro, explota en diamantes. La luciérnaga del centro hay que evitarla, o atraparla igual para que deje de estorbar.

**Con dos jugadores:** uno hace de cebo cavando y el otro mantiene abierto un túnel paralelo para escapar.

**Qué haría falta:** un tipo de tierra que recuerde cuándo se cavó y vuelva a crecer. Ya existe el momento en que se cava cada cuadro, para la animación. Es fácil o mediano.

---

## 9. Cueva giratoria

**De dónde sale:** los puertos de gravedad de *Supaplex* y la opción de gravedad oculta de este mismo juego (la tecla G).

**Qué hay de nuevo:** el **interruptor de gravedad** (`G`). Al pisarlo, la gravedad de toda la cueva gira un cuarto de vuelta: rocas y diamantes pasan a caer hacia la izquierda, hacia arriba o hacia la derecha.

```
########################################
#12.....o.o.o.o.....W.....*.*.*.*......#
#.......o.o.o.o.....W.....*.*.*.*......#
#...G...............W...........G......#
#WWWWWWWWWWWW..WWWWWWWWWWW..WWWWWWWWWWW#
#.....*.*.*.*.......G......o.o.o.o....X#
########################################
```

**El desafío:** los diamantes están en bolsillos donde la gravedad normal los deja atrapados, o tapados por rocas que caen sobre el camino. Cada giro mueve todo, también las rocas que están junto a uno.

**Cómo se pasa:** antes de pisar un interruptor, mirar hacia dónde va a caer cada cosa y ponerse a salvo. Usar los giros para que los diamantes salgan de sus bolsillos hacia el pasillo, y las rocas hacia donde no estorban (o sobre una mariposa que pase por ahí).

**Con dos jugadores:** el giro afecta a los dos, así que el que pisa el interruptor avisa (o espera a que el otro esté a salvo).

**Qué haría falta:** casi nada: el juego ya sabe girar la gravedad. Solo falta la celda del interruptor y una flecha en pantalla que muestre hacia dónde cae todo.

---

## 10. Dos llaves, una puerta

**De dónde sale:** los botones de *Fireboy & Watergirl* y *Portal 2*, donde dos jugadores se turnan para abrirse puertas.

**Qué hay de nuevo:** la **placa** (`_`) y la **compuerta** (`D`). La compuerta está abierta mientras alguien (un niño o una roca) está sobre su placa, y se cierra al soltarla.

```
##############################
#1...._.......D..........*..X#
#WWWWWWWWWWWWWDWWWWWWWDWWW...#
#..*....o.....D...*...D......#
#WWWWWWWWDWWWWWWWWWWWWWWW....#
#2..*....D......_..*......_..#
##############################
```

**El desafío:** cada niño parte en su propio piso. Las compuertas de un piso se abren con placas del otro, así que ninguno puede avanzar solo: tienen que turnarse.

**Cómo se pasa:**
1. J1 pisa su placa y abre la compuerta del piso de J2.
2. J2 pasa y se para en una placa que le abre el paso a J1.
3. Así se avanza hasta juntarse en la salida.

En 1 jugador, el truco es empujar una roca sobre la placa para que la sostenga mientras uno pasa.

**Con dos jugadores:** es el centro de la cueva, pensada para cooperativo, porque hay que hablar y coordinarse. En versus se puede usar al revés: soltar la placa en el momento justo para encerrar al otro.

**Qué haría falta:** placa y compuerta como celdas nuevas, y una lista de qué placa abre qué compuerta. La compuerta no debe cerrarse sobre un niño ni sobre una roca.

---

## Otras ideas sueltas

- **Fantasmas y jaulas** (*Repton*): un fantasma que sigue las paredes y, al entrar a una jaula, se convierte en diamante. Se le guía cavando el camino.
- **Huevos** (*Repton*): una roca especial que, al caer, se rompe y suelta un monstruo.
- **Caja fuerte** (*Repton*): diamantes encerrados que se liberan todos juntos al tomar una llave.
- **Cintas transportadoras** (*Rocks'n'Diamonds*): llevan rocas y diamantes de lado, y un interruptor cambia su sentido.
- **Teletransportadores** (*Repton 3*): dos puntos conectados, para cuevas partidas en pedazos.
- **Interruptor de luz** (*Rocks'n'Diamonds*): con la opción OSCURIDAD de este juego, una cueva que solo se ve por partes, con interruptores que encienden un rato una zona.
- **Reloj** (*Emerald Mine*): un objeto que da tiempo extra, en una cueva con muy poco tiempo.
- **Juego de la vida** (*Rocks'n'Diamonds*): células que nacen y mueren según sus vecinas, como una ameba con reglas propias.

## Orden sugerido para implementarlas

De lo más simple a lo más trabajoso, aprovechando lo que el motor ya tiene:

1. **Cueva giratoria:** la gravedad ya gira.
2. **Pasos de un sentido.**
3. **Nueces.**
4. **Barriles:** usan la explosión que ya existe.
5. **Placas.**
6. **Tierra viva.**
7. **Dos llaves, una puerta:** comparte las placas con la 5.
8. **Llaves que se gastan.**
9. **El comelón.**
10. **Inundación.**

Todas son reglas de las cuevas originales, así que no tocan las cuevas aleatorias de entrenamiento ni su copia en Python. Las de dos jugadores se juegan igual en dos celulares, porque el juego ya sincroniza todo lo que pasa en la cueva.
