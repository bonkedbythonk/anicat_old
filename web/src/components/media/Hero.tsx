"use client";

import { useState } from "react";
import { Play, Maximize, BookOpen, Loader2 } from "lucide-react";
import { type MediaItem } from "@/lib/api";

interface HeroProps {
  item: MediaItem;
  onSelect?: (item: MediaItem, action?: "play") => void;
}

export default function Hero({ item, onSelect }: HeroProps) {
  const [clicked, setClicked] = useState(false);
  const title = item.title.english || item.title.romaji || "Unknown";
  const currentProgress = item.user_status?.progress || 0;
  const total = item.episodes || item.chapters || 0;
  const isManga = item.type === "MANGA";
  
  // If airing, we might be caught up even if progress < total
  const latestAvailable = item.next_airing ? (item.next_airing.episode - 1) : total;
  const isFinished = total > 0 && currentProgress >= total;
  const isCaughtUp = !isFinished && latestAvailable > 0 && currentProgress >= latestAvailable;

  const handlePlay = () => {
    if (onSelect) {
      setClicked(true);
      onSelect(item, "play");
      // Reset after a timeout in case the drawer takes time to open
      setTimeout(() => setClicked(false), 3000);
    }
  };

  return (
    <div className="relative h-[50vh] lg:h-[60vh] w-full overflow-hidden rounded-2xl lg:rounded-3xl border border-white/[0.04] group">
      {/* Background */}
      <div className="absolute inset-0">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img 
          src={item.banner_image || item.cover_image.large} 
          alt={title} 
          className="absolute inset-0 w-full h-full object-cover brightness-[0.3] scale-105 transition-all duration-[2s] group-hover:scale-100 group-hover:brightness-[0.4]"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-background/80 via-transparent to-transparent" />
      </div>

      <div className="relative h-full flex flex-col justify-end pb-10 lg:pb-14 px-6 lg:px-12 space-y-5 max-w-3xl z-10">
        <div className="space-y-3">
          <div className="flex items-center space-x-3">
            <span className="px-3 py-1 bg-accent/90 text-white rounded-full text-[10px] font-bold uppercase tracking-widest shadow-lg shadow-accent/20">
              {item.user_status ? (isManga ? "Reading" : "Watching") : "Featured"}
            </span>
            {item.user_status && !isFinished && !isCaughtUp && (
              <span className="text-gray-400 font-semibold text-xs uppercase tracking-wider">
                {isManga ? "Chapter" : "Episode"} {currentProgress + 1}
              </span>
            )}
          </div>
          <h1 className="text-3xl lg:text-5xl xl:text-6xl font-extrabold tracking-tight leading-[1.05] text-white">
            {title}
          </h1>
        </div>
        
        {item.description && (
          <p 
            className="text-sm text-gray-400 line-clamp-2 leading-relaxed max-w-xl"
            dangerouslySetInnerHTML={{ __html: item.description }}
          />
        )}
        
        <div className="flex items-center space-x-3 pt-2">
          <button 
            onClick={handlePlay}
            disabled={isCaughtUp || clicked}
            className="flex items-center space-x-3 bg-white text-black px-8 py-3.5 rounded-xl hover:bg-accent hover:text-white transition-all duration-300 font-bold text-sm active:scale-95 shadow-xl disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white disabled:hover:text-black"
          >
            {clicked ? (
              <Loader2 size={18} className="animate-spin" />
            ) : isManga ? (
              <BookOpen size={18} />
            ) : (
              <Play fill="currentColor" size={18} />
            )}
            <span>
              {clicked
                ? "Loading..."
                : isFinished
                  ? (isManga ? "Read Again" : "Re-watch")
                  : isCaughtUp
                    ? "Caught Up"
                    : (item.user_status?.progress ? "Resume" : (isManga ? "Read Now" : "Play Now"))
              }
            </span>
          </button>
          
          <button 
            onClick={() => onSelect?.(item)}
            className="flex items-center space-x-3 bg-white/10 backdrop-blur-sm border border-white/10 text-white px-8 py-3.5 rounded-xl hover:bg-white/15 hover:border-white/20 transition-all font-bold text-sm"
          >
            <Maximize size={18} />
            <span>Details</span>
          </button>
        </div>
      </div>
    </div>
  );
}
