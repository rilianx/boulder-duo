# Six caves to try the portals (40 x 22, steel border). Letters: 3 4 5 6 portal 1 with its mouth up, right, down,
# left; 7 8 9 0 portal 2; a cave can name more pairs in its Legend.
import json
W_, H_ = 40, 22
class M:
    def __init__(s, fill='.'):
        s.g = [['#' if x in (0, W_-1) or y in (0, H_-1) else fill for x in range(W_)] for y in range(H_)]
    def put(s, x, y, c):
        assert 0 < x < W_-1 and 0 < y < H_-1, (x, y, c); s.g[y][x] = c
    def pts(s, c, *xy):
        for x, y in xy: s.put(x, y, c)
    def h(s, y, x0, x1, c):
        for x in range(x0, x1+1): s.put(x, y, c)
    def v(s, x, y0, y1, c):
        for y in range(y0, y1+1): s.put(x, y, c)
    def rect(s, x0, y0, x1, y1, c):
        for y in range(y0, y1+1): s.h(y, x0, x1, c)
    def text(s): return '\n'.join(''.join(r) for r in s.g)
caves = []

# 1. Al otro lado: a steel wall down the middle; portal 1 takes you right, portal 2 brings you back. The gems are on
#    both sides and the exit on the left. A firefly on the right waits by portal 2: once the way out on the left is
#    dug, it can come through too.
m = M()
m.v(20, 1, 20, '#')
m.put(20, 15, '6'); m.put(20, 5, '4')          # walk right into (20,15) on the left, come out at (21,5) on the right
m.put(20, 10, '8'); m.put(20, 18, '0')         # walk left into (20,10) on the right, come out at (19,18) on the left
m.h(10, 21, 25, ' '); m.put(24, 10, 'F')
m.pts('1', (3, 17)); m.pts('2', (4, 17)); m.put(2, 2, 'X')
m.pts('*', (5, 4), (12, 3), (8, 9), (15, 12), (6, 13), (11, 19),  (25, 3), (33, 4), (30, 8), (36, 12), (28, 15), (34, 18), (24, 19), (31, 2))
m.pts('o', (9, 6), (14, 15), (27, 6), (35, 15))
caves.append(dict(Name='Al otro lado', Hint='Entra por la boca de un portal y sales por el otro. El portal azul va; el naranja vuelve.',
                  map=m, need=12, time=150, colors='Cyan Gray1 White'))

# 2. Lluvia: two sealed vaults full of gems (and a rock on top) stand on portals; their partners hang from the ceiling of
#    the kids' cave, mouths down, choked with earth. Dig the earth under one and it rains.
m = M()
for x0, top in ((10, '3'), (30, '7')):
    m.v(x0 - 1, 1, 7, '#'); m.v(x0 + 1, 1, 7, '#'); m.put(x0, 1, 'o'); m.v(x0, 2, 6, '*'); m.put(x0, 7, top)
m.h(8, 1, 38, '#')
m.put(16, 12, '5'); m.put(24, 12, '9')         # the vaults come out here, onto the earth just under them
m.pts('1', (3, 18)); m.pts('2', (4, 18)); m.put(37, 20, 'X')
m.pts('*', (6, 15), (33, 16), (20, 19), (12, 10))
m.pts('o', (8, 14), (28, 11), (19, 15))
caves.append(dict(Name='Lluvia', Hint='Los cofres de arriba caen por los portales. Cava la tierra bajo el portal del techo... y apártate.',
                  map=m, need=12, time=150, colors='Blue Cyan White'))

# 3. Parábola: rocks pushed onto the portals in the floor fly out of portals high on towers, two cells through the air,
#    and drop in an arc down a shaft where a butterfly is shut in.
m = M()
m.h(12, 1, 16, 'W'); m.put(8, 12, '3'); m.put(12, 12, '7')
m.rect(17, 1, 38, 20, ' ')
m.v(20, 6, 20, '#'); m.put(20, 6, '4')         # out at (21,6): 22, 23, then down column 24
m.v(23, 8, 16, '#'); m.v(25, 8, 16, '#'); m.put(24, 8, 'p')    # the shaft, with a grate on top (a plate: rocks go through, enemies do not)
m.v(21, 17, 20, '#'); m.v(27, 17, 20, '#'); m.h(17, 21, 23, '#'); m.h(17, 25, 27, '#'); m.put(24, 19, 'B'); m.put(27, 20, '.')
m.v(28, 10, 16, '#'); m.put(28, 10, '8')       # out at (29,10): 30, 31, then down column 32
m.v(31, 12, 16, '#'); m.v(33, 12, 16, '#'); m.put(32, 12, 'q')
m.v(29, 17, 20, '#'); m.v(35, 17, 20, '#'); m.h(17, 29, 31, '#'); m.h(17, 33, 35, '#'); m.put(32, 19, 'B'); m.put(35, 20, '.')
m.rect(36, 13, 38, 20, '.')
m.pts('o', (3, 11), (5, 11), (14, 11), (15, 11))
m.pts('1', (2, 2)); m.pts('2', (3, 2)); m.put(37, 19, 'X')
m.pts('*', (6, 5), (12, 8), (4, 15), (10, 18))
caves.append(dict(Name='Parábola', Hint='Empuja rocas sobre los portales del suelo: salen volando de las torres y caen en curva.',
                  map=m, need=18, time=180, colors='Orange Gray1 White'))

