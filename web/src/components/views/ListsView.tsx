"use client";

import { useState, useEffect } from "react";
import { Loader2, Monitor, CheckCircle2, Bookmark, Pause, XCircle, Heart } from "lucide-react";
import MediaCard from "@/components/media/MediaCard";
import InfiniteScroll from "@/components/shared/InfiniteScroll";
import MediaTypeToggle from "@/components/shared/MediaTypeToggle";
import { usePaginatedList } from "@/lib/usePaginatedList";
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

// Skeleton card grid shown during tab switches instead of a blinding spinner
function ListSkeletonGrid() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-5 animate-pulse">
      {Array.from({ length: 12 }).map((_, i) => (
        <div key={i} className="space-y-2.5">
          <div className="aspect-[2/3] w-full rounded-lg bg-white/10" />
          <div className="h-4 w-3/4 rounded-md bg-white/10" />
          <div className="h-3 w-1/2 rounded-md bg-white/10" />
        </div>
      ))}
    </div>
  );
}

export default function ListsView({ onSelect }: ListsViewProps) {
  const refreshKey = useRefreshTrigger();
  const [activeTab, setActiveTab] = useState("watching");
  const [type, setType] = useState<"ANIME" | "MANGA">("ANIME");
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);

  const { items, loading, loadingMore, hasMore, loadMore } =
    usePaginatedList<MediaItem>({
      fetchFn: async (page) => {
        const data = await mediaApi.getUserList(activeTab, type, page);
        return {
          items: data.media || [],
          hasNextPage: data.page_info?.has_next_page || false,
        };
      },
      deps: [activeTab, type, refreshKey],
    });

  // Track first successful load so we can show skeleton instead of spinner on tab switches
  useEffect(() => {
    if (!loading && items.length > 0) {
      setHasLoadedOnce(true);
    }
  }, [loading, items.length]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">My Lists</h1>
        <MediaTypeToggle value={type} onChange={setType} />
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
      <div className="relative">
        {loading && hasLoadedOnce && (
          <div className="absolute top-0 left-0 right-0 z-10 flex justify-center mt-12 animate-fade-in">
            <div className="bg-black/60 backdrop-blur-md px-6 py-3 rounded-2xl border border-white/10 flex items-center space-x-3 shadow-2xl">
              <Loader2 className="animate-spin text-accent" size={20} />
              <span className="text-xs font-bold text-white uppercase tracking-widest">Updating List...</span>
            </div>
          </div>
        )}

        {items.length > 0 ? (
          <div className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-5 animate-fade-in transition-opacity duration-200 ${loading ? "opacity-50 pointer-events-none" : "opacity-100"}`}>
            {items.map((item) => (
              <MediaCard key={item.id} item={item} onSelect={onSelect} />
            ))}
          </div>
        ) : loading && !hasLoadedOnce ? (
          <ListSkeletonGrid />
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
