"use client";

import { useState, useEffect, useCallback } from "react";

export interface PageResult<T> {
  /** The items for this page. */
  items: T[];
  /** Whether there is a next page available. */
  hasNextPage: boolean;
}

export interface UsePaginatedListOptions<T> {
  /** Function that fetches a page of results. Receives page number (1-based). */
  fetchFn: (page: number) => Promise<PageResult<T>>;
  /**
   * Dependencies that should trigger a full reset to page 1.
   * Follows the same rules as useEffect deps.
   */
  deps: React.DependencyList;
}

export interface UsePaginatedListReturn<T> {
  /** Accumulated items across all loaded pages. */
  items: T[];
  /** Whether the initial (first page) load is in progress. */
  loading: boolean;
  /** Whether a subsequent "load more" page is in progress. */
  loadingMore: boolean;
  /** Whether there are more pages to load. */
  hasMore: boolean;
  /** Load the next page (no-op if already loading or no more pages). */
  loadMore: () => Promise<void>;
}

/**
 * Generic paginated list hook.
 *
 * Handles the common pattern found in SearchView, LibraryView, and
 * ListsView where data is loaded page-by-page with "load more"
 * infinite scroll.
 *
 * - Resets to page 1 whenever any dependency in `deps` changes.
 * - Appends subsequent pages via `loadMore()`.
 */
export function usePaginatedList<T>({
  fetchFn,
  deps,
}: UsePaginatedListOptions<T>): UsePaginatedListReturn<T> {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  // Initial load (reset on dependency change)
  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      try {
        const data = await fetchFn(1);
        if (cancelled) return;
        setItems(data.items);
        setHasMore(data.hasNextPage);
        setPage(1);
      } catch {
        if (!cancelled) setItems([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const data = await fetchFn(nextPage);
      setItems((prev) => [...prev, ...data.items]);
      setHasMore(data.hasNextPage);
      setPage(nextPage);
    } catch {
      // Silently fail — previous items remain visible
    } finally {
      setLoadingMore(false);
    }
  }, [fetchFn, loadingMore, hasMore, page]);

  return { items, loading, loadingMore, hasMore, loadMore };
}
