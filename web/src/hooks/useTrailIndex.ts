import { useEffect, useState } from "react";
import type { TrailIndexEntry } from "../types/trail";
import { fetchTrailIndex } from "../lib/data";

type State =
  | { status: "loading" }
  | { status: "ready"; trails: TrailIndexEntry[] }
  | { status: "error"; message: string };

export function useTrailIndex(): State {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchTrailIndex()
      .then((trails) => {
        if (!cancelled) setState({ status: "ready", trails });
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
