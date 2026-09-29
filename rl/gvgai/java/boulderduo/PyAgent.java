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
        try {
            Bridge.out.println("@S " + Bridge.encode(so));
            Bridge.out.flush();
            while (true) {
                String line = Bridge.in.readLine();
                if (line == null) return Types.ACTIONS.ACTION_NIL;
                String[] p = line.trim().split(" ");
                if (p[0].equals("A")) return Bridge.ACTS[Integer.parseInt(p[1])];
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
