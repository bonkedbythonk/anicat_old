"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";

export interface PageResult<T> {
  /** The items for this page. */
  items: T[];
  /** Whether there is a next page available. */
  hasNextPage: boolean;
}

export interface UsePaginatedListOptions<T> {
  /** React Query key to identify this list and trigger refetches */
  queryKey: unknown[];
  /** Function that fetches a page of results. Receives page number (1-based). */
  fetchFn: (page: number) => Promise<PageResult<T>>;
  /** Optional flag to delay fetching */
  enabled?: boolean;
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
 * infinite scroll. Now backed by React Query for automatic caching
 * and refresh-event invalidation.
 */
export function usePaginatedList<T>({
  queryKey,
  fetchFn,
  enabled = true,
}: UsePaginatedListOptions<T>): UsePaginatedListReturn<T> {
  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam = 1 }) => fetchFn(pageParam),
    getNextPageParam: (lastPage, allPages) => 
      lastPage.hasNextPage ? allPages.length + 1 : undefined,
    initialPageParam: 1,
    enabled,
  });

  const items = useMemo(() => {
    if (!data) return [];
    return data.pages.flatMap((page) => page.items);
  }, [data]);

  const loadMore = useCallback(async () => {
    if (!isFetchingNextPage && hasNextPage) {
      await fetchNextPage();
    }
  }, [fetchNextPage, isFetchingNextPage, hasNextPage]);

  return {
    items,
    loading: isLoading,
    loadingMore: isFetchingNextPage,
    hasMore: !!hasNextPage,
    loadMore,
  };
}
