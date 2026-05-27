import { Marker } from "react-leaflet";
import L from "leaflet";
import type { TrailIndexEntry } from "../types/trail";

import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

const DefaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const SelectedIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [33, 54],
  iconAnchor: [16, 54],
  popupAnchor: [1, -45],
  shadowSize: [54, 54],
  className: "trail-pin-selected",
});

interface Props {
  trail: TrailIndexEntry;
  selected: boolean;
  onSelect: (id: string) => void;
}

export default function TrailPin({ trail, selected, onSelect }: Props) {
  const [lon, lat] = trail.centroid;

  return (
    <Marker
      position={[lat, lon]}
      icon={selected ? SelectedIcon : DefaultIcon}
      eventHandlers={{
        click: () => onSelect(trail.id),
      }}
    />
  );
}
