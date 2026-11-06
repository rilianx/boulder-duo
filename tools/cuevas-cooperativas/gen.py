# Co-op caves: rooms (3 rows x 4 columns) joined by doorways that are open, walls, gates (normal or inverted, of a
# group), or barriers (only J1 / only J2). Rooms hold plates (normal or with a clock) and levers. The puzzle is solved
# on that abstraction by breadth-first search over (both kids' room and plate, levers, clocks); a puzzle is kept only
# if both kids can get out, neither can alone, and it uses what the level is about. Then it is drawn as a 40 x 22 map.
import random, sys, json
from collections import deque
def geom(cols, rows):
    """Room spans filling the 38 x 20 inside of the map, and the doorways between neighbouring rooms."""
    def spans(n, total):
        w = (total - (n - 1)) // n; extra = total - (n - 1) - w * n; out = []; x = 1
        for k in range(n):
            ww = w + (1 if k < extra else 0); out.append((x, x + ww - 1)); x += ww + 1
        return out
    edges = []
    for r in range(rows):
        for c in range(cols):
            if c + 1 < cols: edges.append((r * cols + c, r * cols + c + 1))
            if r + 1 < rows: edges.append((r * cols + c, (r + 1) * cols + c))
    return spans(cols, 38), spans(rows, 20), edges
TIMER = 2   # moves a plate with a clock keeps its group on after it is left (the caves use timer=4 s)

def solve(P, kids=(0, 1)):
    """P: rooms (list of used rooms), edges {k: ('open'|'wall'|('gate',g,inv)|('bar',kid))}, plates [(room,g,timed)],
    levers [(room,g)], start (r1, r2), exit room. Returns the shortest list of actions, or None."""
    E, plates, levers = P['edges'], P['plates'], P['levers']; EDGES = geom(P['cols'], P['rows'])[2]
    ngroups = 1 + max([g for _, g, _ in plates] + [g for _, g in levers] + [t[1] for t in E.values() if t not in ('open', 'wall') and t[0] == 'gate'] + [0])
    adj = {}
    for k, (a, b) in enumerate(EDGES):
        if E.get(k, 'wall') != 'wall': adj.setdefault(a, []).append((b, k)); adj.setdefault(b, []).append((a, k))
    def on(state, g):
        kd, lev, tim = state
        if lev >> g & 1 or tim[g] > 0: return True
        return any(s is not None and s[1] is not None and plates[s[1]][1] == g for s in kd)
    def can(state, k, e, who):
        t = E[e]
        if t == 'open': return True
        if t[0] == 'bar': return t[1] == who
        if t[0] == 'gate': return on(state, t[1]) != t[2]
        return False
    # kid state: None = out (or not playing), (room, plate index or None)
    kd0 = tuple((P['start'][i], None) if i in kids else None for i in (0, 1))
    s0 = (kd0, 0, tuple([0] * ngroups))
    prev = {s0: None}; q = deque([s0])
    while q:
        s = q.popleft(); kd, lev, tim = s
        if all(x is None for x in kd):
            path = []
            while prev[s]: s, a = prev[s]; path.append(a)
            return path[::-1]
        for who in (0, 1):
            me = kd[who]
            if me is None: continue
            room, pl = me
            outs = []
            if pl is not None:   # step off the plate
                outs.append(((room, None), ('off', who, pl)))
            else:
                for j, (pr, g, timed) in enumerate(plates):
                    if pr == room and not any(x is not None and x[1] == j for x in kd): outs.append(((room, j), ('on', who, j)))
                for nb, e in adj.get(room, []): outs.append(((nb, None), ('go', who, nb, e)))
                for j, (lr, g) in enumerate(levers):
                    if lr == room: outs.append(('lever', ('lever', who, j)))
                if room == P['exit']: outs.append((None, ('exit', who)))
            for nk, act in outs:
                if act[0] == 'go' and not can(s, None, act[3], who): continue
                nl = lev
                ntim = [max(0, x - 1) for x in tim]
                if nk == 'lever': nl = lev ^ (1 << levers[act[2]][1]); nk = me
                if act[0] == 'off' and plates[pl][2]: ntim[plates[pl][1]] = TIMER
                nkd = list(kd); nkd[who] = nk; ns = (tuple(nkd), nl, tuple(ntim))
                if ns not in prev: prev[ns] = (s, act); q.append(ns)
    return None

def rand_puzzle(rng, spec):
    cols, rows = spec['cols'], spec['rows']; rooms = list(range(cols * rows)); EDGES = geom(cols, rows)[2]
    E = {}
    for k, (a, b) in enumerate(EDGES):
        x = rng.random()
        if x < spec.get('pwall', .3): E[k] = 'wall'
        elif x < spec.get('pwall', .3) + spec.get('popen', .1): E[k] = 'open'
        elif spec.get('bar') and x < .62: E[k] = ('bar', rng.randrange(2))
        else: E[k] = ('gate', rng.randrange(1, spec['groups'] + 1), bool(spec.get('inv')) and rng.random() < .35)
    plates, levers = [], []
    for g in range(1, spec['groups'] + 1):
        for _ in range(rng.randint(1, spec.get('pp', 1))):
            plates.append((rng.choice(rooms), g, bool(spec.get('timed')) and rng.random() < .4))
        if spec.get('lever') and rng.random() < .55: levers.append((rng.choice(rooms), g))
    # at most one plate and one lever per room (they must fit), a plate not where a lever is
    seen = set(); plates = [p for p in plates if not (p[0] in seen or seen.add(p[0]))]
    lseen = set(); levers = [l for l in levers if not (l[0] in lseen or lseen.add(l[0]))]
    start = (rng.choice(rooms), rng.choice(rooms)) if spec.get('apart') else (rooms[0], rooms[0])
    return dict(cols=cols, rows=rows, rooms=rooms, edges=E, plates=plates, levers=levers, start=start, exit=spec.get('exit', rooms[-1]))

