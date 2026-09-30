package boulderduo;

import core.game.Observation;
import core.game.StateObservation;
import core.vgdl.VGDLRegistry;
import ontology.Types;
import tracks.ArcadeMachine;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.HashMap;

/**
 * Puente entre el GVGAI real y Python (rl/boulder/gvgai_env.py), por stdin/stdout.
 *
 * Python envía:  G <archivo de nivel> <semilla>   jugar una partida (el PC es boulderduo.PyAgent)
 *                Q                                 salir
 * Durante la partida, en cada tick Java escribe "@S <estado>" y Python responde:
 *                A <0..5>        acción: 0 NIL, 1 ARRIBA, 2 ABAJO, 3 IZQUIERDA, 4 DERECHA, 5 USAR (pico)
 *                L <k> <reps>    etiquetas contrafactuales: para ↑ → ↓ ← y quieto, fracción de copias
 *                                del modelo en las que el avatar muere al hacer esa acción y luego nada k ticks
 * Al terminar: "@E <ganó 0/1> <puntaje> <ticks>".
 */
public class Bridge {
    static BufferedReader in;
    static PrintStream out;
    /** modo genérico: la grilla va como conjuntos de tipos de sprite (sin traducir a Boulder Dash) */
    static boolean generic = false;
    static boolean sentTypes = false;
    static final Types.ACTIONS[] ACTS = {Types.ACTIONS.ACTION_NIL, Types.ACTIONS.ACTION_UP, Types.ACTIONS.ACTION_DOWN,
            Types.ACTIONS.ACTION_LEFT, Types.ACTIONS.ACTION_RIGHT, Types.ACTIONS.ACTION_USE};
    // orden de nuestras direcciones (↑ → ↓ ←) y quieto
    static final Types.ACTIONS[] DIRS = {Types.ACTIONS.ACTION_UP, Types.ACTIONS.ACTION_RIGHT, Types.ACTIONS.ACTION_DOWN,
            Types.ACTIONS.ACTION_LEFT, Types.ACTIONS.ACTION_NIL};

    public static void main(String[] args) throws Exception {
        out = System.out;
        // GVGAI imprime sus propios mensajes: los mandamos a stderr para que no ensucien el protocolo
        System.setOut(new PrintStream(System.err, true));
        in = new BufferedReader(new InputStreamReader(System.in));
        String game = args[0];
        generic = args.length > 1 && args[1].equals("generic");
        String line;
        while ((line = in.readLine()) != null) {
            String[] p = line.trim().split(" ");
            if (p[0].equals("Q")) break;
            if (p[0].equals("G")) {
                sentTypes = false;
                resetTiming();
                double[] r = ArcadeMachine.runOneGame(game, p[1], false, "boulderduo.PyAgent", null, Integer.parseInt(p[2]), 0);
                // r = {ganó, puntaje, ticks}
                if (generic)   // tiempo por decisión medido en Java, incluyendo a Python: n, >40 ms, máx y suma (ms)
                    out.println("@M " + decisions + " " + over40 + " " + maxNs / 1e6 + " " + sumNs / 1e6);
                out.println("@E " + (int) r[0] + " " + r[1] + " " + (int) r[2]);
                out.flush();
            }
        }
    }

    static char code(String name) {
        switch (name) {
            case "avatar": return 'A';
            case "crab": return 'c';
            case "butterfly": return 'b';
            case "boulder": return 'o';
            case "diamond": return 'x';
            case "exitdoor": return 'e';
            case "wall": return 'w';
            case "dirt": return '.';
            default: return '-';
        }
    }

    static int prio(char c) {
        return "-.wexobcA".indexOf(c);
    }

