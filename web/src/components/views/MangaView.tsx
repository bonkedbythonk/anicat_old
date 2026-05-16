"use client";

import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import Hero from "@/components/media/Hero";
import MediaRow from "@/components/media/MediaRow";
import { mediaApi, type MediaItem } from "@/lib/api";
import { useRefreshTrigger } from "@/lib/events";

interface MangaViewProps {
  onSelect: (item: MediaItem) => void;
}

export default function MangaView({ onSelect }: MangaViewProps) {
  const refreshKey = useRefreshTrigger();
  const [trendingList, setTrendingList] = useState<MediaItem[]>([]);
  const [popularList, setPopularList] = useState<MediaItem[]>([]);
  const [readingList, setReadingList] = useState<MediaItem[]>([]);
  const [heroManga, setHeroManga] = useState<MediaItem | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadManga = async () => {
      try {
        const [trending, popular, reading] = await Promise.all([
          mediaApi.getTrending("MANGA"),
          mediaApi.search("", "MANGA", 1, { min_score: 70 }),
          mediaApi.getUserList("watching", "MANGA")
        ]);
        setTrendingList(trending.media || []);
        setPopularList(popular.media || []);
        setReadingList(reading.media || []);
        
        // Prioritize manga the user hasn't finished reading
        const availableToRead = reading.media?.filter(item => {
          const progress = item.user_status?.progress || 0;
          const total = item.chapters || 0;
          return total > 0 ? progress < total : true;
        }) || [];

        const pool = availableToRead.length > 0 
          ? availableToRead.slice(0, 5) 
          : (reading.media?.length ? reading.media.slice(0, 5) : trending.media?.slice(0, 5));

        if (pool?.length) {
          setHeroManga(pool[Math.floor(Math.random() * pool.length)]);
        }
      } catch (err) {
        console.error("Failed to load manga view:", err);
      } finally {
        setLoading(false);
      }
    };
    loadManga();
  }, [refreshKey]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="animate-spin text-accent" size={40} />
      </div>
    );
  }

  return (
    <div className="space-y-12 animate-fade-in pb-20">
      {heroManga && <Hero item={heroManga} onSelect={onSelect} />}

      {readingList.length > 0 && (
        <MediaRow title="Continue Reading" items={readingList} onSelect={onSelect} />
      )}
      
      <MediaRow title="Trending Manga" items={trendingList} onSelect={onSelect} />
      
      <MediaRow title="Highly Rated Manga" items={popularList} onSelect={onSelect} />
    </div>
  );
}
