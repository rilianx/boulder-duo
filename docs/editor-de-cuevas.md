# Editor de cuevas

Con el **editor de cuevas** se hacen cuevas nuevas sin tocar el código. Una cueva es un mapa de 40 × 22 letras, y cada letra es una pieza. Lo que hace cada pieza está escrito una sola vez en el juego y es igual en cualquier mapa. Por eso las 10 [cuevas nuevas](cuevas-propuestas.md), las 9 [cuevas clásicas](cuevas-clasicos.md) y las que hagas tú son todas mapas del mismo tipo, y se pueden abrir y cambiar en el editor.

## Cómo se usa

1. En el menú, toca **EDITOR DE CUEVAS**.
2. **Elige una pieza** en la paleta de la izquierda. Al pasar el puntero se ve su nombre.
3. **Pinta** en el mapa con una herramienta:
   - **Lápiz:** un cuadro a la vez, o arrastrando.
   - **Rectángulo:** arrastra para llenar un rectángulo.
   - **Balde:** llena toda la zona del mismo tipo.
   - **Gotero:** toma la pieza de un cuadro. El clic derecho también lo hace.
   - **Deshacer:** o Ctrl+Z.

   El borde siempre es de acero. Hay un solo inicio de J1 y uno de J2. El gorila ocupa 2 × 2.
4. A la derecha se eligen:
   - el **nombre** y la **pista** que aparece al entrar;
   - los **diamantes necesarios** y el **tiempo** (uno por nivel de dificultad, separados por espacios);
   - el **valor de cada diamante** y los **colores**;
   - si **el agua sube**, y cada cuánto;
   - si la cueva es **oscura**;
   - los **ritmos** y las **letras propias** (ver más abajo).
5. **PROBAR SOLO** o **PROBAR DE A DOS** juega la cueva al tiro. Al volver al menú (pausa → menú) se vuelve al editor.
6. **GUARDAR EN MIS CUEVAS** la guarda en este navegador. Aparece en el menú como **MIS CUEVAS** y se juega como cualquier otra, también con dos celulares: el anfitrión le pasa sus cuevas al otro al empezar.
7. **ABRIR** carga una de tus cuevas, o una de las nuevas o clásicas para cambiarla. Una cueva del juego abierta así se guarda como una cueva tuya, y la original no cambia.
8. **EXPORTAR** muestra la cueva como texto, para copiarla o descargarla. **IMPORTAR** lee un texto así, o un mapa solo.

Abajo del mapa, el editor avisa lo que falta para poder jugar (el inicio de J1 o la salida) y lo que conviene revisar:
- si pide más diamantes de los que hay;
- si hay puertas sin llaves;
- si hay compuertas sin placas.

## El texto de una cueva

```
Name: Mi cueva
Hint: Cuidado con los toneles.
DiamondsRequired: 12
CaveTime: 150 135 120 105 90
Colors: Orange Gray1 White
DiamondValue: 10 20
WaterRise: 7.5
Dark: true
Params: laser=1.5,1.5 ape=2
Legend: Q=gate:7
Map:
########################################
#12....................................#
… (22 filas de 40 letras)
```

Todas las líneas antes de `Map:` son opcionales:
- `DiamondsRequired`, `CaveTime` y `WaterRise` pueden llevar un valor por nivel de dificultad.
- `Colors` usa los nombres de colores del Commodore 64 que ofrece el editor: tierra, ladrillo y brillo.
- `DiamondValue` son los puntos de cada diamante, y de los que se juntan después de abrir la salida.

### Ritmos (`Params`)

Cambian lo que tardan las piezas con reloj. Los valores van en segundos, salvo en `log` y `tonel`. Lo que no se escribe queda con su valor normal.

