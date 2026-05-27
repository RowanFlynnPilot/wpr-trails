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

export type Difficulty = "easy" | "moderate" | "difficult" | "strenuous";

export type SceneryTag =
  | "water"
  | "wetland"
  | "overlook"
  | "prairie"
  | "rocky_outcrop"
  | "old_growth"
  | "glacial";

export type DogPolicy = "leashed" | "off_leash" | "prohibited" | "unknown";
export type Exposure = "sheltered" | "mixed" | "exposed";
export type MudSusceptibility = "low" | "moderate" | "high";

export interface IndexEditorial {
  scenery_tags: SceneryTag[] | null;
  dog_policy: DogPolicy | null;
  family_friendly: boolean | null;
  exposure: Exposure | null;
  mud_susceptibility: MudSusceptibility | null;
}

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
  /** [longitude, latitude] of snapped trailhead, or null if no parking found */
  trailhead_coords: [number, number] | null;
  editorial: IndexEditorial;
}

export interface TrailAttributes {
  length_m: number;
  elevation_gain_m: number;
  elevation_max_m: number;
  elevation_min_m: number;
  elevation_profile?: [number, number][];
  difficulty_estimated: Difficulty;
  surface: string[];
  is_loop: boolean;
  osm_network_class: string | null;
  blaze_color: string | null;
  counties: County[];
  park?: string | null;
  managing_authority?: string | null;
}

export interface TrailDerived {
  /** [longitude, latitude] */
  centroid: [number, number];
  /** [minLon, minLat, maxLon, maxLat] */
  bbox: [number, number, number, number];
  drive_minutes_from_wausau: number;
  trailhead_coords: [number, number] | null;
  parking_distance_m?: number | null;
}

export interface Trail {
  id: string;
  name: string;
  activities: Activity[];
  sources: Record<string, unknown>;
  geometry:
    | { type: "LineString"; coordinates: [number, number][] }
    | { type: "MultiLineString"; coordinates: [number, number][][] };
  attributes: TrailAttributes;
  editorial: Record<string, unknown>;
  derived: TrailDerived;
}

export interface ScoreFactor {
  name: string;
  value: number;
  weight: number;
  note: string;
}

export interface RankedTrail {
  trail_id: string;
  name: string;
  score: number;
  factors: ScoreFactor[];
  hard_filters_failed: string[];
}

export interface FilteredOutTrail {
  trail_id: string;
  name: string;
  reason: string;
}

export interface ConditionsSummary {
  recent_precip_in_24h: number | null;
  recent_precip_in_72h: number | null;
  forecast_temp_f: number | null;
  forecast_wind_mph: number | null;
  forecast_precip_chance: number | null;
  daylight_remaining_minutes?: number | null;
  active_closure_ids?: string[];
}

export interface Scores {
  computed_at: string;
  conditions_summary: ConditionsSummary;
  active_alerts: unknown[];
  ranked: RankedTrail[];
  filtered_out: FilteredOutTrail[];
}