    /** tick puntaje ax ay diamantes W H grilla(fila por fila) rocas(x,y,fracción;...) */
    static String encode(StateObservation so) {
        int bs = so.getBlockSize();
        ArrayList<Observation>[][] g = so.getObservationGrid();
        int W = g.length, H = g[0].length;
        char[] cells = new char[W * H];
        StringBuilder rocks = new StringBuilder();
        VGDLRegistry reg = VGDLRegistry.GetInstance();
        for (int x = 0; x < W; x++)
            for (int y = 0; y < H; y++) {
                char best = '-';
                for (Observation o : g[x][y]) {
                    char c = code(reg.getRegisteredSpriteKey(o.itype));
                    if (prio(c) > prio(best)) best = c;
                    if (c == 'o') {
                        double fy = (o.position.y / bs) - Math.floor(o.position.y / bs);
                        rocks.append((int) Math.round(o.position.x / bs)).append(',')
                             .append((int) Math.floor(o.position.y / bs)).append(',')
                             .append(String.format("%.2f", fy)).append(';');
                    }
                }
                cells[y * W + x] = best;
            }
        int ax = (int) Math.round(so.getAvatarPosition().x / bs), ay = (int) Math.round(so.getAvatarPosition().y / bs);
        int gems = 0;
        HashMap<Integer, Integer> res = so.getAvatarResources();
        for (Integer k : res.keySet())
            if (reg.getRegisteredSpriteKey(k).equals("diamond")) gems = res.get(k);
        return so.getGameTick() + " " + so.getGameScore() + " " + ax + " " + ay + " " + gems + " " + W + " " + H + " "
                + new String(cells) + " " + (rocks.length() > 0 ? rocks : "-");
    }

    /**
     * Estado genérico: tick puntaje ax ay tipoAvatar W H celdas enMovimiento recursos
     * celdas = máscara hexadecimal de itypes por casilla (fila por fila, separadas por comas),
 * enMovimiento = igual, solo con los sprites que están entre dos casillas,
     * recursos = itype:cantidad;... (o "-"). La primera vez por partida antes va "@T itype nombre categoría ...".
     */
    static String encodeGeneric(StateObservation so) {
        int bs = so.getBlockSize();
        ArrayList<Observation>[][] g = so.getObservationGrid();
        int W = g.length, H = g[0].length;
        StringBuilder sb = new StringBuilder(), fr = new StringBuilder();
        java.util.HashMap<Integer, Integer> cat = new java.util.HashMap<>();
        for (int y = 0; y < H; y++)
            for (int x = 0; x < W; x++) {
                long m = 0, f = 0;
                for (Observation o : g[x][y]) {
                    if (o.itype < 63) {
                        m |= 1L << o.itype;
                        // entre dos casillas = en movimiento (p. ej. una roca que cae 0,2 casillas por tick)
                        if (o.position.x % bs != 0 || o.position.y % bs != 0) f |= 1L << o.itype;
                    }
                    cat.put(o.itype, o.category);
                }
                if (x + y > 0) { sb.append(','); fr.append(','); }
                sb.append(Long.toHexString(m));
                fr.append(Long.toHexString(f));
            }
        if (!sentTypes) {
            VGDLRegistry reg = VGDLRegistry.GetInstance();
            StringBuilder t = new StringBuilder("@T");
            for (int i = 0; i < reg.numSpriteTypes(); i++)
                t.append(' ').append(i).append(':').append(reg.getRegisteredSpriteKey(i)).append(':')
                 .append(cat.getOrDefault(i, -1));
            out.println(t);
            sentTypes = true;
        }
        StringBuilder res = new StringBuilder();
        for (java.util.Map.Entry<Integer, Integer> e : so.getAvatarResources().entrySet())
            res.append(e.getKey()).append(':').append(e.getValue()).append(';');
        // objetos que se mueven (NPC y móviles, sin el avatar): itype:id:x:y en casillas, con decimales
        StringBuilder objs = new StringBuilder();
        for (int y = 0; y < H; y++)
            for (int x = 0; x < W; x++)
                for (Observation o : g[x][y])
                    if (o.category == Types.TYPE_NPC || o.category == Types.TYPE_MOVABLE)
                        objs.append(o.itype).append(':').append(o.obsID).append(':')
                            .append(String.format(java.util.Locale.ROOT, "%.2f", o.position.x / bs)).append(':')
                            .append(String.format(java.util.Locale.ROOT, "%.2f", o.position.y / bs)).append(';');
        int ax = (int) Math.round(so.getAvatarPosition().x / bs), ay = (int) Math.round(so.getAvatarPosition().y / bs);
        return so.getGameTick() + " " + so.getGameScore() + " " + ax + " " + ay + " " + so.getAvatarType() + " " + W + " "
                + H + " " + sb + " " + fr + " " + (res.length() > 0 ? res : "-") + " " + (objs.length() > 0 ? objs : "-")
                // posición exacta del avatar, en casillas (para ver arrastres de menos de una casilla por tick)
                + " " + String.format(java.util.Locale.ROOT, "%.3f:%.3f", so.getAvatarPosition().x / bs,
                                      so.getAvatarPosition().y / bs);
    }

