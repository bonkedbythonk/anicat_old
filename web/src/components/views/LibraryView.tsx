"use client";

import { useState, useEffect } from "react";
import { Loader2, Monitor, BookOpen, Library } from "lucide-react";
import MediaCard from "@/components/media/MediaCard";
import InfiniteScroll from "@/components/shared/InfiniteScroll";
import { mediaApi, type MediaItem } from "@/lib/api";
import { useRefreshTrigger } from "@/lib/events";

interface LibraryViewProps {
  onSelect: (item: MediaItem) => void;
}

export default function LibraryView({ onSelect }: LibraryViewProps) {
  const refreshKey = useRefreshTrigger();
  const [type, setType] = useState<"ANIME" | "MANGA">("ANIME");
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    setLoading(true);
    mediaApi.getUserList("completed", type, 1)
      .then(data => {
        setItems(data.media || []);
        setHasMore(data.page_info?.has_next_page || false);
        setPage(1);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [type, refreshKey]);

  const loadMore = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const data = await mediaApi.getUserList("completed", type, nextPage);
      setItems(prev => [...prev, ...(data.media || [])]);
      setHasMore(data.page_info?.has_next_page || false);
      setPage(nextPage);
    } catch {
      console.error("Load more failed");
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">Library</h1>
        <div className="flex bg-white/[0.04] p-1 rounded-xl border border-white/[0.06] w-fit">
            <button
              onClick={() => setType("ANIME")}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
                type === "ANIME" ? "bg-accent text-white shadow-lg shadow-accent/20" : "text-gray-500 hover:text-white"
              }`}
            >
              <Monitor size={16} />
              <span>Anime</span>
            </button>
            <button
              onClick={() => setType("MANGA")}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
                type === "MANGA" ? "bg-accent text-white shadow-lg shadow-accent/20" : "text-gray-500 hover:text-white"
              }`}
            >
              <BookOpen size={16} />
              <span>Manga</span>
            </button>
          </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="animate-spin text-accent" size={36} />
        </div>
      ) : items.length > 0 ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-5">
            {items.map((item) => (
              <MediaCard key={item.id} item={item} onSelect={onSelect} />
            ))}
          </div>
          <InfiniteScroll hasMore={hasMore} loading={loadingMore} onLoadMore={loadMore} />
        </>
      ) : (
        <div className="text-center py-24 border-2 border-dashed border-white/[0.04] rounded-2xl">
          <Library size={40} className="mx-auto text-gray-800 mb-4" />
          <p className="text-gray-600 font-semibold">Library is empty</p>
          <p className="text-gray-700 text-sm mt-1">Your completed {type.toLowerCase()} will appear here.</p>
        </div>
      )}
    </div>
  );
}
