package boulderduo;

import tracks.ArcadeMachine;

import java.io.PrintStream;

/** Juega partidas con un agente de GVGAI (p. ej. OLETS) para calibrar: RunAgent <juego> <agente> <nivel> <semilla>... */
public class RunAgent {
    public static void main(String[] args) {
        PrintStream out = System.out;
        System.setOut(new PrintStream(System.err, true));
        for (int k = 3; k < args.length; k++) {
            double[] r = ArcadeMachine.runOneGame(args[0], args[2], false, args[1], null, Integer.parseInt(args[k]), 0);
            out.println("@E " + (int) r[0] + " " + r[1] + " " + (int) r[2]);
            out.flush();
        }
    }
}
