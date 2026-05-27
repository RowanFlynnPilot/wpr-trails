import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "wpr-trails-favorites";

function load(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? new Set(arr) : new Set();
  } catch {
    return new Set();
  }
}

function save(set: Set<string>): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...set]));
  } catch {
    /* swallow — privacy mode, quota, etc. */
  }
}

/**
 * Trail favorites persisted to localStorage. No cloud sync — favorites are
 * per-device, which matches how the tool is used (you check this on your phone
 * before heading out).
 */
export function useFavorites() {
  const [favorites, setFavorites] = useState<Set<string>>(load);

  // Sync across tabs in the same browser session.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setFavorites(load());
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const toggle = useCallback((id: string) => {
    setFavorites((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      save(next);
      return next;
    });
  }, []);

  const isFavorite = useCallback(
    (id: string) => favorites.has(id),
    [favorites],
  );

  return { favorites, isFavorite, toggle };
}
