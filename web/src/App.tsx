import { useMemo, useState } from "react";
import type { Activity, County } from "./types/trail";
import { useTrailIndex } from "./hooks/useTrailIndex";
import { useScores } from "./hooks/useScores";
import FilterBar from "./components/FilterBar";
import MapView from "./components/MapView";
import DetailPanel from "./components/DetailPanel";

export default function App() {
  const indexState = useTrailIndex();
  const scoresState = useScores();
  const [activities, setActivities] = useState<Set<Activity>>(new Set());
  const [counties, setCounties] = useState<Set<County>>(new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const allTrails = indexState.status === "ready" ? indexState.trails : [];

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

  const rankedById = useMemo(() => {
    if (scoresState.status !== "ready") return new Map();
    return new Map(scoresState.scores.ranked.map((r) => [r.trail_id, r]));
  }, [scoresState]);

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
        {indexState.status === "loading" && (
          <div className="flex h-full items-center justify-center text-sm text-gray-500">
            Loading trails…
          </div>
        )}
        {indexState.status === "error" && (
          <div className="flex h-full items-center justify-center text-sm text-red-600">
            Failed to load: {indexState.message}
          </div>
        )}
        {indexState.status === "ready" && (
          <>
            <MapView
              trails={filtered}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
            {selectedId && (
              <DetailPanel
                trailId={selectedId}
                ranked={rankedById.get(selectedId)}
                onClose={() => setSelectedId(null)}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}
