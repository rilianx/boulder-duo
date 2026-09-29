package boulderduo;

import core.game.StateObservation;
import core.player.AbstractPlayer;
import ontology.Types;
import tools.ElapsedCpuTimer;

/** Agente GVGAI que delega cada decisión en Python a través de Bridge. */
public class PyAgent extends AbstractPlayer {
    public PyAgent(StateObservation so, ElapsedCpuTimer t) {}

    @Override
    public Types.ACTIONS act(StateObservation so, ElapsedCpuTimer t) {
        long t0 = System.nanoTime();
        Types.ACTIONS act = decide(so);
        Bridge.recordDecision(System.nanoTime() - t0);
        return act;
    }

    private Types.ACTIONS decide(StateObservation so) {
        try {
            Bridge.out.println(Bridge.generic ? "@G " + Bridge.encodeGeneric(so) : "@S " + Bridge.encode(so));
            Bridge.out.flush();
            while (true) {
                String line = Bridge.in.readLine();
                if (line == null) return Types.ACTIONS.ACTION_NIL;
                String[] p = line.trim().split(" ");
                if (p[0].equals("A")) return Bridge.ACTS[Integer.parseInt(p[1])];
                if (p[0].equals("N")) {
                    // N <ms> <profundidad> <meta> <distancias separadas por comas>: MCTS navegando a la meta
                    String[] ds = p[4].split(",");
                    int[] dist = new int[ds.length];
                    for (int i = 0; i < ds.length; i++) dist[i] = Integer.parseInt(ds[i]);
                    int a = Bridge.mcts(so, dist, Integer.parseInt(p[3]), Double.parseDouble(p[1]), Integer.parseInt(p[2]));
                    return Bridge.ACTS[a];
                }
                if (p[0].equals("F")) {
                    Bridge.future(so, Integer.parseInt(p[1]), Integer.parseInt(p[2]));
                    continue;
                }
                if (p[0].equals("L")) {
                    Bridge.out.println("@L" + Bridge.labels(so, Integer.parseInt(p[1]), Integer.parseInt(p[2])));
                    Bridge.out.flush();
                }
            }
        } catch (Exception e) {
            return Types.ACTIONS.ACTION_NIL;
        }
    }
}
