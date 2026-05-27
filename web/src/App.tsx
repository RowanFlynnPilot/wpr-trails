import { useMemo, useState } from "react";
import { useTrailIndex } from "./hooks/useTrailIndex";
import { useScores } from "./hooks/useScores";
import { useTrail } from "./hooks/useTrail";
import FilterBar, { LENGTH_MAX_MI, type FilterState } from "./components/FilterBar";
import MapView from "./components/MapView";
import DetailPanel from "./components/DetailPanel";

const INITIAL_FILTERS: FilterState = {
  activities: new Set(),
  counties: new Set(),
  difficulties: new Set(),
  maxDriveMin: null,
  lengthMi: [0, LENGTH_MAX_MI],
};

export default function App() {
  const indexState = useTrailIndex();
  const scoresState = useScores();
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const trailState = useTrail(selectedId);

  const allTrails = indexState.status === "ready" ? indexState.trails : [];

  const filtered = useMemo(() => {
    const [loMi, hiMi] = filters.lengthMi;
    const loM = loMi * 1609.34;
    const hiM = hiMi * 1609.34;
    return allTrails.filter((t) => {
      if (filters.activities.size > 0 && !t.activities.some((a) => filters.activities.has(a))) {
        return false;
      }
      if (filters.counties.size > 0 && !t.counties.some((c) => filters.counties.has(c))) {
        return false;
      }
      if (filters.difficulties.size > 0 && !filters.difficulties.has(t.difficulty_estimated)) {
        return false;
      }
      if (filters.maxDriveMin !== null && t.drive_minutes_from_wausau > filters.maxDriveMin) {
        return false;
      }
      if (t.length_m < loM || t.length_m > hiM) {
        return false;
      }
      return true;
    });
  }, [allTrails, filters]);

  const rankedById = useMemo(() => {
    if (scoresState.status !== "ready") return new Map();
    return new Map(scoresState.scores.ranked.map((r) => [r.trail_id, r]));
  }, [scoresState]);

  const selectedTrail = trailState.status === "ready" ? trailState.trail : null;

  return (
    <div className="flex h-full w-full">
      <FilterBar
        state={filters}
        onChange={setFilters}
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
              selectedTrail={selectedTrail}
              onSelect={setSelectedId}
            />
            {selectedId && (
              <DetailPanel
                trailId={selectedId}
                trailState={trailState}
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
