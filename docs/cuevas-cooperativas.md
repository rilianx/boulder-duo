# 10 cuevas cooperativas

Cuevas para **dos jugadores**, en las que **ninguno puede salir solo**. Siguen la idea de la cueva nueva n.º 10 («Dos llaves, una puerta») y se van complicando de a una. Se juegan con el botón **CUEVAS COOPERATIVAS** del menú, en cooperativo o con dos celulares (la opción 1 JUGADOR queda apagada en este juego de cuevas).

## De dónde salen las ideas

No hay mapas de Portal 2 o Fireboy & Watergirl que se puedan usar tal cual: Portal 2 es 3D, y los niveles de Fireboy & Watergirl son de plataformas (se salta y se cae), no están publicados como datos y tienen dueño. Lo que sí se toma de esos juegos son sus patrones de puzle cooperativo:

- **Botón que uno sostiene mientras el otro pasa** (Fireboy & Watergirl, Portal 2): la placa.
- **Palanca que queda como se deja** (Fireboy & Watergirl): la palanca.
- **Botón con tiempo** (Portal 2, Pico Park): la placa con reloj.
- **Zonas que solo cruza uno** (el fuego y el agua de Fireboy & Watergirl): las barreras azul y naranja.
- **Separar a los jugadores** para que nadie pueda hacerlo solo, y **comprobar que de verdad no se pueda** (consejo repetido en guías de diseño cooperativo).

## Las piezas

Las mismas para cualquier mapa, también en el [editor de cuevas](editor-de-cuevas.md):

| Letra | Pieza | Qué hace |
|---|---|---|
| `p`…`u` | placa 1…6 | Enciende su grupo mientras algo (un niño, una roca, un diamante) está encima. |
| `P`…`U` | compuerta 1…6 | Abierta mientras su grupo está encendido. Nunca se cierra encima de alguien. |
| `D` `E` | palanca 1 y 2 | Un empujón la da vuelta: enciende o apaga su grupo, y queda así. |
| `[` `]` | placa con reloj 1 y 2 | Como la placa, pero su grupo sigue encendido unos segundos después de soltarla (4 por defecto; `timer=` en los ritmos). |
| `N` `V` | compuerta inversa 1 y 2 | Al revés que la compuerta: cerrada mientras su grupo está encendido. |
| `(` | barrera de J1 | Solo J1 la cruza (azul). Para J2, las cosas y los enemigos es pared. |
| `)` | barrera de J2 | Solo J2 la cruza (naranja). |

Cada grupo tiene **su color**: una luz en la esquina de sus placas, compuertas y palancas muestra qué abre qué. Para más de dos palancas, relojes o compuertas inversas, un mapa agrega letras propias (por ejemplo `3=tplate:3 4=lever:4`).

## Cómo se hicieron y se comprobaron

1. **Un generador** arma cada cueva como salas en cuadrícula, unidas por puertas que pueden ser pared, paso libre, compuerta (normal o inversa, de un color) o barrera, con placas y palancas en las salas. Cada nivel pide ciertas piezas y un largo de solución.
2. **Un resolvedor** prueba todas las jugadas posibles de los dos niños (en qué sala está cada uno, si está sobre una placa, cómo están las palancas y los relojes) y se queda con las cuevas que se pueden pasar **de a dos** pero **no con un niño solo**, y en las que la solución usa lo nuevo del nivel.
3. **Cada solución se jugó en el juego de verdad**: los niños caminan por el mapa, cuadro a cuadro y de a uno, siguiendo el plan del resolvedor, y los dos salen. Como en la prueba se mueve uno a la vez, en el juego real (los dos a la vez) los relojes alcanzan con más holgura.

Las herramientas están en [`tools/cuevas-cooperativas`](../tools/cuevas-cooperativas/README.md).

Los diamantes pedidos son unos dos tercios de los que hay en las salas por las que pasa la solución.

