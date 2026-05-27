import { Marker } from "react-leaflet";
import L from "leaflet";
import type { Difficulty, TrailIndexEntry } from "../types/trail";

export const DIFFICULTY_COLORS: Record<Difficulty, string> = {
  easy: "#16a34a",       // green-600
  moderate: "#2563eb",   // blue-600
  difficult: "#ea580c",  // orange-600
  strenuous: "#dc2626",  // red-600
};

const iconCache = new Map<string, L.DivIcon>();

function makeIcon(color: string, selected: boolean): L.DivIcon {
  const key = `${color}|${selected ? "s" : "n"}`;
  const cached = iconCache.get(key);
  if (cached) return cached;
  const size = selected ? 20 : 14;
  const borderWidth = selected ? 3 : 2;
  const html = `<div style="
    width:${size}px;height:${size}px;border-radius:9999px;
    background:${color};border:${borderWidth}px solid white;
    box-shadow:0 1px 3px rgba(0,0,0,0.45);
  "></div>`;
  const icon = L.divIcon({
    html,
    className: "", // suppress leaflet's default div-icon margin/padding
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
  iconCache.set(key, icon);
  return icon;
}

interface Props {
  trail: TrailIndexEntry;
  selected: boolean;
  onSelect: (id: string) => void;
}

export default function TrailPin({ trail, selected, onSelect }: Props) {
  const [lon, lat] = trail.centroid;
  const color = DIFFICULTY_COLORS[trail.difficulty_estimated];
  return (
    <Marker
      position={[lat, lon]}
      icon={makeIcon(color, selected)}
      eventHandlers={{
        click: () => onSelect(trail.id),
      }}
    />
  );
}