    /**
     * Cubo del futuro: simula h ticks con el avatar quieto, reps veces, y devuelve por tick la unión de las
     * máscaras de tipos por casilla ("@F" y luego h líneas "t mascara,mascara,...").
     */
    static void future(StateObservation so, int h, int reps) {
        ArrayList<long[]> acc = new ArrayList<>();
        for (int r = 0; r < reps; r++) {
            StateObservation c = so.copy();
            for (int t = 0; t < h; t++) {
                if (c.isGameOver()) break;
                c.advance(Types.ACTIONS.ACTION_NIL);
                ArrayList<Observation>[][] g = c.getObservationGrid();
                int W = g.length, H = g[0].length;
                if (acc.size() <= t) acc.add(new long[W * H]);
                long[] m = acc.get(t);
                int bs = c.getBlockSize();
                for (int y = 0; y < H; y++)
                    for (int x = 0; x < W; x++)
                        for (Observation o : g[x][y]) {
                            if (o.itype >= 63) continue;
                            m[y * W + x] |= 1L << o.itype;
                            // un sprite entre dos casillas ocupa ambas (p. ej. un camión a medio camino)
                            int fx = (int) Math.floor(o.position.x / bs), fy = (int) Math.floor(o.position.y / bs);
                            if (o.position.x % bs != 0 && fx + 1 < W) m[Math.max(0, fy) * W + fx + 1] |= 1L << o.itype;
                            if (o.position.y % bs != 0 && fy + 1 < H) m[(fy + 1) * W + Math.max(0, fx)] |= 1L << o.itype;
                        }
            }
        }
        StringBuilder sb = new StringBuilder("@F ").append(acc.size());
        out.println(sb);
        for (int t = 0; t < acc.size(); t++) {
            StringBuilder l = new StringBuilder();
            long[] m = acc.get(t);
            for (int i = 0; i < m.length; i++) { if (i > 0) l.append(','); l.append(Long.toHexString(m[i])); }
            out.println(l);
        }
        out.flush();
    }

    // ------------------------------------------------------------ tiempo por decisión, medido en Java
    static long decisions = 0, over40 = 0, maxNs = 0, sumNs = 0;

    static void resetTiming() { decisions = over40 = maxNs = sumNs = 0; }

    static void recordDecision(long ns) {
        decisions++; sumNs += ns; maxNs = Math.max(maxNs, ns);
        if (ns > 40_000_000L) over40++;
    }

    // ------------------------------------------------------------ baseline: MCTS que navega a una casilla
    /**
     * UCT con el modelo del juego, para comparar el navegador con el mismo presupuesto por decisión.
     * Acciones: quieto y las 4 direcciones (sin USAR, igual que nuestro navegador). Valor de una simulación:
     * 1 si el avatar pisa la meta, 0 si pierde, y si no 0,5·(1 − d/dmax), con d la distancia al destino
     * (el mismo campo de distancias sin peligro que usa nuestro A*, mandado por Python).
     */
    static final Types.ACTIONS[] NAV_ACTS = {Types.ACTIONS.ACTION_NIL, Types.ACTIONS.ACTION_UP, Types.ACTIONS.ACTION_DOWN,
            Types.ACTIONS.ACTION_LEFT, Types.ACTIONS.ACTION_RIGHT};
    static java.util.Random mctsRng = new java.util.Random(1);

    static class Node {
        Node[] ch = new Node[NAV_ACTS.length];
        int n = 0;
        double v = 0;
    }

    /** celda del avatar en el estado s */
    static int avatarCell(StateObservation s) {
        int bs = s.getBlockSize(), W = s.getObservationGrid().length;
        int ax = (int) Math.round(s.getAvatarPosition().x / bs), ay = (int) Math.round(s.getAvatarPosition().y / bs);
        return ay * W + ax;
    }

    /** valor: 1 en la meta, 0 si pierde; si no, 0,1 + 0,8·(avance relativo a la distancia inicial d0), en [0,1] */
    static double navValue(StateObservation s, int[] dist, int goal, int dmax) {
        if (s.isGameOver() && s.getGameWinner() == Types.WINNER.PLAYER_LOSES) return 0;
        int c = avatarCell(s);
        if (c == goal) return 1;
        if (s.isGameOver()) return 0.5;                     // ganó la partida sin llegar: neutro
        int d = (c >= 0 && c < dist.length && dist[c] >= 0) ? dist[c] : dmax;
        double prog = (navD0 - d) / (double) Math.max(navD0, 1);   // 1 = llegó, 0 = igual que al inicio
        return Math.max(0.02, Math.min(0.98, 0.5 + 0.45 * prog));
    }

