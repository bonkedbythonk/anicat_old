"use client";

import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import Hero from "@/components/media/Hero";
import MediaRow from "@/components/media/MediaRow";
import { mediaApi, type MediaItem } from "@/lib/api";
import { useRefreshTrigger } from "@/lib/events";

interface HomeViewProps {
  onSelect: (item: MediaItem) => void;
}

export default function HomeView({ onSelect }: HomeViewProps) {
  const refreshKey = useRefreshTrigger();
  const [watchingList, setWatchingList] = useState<MediaItem[]>([]);
  const [trendingList, setTrendingList] = useState<MediaItem[]>([]);
  const [seasonalList, setSeasonalList] = useState<MediaItem[]>([]);
  const [recentReleases, setRecentReleases] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [watching, trending, seasonal] = await Promise.all([
          mediaApi.getUserList("watching", "ANIME"),
          mediaApi.getTrending("ANIME"),
          mediaApi.getSeasonal("ANIME"),
        ]);
        
        const watchingMedia = watching.media || [];
        setWatchingList(watchingMedia);
        setTrendingList(trending.media || []);
        setSeasonalList(seasonal.media || []);
        
        // Now fetch schedule for these specific IDs
        if (watchingMedia.length > 0) {
          const watchingIds = watchingMedia.map(m => m.id);
          const schedule = await mediaApi.getSchedule(2, 0, 1, 10, watchingIds);
          setRecentReleases(schedule.media || []);
        } else {
          setRecentReleases([]);
        }
      } catch (err) {
        console.error("Failed to load home data:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [refreshKey]);

  const [heroItem, setHeroItem] = useState<MediaItem | null>(null);

  useEffect(() => {
    if (watchingList.length > 0) {
      // Prioritize items the user hasn't caught up with yet
      const availableToWatch = watchingList.filter(item => {
        const progress = item.user_status?.progress || 0;
        const total = item.episodes || 0;
        // If airing, we might be caught up even if progress < total
        if (item.next_airing) {
          return progress < (item.next_airing.episode - 1);
        }
        return total > 0 ? progress < total : true;
      });

      const pool = availableToWatch.length > 0 ? availableToWatch : watchingList;
      const randomIndex = Math.floor(Math.random() * Math.min(pool.length, 10));
      setHeroItem(pool[randomIndex]);
    } else if (trendingList.length > 0) {
      setHeroItem(trendingList[0]);
    }
  }, [watchingList, trendingList]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-accent" size={36} />
      </div>
    );
  }

  return (
    <div className="space-y-12 animate-fade-in pb-12">
      {heroItem && <Hero item={heroItem} onSelect={onSelect} />}
      
      {watchingList.length > 0 && (
        <MediaRow title="Continue Watching" items={watchingList} onSelect={onSelect} />
      )}
      
      {recentReleases.length > 0 && (
        <MediaRow title="New for You" items={recentReleases} onSelect={onSelect} />
      )}
      
      <MediaRow title="Trending Now" items={trendingList} onSelect={onSelect} />
      
      <MediaRow title="Seasonal Highlights" items={seasonalList} onSelect={onSelect} />
    </div>
  );
}
