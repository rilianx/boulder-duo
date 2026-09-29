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
        String line;
        while ((line = in.readLine()) != null) {
            String[] p = line.trim().split(" ");
            if (p[0].equals("Q")) break;
            if (p[0].equals("G")) {
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