    static int navD0 = 1;
    static final int[][] NAV_DXY = {{0, 0}, {0, -1}, {0, 1}, {-1, 0}, {1, 0}};   // NIL ↑ ↓ ← →

    /** simulación guiada: con prob. 0,7 la acción que más baja la distancia (sin mirar peligro), si no al azar */
    static int rolloutAction(StateObservation s, int[] dist, int W) {
        if (mctsRng.nextDouble() < 0.3) return mctsRng.nextInt(NAV_ACTS.length);
        int c = avatarCell(s), best = mctsRng.nextInt(NAV_ACTS.length), bd = Integer.MAX_VALUE;
        for (int k = 1; k < NAV_ACTS.length; k++) {
            int x = c % W + NAV_DXY[k][0], y = c / W + NAV_DXY[k][1], j = y * W + x;
            if (x < 0 || x >= W || j < 0 || j >= dist.length || dist[j] < 0) continue;
            if (dist[j] < bd) { bd = dist[j]; best = k; }
        }
        return best;
    }

    /** Devuelve el índice en ACTS (0 NIL, 1 ↑, 2 ↓, 3 ←, 4 →) de la acción más visitada. */
    static int mcts(StateObservation so, int[] dist, int goal, double ms, int depth) {
        long end = System.nanoTime() + (long) (ms * 1e6);
        int dmax = 1;
        for (int d : dist) dmax = Math.max(dmax, d);
        dmax += depth;
        int c0 = avatarCell(so), W = so.getObservationGrid().length;
        navD0 = (c0 >= 0 && c0 < dist.length && dist[c0] >= 0) ? dist[c0] : dmax;
        Node root = new Node();
        double C = Math.sqrt(2);
        while (System.nanoTime() < end) {
            StateObservation s = so.copy();
            ArrayList<Node> path = new ArrayList<>();
            Node nd = root;
            path.add(nd);
            int t = 0;
            double val = -1;
            // selección / expansión
            while (t < depth && !s.isGameOver()) {
                int a = -1;
                for (int k = 0; k < NAV_ACTS.length; k++) if (nd.ch[k] == null) { a = k; break; }
                boolean expand = a >= 0;
                if (!expand) {
                    double best = -1e9;
                    for (int k = 0; k < NAV_ACTS.length; k++) {
                        Node c = nd.ch[k];
                        double u = c.v / c.n + C * Math.sqrt(Math.log(nd.n + 1) / c.n) + 1e-6 * mctsRng.nextDouble();
                        if (u > best) { best = u; a = k; }
                    }
                }
                s.advance(NAV_ACTS[a]);
                t++;
                if (expand) nd.ch[a] = new Node();
                nd = nd.ch[a];
                path.add(nd);
                double v = navValue(s, dist, goal, dmax);
                if (v == 1 || v == 0) { val = v; break; }
                if (expand) break;
            }
            // simulación al azar
            if (val < 0) {
                while (t < depth && !s.isGameOver()) {
                    s.advance(NAV_ACTS[rolloutAction(s, dist, W)]);
                    t++;
                    double v = navValue(s, dist, goal, dmax);
                    if (v == 1 || v == 0) { val = v; break; }
                }
                if (val < 0) val = navValue(s, dist, goal, dmax);
            }
            for (Node p : path) { p.n++; p.v += val; }
        }
        if (System.getenv("MCTS_LOG") != null)
            System.err.println("MCTS iter " + root.n + " visitas " + java.util.Arrays.toString(
                    java.util.Arrays.stream(root.ch).mapToInt(c -> c == null ? 0 : c.n).toArray()) + " d0 " + navD0);
        int best = 0, bn = -1;
        for (int k = 0; k < NAV_ACTS.length; k++)
            if (root.ch[k] != null && root.ch[k].n > bn) { bn = root.ch[k].n; best = k; }
        return best;
    }

    static String labels(StateObservation so, int k, int reps) {
        StringBuilder sb = new StringBuilder();
        for (Types.ACTIONS a : DIRS) {
            int dead = 0;
            for (int r = 0; r < reps; r++) {
                StateObservation c = so.copy();
                c.advance(a);
                for (int t = 0; t < k && !c.isGameOver(); t++) c.advance(Types.ACTIONS.ACTION_NIL);
                if (c.isGameOver() && c.getGameWinner() == Types.WINNER.PLAYER_LOSES) dead++;
            }
            sb.append(' ').append(String.format("%.3f", dead / (double) reps));
        }
        return sb.toString();
    }
}
