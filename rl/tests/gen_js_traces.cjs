// Genera trazas de referencia desde la simulación JS real (index.html en Chromium headless).
// Uso: node rl/tests/gen_js_traces.cjs   (requiere el paquete "playwright")
// Salida: rl/tests/fixtures/js_traces.json con, por traza, nivel, acciones y hash por tick.
const { chromium } = require('playwright');
const { writeFileSync } = require('node:fs');
const { pathToFileURL } = require('node:url');
const path = require('node:path');

const here = __dirname;
const page_url = pathToFileURL(path.resolve(here, '../../index.html')).href;
const LEVELS = [1, 2, 3, 5, 8, 12];
const STEPS = 500;

function lcg(seed) { let s = seed >>> 0; return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s; }; }

(async () => {
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(page_url);
const traces = [];
for (const lvl of LEVELS) {
  const R = lcg(lvl * 101 + 7);
  // acciones "pegajosas": repite una dirección unos ticks, como juega una persona o el agente
  const actions = []; let cur = 4;
  for (let k = 0; k < STEPS; k++) { if (R() % 4 === 0) cur = R() % 5; actions.push(cur); }
  const res = await page.evaluate(({ lvl, actions }) => {
    const hashes = [window.__sim.start(lvl)];
    let stopped = null;
    for (let k = 0; k < actions.length; k++) {
      const st = window.__sim.state();
      if (st.agent.exited || st.timeLeft <= 0) { stopped = k; break; }   // el juego cambiaría de nivel
      hashes.push(window.__sim.step(actions[k]));
    }
    const st = window.__sim.state();
    return { hashes, stopped, final: { agent: st.agent, timeLeft: st.timeLeft, grid: st.grid.join(',') } };
  }, { lvl, actions });
  traces.push({ level: lvl, actions: actions.slice(0, res.hashes.length - 1), hashes: res.hashes, final: res.final });
  console.log(`nivel ${lvl}: ${res.hashes.length - 1} ticks, gemas ${res.final.agent.gems}, vivo ${res.final.agent.alive}`);
}
await browser.close();
writeFileSync(path.resolve(here, 'fixtures/js_traces.json'), JSON.stringify(traces));
})();
