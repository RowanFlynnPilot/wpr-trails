import { useEffect, useState } from "react";
import type { Scores } from "../types/trail";
import { fetchScores } from "../lib/data";

type State =
  | { status: "loading" }
  | { status: "ready"; scores: Scores }
  | { status: "error"; message: string };

export function useScores(): State {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchScores()
      .then((scores) => {
        if (!cancelled) setState({ status: "ready", scores });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : String(err);
          setState({ status: "error", message });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
