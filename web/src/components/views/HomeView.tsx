"use client";

import { useMemo, useRef } from "react";
import { Loader2 } from "lucide-react";
import Hero from "@/components/media/Hero";
import MediaRow from "@/components/media/MediaRow";
import { mediaApi, type MediaItem } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

interface HomeViewProps {
  onSelect: (item: MediaItem) => void;
}

// Returns true if the user has watched all available episodes for a media item.
function isCaughtUp(item: MediaItem): boolean {
  const progress = item.user_status?.progress || 0;
  if (progress === 0) return false;

  // If airing, compare against the latest aired episode
  if (item.next_airing?.episode) {
    return progress >= item.next_airing.episode - 1;
  }

  // If episodes count is known, compare directly
  if (item.episodes || item.chapters) {
    return progress >= (item.episodes || item.chapters || 0);
  }

  // Unknown episode count and not airing — treat finished media as caught up
  if (item.status === 'FINISHED') {
    return progress > 0;
  }

  // Unknown total and still airing/releasing — can't determine, show it
  return false;
}

function MediaRowSkeleton({ title }: { title: string }) {
  return (
    <div className="space-y-4 animate-pulse px-1">
      <div className="h-6 w-48 bg-white/10 rounded-md" />
      <div className="flex space-x-4 overflow-hidden">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="w-[150px] md:w-[180px] flex-none space-y-3">
            <div className="aspect-[2/3] w-full bg-white/10 rounded-lg" />
            <div className="h-4 w-3/4 bg-white/10 rounded-md" />
            <div className="h-3 w-1/2 bg-white/10 rounded-md" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function HomeView({ onSelect }: HomeViewProps) {
  // 1. Local watch history — sorted by most recently watched (from media_registry)
  const recentlyWatchedQuery = useQuery({
    queryKey: ["home-recently-watched"],
    queryFn: () => mediaApi.getRecent("ANIME", 20),
    refetchInterval: 15_000,
    staleTime: 10_000,
  });

  // 2. Playback Status — shared query key with NowPlaying component (deduped)
  useQuery({
    queryKey: ["playback-status"],
    queryFn: () => mediaApi.getPlaybackStatus().catch(() => null),
    refetchInterval: 5000,
    staleTime: 4000,
  });

  // 3. AniList Watching List — used for hero fallback and "New for You"
  const watchingQuery = useQuery({
    queryKey: ["home-watching"],
    queryFn: () => mediaApi.getUserList("watching", "ANIME"),
    refetchInterval: 30_000,
    staleTime: 20_000,
  });

  // 4. Background/Non-blocking Discovery Queries
  const trendingQuery = useQuery({
    queryKey: ["home-trending"],
    queryFn: () => mediaApi.getTrending("ANIME"),
  });

  const seasonalQuery = useQuery({
    queryKey: ["home-seasonal"],
    queryFn: () => mediaApi.getSeasonal("ANIME"),
  });

  const newlyReleasingQuery = useQuery({
    queryKey: ["home-newly-releasing"],
    queryFn: () => mediaApi.search('', 'ANIME', 1, { status: 'RELEASING' }),
  });

  // 5. Continue Watching = local watch history filtered to only shows
  //    currently on the user's AniList watching/repeating list, EXCLUDING
  //    items the user has caught up on.
  const continueWatchingList = useMemo(() => {
    const recent = recentlyWatchedQuery.data?.media || [];
    const watching = watchingQuery.data?.media || [];
    // Build a set of watching media IDs for fast lookup
    const watchingIds = new Set(watching.map((m) => m.id));
    return recent.filter((m) => watchingIds.has(m.id) && !isCaughtUp(m));
  }, [recentlyWatchedQuery.data, watchingQuery.data]);

  // 6. "New for You" — based on AniList watching list + schedule
  const watchingMedia = watchingQuery.data?.media || [];
  const watchingIds = useMemo(() => watchingMedia.map((m) => m.id), [watchingMedia]);

  const recentReleasesQuery = useQuery({
    queryKey: ["home-recent-releases", watchingIds],
    enabled: watchingQuery.isSuccess,
    queryFn: async () => {
      const missedEpisodes = watchingMedia.filter((item) => {
        const progress = item.user_status?.progress || 0;
        const nextEp = item.next_airing?.episode;
        let currentReleased = 0;
        if (nextEp) {
          currentReleased = nextEp - 1;
        } else if (item.episodes) {
          currentReleased = item.episodes;
        }
        const isFinished = item.status === 'FINISHED';
        return item.status === 'RELEASING' && !isFinished && progress < currentReleased;
      });

      const releases = [...missedEpisodes];
      if (watchingMedia.length > 0) {
        const schedule = await mediaApi.getSchedule(3, 0, 1, 10, watchingIds);
        const scheduledMedia = schedule.media || [];
        const seenIds = new Set(releases.map((m) => m.id));
        for (const m of scheduledMedia) {
          if (!seenIds.has(m.id)) {
            releases.push(m);
            seenIds.add(m.id);
          }
        }
      }
      return releases;
    },
  });

  // Compute candidate hero item — prefer recently watched (in-progress), then watching list, then trending
  const candidateHeroItem = useMemo(() => {
    // First: pick the most recently watched item that is still in progress
    if (continueWatchingList.length > 0) {
      return continueWatchingList[0];
    }

    // Second: fall back to AniList watching list (first in-progress item)
    if (watchingMedia.length > 0) {
      const availableToWatch = watchingMedia.filter((item) => !isCaughtUp(item));
      if (availableToWatch.length > 0) return availableToWatch[0];
    }

    // Third: trending
    if (trendingQuery.data?.media && trendingQuery.data.media.length > 0) {
      return trendingQuery.data.media[0];
    }
    return null;
  }, [continueWatchingList, watchingMedia, trendingQuery.data]);

  // Stable hero reference to prevent flicker on re-fetch
  const stableHeroRef = useRef<MediaItem | null>(candidateHeroItem);
  const heroItem = useMemo(() => {
    const prev = stableHeroRef.current;
    const next = candidateHeroItem;
    if (prev && next && prev.id === next.id) return prev;
    if (!next && prev) return prev;
    stableHeroRef.current = next;
    return next;
  }, [candidateHeroItem]);

  // Global loading only until critical data is loaded
  if (recentlyWatchedQuery.isLoading && watchingQuery.isLoading) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <Loader2 className="animate-spin text-accent" size={36} />
      </div>
    );
  }

  return (
    <div className="space-y-12 pb-12">
      {heroItem && <Hero item={heroItem} onSelect={onSelect} />}
      
      {continueWatchingList.length > 0 && (
        <MediaRow title="Continue Watching" items={continueWatchingList} onSelect={onSelect} />
      )}
      
      {recentReleasesQuery.isLoading ? (
        <MediaRowSkeleton title="New for You" />
      ) : (
        recentReleasesQuery.data && recentReleasesQuery.data.length > 0 && (
          <MediaRow title="New for You" items={recentReleasesQuery.data} onSelect={onSelect} />
        )
      )}
      
      {trendingQuery.isLoading ? (
        <MediaRowSkeleton title="Trending Now" />
      ) : (
        trendingQuery.data?.media && trendingQuery.data.media.length > 0 && (
          <MediaRow title="Trending Now" items={trendingQuery.data.media} onSelect={onSelect} />
        )
      )}
      
      {newlyReleasingQuery.isLoading ? (
        <MediaRowSkeleton title="Newly Releasing" />
      ) : (
        newlyReleasingQuery.data?.media && newlyReleasingQuery.data.media.length > 0 && (
          <MediaRow title="Newly Releasing" items={newlyReleasingQuery.data.media} onSelect={onSelect} />
        )
      )}
      
      {seasonalQuery.isLoading ? (
        <MediaRowSkeleton title="Seasonal Highlights" />
      ) : (
        seasonalQuery.data?.media && seasonalQuery.data.media.length > 0 && (
          <MediaRow title="Seasonal Highlights" items={seasonalQuery.data.media} onSelect={onSelect} />
        )
      )}
    </div>
  );
}
