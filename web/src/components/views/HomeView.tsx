"use client";

import { useMemo } from "react";
import { Loader2 } from "lucide-react";
import Hero from "@/components/media/Hero";
import MediaRow from "@/components/media/MediaRow";
import { mediaApi, type MediaItem } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

interface HomeViewProps {
  onSelect: (item: MediaItem) => void;
}

// Premium animated shimmer skeleton loader for lazy-loaded media rows
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
  // 1. Critical User-Specific Watch List
  const watchingQuery = useQuery({
    queryKey: ["home-watching"],
    queryFn: () => mediaApi.getUserList("watching", "ANIME"),
  });

  // 2. Playback Status (Polls to stay updated with player activities)
  const playbackStatusQuery = useQuery({
    queryKey: ["home-playback-status"],
    queryFn: () => mediaApi.getPlaybackStatus().catch(() => null),
    refetchInterval: 5000,
  });

  // 3. Background/Non-blocking Discovery Queries
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

  // 4. Secondary Query for Missed/Recent Releases
  const watchingMedia = watchingQuery.data?.media || [];
  const watchingIds = useMemo(() => watchingMedia.map((m) => m.id), [watchingMedia]);

  const recentReleasesQuery = useQuery({
    queryKey: ["home-recent-releases", watchingIds],
    enabled: watchingQuery.isSuccess,
    queryFn: async () => {
      // Calculate what's actually new based on user progress
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
        
        // Merge and de-duplicate
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

  // Re-order watching list based on local playback status if available
  const continueWatchingList = useMemo(() => {
    const list = [...watchingMedia];
    const playbackStatus = playbackStatusQuery.data;
    
    if (playbackStatus && list.length > 0) {
      const lastPlayedId = playbackStatus.media_id;
      const lastPlayedIndex = list.findIndex((m) => m.id === lastPlayedId);
      if (lastPlayedIndex > 0) {
        const [lastPlayedItem] = list.splice(lastPlayedIndex, 1);
        list.unshift(lastPlayedItem);
      }
    }
    return list;
  }, [watchingMedia, playbackStatusQuery.data]);

  // Compute Hero Element
  const heroItem = useMemo(() => {
    if (continueWatchingList.length > 0) {
      const availableToWatch = continueWatchingList.filter((item) => {
        const progress = item.user_status?.progress || 0;
        const total = item.episodes || 0;
        if (item.next_airing) {
          return progress < item.next_airing.episode - 1;
        }
        return total > 0 ? progress < total : true;
      });

      const pool = availableToWatch.length > 0 ? availableToWatch : continueWatchingList;
      return pool[0];
    } else if (trendingQuery.data?.media && trendingQuery.data.media.length > 0) {
      return trendingQuery.data.media[0];
    }
    return null;
  }, [continueWatchingList, trendingQuery.data]);

  // Global loading only until critical list is loaded
  if (watchingQuery.isLoading) {
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