| # | Cueva | Lo nuevo | Movimientos de la solución más corta |
|---|---|---|---|
| 1 | [Turnos](#1) | placa y compuerta | 6 |
| 2 | [Dos pisos](#2) | colores de grupo | 14 |
| 3 | [La palanca](#3) | palanca | 16 |
| 4 | [Esclusa](#4) | compuerta inversa | 16 |
| 5 | [Con reloj](#5) | placa con reloj | 12 |
| 6 | [Fuego y agua](#6) | barreras | 19 |
| 7 | [Relevo](#7) | palanca + inversa | 24 |
| 8 | [Contrarreloj](#8) | reloj + barreras | 25 |
| 9 | [Engranaje](#9) | todo junto | 30 |
| 10 | [Gran final](#10) | todo, separados | 32 |

---

<a id="1"></a>

## 1. Turnos

Lo básico: la placa abre la compuerta de su color mientras alguien está encima. Uno sostiene y el otro pasa; después se invierten los papeles.

**Pista al entrar:** «Uno pisa la placa y el otro pasa. Después, al revés.» · **diamantes:** 4 · **solución:** 6 movimientos

```
########################################
#............W............W............#
#.......*....W.......*....W.......*....#
#...1.2......W............W............#
#............W............W......X.....#
#..*.........W..*.........W..*.........#
#......p.....W............W......p.....#
#............W............W............#
#............W............W............#
#............W............W............#
#............P............P............#
#............W............W............#
#............W............W............#
#............W............W............#
#............W............W............#
#............W............W............#
#............W............W............#
#............W............W............#
#............W............W............#
#............W............W............#
#............W............W............#
########################################
```

---

<a id="2"></a>

## 2. Dos pisos

Tres colores. Ya no basta con turnarse: hay que mirar la luz de color de cada placa y compuerta para saber quién va dónde. J1 y J2 parten en salas distintas.

**Pista al entrar:** «Cada placa abre las compuertas de su color: mira la luz de la esquina.» · **diamantes:** 8 · **solución:** 14 movimientos

```
########################################
#............W............W............#
#.......*....W.......*....W.......*....#
#...1........W............W............#
#............W............W............#
#..*.........W..*.........P..*.........#
#............W......r.....W......p.....#
#............W............W............#
#............W............W............#
#............W............W............#
#............W............W............#
#WWWWWRWWWWWWWWWWWW.WWWWWWWWWWWW.WWWWWW#
#............W............W............#
#.......*....W.......*....W.......*....#
#............W.....2......W............#
#............W............W......X.....#
#..*.........Q..*.........R..*.........#
#............W......q.....W............#
#............W............W............#
#............W............W............#
#............W............W............#
########################################
```

---

<a id="3"></a>

## 3. La palanca

La palanca deja su grupo encendido sin que nadie se quede encima, y se apaga con otro empujón. Sirve para que los dos avancen juntos, pero también puede cerrar lo que el otro necesita abierto.

**Pista al entrar:** «La palanca queda como la dejas: no hace falta quedarse ahí.» · **diamantes:** 8 · **solución:** 16 movimientos

```
########################################
#............W............W............#
#.......*....W.......*....W.......*....#
#...1.2......W............W............#
#............W............W............#
#..*.........P..*............*.........#
#......p.....W............W......q.....#
#............W............W............#
#............W............W............#
#............W............W............#
#............W............W............#
#WWWWWQWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW#
#............W............W............#
#.E.....*....W.......*....W.......*....#
#............W............W............#
#............W............W......X.....#
#..*.........Q..*.........Q..*.........#
#............W............W............#
#............W............W............#
#............W............W............#
#............W............W............#
########################################
```

---

<a id="4"></a>

## 4. Esclusa

La compuerta inversa (con la X) está abierta mientras su grupo está apagado y se cierra cuando se enciende. Con una normal y una inversa del mismo color se arma una esclusa: nunca están las dos abiertas.

**Pista al entrar:** «La compuerta con la X se cierra cuando su color se abre: nunca están abiertas las dos.» · **diamantes:** 9 · **solución:** 16 movimientos

```
########################################
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#...1.2...W.........W.........W........#
#.........W.........W.........W........#
#..*......N..*......P..*......W..*.....#
#.........W.........W......p..W........#
#.........W.........W.........W........#
#.........W.........W.........W........#
#.........W.........W.........W........#
#.........W.........W.........W........#
#WWWWWWWWWWWWWW.WWWWWWWWWNWWWWWWWWVWWWW#
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#.........W.........W.........W........#
#.........W.........W.........W......X.#
#..*.........*......Q..*.........*.....#
#......q..W.........W.........W........#
#.........W.........W.........W........#
#.........W.........W.........W........#
#.........W.........W.........W........#
########################################
```

---

<a id="5"></a>

## 5. Con reloj

La placa con reloj sigue encendida unos segundos después de soltarla. El que la suelta tiene que correr, o el otro tiene que estar listo para cruzar.

**Pista al entrar:** «La placa con reloj sigue apretada unos segundos después de soltarla. ¡Corre!» · **diamantes:** 9 · **solución:** 12 movimientos · ritmos `timer=5`

```
########################################
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#...1.2...W.........W.........W........#
#.........W.........W.........W........#
#..*......Q..*......P..*......P..*.....#
#......]..W.........W......[..W........#
#.........W.........W.........W........#
#.........W.........W.........W........#
#.........W.........W.........W........#
#.........W.........W.........W........#
#WWWW.WWWWWWWWWQWWWWWWWWWQWWWWWWWWPWWWW#
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#.........W.........W.........W........#
#.........W.........W.........W......X.#
#..*......Q..*......Q..*......W..*.....#
#.........W.........W.........W........#
#.........W.........W.........W........#
#.........W.........W.........W........#
#.........W.........W.........W........#
########################################
```

---

<a id="6"></a>

## 6. Fuego y agua

Las barreras dejan pasar a uno solo: la azul a J1, la naranja a J2. Cada uno tiene salas a las que el otro no llega, y desde ahí le abre el camino.

**Pista al entrar:** «La barrera azul solo deja pasar a J1; la naranja, solo a J2.» · **diamantes:** 14 · **solución:** 19 movimientos

```
########################################
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#.........)...1.....R.....2...P........#
#.........W.........W.........W........#
#..*......W..*......W..*......W..*.....#
#.........W.........W.........W........#
#WWWW(WWWWWWWWWRWWWWWWWWW)WWWWWWWWRWWWW#
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#.........(.........(.........W........#
#.........W.........W.........W........#
#..*......W..*......W..*......W..*.....#
#.........W.........W......r..W........#
#WWWW(WWWWWWWWW)WWWWWWWWWQWWWWWWWW.WWWW#
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#.........(.........P.........Q........#
#.........W.........W.........W......X.#
#..*......W..*......W..*......W..*.....#
#.........W......p..W.........W......q.#
########################################
```

---

<a id="7"></a>

## 7. Relevo

Palancas y compuertas inversas juntas: encender un grupo abre un paso y cierra otro, así que importa el orden en que se tocan.

**Pista al entrar:** «Palancas y compuertas al revés: piensen el orden juntos.» · **diamantes:** 10 · **solución:** 24 movimientos · letras propias `3=gatei:3 4=lever:3`

```
########################################
#.........W.........W.........W........#
#.4.....*.W.......*.W.......*.W.......*#
#...1.2...Q.........R.........W........#
#.........W.........W.........W........#
#..*......W..*......W..*......W..*.....#
#......q..W.........W.........W........#
#WWWWWWWWWWWWWWWWWWWWWWWWVWWWWWWWWRWWWW#
#.........W.........W.........W........#
#.......*.W.E.....*.W.......*.W.......*#
#.........W.........Q.........3........#
#.........W.........W.........W........#
#..*......W..*......W..*......W..*.....#
#.........W.........W.........W........#
#WWWW3WWWWWWWWWWWWWWWWWWW3WWWWWWWW.WWWW#
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#.........R.........V.........W........#
#.........W.........W.........W......X.#
#..*......W..*......W..*......W..*.....#
#.........W......p..W......r..W........#
########################################
```

---

<a id="8"></a>

## 8. Contrarreloj

Relojes y barreras: quien suelta la placa no es quien cruza, y el que cruza a veces está detrás de una barrera que el otro no puede pasar.

**Pista al entrar:** «Relojes y barreras: cuando uno suelta, el otro corre.» · **diamantes:** 13 · **solución:** 25 movimientos · ritmos `timer=6` · letras propias `3=tplate:3`

```
########################################
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#...1.2...(...................)........#
#.........W.........W.........W........#
#..*......W..*......W..*......W..*.....#
#.........W......3..W.........W........#
#WWWWRWWWWWWWWW)WWWWWWWWW(WWWWWWWWWWWWW#
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#.........P.........R..................#
#.........W.........W.........W........#
#..*......W..*......W..*......W..*.....#
#......q..W.........W.........W........#
#WWWW.WWWWWWWWW.WWWWWWWWW)WWWWWWWW)WWWW#
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#.........).........Q.........P........#
#.........W.........W.........W......X.#
#..*......W..*......W..*......W..*.....#
#.........W......[..W.........W........#
########################################
```

---

<a id="9"></a>

## 9. Engranaje

Cuatro colores, placas dobles, relojes, palancas y compuertas inversas. Es la más larga en número de pasos.

**Pista al entrar:** «Placas, relojes, palancas y compuertas al revés, todo junto.» · **diamantes:** 12 · **solución:** 30 movimientos · ritmos `timer=6` · letras propias `3=tplate:3 4=lever:4`

```
########################################
#.........W.........W.........W........#
#.......*.W.......*.W.E.....*.W.......*#
#...1.2.............Q.........R........#
#.........W.........W.........W........#
#..*......W..*......W..*......W..*.....#
#.........W.........W......s..W........#
#WWWWVWWWWWWWWWWWWWWWWWWWPWWWWWWWW.WWWW#
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#...................P.........R........#
#.........W.........W.........W........#
#..*......W..*......W..*......W..*.....#
#.........W......3..W......[..W......q.#
#WWWWWWWWWWWWWW.WWWWWWWWWVWWWWWWWWQWWWW#
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.4.....*#
#.........R.........P.........R........#
#.........W.........W.........W......X.#
#..*......W..*......W..*......W..*.....#
#......p..W.........W.........W......3.#
########################################
```

---

<a id="10"></a>

## 10. Gran final

Parten separados y usan todo: barreras, relojes, palancas y compuertas inversas. La solución más corta tiene 32 movimientos.

**Pista al entrar:** «Empiezan separados. Todo lo aprendido, y un solo camino.» · **diamantes:** 16 · **solución:** 32 movimientos · ritmos `timer=6` · letras propias `3=tplate:3 4=lever:4`

```
########################################
#.........W.........W.........W........#
#.......*.W.D.....*.W.......*.W.......*#
#.........V.........(.....2...W...1....#
#.........W.........W.........W........#
#..*......W..*......W..*......W..*.....#
#......q..W.........W......3..W........#
#WWWW(WWWWWWWWW.WWWWWWWWW)WWWWWWWWQWWWW#
#.........W.........W.........W........#
#.......*.W.......*.W.......*.W.......*#
#.........(.........V.........R........#
#.........W.........W.........W........#
#..*......W..*......W..*......W..*.....#
#......s..W......p..W.........W........#
#WWWWQWWWWWWWWW)WWWWWWWWW(WWWWWWWWSWWWW#
#.........W.........W.........W........#
#.4.....*.W.......*.W.......*.W.......*#
#.........Q.........(.........Q........#
#.........W.........W.........W......X.#
#..*......W..*......W..*......W..*.....#
#......p..W.........W.........W........#
########################################
```