| Nombre | Normal | Qué es |
|---|---|---|
| `laser=a,b` | 1,5 y 1,5 | segundos encendido y apagado |
| `croc=a,b` | 2 y 2 | segundos con la boca abierta y cerrada |
| `tar=a,b` | 2 y 2 | segundos abierta y cerrada |
| `belt=s` | 6 | cada cuánto se dan vuelta las cintas |
| `ape=s` | 3 | cada cuánto tira un tonel el gorila (0: nunca) |
| `log=n` | 2 | turnos por cuadro del tronco |
| `tonel=n` | 2 | turnos por cuadro del tonel |
| `hammer=s` | 8 | cuánto dura el martillo |
| `amulet=s` | 10 | cuánto dura el amuleto |
| `regrow=s` | 6 | cuánto tarda en crecer la tierra viva |

Pisar una pieza con ritmo mientras es peligrosa mata, igual que estar en ella cuando cambia. Las piezas con ritmo vienen en dos **turnos**, `a` y `b`. Si los dos tiempos son iguales, mientras las `a` son peligrosas las `b` son seguras. Así se arman cruces en dos tiempos, como en las cuevas «Rayos» y «Cocodrilos».

### Letras propias (`Legend`)

Una cueva puede agregar letras o cambiar las de siempre, con `letra=pieza:dato`. El dato puede ser:
- una dirección (`u` `r` `d` `l`);
- un turno (`a` `b`);
- un color de llave o puerta: 0 dorada, 1 roja, 2 azul, 3 verde, 4 morada, 5 naranja, 6 blanca;
- el número de grupo de una placa o compuerta.

Por ejemplo, `7=plate:7 8=gate:7` agrega un séptimo par de placa y compuerta, y `O=key:4 0=door:4` una llave y una puerta moradas. Las letras propias aparecen en la paleta del editor.

## Las letras

**Básico**

| Letra | Pieza | Qué hace | En «Letras propias» |
|---|---|---|---|
| (espacio) | vacío | Espacio libre: aquí caen las cosas y andan los enemigos. | `_sp_=empty` |
| `.` | tierra | Se cava al pasar. | `.=dirt` |
| `W` | ladrillo | Pared que una explosión rompe. Lo que cae sobre ella rueda. | `W=wall` |
| `#` | acero | Pared indestructible. El borde del mapa siempre es de acero. | `#=steel` |
| `o` | roca | Cae, rueda y se empuja de lado. Al caer aplasta. | `o=rock` |
| `*` | diamante | Cae y rueda como la roca. Se recoge. | `*=gem` |
| `X` | salida | Se abre al juntar los diamantes pedidos (y con todas las placas de roca tapadas y todos los remaches fuera, si los hay). | `X=exit` |
| `1` | inicio J1 | Donde parte J1 (obligatorio, uno solo). | `1=start1` |
| `2` | inicio J2 | Donde parte J2 (si falta, parte junto a J1). | `2=start2` |
| `F` | luciérnaga ← | Sigue las paredes por la izquierda. Explota al tocar a un niño o al caerle algo encima. | `F=firefly:l` |
| `B` | mariposa → | Sigue las paredes por la derecha. Aplastada, deja 9 diamantes. | `B=butterfly:r` |

**Cuevas nuevas**

