"use client";

import { getQueryClient } from "@/components/Providers";

/**
 * Fire a global data-refresh event.
 *
 * Invalidates ALL React Query caches so that components using
 * `useQuery` or `useInfiniteQuery` re-fetch automatically.
 */
export function dispatchRefresh() {
  if (typeof window === "undefined") return;

  try {
    const qc = getQueryClient();
    if (qc) {
      qc.invalidateQueries();
    }
  } catch {
    // Providers may not be mounted yet
  }
}