# 4. Viajeros: two corridors joined by portals into a loop: what runs to the end of one comes out at the start of the
#    other. Two butterflies and a firefly go round and round; rocks over the corridors, a cell of earth under each.
m = M()
m.v(16, 11, 13, '#'); m.v(23, 14, 16, '#'); m.v(37, 14, 16, '#'); m.v(2, 11, 13, '#')
m.h(12, 3, 15, ' '); m.put(16, 12, '6'); m.put(23, 15, '4')     # corridor A to the right, into portal 1, out in corridor B
m.h(15, 24, 36, ' '); m.put(37, 15, '0'); m.put(2, 12, '8')     # corridor B to the right, into portal 2, out at the start of A
m.pts('B', (5, 12), (30, 15)); m.pts('F', (11, 12))
m.pts('o', (5, 10), (9, 10), (13, 10), (27, 13), (31, 13), (35, 13))
m.pts('1', (19, 3)); m.pts('2', (20, 3)); m.put(20, 20, 'X')
m.pts('*', (4, 4), (10, 6), (30, 5), (36, 3), (19, 14), (20, 17), (8, 18), (32, 19))
caves.append(dict(Name='Viajeros', Hint='Mariposas y luciérnagas dan la vuelta por los portales. Suelta las rocas cuando pase una mariposa.',
                  map=m, need=18, time=180, colors='Purple Gray1 White'))

# 5. Rebote: gems and a rock bounce for ever between portals in the floor. To stop one, stand on the mouth it would
#    come out of; then pick it up from the side.
m = M()
m.h(16, 1, 38, 'W')
m.put(8, 16, '3'); m.put(16, 16, '3')          # pair 1: a gem
m.put(23, 16, '7'); m.put(31, 16, '7')         # pair 2: a gem and, later, a rock
m.put(35, 16, '!'); m.put(37, 16, '!')         # pair 3 (own letters): a gem
m.rect(1, 10, 38, 15, ' ')
m.pts('*', (8, 12), (23, 11), (35, 12)); m.put(31, 10, 'o')
m.pts('1', (2, 3)); m.pts('2', (3, 3)); m.put(37, 19, 'X'); m.h(16, 2, 3, '.')
m.pts('*', (10, 4), (20, 6), (30, 3), (6, 18), (18, 19), (28, 18))
caves.append(dict(Name='Rebote', Hint='Lo que cae en un portal del suelo sale disparado del otro. Párate sobre una boca para frenarlo.',
                  map=m, need=7, time=180, colors='Green Brown White', Legend='!=portal:3:u'))

# 6. Lanzamiento: push rocks into the portals of the wall: they fly out of the towers and must land on the three
#    plates. Four rocks for three plates.
m = M()
m.v(10, 1, 15, '#'); m.h(16, 1, 38, 'W'); m.put(1, 16, '.')
for y in (6, 10, 14): m.h(y + 1, 2, 9, 'W')
m.put(10, 6, '6'); m.put(10, 10, '0'); m.put(10, 14, '?')
m.pts('o', (9, 6), (9, 10), (9, 14), (4, 10))
m.rect(11, 1, 38, 15, ' ')
m.v(20, 4, 15, '#'); m.put(20, 4, '4')          # out at (21,4): lands in column 24
m.v(26, 6, 15, '#'); m.put(26, 6, '8')          # out at (27,6): column 30
m.v(31, 8, 15, '#'); m.put(31, 8, '@')          # out at (32,8): column 35
m.pts('_', (24, 16), (30, 16), (35, 16))
m.pts('1', (2, 3)); m.pts('2', (3, 3)); m.put(37, 19, 'X')
caves.append(dict(Name='Lanzamiento', Hint='Empuja las rocas a los portales de la pared: deben caer sobre las tres placas para abrir la salida.',
                  map=m, need=0, time=200, colors='Gray1 Red White', Legend='?=portal:3:l @=portal:3:r'))

out = []
for k, c in enumerate(caves, 1):
    t = c['map'].text(); rows = t.split('\n'); assert len(rows) == 22 and all(len(r) == 40 for r in rows)
    P = {'Name': f"Portal {k}. {c['Name']}", 'Hint': c['Hint'], 'Map': t, 'DiamondsRequired': str(c['need']),
         'CaveTime': ' '.join(str(max(60, c['time'] - 15 * i)) for i in range(5)), 'Colors': c['colors'], 'DiamondValue': '10 20'}
    if c.get('Legend'): P['Legend'] = c['Legend']
    out.append(P); print(P['Name'], 'gems', t.count('*'), 'need', c['need']); print(t)
json.dump(out, open('portal_set.json', 'w'), ensure_ascii=False)