| Letra | Pieza | Qué hace | En «Letras propias» |
|---|---|---|---|
| `n` | nuez | Como una roca, pero si le cae una roca encima se vuelve diamante. | `n=nut` |
| `a` | llave dorada | Se recoge. Cada una abre una sola puerta de su color. | `a=key:0` |
| `A` | puerta dorada | Se abre con una llave de su color, que se gasta. | `A=door:0` |
| `^` | paso ↑ | Se cruza solo en la dirección de la flecha, saltando al otro lado. | `^=port:u` |
| `>` | paso → | Se cruza solo en la dirección de la flecha, saltando al otro lado. | `>=port:r` |
| `v` | paso ↓ | Se cruza solo en la dirección de la flecha, saltando al otro lado. | `v=port:d` |
| `<` | paso ← | Se cruza solo en la dirección de la flecha, saltando al otro lado. | `<=port:l` |
| `%` | barril | Como una roca, pero explota si cae, si le cae algo encima o si lo alcanza una explosión. | `%=barrel` |
| `_` | placa de roca | Sólida. La salida no se abre hasta que todas tengan una roca encima. | `_=target` |
| `Y` | comelón → | Avanza recto, se come los diamantes y da la vuelta al chocar. Mata al tocar. Aplastado, devuelve lo que comió más uno. | `Y=eater:r` |
| `y` | comelón ← | Avanza recto, se come los diamantes y da la vuelta al chocar. Mata al tocar. Aplastado, devuelve lo que comió más uno. | `y=eater:l` |
| `:` | tierra viva | Se cava al pasar. | `:=ldirt` |
| `G` | interruptor de gravedad | Al empujarlo, todo pasa a caer hacia otro lado (un cuarto de vuelta). | `G=switch` |
| `~` | agua que sube (desde esta fila) | Desde esta fila hacia abajo hay agua, y sube según «El agua sube cada…». Bajo el agua el aire dura 4 segundos. | `~=water` |

**Placas y compuertas**

| Letra | Pieza | Qué hace | En «Letras propias» |
|---|---|---|---|
| `p` | placa 1 | Mientras algo (un niño, una roca, un diamante) está sobre ella, abre las compuertas de su número. | `p=plate:1` |
| `q` | placa 2 | Mientras algo (un niño, una roca, un diamante) está sobre ella, abre las compuertas de su número. | `q=plate:2` |
| `r` | placa 3 | Mientras algo (un niño, una roca, un diamante) está sobre ella, abre las compuertas de su número. | `r=plate:3` |
| `s` | placa 4 | Mientras algo (un niño, una roca, un diamante) está sobre ella, abre las compuertas de su número. | `s=plate:4` |
| `t` | placa 5 | Mientras algo (un niño, una roca, un diamante) está sobre ella, abre las compuertas de su número. | `t=plate:5` |
| `u` | placa 6 | Mientras algo (un niño, una roca, un diamante) está sobre ella, abre las compuertas de su número. | `u=plate:6` |
| `P` | compuerta 1 | Abierta mientras hay algo sobre una placa de su número. Nunca se cierra encima de algo. | `P=gate:1` |
| `Q` | compuerta 2 | Abierta mientras hay algo sobre una placa de su número. Nunca se cierra encima de algo. | `Q=gate:2` |
| `R` | compuerta 3 | Abierta mientras hay algo sobre una placa de su número. Nunca se cierra encima de algo. | `R=gate:3` |
| `S` | compuerta 4 | Abierta mientras hay algo sobre una placa de su número. Nunca se cierra encima de algo. | `S=gate:4` |
| `T` | compuerta 5 | Abierta mientras hay algo sobre una placa de su número. Nunca se cierra encima de algo. | `T=gate:5` |
| `U` | compuerta 6 | Abierta mientras hay algo sobre una placa de su número. Nunca se cierra encima de algo. | `U=gate:6` |

**Montezuma**

| Letra | Pieza | Qué hace | En «Letras propias» |
|---|---|---|---|
| `k` | llave roja | Se recoge. Cada una abre una sola puerta de su color. | `k=key:1` |
| `K` | puerta roja | Se abre con una llave de su color, que se gasta. | `K=door:1` |
| `m` | llave azul | Se recoge. Cada una abre una sola puerta de su color. | `m=key:2` |
| `M` | puerta azul | Se abre con una llave de su color, que se gasta. | `M=door:2` |
| `j` | llave verde | Se recoge. Cada una abre una sola puerta de su color. | `j=key:3` |
| `J` | puerta verde | Se abre con una llave de su color, que se gasta. | `J=door:3` |
| `=` | rayo (turno a) | Se enciende y se apaga. Mata a quien lo pisa encendido o está en él cuando se enciende. Para las cosas y los enemigos es pared. | `==laser:a` |
| `-` | rayo (turno b) | Se enciende y se apaga. Mata a quien lo pisa encendido o está en él cuando se enciende. Para las cosas y los enemigos es pared. | `-=laser:b` |
| `i` | antorcha | Quien la toma ve lejos en una cueva oscura. | `i=torch` |
| `e` | amuleto | Al tomarlo, los enemigos, los troncos, los toneles y el gorila se quedan quietos 10 segundos. | `e=amulet` |
| `h` | espada | El próximo enemigo que toque a su dueño muere en vez del niño. | `h=sword` |

