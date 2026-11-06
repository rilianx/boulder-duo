import sys, json, time
from gen import *
SPECS = [
 ('Turnos', dict(cols=3, rows=1, groups=2, pp=2, pwall=.0, popen=.0, need={'gate'}, len=(4, 10))),
 ('Dos pisos', dict(cols=3, rows=2, groups=3, pwall=.3, popen=.1, need={'gate'}, len=(8, 14), apart=True)),
 ('La palanca', dict(cols=3, rows=2, groups=2, lever=True, pwall=.3, need={'gate','lever'}, len=(8, 16))),
 ('Esclusa', dict(cols=4, rows=2, groups=2, inv=True, pwall=.3, need={'gate','inv'}, len=(9, 18))),
 ('Con reloj', dict(cols=4, rows=2, groups=2, timed=True, pwall=.3, need={'timed'}, len=(9, 18))),
 ('Fuego y agua', dict(cols=4, rows=3, groups=3, bar=True, pwall=.25, need={'gate','bar'}, len=(10, 22), apart=True)),
 ('Relevo', dict(cols=4, rows=3, groups=3, lever=True, inv=True, pwall=.25, need={'gate','lever','inv'}, len=(12, 24))),
 ('Contrarreloj', dict(cols=4, rows=3, groups=3, timed=True, bar=True, pwall=.25, need={'timed','bar'}, len=(12, 26))),
 ('Engranaje', dict(cols=4, rows=3, groups=4, lever=True, inv=True, timed=True, pwall=.2, pp=2, need={'lever','inv','timed'}, len=(14, 30))),
 ('Gran final', dict(cols=4, rows=3, groups=4, lever=True, inv=True, timed=True, bar=True, pwall=.2, pp=2, need={'lever','inv','timed','bar'}, len=(16, 40), apart=True)),
]
k = int(sys.argv[1]); tries = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
name, spec = SPECS[k]
t0 = time.time(); best = None
for seed in range(1, 6):
    r = search(spec, seed * 1000 + k, tries)
    if r and (not best or r[0] > best[0]): best = r
if not best: print(k, name, 'NONE', round(time.time() - t0)); sys.exit()
sc, P, path = best
m, leg, need, meta = draw(P, path, name)
print(k, name, 'moves', sum(1 for a in path if a[0] in ('go','lever','on')), 'uses', sorted(uses(P, path)), round(time.time() - t0), 's')
print(m)
json.dump(dict(name=name, P=P, path=path, map=m, legend=leg, need=need, meta=meta), open(f'c{k}.json', 'w'))
