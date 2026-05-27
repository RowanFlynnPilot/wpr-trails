import { useEffect } from "react";
import { MapContainer, Polyline, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import type { Trail, TrailIndexEntry } from "../types/trail";
import TrailPin from "./TrailPin";

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
  return (
    <>
      {lines.map((line, i) => (
        <Polyline
          key={i}
          positions={line}
          pathOptions={{ color: "#059669", weight: 4, opacity: 0.85 }}
        />
      ))}
    </>
  );
}

function FitToTrail({ trail }: { trail: Trail }) {
  const map = useMap();
  useEffect(() => {
    const [minLng, minLat, maxLng, maxLat] = trail.derived.bbox;
    const bounds = L.latLngBounds([minLat, minLng], [maxLat, maxLng]);
    // Pad the right side to leave room for the 384px detail panel.
    map.flyToBounds(bounds, {
      paddingTopLeft: [40, 40],
      paddingBottomRight: [420, 40],
      duration: 0.6,
      maxZoom: 14,
    });
  }, [trail.id, map]);
  return null;
}
