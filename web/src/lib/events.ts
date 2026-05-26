"use client";

import { getQueryClient } from "@/components/Providers";

/**
 * Query keys that should be invalidated after a generic mutation (status change,
 * list add/remove, playback progress update, etc.).
 *
 * Does NOT invalidate detail-level caches like media-detail, media-episodes,
 * or static config/health queries. Those are refreshed independently.
 */
const MUTATION_AFFECTED_KEYS = [
  ["lists"],
  ["home-recently-watched"],
  ["home-watching"],
  ["library"],
  ["playback-status"],
  ["home-smart-playlist"],
  ["media-episodes"],
] as const;

/**
 * Fire a targeted data-refresh event.
 *
 * Invalidates only the React Query caches that are commonly affected by
 * mutations (status updates, list changes, playback progress). Components
 * that need specific detail-level invalidation should do it directly.
 *
 * Pass `extraKeys` to also invalidate additional query key patterns.
 */
export function dispatchRefresh(extraKeys?: Array<readonly unknown[]>) {
  if (typeof window === "undefined") return;

  try {
    const qc = getQueryClient();
    if (qc) {
      for (const key of MUTATION_AFFECTED_KEYS) {
        qc.invalidateQueries({ queryKey: key as readonly unknown[] });
      }
      if (extraKeys) {
        for (const key of extraKeys) {
          qc.invalidateQueries({ queryKey: key as readonly unknown[] });
        }
      }
    }
  } catch {
    // Providers may not be mounted yet
  }
}
