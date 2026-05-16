"use client";

import { useState, useRef } from "react";
import { Play, Loader2 } from "lucide-react";
import { mediaApi, type MediaItem } from "@/lib/api";

interface MediaCardProps {
  item: MediaItem;
  onSelect?: (item: MediaItem) => void;
}

export default function MediaCard({ item, onSelect }: MediaCardProps) {
  const [loading, setLoading] = useState(false);
  const isProcessing = useRef(false);
  const handlePlay = async (e: React.MouseEvent) => {
    if (loading || isProcessing.current) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    isProcessing.current = true;
    setLoading(true);
    try {
      await mediaApi.play(item.id);
    } catch (error) {
      console.error("Failed to trigger playback:", error);
    } finally {
      setLoading(false);
      setTimeout(() => {
        isProcessing.current = false;
      }, 500);
    }
  };

  const title = item.title.english || item.title.romaji || "Media";
  const isManga = item.type === 'MANGA';
  const progress = item.user_status?.progress || 0;
  const totalCount = item.episodes || item.chapters || 0;
  const nextEp = item.next_airing?.episode;
  
  // Only treat this as "new" when there is an actual upcoming airing.
  let currentReleased = 0;
  if (nextEp) {
    currentReleased = nextEp - 1;
  } else if (totalCount > 0) {
    currentReleased = totalCount;
  }
  
  const isFinished = item.status === 'FINISHED' || (item.end_date && new Date(item.end_date) < new Date());
  
  const isAiringNow = item.next_airing?.airing_at ? (
    new Date(item.next_airing.airing_at + "Z") > new Date(Date.now() - 14 * 24 * 60 * 60 * 1000)
  ) : !!nextEp;

  const hasNewEpisodes = 
    item.user_status?.status === 'watching' && 
    item.status === 'RELEASING' && 
    !isFinished &&
    isAiringNow &&
    progress < currentReleased &&
    (totalCount === 0 || progress < totalCount);

  return (
    <div 
      onClick={() => onSelect?.(item)} 
      className="group cursor-pointer flex flex-col space-y-2.5 w-full text-left"
    >
      <div className="relative aspect-[2/3] w-full overflow-hidden rounded-lg bg-surface card-glow">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img 
          src={item.cover_image.large} 
          alt={title} 
          className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
          style={{ transform: 'translateZ(0)' }}
        />
        
        {/* Play overlay */}
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center z-10" style={{ transform: 'translateZ(1px)' }}>
          <button 
            onClick={handlePlay}
            disabled={loading}
            className="bg-accent p-3.5 rounded-full hover:scale-110 active:scale-95 transition-transform duration-200 shadow-xl shadow-accent/30 text-white disabled:opacity-70 disabled:scale-100"
          >
            {loading ? (
              <Loader2 className="animate-spin" size={22} />
            ) : (
              <Play fill="currentColor" size={22} className="ml-0.5" />
            )}
          </button>
        </div>


        {/* Score badge */}
        {item.average_score && (
          <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm px-2 py-0.5 rounded-md text-[10px] font-bold text-accent z-10">
            ★ {(item.average_score / 10).toFixed(1)}
          </div>
        )}

        {/* Progress bar */}
        {item.user_status && progress > 0 && (
          <div className="absolute bottom-0 left-0 right-0 h-[3px] bg-black/60 z-10">
            <div 
              className="h-full bg-accent rounded-full" 
              style={{ width: `${Math.min((progress / (totalCount || currentReleased || 1)) * 100, 100)}%` }}
            />
          </div>
        )}

        {/* New badge - Moved to bottom of container for better stacking */}
        {hasNewEpisodes && (
          <div 
            className="absolute top-2 left-2 bg-accent text-white px-1.5 py-0.5 rounded text-[9px] font-black z-50 shadow-lg"
            style={{ transform: 'translateZ(10px)', pointerEvents: 'none' }}
          >
            NEW
          </div>
        )}
      </div>
      
      <div className="flex flex-col space-y-0.5 px-0.5">
        <h3 className="text-[13px] font-semibold text-gray-300 line-clamp-2 leading-snug group-hover:text-white transition-colors">
          {title}
        </h3>
        {item.user_status && progress > 0 ? (
          <div className="flex items-center space-x-2">
            <p className={`text-[11px] font-medium ${hasNewEpisodes ? "text-accent" : "text-gray-500"}`}>
              {isManga ? "CH" : "EP"} {progress} / {totalCount || currentReleased || "?"}
            </p>
            {hasNewEpisodes && (
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            )}
          </div>
        ) : (
          <p className="text-[11px] text-gray-500 font-medium">
            {item.season && item.season.charAt(0) + item.season.slice(1).toLowerCase()} {item.seasonYear}
          </p>
        )}
      </div>
    </div>
  );
}