def uses(P, path):
    u = set()
    for a in path:
        if a[0] == 'lever': u.add('lever')
        if a[0] == 'go':
            t = P['edges'][a[3]]
            if t != 'open' and t[0] == 'bar': u.add('bar')
            if t != 'open' and t[0] == 'gate': u.add('inv' if t[2] else 'gate')
        if a[0] == 'off' and P['plates'][a[2]][2]: u.add('timed')
    return u

def search(spec, seed, tries):
    rng = random.Random(seed); best = None
    for _ in range(tries):
        P = rand_puzzle(rng, spec)
        path = solve(P)
        if not path: continue
        if solve(P, (0,)) or solve(P, (1,)): continue          # one kid alone must not make it
        u = uses(P, path)
        if not spec['need'] <= u: continue
        moves = sum(1 for a in path if a[0] in ('go', 'lever', 'on'))
        if not spec['len'][0] <= moves <= spec['len'][1]: continue
        sc = moves + 3 * len(u) + rng.random()
        if not best or sc > best[0]: best = (sc, P, path)
    return best

def draw(P, path, name):
    """The puzzle as a 40 x 22 map, with its own letters (Legend) for groups past the default ones."""
    RX, RY, EDGES = geom(P['cols'], P['rows']); COLS = P['cols']
    g = [['#' if x in (0, 39) or y in (0, 21) else 'W' for x in range(40)] for y in range(22)]
    for r in P['rooms']:
        c, rr = r % COLS, r // COLS
        for y in range(RY[rr][0], RY[rr][1] + 1):
            for x in range(RX[c][0], RX[c][1] + 1): g[y][x] = '.'
    legend = {}; extra = iter('3456789!?&$@+0')
    def letter(kind, grp):
        default = {('plate', 1): 'p', ('plate', 2): 'q', ('plate', 3): 'r', ('plate', 4): 's', ('plate', 5): 't', ('plate', 6): 'u',
                   ('gate', 1): 'P', ('gate', 2): 'Q', ('gate', 3): 'R', ('gate', 4): 'S', ('gate', 5): 'T', ('gate', 6): 'U',
                   ('lever', 1): 'D', ('lever', 2): 'E', ('gatei', 1): 'N', ('gatei', 2): 'V', ('tplate', 1): '[', ('tplate', 2): ']'}
        if (kind, grp) in default: return default[(kind, grp)]
        key = f'{kind}:{grp}'
        if key not in legend: legend[key] = next(extra)
        return legend[key]
    for k, (a, b) in enumerate(EDGES):
        t = P['edges'].get(k)
        if t is None or t == 'wall': continue
        ca, ra = a % COLS, a // COLS
        if b == a + 1: x, y = RX[ca][1] + 1, (RY[ra][0] + RY[ra][1]) // 2
        else: x, y = (RX[ca][0] + RX[ca][1]) // 2, RY[ra][1] + 1
        g[y][x] = '.' if t == 'open' else ('(' if t[1] == 0 else ')') if t[0] == 'bar' else letter('gatei' if t[2] else 'gate', t[1])
    def spot(r, dx, dy):
        c, rr = r % COLS, r // COLS; return RX[c][0] + dx, RY[rr][0] + dy
    for r, grp, timed in P['plates']:
        x, y = spot(r, 6, 5); g[y][x] = letter('tplate' if timed else 'plate', grp)
    for r, grp in P['levers']:
        x, y = spot(r, 1, 1); g[y][x] = letter('lever', grp)
    used = set(); gems = 0
    for a in path:
        if a[0] == 'go': used.add(a[2])
    used |= set(P['start'])
    for r in P['rooms']:
        for dx, dy in ((7, 1), (2, 4)):
            x, y = spot(r, dx, dy)
            if g[y][x] == '.': g[y][x] = '*'; gems += r in used
    x, y = spot(P['start'][0], 3, 2); g[y][x] = '1'
    x, y = spot(P['start'][1], 5, 2); g[y][x] = '2'
    x, y = spot(P['exit'], 6, 3); g[y][x] = 'X'
    leg = ' '.join(f'{ch}={k}' for k, ch in legend.items())
    meta = dict(plates=[spot(r, 6, 5) for r, _, _ in P['plates']], levers=[spot(r, 1, 1) for r, _ in P['levers']],
                rooms=[((RX[r % COLS][0] + RX[r % COLS][1]) // 2, (RY[r // COLS][0] + RY[r // COLS][1]) // 2) for r in P['rooms']], exit=spot(P['exit'], 6, 3))
    return '\n'.join(''.join(r) for r in g), leg, max(2, gems * 2 // 3), meta

if __name__ == '__main__':
    print(solve(json.loads(sys.argv[1])) if len(sys.argv) > 1 else 'ok')
