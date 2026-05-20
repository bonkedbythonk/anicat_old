"use client";

import { useState } from "react";
import { Loader2, Library } from "lucide-react";
import LazyCard from "@/components/media/LazyCard";
import InfiniteScroll from "@/components/shared/InfiniteScroll";
import MediaTypeToggle from "@/components/shared/MediaTypeToggle";
import { usePaginatedList } from "@/lib/usePaginatedList";
import { mediaApi, type MediaItem } from "@/lib/api";
import { useRefreshTrigger } from "@/lib/events";

interface LibraryViewProps {
  onSelect: (item: MediaItem) => void;
}

export default function LibraryView({ onSelect }: LibraryViewProps) {
  const refreshKey = useRefreshTrigger();
  const [type, setType] = useState<"ANIME" | "MANGA">("ANIME");

  const { items, loading, loadingMore, hasMore, loadMore } =
    usePaginatedList<MediaItem>({
      fetchFn: async (page) => {
        const data = await mediaApi.getUserList("completed", type, page);
        return {
          items: data.media || [],
          hasNextPage: data.page_info?.has_next_page || false,
        };
      },
      deps: [type, refreshKey],
    });

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">Library</h1>
        <MediaTypeToggle value={type} onChange={setType} />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="animate-spin text-accent" size={36} />
        </div>
      ) : items.length > 0 ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-5">
            {items.map((item) => (
              <LazyCard key={item.id} item={item} onSelect={onSelect} />
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
