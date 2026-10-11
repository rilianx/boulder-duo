# 10 cuevas nuevas (propuestas)

Ideas para cuevas con desafíos que no están en Boulder Dash 1 ni 2. Cada una toma algo de otro juego del género (o vecino) y lo adapta a este, que se juega solo o **de a dos**. **Ya se pueden jugar:** en el menú, botón **CUEVAS NUEVAS** (también con VISTA 3D y con dos celulares). Al entrar a cada una aparece una pista corta.

Cada mapa tiene el **tamaño de una cueva original** (40 × 22, con borde de acero), igual que en el [catálogo](catalogo-cuevas.md). Para cada cueva: de dónde sale la idea, qué hay de nuevo, el mapa, el desafío, cómo se pasa, qué cambia con dos jugadores y cómo quedó en el juego. Los números (diamantes, rocas) son los del mapa; los tiempos son una primera propuesta, para ajustar jugando.

**Mapas:** `#` acero · `W` ladrillo · `.` tierra · ` ` vacío · `o` roca · `*` diamante · `X` salida · `F` luciérnaga · `B` mariposa · `1` `2` los niños, más las letras nuevas de cada cueva.

| # | Cueva | Idea de | Diamantes necesarios | Desafío |
|---|---|---|---|---|
| 1 | [Nueces](#1-nueces) | Emerald Mine | 12 | Romper nueces dejándoles caer una roca |
| 2 | [Llaves que se gastan](#2-llaves-que-se-gastan) | Emerald Mine, Zelda | 12 | Elegir qué puertas abrir con pocas llaves |
| 3 | [Pasos de un sentido](#3-pasos-de-un-sentido) | Supaplex | 22 | Planear el orden: no hay vuelta atrás |
| 4 | [Barriles](#4-barriles) | Supaplex, Emerald Mine | 16 | Llevar explosivos que estallan al caer |
| 5 | [Placas](#5-placas) | Sokoban | — (placas) | Hacer caer rocas justo sobre las placas |
| 6 | [Inundación](#6-inundación) | Mr. Driller | 16 | Subir antes de que suba el agua |
| 7 | [El comelón](#7-el-comelón) | Emerald Mine, Rocks'n'Diamonds | 30 | Dejarlo comer y aplastarlo en el momento justo |
| 8 | [Tierra viva](#8-tierra-viva) | Lode Runner | 20 | Túneles que se cierran solos: trampas |
| 9 | [Cueva giratoria](#9-cueva-giratoria) | Supaplex y la gravedad oculta de este juego | 24 | Girar la gravedad para vaciar bolsillos |
| 10 | [Dos llaves, una puerta](#10-dos-llaves-una-puerta) | Fireboy & Watergirl, Portal 2 | 8 | Turnarse en las placas para abrirse paso |

---

<a id="1-nueces"></a>

## 1. Nueces

**De dónde sale:** las nueces de *Emerald Mine* (1987), que se rompen dejándoles caer una roca encima y sueltan una esmeralda.

**Qué hay de nuevo:** la **nuez** (`n`). Se comporta como una roca: cae, rueda y se empuja. Si le cae una roca se rompe y deja un diamante. Si cae sobre algo, o le cae otra nuez, no le pasa nada.

**Necesarios:** 12 diamantes · **diamantes en el mapa:** 0 · **rocas:** 17 · **tiempo:** 150 s

```
########################################
#12....o.......o.......o.......o.......#
#......................................#
#......n.......n.......n.......n.......#
#WWWWWWWWWWWWWWWWWW..WWWWWWWWWWWWWWWWWW#
#......................................#
#..o...o...o...o......o...o...o...o....#
#......................................#
#                                      #
#    F                                 #
#                                      #
#    n     n        n      n      n    #
#WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW...W#
#...o.....o.....o.........o.....o......#
#......................................#
#...n.....n.....n.........n.....n......#
#...n...........n...............n......#
#........   ...........................#
#........ B ...........................#
#........   ...........................#
#....................................X.#
########################################
```

**Qué hay:** Tres pisos y ningún diamante suelto, solo 17 nueces:
  - Arriba, cuatro nueces sobre una repisa de ladrillo, cada una con una roca dos cuadros más arriba y tierra en medio.
  - Al medio, una sala vacía con una luciérnaga y cinco nueces en el suelo. Sobre la sala hay una capa de tierra con ocho rocas, y solo dos de ellas están justo sobre una nuez.
  - Abajo, nueces con una roca a la espera dos cuadros más arriba, y tres de ellas con otra nuez debajo. Además hay una mariposa encerrada.

**El desafío:** Se necesitan 12 diamantes y cada uno sale de una nuez rota. En la sala, solo dos nueces tienen una roca justo encima: a las otras tres hay que llevársela. En las pilas de dos nueces, la segunda necesita otra roca.

**Cómo se pasa:**

- **Arriba:** cavar la tierra entre roca y nuez. La roca cae y la rompe: cuatro diamantes fáciles.
- **En la sala:** empujar las rocas de la capa de tierra (de lado, cavando delante) hasta quedar justo sobre la columna de una nuez, y cavar debajo para que caiga a través de la sala. Si una roca cae en el lugar equivocado, se pierde.
- **Abajo:** lo mismo, y una roca que se cae a un lado puede empujarse de nuevo.
- **La mariposa:** aplastada da 9 diamantes, por si faltan.
- **Salida:** abajo a la derecha, por el hueco del suelo de la sala.

**Con dos jugadores:** uno suelta la roca y el otro espera para tomar el diamante antes de que ruede. Desde arriba uno puede guiar al otro: «un cuadro más a la izquierda».

**En el juego:** la nuez es una celda con la física de la roca (cae, rueda y se empuja). Una roca que cae sobre ella la vuelve diamante.

---

<a id="2-llaves-que-se-gastan"></a>

## 2. Llaves que se gastan

**De dónde sale:** las llaves y puertas de colores de *Emerald Mine*, y las llaves pequeñas de *Zelda*, que sirven para una sola puerta.

**Qué hay de nuevo:** la **llave** (`a`) y la **puerta** (`A`). La llave se recoge como un diamante (se ve en la barra) y se gasta al abrir una puerta.

**Necesarios:** 12 diamantes · **diamantes en el mapa:** 18 · **rocas:** 38 · **tiempo:** 150 s

```
########################################
#12..o.....o.....o......o.....o....o...#
#.........a....................a.......#
#..o....o.....o....o......o.....o....o.#
#......................................#
#....o.......o..........o........o.....#
#......................................#
#WWWWWWAWWWWWWWWWWWWAWWWWWWWWWWWWAWWWWW#
#............Wo.o.o.o.o.o.W            #
#.*..*..*..*.W.*o*o*o*o*o.W            #
#............W.o.o.o.o.o..W  F         #
#..*..*..*...W............W            #
#............W.....*......W            #
#.*.....*....W............W            #
#............W............W            #
#............W..o.........W        F   #
#...o........W............W            #
#........o...W........o...W            #
#............W............W            #
#.....o......W............W            #
#............W............W *   *   * X#
########################################
```

**Qué hay:** Arriba hay una franja de tierra con rocas y dos llaves. Debajo, separadas por un muro de ladrillo con tres puertas, hay tres salas:
  1. Nueve diamantes fáciles en tierra.
  2. Seis diamantes entre rocas, que se derrumban al sacarlos.
  3. Una sala vacía con dos luciérnagas, tres diamantes en el suelo y la salida.

**El desafío:** Tres puertas y solo dos llaves. La sala 3 es obligatoria (tiene la salida) y se necesitan 12 diamantes: la sala 1 más la 3 dan 12 justos; la 2 más la 3 dan solo 9.

**Cómo se pasa:** Mirar las salas antes de abrir: con la sala 1 y la 3 se pasa. Al abrir la puerta de la sala 3, las luciérnagas pueden subir por los túneles de arriba, así que conviene abrirla al final, con los nueve diamantes de la sala 1 ya juntos, y bajar rápido por los del suelo.

**Con dos jugadores:** las llaves son del equipo, pero cada una la lleva quien la recogió. Hay que ponerse de acuerdo sobre qué puerta abre cada uno.

**En el juego:** cada niño lleva sus llaves (🔑 en el marcador). Una puerta se abre solo para quien tiene una, y se la gasta; la puerta abierta queda como un hueco.

---

<a id="3-pasos-de-un-sentido"></a>

## 3. Pasos de un sentido

**De dónde sale:** los puertos de *Supaplex* (1991), pasos que se cruzan solo en una dirección.

**Qué hay de nuevo:** el **paso** (`>` `<` `v`), una celda que el niño cruza solo en el sentido de la flecha, saltando al otro lado. Las rocas y los enemigos no la atraviesan.

**Necesarios:** 22 diamantes · **diamantes en el mapa:** 26 · **rocas:** 11 · **tiempo:** 180 s

```
########################################
#12...o.*....W....o...*...W.....o..*...#
#...*........>..*.........>...*........#
#............W............W............#
#WWWWWWWWWWWWWWWWWWWvWWWWWWWWWWWWWvWWWW#
#......*..W...*.o...........W.......*..#
#..*......<.................<..*.......#
#.........W............*....W......o...#
#WWWWvWWWWWWWWWWWWWWWWWWvWWWWWWWWWWWWWW#
#........*..o......W...*...o...........#
#...*..............>.............*.....#
#..............*...W...................#
#WWWWWWWWWWWWWWWWWWWWWWWWWWWWWvWWWWWWWW#
#.......o...W.........*..W....*..o.....#
#...........<....*.......<.............#
#.....*.....W............W.........*...#
#WWWvWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW#
#..........o........W.....*..o.........#
#.......*...........W..................#
#...................>...........*......#
#.............*.....W................X.#
########################################
```

**Qué hay:** Cinco pisos separados por ladrillo:
  - Cada piso está dividido en tramos por pasos horizontales y baja al siguiente por pasos hacia abajo.
  - Hay 26 diamantes, dos o tres por tramo, y algunas rocas.
  - Se parte arriba a la izquierda y la salida está abajo a la derecha.

**El desafío:** Se necesitan 22 diamantes, o sea, se pueden perder solo 4. Los caminos se bifurcan:
  - En el piso 1, el paso hacia abajo del tramo del medio deja atrás el tramo de la derecha.
  - En el piso 2, el paso del tramo del medio lleva directo al lado derecho del piso 3 y deja atrás 5 diamantes: el tramo izquierdo del piso 2 y el del piso 3. Con esos 5 perdidos ya no alcanza.

**Cómo se pasa:**

Seguir con la vista las flechas antes de moverse. Hay un camino que pasa por todos los tramos:
  - En el piso 1, todo hacia la derecha y bajar por el último paso.
  - En el piso 2, de derecha a izquierda, bajando por el paso del extremo izquierdo.
  - En el piso 3, hacia la derecha.
  - En el piso 4, hacia la izquierda.
  - En el piso 5, hacia la derecha hasta la salida.

Antes de cruzar cada paso, tomar todo lo de ese tramo. Es una cueva de pensar más que de reflejos.

**Con dos jugadores:** cada uno puede tomar una rama distinta y juntar los diamantes que el otro deja atrás: entre los dos sobran. Pero el que va adelante no puede volver a ayudar.

**En el juego:** la flecha se cruza solo hacia donde apunta: el niño salta al cuadro siguiente, y si ahí hay tierra la cava. En sentido contrario es una pared.

---

<a id="4-barriles"></a>

## 4. Barriles

**De dónde sale:** los discos naranjos de *Supaplex*, que explotan al caer, y las bombas de *Emerald Mine*.

**Qué hay de nuevo:** el **barril** (`%`). Se empuja como una roca. Si cae, o le cae algo encima, explota en 3×3 como una luciérnaga: rompe ladrillo, tierra y diamantes, y mata.

**Necesarios:** 16 diamantes · **diamantes en el mapa:** 19 · **rocas:** 17 · **tiempo:** 180 s

```
########################################
#12.........o...........o..............#
#...o...............o.......o......o...#
#.......%.......o..............%.......#
#......................................#
#.....o...........o.......o..........o.#
#.............o........................#
#......................................#
#..WWWWWWWWW.WWWWWWWWWW....WWWWWWWWW...#
#..W       W.W        W....W       W...#
#..W * * * W.W * * * *W....W * * * W...#
#..W       W.W        W....W       W...#
#..W * * * W.W  * * * W....W * * * W...#
#..WWWWWWWWW.WWWWWWWWWW....WWWWWWWWW...#
#......................................#
#......................................#
#....o...........   .....o.............#
#................ F ................o..#
#.........o......   ...................#
#.............................o........#
#....................................X.#
########################################
```

**Qué hay:** Arriba hay tierra con rocas y dos barriles. Al medio, tres salas de ladrillo cerradas con 19 diamantes en total; entre las dos primeras queda una sola columna de tierra. Abajo hay una luciérnaga encerrada en un huequito.

**El desafío:** Se necesitan 16, más de lo que tienen las dos primeras salas juntas (13), así que hay que abrir las tres. Hay dos barriles y una luciérnaga para tres salas.

**Cómo se pasa:**

- **Las dos primeras salas:** cavar un pozo en la columna de tierra que las separa, empujar un barril sobre el pozo y apartarse. Al caer explota contra el fondo del pozo y abre las dos salas de un golpe. El pozo no debe llegar hasta abajo, o el barril pasa de largo.
- **La tercera sala:** dejar caer el otro barril sobre su techo.
- **La luciérnaga:** sirve de repuesto si un barril explota antes de tiempo.
- **Salida:** abajo a la derecha.

**Con dos jugadores:** uno empuja el barril y el otro, desde lejos, cava el último cuadro del pozo. Nadie debe estar a menos de un cuadro.

**En el juego:** el barril tiene la física de la roca. Estalla (3 × 3) si cae, si le cae algo encima o si lo alcanza otra explosión, así que los barriles juntos estallan en cadena.

---

<a id="5-placas"></a>

## 5. Placas

**De dónde sale:** *Sokoban*, pero con gravedad: aquí las rocas no se dejan donde uno quiere, caen.

**Qué hay de nuevo:** la **placa** (`_`), una celda del suelo que se ilumina cuando tiene una roca encima. Con todas encendidas se abre la salida: en esta cueva no hay diamantes que juntar.

**Para abrir la salida:** las 5 placas con roca · **diamantes en el mapa:** 0 · **rocas:** 7 · **tiempo:** 200 s

```
########################################
#12...................................X#
#......................................#
#......................................#
#....o......o.......o......o...........#
#......................................#
#......................................#
#                                      #
#                                      #
#                                      #
#                                      #
#WWWWWWWW_WWWWWWWW_WWWWWWWWWWW_WWWWW..W#
#......................................#
#                                      #
#            o                         #
#           WWW                    F   #
#                                      #
#                           o    o     #
#WWWWWW_WWWWWWWWWWWWWW_WWWWWWWWWWWWWWWW#
#......................................#
#......................................#
########################################
```

**Qué hay:** Dos salas vacías una sobre otra:
  - **Arriba**, el suelo tiene tres placas y encima de la sala hay una capa de tierra con cuatro rocas que no están sobre las placas.
  - **Abajo**, el suelo tiene dos placas, y hay tres rocas (una sobre un saliente de ladrillo) y una luciérnaga.
  - Se parte arriba a la izquierda, y la salida está arriba a la derecha.

**El desafío:** Llevar una roca a cada una de las cinco placas.
  - En la sala de arriba, las rocas tienen que *caer* exactamente sobre la placa. Si caen sobre otra roca, ruedan.
  - En la de abajo se pueden empujar por el suelo, pero con la luciérnaga dando vueltas.

**Cómo se pasa:**

- **Arriba:** cavar delante de cada roca para empujarla de lado hasta la columna de una placa, y después cavar la tierra que la sostiene. Cae a través de la sala justo sobre la placa. Hay una roca de sobra para un error.
- **Abajo:** bajar por el hueco del suelo de la derecha, empujar la roca del saliente para que caiga y llevarla por el suelo a su placa, y lo mismo con una de las del suelo.
- **Salida:** volver arriba.

**Con dos jugadores:** uno empuja desde arriba y el otro, en la sala de abajo, distrae a la luciérnaga o empuja.

**En el juego:** la placa es sólida. La salida se abre cuando todas las placas tienen una roca encima; esta cueva no pide diamantes.

---

<a id="6-inundación"></a>

## 6. Inundación

**De dónde sale:** el aire que se acaba en *Mr. Driller* y el agua que sube de tantos juegos de plataformas.

**Qué hay de nuevo:** el **agua** (`~`). Sube una fila cada algunos segundos desde abajo, y las rocas y los diamantes se hunden en ella. Un niño bajo el agua aguanta unos segundos (se ve una barra de aire) y después se ahoga.

**Necesarios:** 16 diamantes · **diamantes en el mapa:** 20 · **rocas:** 15 · **tiempo:** 150 s

```
########################################
#........o...X.............o.......*...#
#....*..............o..................#
#.............................*........#
#WWWWWWWWWWWWWWWWWWWWW..WWWWWWWWWWWWWWW#
#..o..............*...........o........#
#.........*...o.....................*..#
#.........................*............#
#WWW..WWWWWWWWWWWWWWWWWWWWWWWWWWWW..WWW#
#..........o....*........o.............#
#.......*....................*......o..#
#.....................*................#
#WWWWWWWWWWWWWWWWW..WWWWWWWWWWWWWWWWWWW#
#......o....*...............o..........#
#...*............o...............*.....#
#.......................*..............#
#WWWWWWW..WWWWWWWWWWWWWWWWWWWW..WWWWWWW#
#.........o...*........o...........*...#
#.....*....................*.....o.....#
#.12................*..................#
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
########################################
```

**Qué hay:** Cinco pisos de ladrillo, cada uno con huecos en lugares distintos para subir al siguiente. Hay unos cuatro diamantes por piso (20 en total) y rocas. Se parte abajo, junto al agua, y la salida está arriba.

**El desafío:** Se necesitan 16 diamantes, mientras el agua no deja volver a buscar los que quedaron abajo.

**Cómo se pasa:** Juntar los diamantes de cada piso antes de subir, sin cavar de más. Los huecos de un piso y del siguiente no están alineados, así que hay que cruzar cada piso de lado a lado. No cavar hacia arriba bajo una roca. Mirar el ritmo del agua y no quedarse atrás.

**Con dos jugadores:** uno va adelante abriendo camino y el otro limpia el piso. Si uno se queda bajo el agua, el otro puede abrirle una salida hacia arriba.

**En el juego:** el agua sube una fila cada 7,5 segundos (menos en los niveles altos). Bajo el agua un niño tiene 4 segundos de aire (una barra sobre su cabeza), que se recupera al salir. Las rocas y los diamantes siguen cayendo igual.

---

<a id="7-el-comelón"></a>

## 7. El comelón

**De dónde sale:** el *Yam-Yam* de *Emerald Mine* y *Rocks'n'Diamonds*, una bestia que se come lo que encuentra y explota soltando lo que tenía adentro.

**Qué hay de nuevo:** el **comelón** (`Y`). Avanza en línea recta por el espacio vacío y da la vuelta al chocar. Se come los diamantes que encuentra y mata al tocar. Si le cae una roca encima explota y deja **todos** los diamantes que se comió, más uno de propina, alrededor.

**Necesarios:** 30 diamantes · **diamantes en el mapa:** 41 · **rocas:** 11 · **tiempo:** 150 s

```
########################################
#.......o.......o.......o.......o......#
#......................................#
#.Y                                   .#
#.  * * * * * * * * * * * * * * * *   .#
#......................................#
#.12...................................#
#......................................#
#.....o.......o.......o.......o........#
#......................................#
#.                                   Y.#
#.   *   *   *   *   *   *   *   *    .#
#......................................#
#......................................#
#......................................#
#.........o.........o.......o..........#
#......................................#
#.                                    .#
#. * * * * * * * * * * * * * * * * *  .#
#......................................#
#....................................X.#
########################################
```

**Qué hay:** Tres pasillos vacíos, uno sobre otro, con 41 diamantes en fila en el suelo. Hay un comelón en el de arriba y otro en el del medio. Sobre cada pasillo, con un cuadro de tierra en medio, esperan algunas rocas. Se parte entre el pasillo de arriba y el del medio.

**El desafío:** Se necesitan 30. Si uno se apura a juntar, compite con los comelones; si los deja comer, se llenan, y aplastados devuelven todo junto.

**Cómo se pasa:** Juntar primero el pasillo de abajo, donde no hay comelón. Dejar que los otros dos coman un rato y, cuando pasen bajo una roca, cavar el cuadro de tierra que la sostiene. Hay que medir el tiempo: muy pronto dan poco, y muy tarde se acaba el reloj o uno se cruza en su camino. Salida abajo a la derecha.

**Con dos jugadores:** uno distrae al comelón (lo hace dar la vuelta cruzándose a lo lejos) mientras el otro suelta la roca.

**En el juego:** el comelón avanza en línea recta por el vacío, se come los diamantes de su camino y da la vuelta al chocar. Si toca a un niño, el niño muere (solo él). Aplastado por una roca o un barril, suelta todo lo que comió más uno.

---

<a id="8-tierra-viva"></a>

## 8. Tierra viva

**De dónde sale:** los hoyos de *Lode Runner* (1983), que se vuelven a llenar solos y atrapan a los guardias.

**Qué hay de nuevo:** la **tierra viva** (`:`). Se cava como la normal, pero el hoyo se vuelve a llenar a los 6 segundos. Si al llenarse hay un enemigo adentro, lo aplasta: una mariposa deja 9 diamantes y una luciérnaga nada. Nunca se cierra sobre un niño, pero sí puede dejarlo encerrado (basta con volver a cavar).

**Necesarios:** 20 diamantes · **diamantes en el mapa:** 8 · **rocas:** 4 · **tiempo:** 150 s

```
########################################
#12::::::::::::::::::::::::::::::::::::#
#:::::::::::::*::::::::::::::::::::::::#
#::::::::::::::::::::::::*:::::::::::::#
#:::::B::::::::::::::::::::::::::B:::::#
#::::::::::::::::::::::::::::::::::::::#
#:::::::::::::::::::F::::::::::::::::::#
#:::::::::::::::::::::::::::::::::::*::#
#:::*::::::::::::::::::::::::::::::::::#
#::::::::::::::::::::::::::::::::::::::#
#.......o.........o........o.......o...#
#......................................#
#::::::::::::::::::::::::::::::::::::::#
#::::::::::::::::::::::::::::::*:::::::#
#::::::::*:::::::::::::::::::::::::::::#
#::::::::::::::::::::::::::::::::::::::#
#:::::::::::B:::::::::::::::B::::::::::#
#:::::::::::::::::::F::::::::::::::::::#
#::::::::::::::::::::::::::::::::::::::#
#::::::::::::::::*:::::::::::::::::::::#
#:::::::::::::::::::::::*:::::::::::::X#
########################################
```

**Qué hay:** Casi toda la cueva es tierra viva. Hay cuatro mariposas y dos luciérnagas enterradas en ella, sin espacio para moverse, y 8 diamantes sueltos. Por la mitad cruza una franja de tierra normal, con algunas rocas.

**El desafío:** Se necesitan 20: los 8 diamantes más los de al menos dos mariposas. Los enemigos solo pueden moverse por los túneles que uno abre, y esos túneles se cierran detrás.

**Cómo se pasa:** Abrir un túnel hasta una mariposa, dejar que lo siga y alejarse. Cuando la tierra se cierre con la mariposa adentro, explota en diamantes. Volver por la franja de tierra normal, que no se cierra. A las luciérnagas no conviene abrirles camino.

**Con dos jugadores:** uno hace de cebo cavando y el otro mantiene abierto un túnel paralelo para escapar.

**En el juego:** la tierra viva se cava como la normal y vuelve a crecer a los 6 segundos. Si hay una luciérnaga o una mariposa, la aplasta (la mariposa deja diamantes); si hay un niño o una roca, espera.

---

<a id="9-cueva-giratoria"></a>

## 9. Cueva giratoria

**De dónde sale:** los puertos de gravedad de *Supaplex* y la opción de gravedad oculta de este mismo juego (la tecla G).

**Qué hay de nuevo:** el **interruptor de gravedad** (`G`). Al pisarlo, la gravedad de toda la cueva gira un cuarto de vuelta: rocas y diamantes pasan a caer hacia la izquierda, hacia arriba o hacia la derecha. Los niños, como siempre, no caen.

**Necesarios:** 24 diamantes · **diamantes en el mapa:** 40 · **rocas:** 64 · **tiempo:** 180 s

```
########################################
#12....................................#
#...........G..............G...........#
#..WWWWWWW.......o....o.......WWWWWWW..#
#..Wooooo.....................W*****W..#
#..Wooooo.....................W*****W..#
#..Wooooo.....            ....WoooooW..#
#..W*****.....            ....WoooooW..#
#..W*****.....  B         ....WoooooW..#
#..WWWWWWW....            ....W.....W..#
#.............            .............#
#.............            .............#
#..W.....W....            ....WWWWWWW..#
#..WoooooW....         B  .....oooooW..#
#..WoooooW....            .....oooooW..#
#..WoooooW....            .....oooooW..#
#..W*****W.....................*****W..#
#..W*****W.....................*****W..#
#..WWWWWWW........o..o........WWWWWWW..#
#...........G..............G...........#
#....................................X.#
########################################
```

**Qué hay:** En el centro hay una sala vacía con dos mariposas, y en cada esquina un bolsillo de ladrillo con 10 diamantes y 15 rocas. Cada bolsillo tiene la boca de un lado distinto:
  - arriba a la izquierda, a la derecha (rocas encima, diamantes abajo);
  - arriba a la derecha, por abajo (diamantes encima de las rocas);
  - abajo a la izquierda, por arriba (diamantes al fondo, bajo las rocas);
  - abajo a la derecha, a la izquierda.

Hay cuatro interruptores alrededor de la sala.

**El desafío:** Se necesitan 24, de al menos tres bolsillos. Con la gravedad normal solo se vacía uno: el que tiene la boca abajo, cavándola desde un lado mientras caen primero las rocas. Los demás necesitan que la gravedad apunte hacia su boca, y cada giro mueve también las rocas de los otros bolsillos.

**Cómo se pasa:**

Para cada bolsillo:
  1. Cavar un canal desde su boca.
  2. Ponerse fuera del camino.
  3. Girar la gravedad hacia la boca: salen primero las rocas y después los diamantes.

Antes de cada giro, mirar qué más se va a mover: las rocas de arriba y de abajo de la sala pueden caer sobre una mariposa (9 diamantes más) o sobre uno.

**Con dos jugadores:** el giro afecta a los dos, así que quien pisa el interruptor avisa o espera a que el otro esté a salvo.

**En el juego:** al pisar el interruptor la gravedad gira un cuarto de vuelta (abajo → izquierda → arriba → derecha → abajo), con un aviso en pantalla. Al salir de la cueva vuelve a ser normal.

---

<a id="10-dos-llaves-una-puerta"></a>

## 10. Dos llaves, una puerta

**De dónde sale:** los botones de *Fireboy & Watergirl* y *Portal 2*, donde dos jugadores se turnan para abrirse paso.

**Qué hay de nuevo:** la **placa** (`p` `q` `r` `s` `t` `u`) y su **compuerta** (`P` `Q` `R` `S` `T` `U`). La compuerta está abierta mientras alguien (un niño o una roca) está sobre su placa, y se cierra al soltarla, pero nunca sobre alguien.

**Necesarios:** 8 diamantes · **diamantes en el mapa:** 10 · **rocas:** 6 · **tiempo:** 240 s

```
########################################
#.1.......W.........W.........W........#
#.........W....r.o..W....t.o..W........#
#.........W.........W.........W..*.....#
#...*.....W.........W.........W........#
#.........Q.........S.........U........#
#.........W...*.....W.........W........#
#.........W.........W...*.....W........#
#.....p.o.W.........W.........W........#
#.........W..*......W.........W........#
#.........#####################....X...#
#.........#####################........#
#.........W.........W.........W........#
#.........W.........W.....*...W........#
#......*..W......*..W.........W........#
#.........W.........W.........W........#
#.........P.........R.........T........#
#.........W.........W.........W....u.o.#
#.........W.........W.......*.W........#
#.........W....q.o..W....s.o..W........#
#.2.......W.........W.........W.....*..#
########################################
```

**Qué hay:** Dos pisos largos separados por acero, unidos solo en los extremos. Cada piso está dividido en tramos por compuertas, y la placa de cada compuerta está **en el otro piso**. Junto a cada placa hay una roca, y hay diamantes en los tramos. J1 parte arriba, J2 abajo; la salida está en el extremo derecho, donde se juntan los dos pisos.

**El desafío:** Ninguno puede avanzar solo: cada compuerta se abre desde el piso del otro. Se necesitan 8 diamantes de los 10.

**Cómo se pasa:**

La cadena va así:
  1. J1 pisa `p` y J2 cruza `P`.
  2. J2 pisa `q` y J1 cruza `Q`.
  3. J1 pisa `r` y J2 cruza `R`.
  4. J2 pisa `s` y J1 cruza `S`.
  5. J1 pisa `t` y J2 cruza `T` al extremo derecho.
  6. Allí J2 pisa `u` y J1 cruza `U`.

En 1 jugador se puede igual, pero es largo: hay que empujar la roca de cada placa sobre ella para que la sostenga, y cruzar de un piso al otro por el extremo izquierdo.

**Con dos jugadores:** es el centro de la cueva, pensada para cooperativo: hay que hablar y coordinarse. En versus se puede usar al revés: soltar la placa en el momento justo para encerrar al otro.

**En el juego:** cada placa abre su compuerta mientras haya algo encima (un niño, una roca, una nuez, un barril o un diamante) y la cierra al quedar libre, pero nunca sobre algo.

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

De lo más simple a lo más trabajoso, aprovechando lo que el juego ya tiene:

1. **Cueva giratoria**: la gravedad ya gira.
2. **Pasos de un sentido**.
3. **Nueces**.
4. **Barriles**: usan la explosión que ya existe.
5. **Placas**.
6. **Tierra viva**.
7. **Dos llaves, una puerta**: comparte las placas con la 5.
8. **Llaves que se gastan**.
9. **El comelón**.
10. **Inundación**.

Todas son reglas de las cuevas originales, así que no tocan las cuevas aleatorias de entrenamiento ni su copia en Python. Las de dos jugadores se juegan igual en dos celulares, porque el juego ya sincroniza todo lo que pasa en la cueva.
