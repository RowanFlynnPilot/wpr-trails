import { MapContainer, TileLayer } from "react-leaflet";
import type { TrailIndexEntry } from "../types/trail";
import TrailPin from "./TrailPin";

interface Props {
  trails: TrailIndexEntry[];
}

export default function MapView({ trails }: Props) {
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
        <TrailPin key={trail.id} trail={trail} />
      ))}
    </MapContainer>
  );
}
