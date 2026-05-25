"use client";

import { useState, useEffect, useRef, memo } from "react";
import { Play, Maximize, BookOpen, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { mediaApi, type MediaItem, API_BASE_ORIGIN } from "@/lib/api";

interface HeroProps {
  item: MediaItem;
  onSelect?: (item: MediaItem, action?: "play") => void;
}

const Hero = memo(function Hero({ item, onSelect }: HeroProps) {
  const [clicked, setClicked] = useState(false);
  const [showVideo, setShowVideo] = useState(false);
  const [isVideoVisible, setIsVideoVisible] = useState(false);

  const iframeRef = useRef<HTMLIFrameElement>(null);

  const { data: config = null } = useQuery({
    queryKey: ["media-config", item.id],
    queryFn: () => mediaApi.getConfig(),
    staleTime: 60_000,
  });

  useEffect(() => {
    setShowVideo(false);
    setIsVideoVisible(false);
    if (!item.trailer?.id || item.trailer.site !== "youtube") return;

    const enabled = !!config?.stream?.autoplay_trailers;
    if (!enabled) return;

    const timer = setTimeout(() => {
      setShowVideo(true);
    }, 2500);

    return () => clearTimeout(timer);
  }, [item.id, item.trailer?.id, item.trailer?.site, config?.stream?.autoplay_trailers]);



  const title = item.title.english || item.title.romaji || "Unknown";
  const currentProgress = item.user_status?.progress || 0;
  const total = item.episodes || item.chapters || 0;
  const isManga = item.type === "MANGA";
  const hasBanner = !!item.banner_image;

  const latestAvailable = item.next_airing ? (item.next_airing.episode - 1) : total;
  const isFinished = total > 0 && currentProgress >= total;
  const isCaughtUp = !isFinished && latestAvailable > 0 && currentProgress >= latestAvailable;

  const handlePlay = () => {
    if (onSelect) {
      setClicked(true);
      onSelect(item, "play");
      setTimeout(() => setClicked(false), 3000);
    }
  };

  return (
    // Rounded corners on lg+, edge-to-edge on mobile via -mx-6
    <div className="relative h-[52vh] lg:h-[58vh] w-full overflow-hidden group -mx-6 lg:mx-0 lg:rounded-2xl">

      {/* Background */}
      <div className="absolute inset-0 bg-background">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={item.banner_image || item.cover_image.large}
          alt={title}
          className={`absolute inset-0 w-full h-full object-cover transition-[transform,filter,opacity] duration-[2s] ${
            hasBanner
              ? "brightness-[0.45] group-hover:brightness-[0.55] scale-[1.03] group-hover:scale-100"
              : "brightness-[0.28] blur-xl scale-110"
          } ${isVideoVisible && item.trailer?.id ? "opacity-0 pointer-events-none" : "opacity-100"}`}
        />

        {/* Muted auto-play trailer — overflow-hidden wrapper clips the scaled iframe */}
        {showVideo && item.trailer?.id && item.trailer.site === "youtube" && (
          <>
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
              <iframe
                ref={iframeRef}
                onLoad={() => {
                  setTimeout(() => {
                    setIsVideoVisible(true);
                  }, 600);
                }}
                src={`https://www.youtube-nocookie.com/embed/${item.trailer.id}?autoplay=1&mute=1&loop=1&playlist=${item.trailer.id}&controls=0&showinfo=0&rel=0&iv_load_policy=3&playsinline=1&modestbranding=1&disablekb=1&fs=0`}
                className={`absolute inset-[-15%] w-[130%] h-[130%] brightness-[0.45] pointer-events-none transition-opacity duration-1000 ${isVideoVisible ? "opacity-100" : "opacity-0"}`}
                allow="autoplay; encrypted-media"
                title="Airing Trailer"
              />
            </div>
            {/* Transparent overlay — blocks YouTube hover controls */}
            <div className="absolute inset-0 z-10 pointer-events-auto bg-transparent" />
          </>
        )}

        {/* Cinematic gradients: heavy at bottom-left for readability, fades on right */}
        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/55 to-background/5" />
        <div className="absolute inset-0 bg-gradient-to-r from-background/75 via-background/15 to-transparent" />
      </div>

      {/* Content */}
      <div className="relative h-full flex flex-row items-end justify-between pb-8 lg:pb-12 px-6 lg:px-10 z-10">
        {/* Left: Info & Actions */}
        <div className="space-y-3 max-w-2xl">
          <div className="space-y-2">
            <div className="flex items-center space-x-2.5">
              <span className="px-2.5 py-1 bg-accent text-white rounded-md text-[10px] font-bold uppercase tracking-widest shadow-lg shadow-accent/30">
                {item.user_status ? (isManga ? "Reading" : "Watching") : "Featured"}
              </span>
              {item.user_status && !isFinished && !isCaughtUp && (
                <span className="text-white/55 font-semibold text-xs uppercase tracking-wider">
                  {isManga ? "Chapter" : "Episode"} {currentProgress + 1}
                </span>
              )}
            </div>
            <h1
              className="text-3xl lg:text-5xl xl:text-6xl font-black tracking-tight leading-[1.05] text-white animate-fade-in"
              style={{ textShadow: "0 2px 24px rgba(0,0,0,0.9)" }}
            >
              {title}
            </h1>
          </div>

          {/* Metadata row */}
          <div className="flex items-center flex-wrap gap-x-2.5 gap-y-1 text-xs font-semibold">
            {item.format && (
              <span className="px-1.5 py-0.5 bg-white/10 rounded text-[9px] uppercase tracking-wider text-white/50">
                {item.format}
              </span>
            )}
            {item.seasonYear && <span className="text-white/50">{item.seasonYear}</span>}
            {item.average_score && (
              <span className="flex items-center gap-1 text-amber-400 font-bold">
                ★ {item.average_score}%
              </span>
            )}
            {item.genres && item.genres.length > 0 && (
              <span className="text-white/40">
                {item.genres.slice(0, 3).join(" · ")}
              </span>
            )}
          </div>

          {item.description && (
            <p
              className="text-sm text-white/45 line-clamp-2 leading-relaxed max-w-lg"
              dangerouslySetInnerHTML={{ __html: item.description }}
            />
          )}

          <div className="flex items-center space-x-2.5 pt-1">
            <button
              onClick={handlePlay}
              disabled={isCaughtUp || clicked}
              className="flex items-center space-x-2 bg-white text-black hover:bg-white/90 px-6 py-2.5 rounded-lg font-bold text-sm active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-all shadow-lg"
            >
              {clicked ? (
                <Loader2 size={16} className="animate-spin" />
              ) : isManga ? (
                <BookOpen size={16} />
              ) : (
                <Play fill="currentColor" size={16} />
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
              className="flex items-center space-x-2 bg-white/[0.08] hover:bg-white/[0.15] backdrop-blur-sm border border-white/10 text-white px-6 py-2.5 rounded-lg font-bold text-sm active:scale-95 cursor-pointer transition-all"
            >
              <Maximize size={16} />
              <span>Details</span>
            </button>
          </div>
        </div>

        {/* Right: Portrait cover (only when no landscape banner) */}
        {!hasBanner && (
          <div className="hidden md:block w-[160px] lg:w-[200px] aspect-[2/3] shrink-0 ml-8 rounded-xl overflow-hidden border border-white/10 shadow-[0_20px_60px_rgba(0,0,0,0.9)] transition-transform duration-500 hover:scale-105">
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
