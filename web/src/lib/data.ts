import type { Scores, Trail, TrailIndexEntry } from "../types/trail";

const DATA_BASE_URL =
  import.meta.env.VITE_DATA_BASE_URL ??
  "https://rowanflynnpilot.github.io/wpr-trails/data/processed";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${DATA_BASE_URL}/${path}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${path}: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export function fetchTrailIndex(): Promise<TrailIndexEntry[]> {
  return fetchJson<TrailIndexEntry[]>("index.json");
}

export function fetchScores(): Promise<Scores> {
  return fetchJson<Scores>("scores.json");
}

export function fetchTrail(id: string): Promise<Trail> {
  return fetchJson<Trail>(`trails/${id}.json`);
}
