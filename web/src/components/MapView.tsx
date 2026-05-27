import { useEffect, useRef } from "react";
import { MapContainer, Polyline, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet.markercluster";
import type { Trail, TrailIndexEntry } from "../types/trail";
import { DIFFICULTY_COLORS } from "./TrailPin";

interface Props {
  trails: TrailIndexEntry[];
  selectedId: string | null;
  selectedTrail: Trail | null;
  favorites: Set<string>;
  onSelect: (id: string) => void;
}

export default function MapView({
  trails,
  selectedId,
  selectedTrail,
  favorites,
  onSelect,
}: Props) {
  return (
    <MapContainer
      center={[44.9, -89.7]}
      zoom={9}
      scrollWheelZoom
      className="h-full w-full"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClusteredTrailMarkers
        trails={trails}
        selectedId={selectedId}
        favorites={favorites}
        onSelect={onSelect}
      />
      {selectedTrail && (
        <>
          <TrailPolyline trail={selectedTrail} />
          <FitToTrail trail={selectedTrail} />
        </>
      )}
    </MapContainer>
  );
}

/**
 * Imperative bridge to leaflet.markercluster. We tried react-leaflet-cluster
 * but its versions either need React 19 or don't propagate react-leaflet v4's
 * context to children, so Markers render nothing. Doing it directly with the
 * vanilla Leaflet plugin avoids both problems.
 */
function ClusteredTrailMarkers({
  trails,
  selectedId,
  favorites,
  onSelect,
}: {
  trails: TrailIndexEntry[];
  selectedId: string | null;
  favorites: Set<string>;
  onSelect: (id: string) => void;
}) {
  const map = useMap();
  // onSelect via ref so it doesn't churn the marker effect when the parent
  // re-renders for unrelated reasons.
  const onSelectRef = useRef(onSelect);
  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  // Single effect: create cluster group, populate markers, clean up on unmount.
  // Combined deliberately — splitting create vs populate races with effect
  // cleanup, leaving the wrong group on the map.
  useEffect(() => {
    const group = L.markerClusterGroup({
      chunkedLoading: true,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      maxClusterRadius: 50,
      disableClusteringAtZoom: 12,
    });
    for (const trail of trails) {
      const [lon, lat] = trail.centroid;
      const color = DIFFICULTY_COLORS[trail.difficulty_estimated];
      const isSelected = trail.id === selectedId;
      const isFav = favorites.has(trail.id);
      const size = isSelected ? 20 : 14;
      const border = isSelected ? 3 : 2;
      const borderColor = isFav ? "#eab308" : "white";
      const html = `<div style="
        width:${size}px;height:${size}px;border-radius:9999px;
        background:${color};border:${border}px solid ${borderColor};
        box-shadow:0 1px 3px rgba(0,0,0,0.45);
      "></div>`;
      const marker = L.marker([lat, lon], {
        icon: L.divIcon({
          html,
          className: "",
          iconSize: [size, size],
          iconAnchor: [size / 2, size / 2],
        }),
      });
      marker.on("click", () => onSelectRef.current(trail.id));
      group.addLayer(marker);
    }
    map.addLayer(group);
    // Force the map to recompute size in case the container started 0x0;
    // without this the cluster plugin can produce no marker DOM in
    // headless / hidden-on-mount scenarios.
    requestAnimationFrame(() => map.invalidateSize());
    return () => {
      map.removeLayer(group);
    };
  }, [map, trails, selectedId, favorites]);

  return null;
}

function TrailPolyline({ trail }: { trail: Trail }) {
  const lines: [number, number][][] =
    trail.geometry.type === "LineString"
      ? [trail.geometry.coordinates.map(([lng, lat]) => [lat, lng])]
      : trail.geometry.coordinates.map((line) =>
          line.map(([lng, lat]) => [lat, lng]),
        );
  const color = DIFFICULTY_COLORS[trail.attributes.difficulty_estimated];
  return (
    <>
      {lines.map((line, i) => (
        <Polyline
          key={i}
          positions={line}
          pathOptions={{ color, weight: 4, opacity: 0.85 }}
        />
      ))}
    </>
  );
}

function FitToTrail({ trail }: { trail: Trail }) {
  const map = useMap();
  useEffect(() => {
    try {
      const [minLng, minLat, maxLng, maxLat] = trail.derived.bbox;
      const bounds = L.latLngBounds([minLat, minLng], [maxLat, maxLng]);
      const isDesktop = typeof window !== "undefined" && window.innerWidth >= 640;
      const opts = isDesktop
        ? { paddingTopLeft: [40, 40] as [number, number], paddingBottomRight: [420, 40] as [number, number] }
        : { paddingTopLeft: [40, 40] as [number, number], paddingBottomRight: [40, Math.min(window.innerHeight * 0.6, 400)] as [number, number] };
      map.flyToBounds(bounds, {
        ...opts,
        duration: 0.6,
        maxZoom: 14,
      });
    } catch (err) {
      console.error("FitToTrail crash:", err, "trail:", trail);
    }
  }, [trail.id, map]);
  return null;
}
