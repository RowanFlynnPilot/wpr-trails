import type { TrailIndexEntry } from "../types/trail";

const DATA_BASE_URL =
  import.meta.env.VITE_DATA_BASE_URL ??
  "https://rowanflynnpilot.github.io/wpr-trails/data/processed";

export async function fetchTrailIndex(): Promise<TrailIndexEntry[]> {
  const res = await fetch(`${DATA_BASE_URL}/index.json`);
  if (!res.ok) {
    throw new Error(`Failed to fetch trail index: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as TrailIndexEntry[];
}
