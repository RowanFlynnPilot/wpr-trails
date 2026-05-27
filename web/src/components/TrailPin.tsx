import type { Difficulty } from "../types/trail";

/** Pin / polyline / chip swatch color per difficulty tier. */
export const DIFFICULTY_COLORS: Record<Difficulty, string> = {
  easy: "#16a34a",       // green-600
  moderate: "#2563eb",   // blue-600
  difficult: "#ea580c",  // orange-600
  strenuous: "#dc2626",  // red-600
};
