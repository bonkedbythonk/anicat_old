"use client";

import { useCallback, useRef, memo, useState } from "react";
import { Play, BookOpen, Star, Tag } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { type MediaItem, mediaApi } from "@/lib/api";

interface MediaCardProps {
  item: MediaItem;
  onSelect?: (item: MediaItem, action?: "play") => void;
}

const MediaCard = memo(function MediaCard({ item, onSelect }: MediaCardProps) {
  const queryClient = useQueryClient();
  // UX-14: Rich hover preview state
  const [isHovered, setIsHovered] = useState(false);

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
    setIsHovered(true);
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
    setIsHovered(false);
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
            className="bg-accent p-3.5 rounded-full hover:scale-110 active:scale-95 transition-transform duration-200 shadow-xl shadow-accent/30 text-white"
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
          <div className="absolute top-2 right-2 z-20 px-2 py-1 rounded-full bg-accent text-white text-[9px] font-bold uppercase tracking-wider shadow-lg">
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

      {/* UX-14: Rich hover preview panel */}
      <AnimatePresence>
        {isHovered && item.description && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 right-0 -bottom-2 translate-y-full z-50 bg-surface/95 backdrop-blur-xl border border-white/[0.08] rounded-xl p-3 shadow-2xl shadow-black/50"
          >
            <p className="text-[11px] text-gray-400 line-clamp-3 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: item.description }}
            />
            {item.genres && (
              <div className="flex flex-wrap gap-1 mt-2">
                {item.genres.slice(0, 4).map(g => (
                  <span key={g} className="px-1.5 py-0.5 rounded-md bg-white/[0.04] border border-white/[0.06] text-[9px] font-medium text-gray-400">
                    {g}
                  </span>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

export default MediaCard;
