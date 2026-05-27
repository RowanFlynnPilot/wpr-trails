import { Marker, Popup } from "react-leaflet";
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

interface Props {
  trail: TrailIndexEntry;
}

export default function TrailPin({ trail }: Props) {
  const [lon, lat] = trail.centroid;
  const lengthMi = (trail.length_m / 1609.34).toFixed(1);

  return (
    <Marker position={[lat, lon]} icon={DefaultIcon}>
      <Popup>
        <div className="text-sm">
          <div className="font-semibold">{trail.name}</div>
          <div className="text-gray-600">
            {lengthMi} mi · {trail.difficulty_estimated} ·{" "}
            {trail.drive_minutes_from_wausau} min from Wausau
          </div>
          <div className="text-gray-500 text-xs mt-1">
            {trail.activities.join(", ")}
          </div>
        </div>
      </Popup>
    </Marker>
  );
}
