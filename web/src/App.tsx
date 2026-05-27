import { useCallback, useMemo, useState } from "react";
import { useTrailIndex } from "./hooks/useTrailIndex";
import { useScores } from "./hooks/useScores";
import { useTrail } from "./hooks/useTrail";
import { useFavorites } from "./hooks/useFavorites";
import FilterBar, { LENGTH_MAX_MI, type FilterState } from "./components/FilterBar";
import MapView from "./components/MapView";
import DetailPanel from "./components/DetailPanel";
import WeatherBanner from "./components/WeatherBanner";
import ChromeBar from "./components/ChromeBar";
import SponsorStrip from "./components/SponsorStrip";

const INITIAL_FILTERS: FilterState = {
  search: "",
  activities: new Set(),
  counties: new Set(),
  difficulties: new Set(),
  scenery: new Set(),
  familyOnly: false,
  favoritesOnly: false,
  maxDriveMin: null,
  lengthMi: [0, LENGTH_MAX_MI],
};

export default function App() {
  const indexState = useTrailIndex();
  const scoresState = useScores();
  const { favorites, isFavorite, toggle: toggleFavorite } = useFavorites();
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const trailState = useTrail(selectedId);

  const allTrails = indexState.status === "ready" ? indexState.trails : [];

  const filtered = useMemo(() => {
    const [loMi, hiMi] = filters.lengthMi;
    const loM = loMi * 1609.34;
    const hiM = hiMi * 1609.34;
    const q = filters.search.trim().toLowerCase();
    return allTrails.filter((t) => {
      if (q && !t.name.toLowerCase().includes(q)) return false;
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
      if (t.length_m < loM || t.length_m > hiM) return false;
      if (filters.scenery.size > 0) {
        const tags = t.editorial.scenery_tags ?? [];
        if (!tags.some((s) => filters.scenery.has(s))) return false;
      }
      if (filters.familyOnly && t.editorial.family_friendly !== true) return false;
      if (filters.favoritesOnly && !favorites.has(t.id)) return false;
      return true;
    });
  }, [allTrails, filters, favorites]);

  const rankedById = useMemo(() => {
    if (scoresState.status !== "ready") return new Map();
    return new Map(scoresState.scores.ranked.map((r) => [r.trail_id, r]));
  }, [scoresState]);

  const selectedTrail = trailState.status === "ready" ? trailState.trail : null;
  const computedAt =
    scoresState.status === "ready" ? scoresState.scores.computed_at : null;

  const pickRandom = useCallback(() => {
    if (filtered.length === 0) return;
    const pick = filtered[Math.floor(Math.random() * filtered.length)];
    setSelectedId(pick.id);
    setSidebarOpen(false);
  }, [filtered]);

  return (
    <div className="flex h-full w-full flex-col">
      <ChromeBar updatedAt={computedAt} onMenuClick={() => setSidebarOpen(true)} />
      <SponsorStrip />
      <div className="flex min-h-0 flex-1">
        <FilterBar
          state={filters}
          onChange={setFilters}
          trailCount={filtered.length}
          totalCount={allTrails.length}
          favoriteCount={favorites.size}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onPickRandom={pickRandom}
          randomDisabled={filtered.length === 0}
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
                favorites={favorites}
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
                  isFavorite={isFavorite(selectedId)}
                  onToggleFavorite={() => toggleFavorite(selectedId)}
                />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
