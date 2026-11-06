// Plays each co-op cave in the real game, following the solver's plan: every action becomes a walk (shortest way on the
// live grid, one cell per tick) by that kid while the other stands still. Reports whether both kids get out.
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs';
const D = process.argv[2], C = process.argv[3], which = (process.argv[4] || '0,1,2,3,4,5,6,7,8,9').split(',').map(Number);
const b = await chromium.launch(); const pg = await b.newPage(); const errs = []; pg.on('pageerror', e => errs.push(e.message));
await pg.goto('file://' + D + '/ed/dbg.html'); await pg.waitForTimeout(300);
const ev = c => pg.evaluate(c => __ev(c), c);
await ev(`window.RP = {
  free(p, i, goal){ const t = grid[i]; if (i === goal && (t === PLATE || t === TPLATE || t === EXIT)) return true; return t === E || t === DIRT || t === GEM || (KIDON[t] && kidOk(p, t) && t !== PLATE && t !== TPLATE); },
  path(p, goals){
    const s = p.y*W + p.x, prev = new Int32Array(W*H).fill(-2); prev[s] = -1; const q = [s];
    for (let h = 0; h < q.length; h++) { const i = q[h]; if (goals.has(i) && i !== s) { const out = []; let c = i; while (prev[c] !== -1) { out.push(c); c = prev[c]; } return out.reverse(); }
      for (let d = 0; d < 4; d++) { const j = i + OFF[d]; if (prev[j] === -2 && RP.free(p, j, goals.has(j) ? j : -1)) { prev[j] = i; q.push(j); } } }
    return null;
  },
  walk(p, goals, push){
    for (let n = 0; n < 400; n++) {
      if (goals.has(p.y*W + p.x)) return true;
      const pa = RP.path(p, goals); if (!pa) { tick(); continue; }
      const j = pa[0], i = p.y*W + p.x, d = OFF.indexOf(j - i);
      p.held = [d]; stepPlayer(p); p.held = []; tick();
      if (!p.alive) return p.exited;
    }
    return false;
  },
};
1`);
const res = [];
for (const k of which) {
  const c = JSON.parse(fs.readFileSync(`${C}/c${k}.json`, 'utf8'));
  const P = { Name: 'Cooperativa ' + (k + 1) + '. ' + c.name, Map: c.map, Legend: c.legend, DiamondsRequired: '0', CaveTime: '999', Params: 'timer=' + ({4: 5, 7: 6, 8: 6, 9: 6}[k] || 4) };
  const r = await ev(`(() => {
    const c = ${JSON.stringify(c)};
    CAVE_SETS.edit = { name: 'e', caves: [{ props: ${JSON.stringify(P)}, objects: [] }] }; caveSet = 'edit'; mode = 'coop'; solo = false;
    players = [newPlayer(0), newPlayer(1)]; initLevel(1); state = 'play'; players.forEach(p => p.immune = 0);
    const at = ([x, y]) => y * W + x, near = (cx, cy, r) => { const s = new Set(); for (let y = cy - r; y <= cy + r; y++) for (let x = cx - r; x <= cx + r; x++) s.add(y * W + x); return s; };
    let n = 0;
    for (const a of c.path) {
      const p = players[a[1]]; let ok = true;
      if (a[0] === 'go') { const [x, y] = c.meta.rooms[a[2]]; ok = RP.walk(p, near(x, y, 1)); }
      else if (a[0] === 'on') ok = RP.walk(p, new Set([at(c.meta.plates[a[2]])]));
      else if (a[0] === 'off') { const i = p.y * W + p.x, s = new Set(); for (const o of OFF) if (grid[i + o] === E || grid[i + o] === DIRT || grid[i + o] === GEM) s.add(i + o); ok = RP.walk(p, s); }
      else if (a[0] === 'lever') { const L = at(c.meta.levers[a[2]]), s = new Set(OFF.map(o => L + o)); ok = RP.walk(p, s); if (ok) { const before = leverOn[grp[L]]; for (let t = 0; t < 4; t++) tick(); p.held = [OFF.indexOf(L - (p.y * W + p.x))]; stepPlayer(p); p.held = []; tick(); ok = leverOn[grp[L]] !== before; } }
      else if (a[0] === 'exit') { ok = RP.walk(p, new Set([at(c.meta.exit)])) || p.exited; }
      if (!ok) return 'FAIL at action ' + n + ' ' + JSON.stringify(a);
      n++;
    }
    return players.every(p => p.exited) ? 'OK ' + n + ' actions, ' + ctick + ' ticks' : 'NOT OUT';
  })()`);
  res.push(k + ' ' + c.name + ': ' + r); console.log(res[res.length - 1]);
}
console.log('errs', errs); await b.close();
