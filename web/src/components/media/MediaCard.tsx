"use client";

import { useCallback, useRef, memo } from "react";
import { Play, BookOpen, Star } from "lucide-react";
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
      <div className="relative aspect-[2/3] w-full overflow-hidden rounded-lg bg-surface card-glow border border-white/[0.04] group-hover:border-accent/25 group-hover:shadow-[0_12px_36px_rgba(0,0,0,0.7)]">
        <img 
          src={item.cover_image.large} 
          alt={title} 
          loading="lazy"
          decoding="async"
          className="absolute inset-0 w-full h-full object-cover transition-transform duration-[400ms] group-hover:scale-105"
        />
        
        {/* Play overlay */}
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-[400ms] flex items-center justify-center z-10">
          <button 
            onClick={handlePlay}
            className="glass-button p-3.5 rounded-full hover:scale-110 active:scale-95 transition-transform duration-200"
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
          <div className="absolute top-3 left-2.5 z-20 px-2 py-0.5 rounded-md bg-black/60 backdrop-blur-sm border border-white/10 text-[9px] font-bold text-accent uppercase tracking-wider max-w-[90%] truncate">
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

      {/* Card info */}
      <div className="space-y-2 px-0.5">
        <h3 className="text-sm font-bold text-white leading-tight line-clamp-2 group-hover:text-accent transition-colors duration-200">
          {title}
        </h3>

        {/* Score + status row */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {item.average_score && (
            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[9px] font-bold">
              <Star size={8} fill="currentColor" />
              {item.average_score}%
            </span>
          )}
          {item.user_status && (
            <span className={`inline-flex items-center px-1.5 py-0.5 rounded-md text-[9px] font-bold ${
              isFinished
                ? "bg-blue-500/10 border border-blue-500/20 text-blue-400"
                : hasNewEpisodes
                ? "bg-accent/10 border border-accent/20 text-accent"
                : "bg-white/[0.05] border border-white/[0.06] text-gray-400"
            }`}>
              {isFinished ? "All eps out" : hasNewEpisodes ? `Ep ${progress + 1}` : `${progress}/${totalCount || "?"}`}
            </span>
          )}
        </div>

        {/* Genre pills */}
        {item.genres && item.genres.length > 0 && (
          <div className="flex gap-1 flex-wrap">
            {item.genres.slice(0, 2).map((g) => (
              <span key={g} className="px-1.5 py-0.5 rounded text-[8px] font-semibold bg-white/[0.04] border border-white/[0.05] text-gray-500 group-hover:text-gray-400 transition-colors">
                {g}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});
export default MediaCard;
