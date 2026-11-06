// Tries what each portal cave is about, in the real game.
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
const D = process.argv[2];
const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1300, height: 760 } }); const errs = []; pg.on('pageerror', e => errs.push(e.message + (e.stack || '').split('\n')[1]));
await pg.goto('file://' + D + '/ed/dbg.html'); await pg.waitForTimeout(300);
const ev = c => pg.evaluate(c => __ev(c), c);
await ev(`window.K = {
  lv(n){ caveSet='ptl'; mode='coop'; solo=false; players=[newPlayer(0),newPlayer(1)]; initLevel(n); state='play'; players.forEach(p=>p.immune=0); },
  at(k, x, y){ const p=players[k]; vacate(p.y*W+p.x); p.x=x; p.y=y; standOn(y*W+x); grid[y*W+x]=p.cell; },
  go(k, d, n=1){ const p=players[k]; for (let t=0;t<n;t++){ p.held=[d]; stepPlayer(p); tick(); } p.held=[]; return [p.x,p.y]; },
  wait(n){ for (let t=0;t<n;t++) tick(); },
  count(t, x0=1, y0=1, x1=38, y1=20){ let n=0; for(let y=y0;y<=y1;y++) for(let x=x0;x<=x1;x++) if(grid[y*W+x]===t) n++; return n; },
  g(x,y){ return grid[y*W+x]; },
}; 1`);
const out = async (name, code) => { try { console.log(name, await ev(code)); } catch (e) { console.log(name, 'ERR', e.message.split('\n')[0]); } };
await out('1 al otro lado', `K.lv(1); K.at(0,18,15); const a=K.go(0,1,2); K.at(1,22,10); grid[10*W+21]=E; const b=K.go(1,3,2); const c=K.go(1,3,1); JSON.stringify({there:a, back:b, after:c})`);
await out('1 firefly comes through', `K.lv(1); K.at(0,18,18); K.at(1,2,2); grid[18*W+19]=E; grid[18*W+18]=E; K.at(0,17,18); let crossed=0; for(let t=0;t<400;t++){ tick(); if (K.count(FIRE,1,1,19,20)) { crossed=t; break; } } crossed`);
await out('2 lluvia', `K.lv(2); K.at(0,15,13); K.at(1,2,2); const s=K.count(GEM,1,9,38,20); K.go(0,1,1); K.go(0,3,1); K.go(0,3,1); const L=[]; for(let t=0;t<40;t++){ tick(); if(t%8==7) L.push(K.count(GEM,10,10,22,20)); } JSON.stringify({before:s, vaultLeft:K.count(GEM,10,1,10,6), there:L, kid:players[0].alive})`);
await out('3 parábola', `K.lv(3); K.at(0,2,2); K.at(1,3,2); const L=[]; for (const [x, c] of [[8,0],[12,0],[8,0],[12,0],[8,0],[12,0],[8,0],[12,0]]) { grid[11*W+x]=ROCK; fall[11*W+x]=0; aux[11*W+x]=0; K.wait(30); } JSON.stringify({butterflies:K.count(BUTT), gemsRight:K.count(GEM,21,17,35,20), rocksInChambers:K.count(ROCK,21,17,35,20)})`);
await out('4 viajeros', `K.lv(4); K.at(0,2,2); K.at(1,3,2); let moves=0, prev=K.count(BUTT,3,12,15,12)+K.count(FIRE,3,12,15,12); for(let t=0;t<600;t++){ tick(); const now=K.count(BUTT,3,12,15,12)+K.count(FIRE,3,12,15,12); if(now!==prev){ moves++; prev=now; } } const before=K.count(BUTT); for (const x of [5,9,13]) { grid[11*W+x]=E; } for(let t=0;t<600;t++) tick(); JSON.stringify({crossings:moves, butterflies:[before, K.count(BUTT)], gems:K.count(GEM)})`);
await out('4 timed drop', `K.lv(4); K.at(0,2,2); K.at(1,3,2); const R=[]; for (const [x, lead] of [[9,1],[9,2],[13,1],[13,2]]) { let ok=false; for(let t=0;t<800;t++){ tick(); if (grid[12*W+x-lead]===BUTT && dir[12*W+x-lead]===1) { grid[11*W+x]=E; ok=true; break; } } K.wait(10); R.push(ok+':'+K.count(BUTT)); if (K.count(ROCK,3,12,15,12)) { for (let i=12*W+3;i<=12*W+15;i++) if (grid[i]===ROCK) grid[i]=E; } grid[10*W+x]=ROCK; grid[11*W+x]=DIRT; } JSON.stringify(R)`);
await out('5 rebote', `K.lv(5); K.at(0,2,2); K.at(1,3,2); K.wait(20); const a=K.count(GEM,1,10,38,15); K.at(0,16,15); K.wait(40); const restA=K.g(8,15); JSON.stringify({bouncingGems:a, restingOnOther: restA===GEM, kidOK: players[0].alive})`);
await out('6 lanzamiento', `K.lv(6); const r=[]; for (const y of [6,10,14]) { K.at(0,8,y); K.go(0,1,3); K.wait(30); } JSON.stringify({onTargets: targets.map(i=>grid[i-W]===ROCK), exitOpen: exitOpenFor(players[0])})`);
await ev(`K.lv(3); caveShownAt=-9999; 1`); await pg.waitForTimeout(500); await pg.screenshot({ path: D + '/portal/p3.png' });
await ev(`K.lv(6); caveShownAt=-9999; 1`); await pg.waitForTimeout(500); await pg.screenshot({ path: D + '/portal/p6.png' });
console.log(errs); await b.close();
