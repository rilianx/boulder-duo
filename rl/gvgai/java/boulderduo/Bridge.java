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
                double[] r = ArcadeMachine.runOneGame(game, p[1], false, "boulderduo.PyAgent", null, Integer.parseInt(p[2]), 0);
                // r = {ganó, puntaje, ticks}
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
        int ax = (int) Math.round(so.getAvatarPosition().x / bs), ay = (int) Math.round(so.getAvatarPosition().y / bs);
        return so.getGameTick() + " " + so.getGameScore() + " " + ax + " " + ay + " " + so.getAvatarType() + " " + W + " "
                + H + " " + sb + " " + fr + " " + (res.length() > 0 ? res : "-");
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
