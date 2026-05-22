"use client";

import { useCallback, useRef, memo } from "react";
import { Play, BookOpen, Star, Tag } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { type MediaItem, mediaApi } from "@/lib/api";

interface MediaCardProps {
  item: MediaItem;
  onSelect?: (item: MediaItem, action?: "play") => void;
}

const MediaCard = memo(function MediaCard({ item, onSelect }: MediaCardProps) {
  const queryClient = useQueryClient();

  const handlePlay = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onSelect) {
      onSelect(item, "play");
    }
  };

  // Smart pre-fetch: when user hovers for 300ms+, pre-load the detail
  const prefetchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = useCallback(() => {
    prefetchTimerRef.current = setTimeout(() => {
      queryClient.prefetchQuery({
        queryKey: ["media-detail", item.id],
        queryFn: () => mediaApi.getDetails(item.id),
        staleTime: 60_000,
      });
      queryClient.prefetchQuery({
        queryKey: ["media-episodes", item.id],
        queryFn: () => mediaApi.getEpisodes(item.id),
        staleTime: 60_000,
      });
    }, 300);
  }, [item.id, queryClient]);

  const handleMouseLeave = useCallback(() => {
    if (prefetchTimerRef.current) {
      clearTimeout(prefetchTimerRef.current);
      prefetchTimerRef.current = null;
    }
  }, []);

  const title = item.title.english || item.title.romaji || "Media";
  const isManga = item.type === 'MANGA';
  const progress = item.user_status?.progress || 0;
  const totalCount = item.episodes || item.chapters || 0;
  const nextEp = item.next_airing?.episode;
  
  let currentReleased = 0;
  if (nextEp) {
    currentReleased = nextEp - 1;
  } else if (totalCount > 0) {
    currentReleased = totalCount;
  }
  
  const isFinished = item.status === 'FINISHED' || (item.end_date && new Date(item.end_date) < new Date());
  
  const hasNewEpisodes = 
    item.user_status?.status === 'watching' && 
    item.status === 'RELEASING' && 
    !isFinished &&
    progress < currentReleased &&
    (totalCount === 0 || progress < totalCount);

  return (
    <div 
      onClick={() => onSelect?.(item)} 
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="group cursor-pointer flex flex-col space-y-2.5 w-full text-left relative"
    >
      <div className="relative aspect-[2/3] w-full overflow-hidden rounded-lg bg-surface card-glow">
        <img 
          src={item.cover_image.large} 
          alt={title} 
          loading="lazy"
          decoding="async"
          className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
        />
        
        {/* Play overlay */}
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center z-10">
          <button 
            onClick={handlePlay}
            className="glass-button p-3.5 rounded-full hover:scale-110 active:scale-95 transition-all duration-200"
          >
            {isManga ? (
              <BookOpen size={20} />
            ) : (
              <Play size={20} fill="currentColor" />
            )}
          </button>
        </div>

        {/* UX-12: Recommendation reason pill */}
        {item.playlist_reason && (
          <div className="absolute top-2 left-2 z-20 px-2 py-0.5 rounded-md bg-black/60 backdrop-blur-sm border border-white/10 text-[9px] font-bold text-accent uppercase tracking-wider max-w-[90%] truncate">
            {item.playlist_reason}
          </div>
        )}

        {/* New episode badge */}
        {hasNewEpisodes && (
          <div className="absolute top-3 right-3 z-20 px-2.5 py-1 rounded-full bg-accent text-white text-[9px] font-bold uppercase tracking-wider shadow-lg">
            New Ep
          </div>
        )}
        
        {/* Progress bar */}
        {item.user_status && totalCount > 0 && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/10 z-10">
            <div 
              className="h-full bg-accent transition-all duration-700"
              style={{ width: `${(progress / totalCount) * 100}%` }}
            />
          </div>
        )}
      </div>

      <div className="space-y-1 px-0.5">
        <h3 className="text-sm font-bold text-white leading-tight line-clamp-2 group-hover:text-accent transition-colors">
          {title}
        </h3>
        <div className="flex items-center space-x-2 text-[10px] text-gray-500 font-medium">
          {item.average_score && (
            <span className="flex items-center space-x-1">
              <Star size={10} className="text-amber-400" fill="currentColor" />
              <span>{item.average_score}%</span>
            </span>
          )}
          {item.genres && item.genres.length > 0 && (
            <span className="flex items-center space-x-1">
              <Tag size={10} />
              <span className="truncate max-w-[100px]">{item.genres.slice(0, 2).join(", ")}</span>
            </span>
          )}
        </div>
        {item.user_status && (
          <span className="text-[10px] font-semibold text-gray-500">
            {isFinished ? '✓ Finished' : `${progress}/${totalCount || '?'}`}
          </span>
        )}
      </div>
    </div>
  );
});
export default MediaCard;
