"use client";

import { useEffect, useState, useCallback } from "react";

export const REFRESH_EVENT = "anicat-refresh-data";

/**
 * Fire a global data-refresh event.
 *
 * Also invalidates ALL React Query caches so that components using
 * `useQuery` re-fetch automatically. Components still using the
 * legacy `useRefreshTrigger` pattern receive the custom event.
 */
export function dispatchRefresh() {
  if (typeof window === "undefined") return;

  // React Query cache invalidation — the preferred path
  try {
    const { getQueryClient } = require("@/components/Providers");
    const qc = getQueryClient();
    if (qc) {
      qc.invalidateQueries();
    }
  } catch {
    // Providers may not be mounted yet (e.g. during SSR or early init)
  }

  // Legacy custom event — keeps existing useRefreshTrigger listeners working
  window.dispatchEvent(new CustomEvent(REFRESH_EVENT));
}

/**
 * Legacy refresh trigger — listens for the custom DOM event.
 *
 * **Deprecated.** Prefer `useQuery` with `queryClient.invalidateQueries()`.
 * Only LibraryView and ListsView still use this via `usePaginatedList`.
 * Once those migrate to `useInfiniteQuery`, this can be removed.
 *
 * @deprecated
 */
export function useRefreshTrigger() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = useCallback(() => {
    setRefreshKey((prev) => prev + 1);
  }, []);

  useEffect(() => {
    window.addEventListener(REFRESH_EVENT, handleRefresh);
    return () => window.removeEventListener(REFRESH_EVENT, handleRefresh);
  }, [handleRefresh]);

  return refreshKey;
}
