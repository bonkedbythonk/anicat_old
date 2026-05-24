"use client";

import { useState, memo } from "react";
import { Play, Maximize, BookOpen, Loader2 } from "lucide-react";
import { type MediaItem } from "@/lib/api";

interface HeroProps {
  item: MediaItem;
  onSelect?: (item: MediaItem, action?: "play") => void;
}

const Hero = memo(function Hero({ item, onSelect }: HeroProps) {
  const [clicked, setClicked] = useState(false);
  const title = item.title.english || item.title.romaji || "Unknown";
  const currentProgress = item.user_status?.progress || 0;
  const total = item.episodes || item.chapters || 0;
  const isManga = item.type === "MANGA";
  const hasBanner = !!item.banner_image;
  
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
          className={`absolute inset-0 w-full h-full object-cover transition-[transform,filter] duration-[2s] group-hover:scale-100 ${
            hasBanner 
              ? "brightness-[0.25] group-hover:brightness-[0.35] scale-105" 
              : "brightness-[0.18] blur-2xl scale-110"
          }`}
        />
        {/* Vignette: darker at edges, lighter toward center */}
        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/70 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-background/90 via-transparent to-background/50" />
      </div>

      <div className="relative h-full flex flex-row items-end justify-between pb-10 lg:pb-14 px-6 lg:px-12 z-10">
        {/* Left Side: Info & Actions */}
        <div className="space-y-4 max-w-2xl">
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
            <h1 className="text-3xl lg:text-5xl xl:text-6xl font-black tracking-tight leading-[1.05] bg-gradient-to-r from-white via-white to-white/80 bg-clip-text text-transparent animate-fade-in">
              {title}
            </h1>
          </div>
          
          {/* Metadata Row */}
          <div className="flex items-center flex-wrap gap-x-3 gap-y-1.5 text-xs text-gray-300 font-semibold">
            {item.format && (
              <span className="px-2 py-0.5 bg-white/10 rounded text-[9px] uppercase tracking-wider">
                {item.format}
              </span>
            )}
            {item.seasonYear && (
              <span>{item.seasonYear}</span>
            )}
            {item.average_score && (
              <span className="flex items-center text-amber-400">
                ★ {item.average_score}%
              </span>
            )}
            {item.genres && item.genres.length > 0 && (
              <span className="text-gray-400">
                {item.genres.slice(0, 3).join(" • ")}
              </span>
            )}
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
              className="flex items-center space-x-3 glass-button px-8 py-3.5 rounded-full font-bold text-sm active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
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
              className="flex items-center space-x-3 bg-white/10 hover:bg-white/20 transition-all text-white px-8 py-3.5 rounded-full font-bold text-sm active:scale-95 cursor-pointer"
            >
              <Maximize size={18} />
              <span>Details</span>
            </button>
          </div>
        </div>

        {/* Right Side: Portrait Cover (only shown if there is no landscape banner, on larger screens) */}
        {!hasBanner && (
          <div className="hidden md:block w-[180px] lg:w-[220px] aspect-[2/3] shrink-0 ml-8 rounded-2xl overflow-hidden border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.8)] transition-transform duration-500 hover:scale-105">
            <img 
              src={item.cover_image.large} 
              alt={title} 
              className="w-full h-full object-cover"
            />
          </div>
        )}
      </div>
    </div>
  );
});

export default Hero;
