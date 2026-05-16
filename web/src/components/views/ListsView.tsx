"use client";

import { useState, useEffect } from "react";
import { Loader2, Monitor, BookOpen, CheckCircle2, Bookmark, Pause, XCircle, Heart } from "lucide-react";
import MediaCard from "@/components/media/MediaCard";
import InfiniteScroll from "@/components/shared/InfiniteScroll";
import { mediaApi, type MediaItem } from "@/lib/api";
import { useRefreshTrigger } from "@/lib/events";

const LIST_TABS = [
  { key: "watching", label: "Reading/Watching", icon: Monitor },
  { key: "completed", label: "Completed", icon: CheckCircle2 },
  { key: "planning", label: "Planning", icon: Bookmark },
  { key: "paused", label: "Paused", icon: Pause },
  { key: "dropped", label: "Dropped", icon: XCircle },
];

interface ListsViewProps {
  onSelect: (item: MediaItem) => void;
}

export default function ListsView({ onSelect }: ListsViewProps) {
  const refreshKey = useRefreshTrigger();
  const [activeTab, setActiveTab] = useState("watching");
  const [type, setType] = useState<"ANIME" | "MANGA">("ANIME");
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    setLoading(true);
    mediaApi.getUserList(activeTab, type, 1)
      .then(data => {
        setItems(data.media || []);
        setHasMore(data.page_info?.has_next_page || false);
        setPage(1);
      })
      .catch(err => {
        console.error("Failed to load list:", err);
        setItems([]);
      })
      .finally(() => setLoading(false));
  }, [activeTab, type, refreshKey]);

  const loadMore = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const data = await mediaApi.getUserList(activeTab, type, nextPage);
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
        <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">My Lists</h1>
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

      {/* Tabs */}
      <div className="flex space-x-1 bg-white/[0.02] p-1 rounded-xl border border-white/[0.06] overflow-x-auto scrollbar-hide">
        {LIST_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg font-semibold text-sm whitespace-nowrap transition-all ${
              activeTab === tab.key
                ? "bg-accent text-white shadow-lg shadow-accent/20"
                : "text-gray-500 hover:text-white"
            }`}
          >
            <tab.icon size={15} />
            <span>{tab.key === "watching" ? (type === "MANGA" ? "Reading" : "Watching") : tab.label}</span>
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className={`relative transition-all duration-300 ${loading ? "opacity-50 pointer-events-none grayscale-[0.2]" : "opacity-100"}`}>
        {loading && items.length > 0 && (
          <div className="absolute top-0 left-0 right-0 z-10 flex justify-center mt-12">
            <div className="bg-black/60 backdrop-blur-md px-6 py-3 rounded-2xl border border-white/10 flex items-center space-x-3 shadow-2xl">
              <Loader2 className="animate-spin text-accent" size={20} />
              <span className="text-xs font-bold text-white uppercase tracking-widest">Updating List...</span>
            </div>
          </div>
        )}

        {items.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-5 animate-fade-in">
            {items.map((item) => (
              <MediaCard key={item.id} item={item} onSelect={onSelect} />
            ))}
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center py-48">
            <div className="flex flex-col items-center space-y-4">
              <Loader2 className="animate-spin text-accent" size={48} />
              <p className="text-gray-500 font-bold uppercase tracking-[0.2em] text-[10px]">Synchronizing List</p>
            </div>
          </div>
        ) : (
          <div className="text-center py-24 border-2 border-dashed border-white/[0.04] rounded-2xl">
            <Heart size={40} className="mx-auto text-gray-800 mb-4" />
            <p className="text-gray-600 font-semibold">This list is empty</p>
            <p className="text-gray-700 text-sm mt-1">Search for {type.toLowerCase()} and add them to your list.</p>
          </div>
        )}
      </div>

      <InfiniteScroll hasMore={hasMore} loading={loadingMore} onLoadMore={loadMore} />
    </div>
  );
}
