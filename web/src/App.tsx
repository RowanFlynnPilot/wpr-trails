import { useMemo, useState } from "react";
import type { Activity, County } from "./types/trail";
import { useTrailIndex } from "./hooks/useTrailIndex";
import FilterBar from "./components/FilterBar";
import MapView from "./components/MapView";

export default function App() {
  const state = useTrailIndex();
  const [activities, setActivities] = useState<Set<Activity>>(new Set());
  const [counties, setCounties] = useState<Set<County>>(new Set());

  const allTrails = state.status === "ready" ? state.trails : [];

  const filtered = useMemo(() => {
    return allTrails.filter((t) => {
      if (activities.size > 0 && !t.activities.some((a) => activities.has(a))) {
        return false;
      }
      if (counties.size > 0 && !t.counties.some((c) => counties.has(c))) {
        return false;
      }
      return true;
    });
  }, [allTrails, activities, counties]);

  const toggle = <T,>(set: Set<T>, value: T): Set<T> => {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    return next;
  };

  return (
    <div className="flex h-full w-full">
      <FilterBar
        activities={activities}
        counties={counties}
        onToggleActivity={(a) => setActivities((s) => toggle(s, a))}
        onToggleCounty={(c) => setCounties((s) => toggle(s, c))}
        trailCount={filtered.length}
        totalCount={allTrails.length}
      />
      <main className="relative flex-1">
        {state.status === "loading" && (
          <div className="flex h-full items-center justify-center text-sm text-gray-500">
            Loading trails…
          </div>
        )}
        {state.status === "error" && (
          <div className="flex h-full items-center justify-center text-sm text-red-600">
            Failed to load: {state.message}
          </div>
        )}
        {state.status === "ready" && <MapView trails={filtered} />}
      </main>
    </div>
  );
}
