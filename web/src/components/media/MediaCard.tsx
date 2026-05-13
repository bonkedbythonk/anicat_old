"use client";

import { Play } from "lucide-react";
import { mediaApi, type MediaItem } from "@/lib/api";

interface MediaCardProps {
  item: MediaItem;
  onSelect?: (item: MediaItem) => void;
}

export default function MediaCard({ item, onSelect }: MediaCardProps) {
  const handlePlay = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await mediaApi.play(item.id);
    } catch (error) {
      console.error("Failed to trigger playback:", error);
    }
  };

  const title = item.title.english || item.title.romaji || "Media";
  const progress = item.user_status?.progress || 0;
  const totalEps = item.episodes || 1;

  return (
    <button 
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
            className="bg-accent p-3.5 rounded-full hover:scale-110 active:scale-95 transition-transform duration-200 shadow-xl shadow-accent/30 text-white"
          >
            <Play fill="currentColor" size={22} className="ml-0.5" />
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
              style={{ width: `${Math.min((progress / totalEps) * 100, 100)}%` }}
            />
          </div>
        )}
      </div>
      
      <div className="flex flex-col space-y-0.5 px-0.5">
        <h3 className="text-[13px] font-semibold text-gray-300 line-clamp-2 leading-snug group-hover:text-white transition-colors">
          {title}
        </h3>
        {item.user_status && progress > 0 ? (
          <p className="text-[11px] text-accent font-medium">
            EP {progress} / {item.episodes || "?"}
          </p>
        ) : (
          <p className="text-[11px] text-gray-500 font-medium">
            {item.season && item.season.charAt(0) + item.season.slice(1).toLowerCase()} {item.seasonYear}
          </p>
        )}
      </div>
    </button>
  );
}
