import { useEffect } from "react";
import { MapContainer, Polyline, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import type { Trail, TrailIndexEntry } from "../types/trail";
import TrailPin, { DIFFICULTY_COLORS } from "./TrailPin";

interface Props {
  trails: TrailIndexEntry[];
  selectedId: string | null;
  selectedTrail: Trail | null;
  onSelect: (id: string) => void;
}

export default function MapView({ trails, selectedId, selectedTrail, onSelect }: Props) {
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
      {trails.map((trail) => (
        <TrailPin
          key={trail.id}
          trail={trail}
          selected={trail.id === selectedId}
          onSelect={onSelect}
        />
      ))}
      {selectedTrail && (
        <>
          <TrailPolyline trail={selectedTrail} />
          <FitToTrail trail={selectedTrail} />
        </>
      )}
    </MapContainer>
  );
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
      // Pad differently depending on the detail panel position:
      // desktop = 384px right drawer; mobile = bottom sheet up to ~75vh.
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
