import { useEffect, useState } from "react";
import type { Trail } from "../types/trail";
import { fetchTrail } from "../lib/data";

type State =
  | { status: "idle" }
  | { status: "loading"; id: string }
  | { status: "ready"; trail: Trail }
  | { status: "error"; id: string; message: string };

const cache = new Map<string, Trail>();

export function useTrail(id: string | null): State {
  const [state, setState] = useState<State>(
    id === null ? { status: "idle" } : { status: "loading", id },
  );

  useEffect(() => {
    if (id === null) {
      setState({ status: "idle" });
      return;
    }
    const cached = cache.get(id);
    if (cached) {
      setState({ status: "ready", trail: cached });
      return;
    }
    setState({ status: "loading", id });
    let cancelled = false;
    fetchTrail(id)
      .then((trail) => {
        cache.set(id, trail);
        if (!cancelled) setState({ status: "ready", trail });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : String(err);
          setState({ status: "error", id, message });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return state;
}