**Pitfall**

| Letra | Pieza | Qué hace | En «Letras propias» |
|---|---|---|---|
| `w` | agua | No se puede entrar. Lo que cae en ella se hunde. | `w=pond` |
| `c` | cocodrilo (turno a) | Abre y cierra la boca. Cerrada se pisa; abierta muerde a quien la pisa o está encima. | `c=croc:a` |
| `C` | cocodrilo (turno b) | Abre y cierra la boca. Cerrada se pisa; abierta muerde a quien la pisa o está encima. | `C=croc:b` |
| `z` | brea (turno a) | Se abre y se cierra. Cerrada aguanta niños y cosas; abierta mata al niño que la pisa, y al abrirse se traga lo que tiene (una roca la tapa para siempre). | `z=tar:a` |
| `Z` | brea (turno b) | Se abre y se cierra. Cerrada aguanta niños y cosas; abierta mata al niño que la pisa, y al abrirse se traga lo que tiene (una roca la tapa para siempre). | `Z=tar:b` |
| `l` | tronco ← | Rueda por su carril. Pasa por encima de diamantes y objetos, y al alcanzar a un niño le hace saltar un diamante. Lo detienen las rocas; en la pared vuelve a salir por la otra punta. | `l=log:l` |
| `L` | tronco → | Rueda por su carril. Pasa por encima de diamantes y objetos, y al alcanzar a un niño le hace saltar un diamante. Lo detienen las rocas; en la pared vuelve a salir por la otra punta. | `L=log:r` |

**Donkey Kong**

| Letra | Pieza | Qué hace | En «Letras propias» |
|---|---|---|---|
| `d` | gorila | Ocupa 2 × 2. Tira un tonel hacia el lado libre cada 3 segundos. Si el mapa tiene remaches, al sacarlos todos se deshace en diamantes. | `d=ape` |
| `b` | tonel → | Rueda y pasa por encima de diamantes y objetos; cae donde no hay suelo y, al caer, sigue hacia el otro lado. Mata al tocar. | `b=tonel:r` |
| `f` | bidón | Quema lo que cae en él y al niño que lo toca. Un tonel que llega a él suelta una luciérnaga. | `f=drum` |
| `H` | martillo | Durante 8 segundos, los toneles que tocan a su dueño se vuelven diamantes. | `H=hammer` |
| `x` | remache | Se saca pisándolo. Mientras quede alguno, la salida no se abre. | `x=rivet` |
| `{` | cinta ← | Lleva lo que tiene encima (a un niño, si está quieto). Todas se dan vuelta cada 6 segundos. | `{=belt:l` |
| `}` | cinta → | Lleva lo que tiene encima (a un niño, si está quieto). Todas se dan vuelta cada 6 segundos. | `}=belt:r` |

## Cómo está hecho

En el juego, cada pieza se describe con propiedades:
- si cae, si rueda lo que le cae encima y si se empuja;
- si aguanta las explosiones;
- si un niño puede pararse en ella, y si también una cosa;
- si tiene un ritmo, si se recoge, si se traga lo que cae y si es un enemigo.

Las reglas del juego miran esas propiedades y nunca preguntan en qué cueva están, y un mapa son solo letras que nombran piezas. Las piezas nuevas no cambian nada en las cuevas de Boulder Dash 1 y 2, que se comportan exactamente igual que antes. Tampoco cambian el entrenamiento del PC ni su copia en Python.
