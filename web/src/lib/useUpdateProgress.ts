"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { mediaApi, type MediaItem } from "@/lib/api";
import { dispatchRefresh } from "@/lib/events";

/**
 * UX-10: Optimistic progress update mutation.
 *
 * Updates the user's progress instantly in the React Query cache before
 * the API call completes. Rolls back on error to prevent stale UI.
 */
export function useUpdateProgress() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      mediaId,
      progress,
      status,
      score,
    }: {
      mediaId: number;
      progress?: number;
      status?: string;
      score?: number;
    }) => {
      return mediaApi.updateStatus(mediaId, status, score, progress);
    },

    onMutate: async ({ mediaId, progress, status, score }) => {
      // Cancel any in-flight detail refetches so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: ["media-detail", mediaId] });

      // Snapshot previous value for rollback
      const previous = queryClient.getQueryData<MediaItem>(["media-detail", mediaId]);

      // Optimistically update the cached media item
      queryClient.setQueryData(["media-detail", mediaId], (old: MediaItem | undefined) => {
        if (!old) return old;
        return {
          ...old,
          user_status: {
            ...old.user_status,
            status: status || old.user_status?.status || "watching",
            progress: progress !== undefined ? progress : old.user_status?.progress,
            score: score !== undefined ? score : old.user_status?.score,
          },
        };
      });

      return { previous };
    },

    onError: (_err, { mediaId }, context) => {
      // Rollback to the previous value
      if (context?.previous) {
        queryClient.setQueryData(["media-detail", mediaId], context.previous);
      }
    },

    onSettled: (_data, _error, { mediaId }) => {
      // Always refetch from server to ensure consistency
      queryClient.invalidateQueries({ queryKey: ["media-detail", mediaId] });
      queryClient.invalidateQueries({ queryKey: ["home-recently-watched"] });
      queryClient.invalidateQueries({ queryKey: ["home-watching"] });
      dispatchRefresh();
    },
  });
}
