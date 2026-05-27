export type Activity =
  | "hiking"
  | "biking"
  | "horseback"
  | "xc_ski"
  | "snowshoe"
  | "snowmobile";

export type County =
  | "marathon"
  | "lincoln"
  | "langlade"
  | "taylor"
  | "shawano"
  | "portage";

export type Difficulty = "easy" | "moderate" | "difficult";

export interface TrailIndexEntry {
  id: string;
  name: string;
  activities: Activity[];
  counties: County[];
  length_m: number;
  elevation_gain_m: number;
  elevation_max_m: number;
  difficulty_estimated: Difficulty;
  /** [longitude, latitude] — GeoJSON convention */
  centroid: [number, number];
  drive_minutes_from_wausau: number;
}
