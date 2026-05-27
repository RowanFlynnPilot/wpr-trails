import { useMemo, useState } from "react";
import { useTrailIndex } from "./hooks/useTrailIndex";
import { useScores } from "./hooks/useScores";
import { useTrail } from "./hooks/useTrail";
import FilterBar, { LENGTH_MAX_MI, type FilterState } from "./components/FilterBar";
import MapView from "./components/MapView";
import DetailPanel from "./components/DetailPanel";
import WeatherBanner from "./components/WeatherBanner";

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
  const [sidebarOpen, setSidebarOpen] = useState(false);
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
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <main className="relative flex-1">
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open filters"
          className="absolute left-3 top-3 z-[450] flex h-9 w-9 items-center justify-center rounded-md border border-gray-200 bg-white shadow-sm hover:bg-gray-50 sm:hidden"
        >
          <span className="sr-only">Open filters</span>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
            <path d="M2 4h14M2 9h14M2 14h14" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
          </svg>
        </button>
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
            {scoresState.status === "ready" && (
              <WeatherBanner
                conditions={scoresState.scores.conditions_summary}
                alertCount={scoresState.scores.active_alerts.length}
                computedAt={scoresState.scores.computed_at}
              />
            )}
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
