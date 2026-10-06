/* Big random caves for two players (80 x 44, four times a normal cave), in the spirit of Boulder Dash 1's cave A.
   Not wired into the game yet: genBigCave(seed, opts) only builds the map, so it can be looked at first.

   - Fill: the cave A recipe (per cell a random byte: under 9 a diamond, under 50 a boulder, under 60 empty space,
     else dirt), on a dirt base inside a steel border.
   - Walls: a brick pattern drawn in each half from its outer edge, the right half the mirror of the left, so both
     players meet the same layout (see PATTERNS).
   - Pockets: little set pieces of different kinds (a rock chest, a hollow grotto, a heap of boulders, a vein of
     diamonds, a brick vault, a rock column), the same kinds in each half at random places.
   - Fair but not identical: the halves are filled apart, then the poorer one gets diamonds until both have the same.
   - J1 starts at the top left, J2 at the top right; the exit is at the bottom in the middle.
   - Every diamond can be reached: from a kid's start, walking through dirt and space (rocks and walls block, as if
     nothing moved). A diamond that cannot is moved to a reachable spot of its half, and the exit always can be. */
(function (root) {
  const W = 80, H = 44;
  const E = 0, DIRT = 1, WALL = 2, STEEL = 3, ROCK = 4, GEM = 5, EXIT = 6;   // the game's own tile codes

  function rng(seed) {
    let s = seed | 0;
    return () => { s = s + 0x6D2B79F5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  }

  // brick patterns, drawn in "half" coordinates: u = cells from the outer edge (1..39), y = row (1..42)
  const PATTERNS = {
    // cave A's own: long walls that leave the way open alternately by the middle and by the edge, so the way down
    // snakes from side to side (here two bands of it, one above the other)
    zigzag(put) {
      for (const y of [8, 15, 29, 36]) {
        const middleGap = y === 8 || y === 29;
        for (let u = 1; u <= 39; u++) if (middleGap ? u <= 30 : u >= 9) put(u, y, WALL);
      }
    },
    // stairs: short ledges going down and in, towards the exit in the middle
    escalones(put) {
      for (let k = 0; k < 8; k++) {
        const y = 5 + k * 5, u0 = 2 + (k % 2 ? 14 : 4) + k * 2;
        for (let u = u0; u < Math.min(39, u0 + 9); u++) put(u, y, WALL);
      }
    },
    // rooms: a grid of brick walls with doorways
    camaras(put) {
      for (const y of [11, 22, 33]) for (let u = 1; u <= 39; u++) if ((u + y) % 13 > 2) put(u, y, WALL);
      for (const u of [13, 26]) for (let y = 1; y <= 42; y++) if ((y + u) % 11 > 2 && y % 11) put(u, y, WALL);
    },
    // funnel: slanted walls closing in towards the bottom middle, with gaps here and there
    embudo(put) {
      for (let k = 0; k < 3; k++) for (let s = 0; s < 26; s++) {
        const u = 2 + s + k * 4, y = 6 + k * 11 + Math.floor(s / 2);
        if (u <= 37 && y <= 41 && s % 9 !== 4) put(u, y, WALL);
      }
    },
  };

  // pockets: little set pieces, placed at (x, y) = top left; each says how much room it needs
  const POCKETS = {
    // a chest of diamonds walled in by boulders, with one way in through dirt
    cofre: { w: 5, h: 5, make(set, R) {
      for (let y = 0; y < 5; y++) for (let x = 0; x < 5; x++) set(x, y, x === 0 || y === 0 || x === 4 || y === 4 ? ROCK : GEM);
      const side = Math.floor(R() * 3);   // a door left, right or below (never above: the lid stays on)
      if (side === 0) set(0, 2, DIRT); else if (side === 1) set(4, 2, DIRT); else set(2, 4, DIRT);
    } },
    // a hollow grotto: empty inside, diamonds on its floor and boulders hanging from its roof
    gruta: { w: 7, h: 4, make(set, R) {
      for (let y = 1; y < 3; y++) for (let x = 1; x < 6; x++) set(x, y, E);
      for (let x = 1; x < 6; x++) if (R() < .5) set(x, 2, GEM);
      for (let x = 1; x < 6; x++) if (R() < .45) set(x, 0, ROCK);
    } },
    // a heap of boulders with diamonds underneath: dig them out and the heap comes down
    monton: { w: 7, h: 5, make(set) {
      [[3], [2, 3, 4], [1, 2, 3, 4, 5]].forEach((xs, y) => xs.forEach(x => set(x, y + 1, ROCK)));
      for (const x of [1, 3, 5]) set(x, 4, GEM);
    } },
    // a vein of diamonds running slantwise through the dirt
    veta: { w: 7, h: 7, make(set, R) {
      const dir = R() < .5 ? 1 : -1;
      for (let k = 0; k < 6; k++) set(dir > 0 ? k : 6 - k, k, GEM);
    } },
    // a little brick vault with a doorway
    boveda: { w: 6, h: 5, make(set, R) {
      for (let y = 0; y < 5; y++) for (let x = 0; x < 6; x++) set(x, y, x === 0 || y === 0 || x === 5 || y === 4 ? WALL : E);
      for (let x = 1; x < 5; x++) set(x, 3, GEM);
      set(R() < .5 ? 0 : 5, 2, DIRT);
    } },
    // a column of boulders standing on a diamond
    columna: { w: 1, h: 5, make(set) { for (let y = 0; y < 4; y++) set(0, y, ROCK); set(0, 4, GEM); } },
  };
  const KINDS = ['cofre', 'gruta', 'monton', 'veta', 'boveda', 'columna', 'gruta', 'veta'];

  function genBigCave(seed, opts = {}) {
    const R = rng(seed * 7919 + 13), pattern = opts.pattern || ['zigzag', 'escalones', 'camaras', 'embudo'][seed % 4];
    const g = new Uint8Array(W * H).fill(DIRT);
    const at = (x, y) => y * W + x, inside = (x, y) => x > 0 && y > 0 && x < W - 1 && y < H - 1;
    // each half filled apart with cave A's recipe
    for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
      const r = R() * 256;
      g[at(x, y)] = r < 9 ? GEM : r < 50 ? ROCK : r < 60 ? E : DIRT;
    }
    // the bricks, the same pattern from both outer edges
    const both = (u, y, t) => { for (const x of [u, W - 1 - u]) if (inside(x, y)) g[at(x, y)] = t; };
    PATTERNS[pattern](both);
    // the starts and the exit, with room around
    const starts = [[3, 2], [W - 4, 2]], exit = [R() < .5 ? 39 : 40, H - 2];
    const keepClear = [];
    starts.forEach(([x, y]) => { for (let dy = -1; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) if (inside(x + dx, y + dy)) { g[at(x + dx, y + dy)] = DIRT; keepClear.push([x + dx, y + dy]); } g[at(x, y)] = E; });
    // pockets: the same kinds in each half, each at its own random place, clear of the walls, the starts and each other
    const taken = new Uint8Array(W * H);
    const free = (x0, y0, w, h) => {
      for (let y = y0 - 1; y <= y0 + h; y++) for (let x = x0 - 1; x <= x0 + w; x++) {
        if (!inside(x, y) || taken[at(x, y)] || g[at(x, y)] === WALL) return false;
        if (starts.some(([sx, sy]) => Math.abs(sx - x) < 5 && Math.abs(sy - y) < 5)) return false;
        if (Math.abs(exit[0] - x) < 4 && Math.abs(exit[1] - y) < 4) return false;
      }
      return true;
    };
    const kinds = KINDS.slice().sort(() => R() - .5).slice(0, opts.pockets || 7), placed = [];
    for (const side of [0, 1]) for (const k of kinds) {
      const P = POCKETS[k];
      for (let tries = 0; tries < 200; tries++) {
        const x0 = side ? 41 + Math.floor(R() * (38 - P.w)) : 1 + Math.floor(R() * (38 - P.w)), y0 = 1 + Math.floor(R() * (H - 2 - P.h));
        if (!free(x0, y0, P.w, P.h)) continue;
        for (let y = y0 - 1; y <= y0 + P.h; y++) for (let x = x0 - 1; x <= x0 + P.w; x++) taken[at(x, y)] = 1;
        for (let y = y0; y < y0 + P.h; y++) for (let x = x0; x < x0 + P.w; x++) g[at(x, y)] = DIRT;
        P.make((x, y, t) => { g[at(x0 + x, y0 + y)] = t; }, R);
        placed.push({ kind: k, side, x: x0, y: y0 });
        break;
      }
    }
    g[at(exit[0], exit[1])] = EXIT; g[at(exit[0], exit[1] - 1)] = DIRT;
    // steel all round
    for (let x = 0; x < W; x++) { g[at(x, 0)] = STEEL; g[at(x, H - 1)] = STEEL; }
    for (let y = 0; y < H; y++) { g[at(0, y)] = STEEL; g[at(W - 1, y)] = STEEL; }
    // where each kid can walk to (dirt, space and diamonds; nothing moves)
    const reach = (sx, sy) => {
      const seen = new Uint8Array(W * H), q = [at(sx, sy)]; seen[q[0]] = 1;
      for (let h = 0; h < q.length; h++) for (const d of [1, -1, W, -W]) {
        const j = q[h] + d, t = g[j];
        if (!seen[j] && (t === E || t === DIRT || t === GEM || t === EXIT)) { seen[j] = 1; q.push(j); }
      }
      return seen;
    };
    const half = i => (i % W) < 40 ? 0 : 1;
    let moved = 0;
    for (let round = 0; round < 3; round++) {
      const rs = starts.map(([x, y]) => reach(x, y));
      const ok = i => rs[0][i] || rs[1][i];
      // the exit must be reachable by both: open a way up from it if not
      if (!rs[0][at(exit[0], exit[1])] || !rs[1][at(exit[0], exit[1])]) {
        for (let y = exit[1] - 1; y > 0; y--) { const i = at(exit[0], y); if (g[i] === WALL || g[i] === ROCK) g[i] = DIRT; }
        continue;
      }
      // a diamond nobody can walk to goes to a reachable dirt spot of its half
      const lost = []; for (let i = 0; i < W * H; i++) if (g[i] === GEM && !ok(i)) lost.push(i);
      if (!lost.length) break;
      for (const i of lost) {
        g[i] = DIRT;
        for (let tries = 0; tries < 400; tries++) {
          const j = at(1 + Math.floor(R() * 38) + (half(i) ? 40 : 0), 1 + Math.floor(R() * (H - 2)));
          if (g[j] === DIRT && ok(j) && !keepClear.some(([x, y]) => at(x, y) === j)) { g[j] = GEM; moved++; break; }
        }
      }
    }
    // fair: the poorer half gets diamonds until both have as many
    const count = s => { let n = 0; for (let i = 0; i < W * H; i++) if (g[i] === GEM && half(i) === s) n++; return n; };
    const rs = starts.map(([x, y]) => reach(x, y));
    let added = 0;
    for (let guard = 0; guard < 400 && count(0) !== count(1); guard++) {
      const s = count(0) < count(1) ? 0 : 1, j = at(1 + Math.floor(R() * 38) + (s ? 40 : 0), 1 + Math.floor(R() * (H - 2)));
      if (g[j] === DIRT && rs[s][j]) { g[j] = GEM; added++; }
    }
    const gems = count(0) + count(1);
    return { w: W, h: H, grid: g, starts, exit, pattern, pockets: placed, gems, need: Math.round(gems * .6), time: 300, moved, added, seed };
  }

  root.genBigCave = genBigCave;
  root.BIGCAVE = { W, H, E, DIRT, STEEL, WALL, ROCK, GEM, EXIT, PATTERNS, POCKETS };
  if (typeof module !== 'undefined') module.exports = { genBigCave };
})(typeof window !== 'undefined' ? window : globalThis);
