"use client";

import { useState, useEffect, useRef, memo, useMemo } from "react";
import { Play, Maximize, BookOpen, Loader2, Clock, Tv } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { mediaApi, type MediaItem, API_BASE_ORIGIN } from "@/lib/api";

interface HeroProps {
  item?: MediaItem; // Backwards compatibility for single-item featured mode (e.g. MangaView)
  onSelect?: (item: MediaItem, action?: "play") => void;
  continueList?: MediaItem[];
  recentReleases?: MediaItem[];
  airingToday?: MediaItem[];
  fallbackList?: MediaItem[];
  onFocusChange?: (item: MediaItem | null) => void;
}

interface CommandCenterItem {
  item: MediaItem;
  type: "new_release" | "airing_today" | "continue" | "fallback";
  reasonText: string;
  badgeColor: string;
  playEpisode: string | null;
  unwatchedCount?: number;
}

// Live ticking countdown badge component
function AiringCountdown({ airingAt }: { airingAt: string }) {
  const [timeLeft, setTimeLeft] = useState("");

  useEffect(() => {
    const target = new Date(airingAt.endsWith("Z") ? airingAt : `${airingAt}Z`).getTime();

    const updateTimer = () => {
      const now = Date.now();
      const diff = target - now;

      if (diff <= 0) {
        setTimeLeft("Aired!");
        return;
      }

      const hours = Math.floor(diff / 3600000);
      const minutes = Math.floor((diff % 3600000) / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);

      const parts = [];
      if (hours > 0) parts.push(`${hours}h`);
      parts.push(`${minutes}m`);
      if (hours === 0) parts.push(`${seconds}s`);

      setTimeLeft(`in ${parts.join(" ")}`);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [airingAt]);

  return <span>{timeLeft}</span>;
}

const Hero = memo(function Hero({
  item: singleItem,
  onSelect,
  continueList = [],
  recentReleases = [],
  airingToday = [],
  fallbackList = [],
  onFocusChange,
}: HeroProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isIntersecting, setIsIntersecting] = useState(true);
  const [clicked, setClicked] = useState(false);
  const [showVideo, setShowVideo] = useState(false);
  const [isVideoVisible, setIsVideoVisible] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(0);

  const iframeRef = useRef<HTMLIFrameElement>(null);

  // 1. Build the priority queue
  const queue = useMemo(() => {
    // If a single item is passed directly, use a single-item featured queue (backwards compatibility)
    if (singleItem) {
      const isManga = singleItem.type === "MANGA";
      return [{
        item: singleItem,
        type: "fallback" as const,
        reasonText: singleItem.user_status ? (isManga ? "Resume reading" : "Resume watching") : "Featured choice",
        badgeColor: singleItem.user_status
          ? "bg-gradient-to-r from-accent to-accent-light shadow-md shadow-accent/20 text-white border-t border-white/10"
          : "bg-white/10 border border-white/10 text-white/70",
        playEpisode: String((singleItem.user_status?.progress || 0) + 1),
      }];
    }

    const seen = new Set<number>();
    const items: CommandCenterItem[] = [];

    // Priority 1: Unwatched releases (episodes behind)
    recentReleases.forEach((item) => {
      if (seen.has(item.id)) return;
      const progress = item.user_status?.progress || 0;
      const nextEp = item.next_airing?.episode;
      let currentReleased = 0;
      if (nextEp) {
        currentReleased = nextEp - 1;
      } else if (item.episodes) {
        currentReleased = item.episodes;
      }
      const unwatchedCount = currentReleased - progress;
      if (unwatchedCount > 0) {
        seen.add(item.id);
        items.push({
          item,
          type: "new_release",
          reasonText: `${unwatchedCount} new episode${unwatchedCount > 1 ? "s" : ""} available`,
          badgeColor: "bg-gradient-to-r from-pink-500 to-rose-500 shadow-md shadow-rose-500/20 text-white border-t border-white/10",
          playEpisode: String(progress + 1),
          unwatchedCount,
        });
      }
    });

    // Priority 2: Airing Today
    airingToday.forEach((item) => {
      if (seen.has(item.id)) return;
      const nextAiring = item.next_airing;
      if (nextAiring && nextAiring.airing_at) {
        seen.add(item.id);
        const airingTime = new Date(nextAiring.airing_at.endsWith("Z") ? nextAiring.airing_at : `${nextAiring.airing_at}Z`).getTime();
        const now = Date.now();
        const timeDiff = airingTime - now;

        if (timeDiff <= 0) {
          const progress = item.user_status?.progress || 0;
          const nextEpNum = nextAiring.episode;
          const isUnwatched = nextEpNum > progress;
          items.push({
            item,
            type: "airing_today",
            reasonText: `Episode ${nextEpNum} aired today`,
            badgeColor: "bg-gradient-to-r from-emerald-500 to-teal-500 shadow-md shadow-emerald-500/20 text-white border-t border-white/10",
            playEpisode: isUnwatched ? String(nextEpNum) : null,
          });
        } else {
          items.push({
            item,
            type: "airing_today",
            reasonText: `Episode ${nextAiring.episode} airing today`,
            badgeColor: "bg-gradient-to-r from-amber-500 to-orange-500 shadow-md shadow-amber-500/20 text-white border-t border-white/10",
            playEpisode: null,
          });
        }
      }
    });

    // Priority 3: Continue Watching Fallback
    continueList.forEach((item) => {
      if (seen.has(item.id)) return;
      seen.add(item.id);
      const progress = item.user_status?.progress || 0;
      items.push({
        item,
        type: "continue",
        reasonText: "Resume watching",
        badgeColor: "bg-gradient-to-r from-accent to-accent-light shadow-md shadow-accent/20 text-white border-t border-white/10",
        playEpisode: String(progress + 1),
      });
    });

    // Priority 4: Ultimate Fallback (Trending/Seasonal)
    if (items.length === 0) {
      fallbackList.forEach((item) => {
        if (seen.has(item.id)) return;
        seen.add(item.id);
        items.push({
          item,
          type: "fallback",
          reasonText: "Featured choice",
          badgeColor: "bg-white/10 border border-white/10 text-white/70",
          playEpisode: "1",
        });
      });
    }

    return items;
  }, [singleItem, continueList, recentReleases, airingToday, fallbackList]);

  // Adjust focused index if out of bounds
  const activeIndex = Math.min(focusedIndex, Math.max(0, queue.length - 1));
  const activeCcItem = queue[activeIndex] || null;
  const item = activeCcItem?.item || null;

  // Propagate focused item up to sync ambient background color
  useEffect(() => {
    if (onFocusChange) {
      onFocusChange(item);
    }
  }, [item, onFocusChange]);

  // 2. Query for configuration (e.g. video auto-play setting)
  const { data: config = null } = useQuery({
    queryKey: ["media-config", item?.id],
    queryFn: () => (item ? mediaApi.getConfig() : Promise.resolve(null)),
    staleTime: 60_000,
    enabled: !!item,
  });

  // 3. Intersection observer for video autoplay
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsIntersecting(entry.isIntersecting);
      },
      { threshold: 0.1 }
    );

    observer.observe(el);
    return () => {
      observer.unobserve(el);
    };
  }, []);

  // 4. Handle trailer autoplay timer
  useEffect(() => {
    setShowVideo(false);
    setIsVideoVisible(false);
    if (!item?.trailer?.id || item.trailer.site !== "youtube") return;

    const enabled = !!config?.stream?.autoplay_trailers;
    if (!enabled || !isIntersecting) return;

    const timer = setTimeout(() => {
      setShowVideo(true);
    }, 2500);

    return () => clearTimeout(timer);
  }, [item?.id, item?.trailer?.id, item?.trailer?.site, config?.stream?.autoplay_trailers, isIntersecting]);

  if (!item) return null;

  const title = item.title.english || item.title.romaji || "Unknown";
  const currentProgress = item.user_status?.progress || 0;
  const total = item.episodes || item.chapters || 0;
  const isManga = item.type === "MANGA";
  const hasBanner = !!item.banner_image;

  const latestAvailable = item.next_airing ? (item.next_airing.episode - 1) : total;
  const isFinished = total > 0 && currentProgress >= total;
  const isCaughtUp = !isFinished && latestAvailable > 0 && currentProgress >= latestAvailable;

  const handlePlay = () => {
    if (onSelect && item) {
      setClicked(true);
      // Play the prioritized episode resolved by the command center
      onSelect(item, "play");
      setTimeout(() => setClicked(false), 3000);
    }
  };

  // Determine button state and label
  const isAiringFuture = activeCcItem?.type === "airing_today" && !activeCcItem.playEpisode;
  const nextEpisodeToWatch = activeCcItem?.playEpisode;

  return (
    <div className="flex flex-col gap-4">
      {/* Hero card container */}
      <div ref={containerRef} className="relative h-[52vh] lg:h-[58vh] w-full overflow-hidden group -mx-6 lg:mx-0 lg:rounded-2xl hero-card-container forced-dark-container">
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

          {/* Muted auto-play trailer */}
          {showVideo && item.trailer?.id && item.trailer.site?.toLowerCase() === "youtube" && (
            <>
              <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <iframe
                  ref={iframeRef}
                  onLoad={() => {
                    setTimeout(() => {
                      setIsVideoVisible(true);
                    }, 600);
                  }}
                  src={`${API_BASE_ORIGIN}/api/actions/trailer/${item.trailer.id}`}
                  className={`absolute inset-[-15%] w-[130%] h-[130%] brightness-[0.45] pointer-events-none transition-opacity duration-1000 ${isVideoVisible ? "opacity-100" : "opacity-0"}`}
                  allow="autoplay; encrypted-media"
                  title="Airing Trailer"
                />
              </div>
              {/* Transparent overlay */}
              <div className="absolute inset-0 z-10 pointer-events-auto bg-transparent" />
            </>
          )}

          {/* Cinematic gradients */}
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/55 to-background/5" />
          <div className="absolute inset-0 bg-gradient-to-r from-background/75 via-background/15 to-transparent" />
        </div>

        {/* Content wrapper */}
        <div className="relative h-full flex flex-row items-end justify-between pb-8 lg:pb-12 px-6 lg:px-10 z-10 gap-6">
          {/* Left side: Info & Actions */}
          <div className="space-y-3 max-w-2xl">
            <div className="space-y-2">
              <div className="flex items-center flex-wrap gap-2">
                {/* Dynamically Styled Priority Badge */}
                <span className={`px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-widest flex items-center gap-1.5 shadow-lg ${activeCcItem?.badgeColor}`}>
                  {activeCcItem?.type === "new_release" && <Tv size={11} />}
                  {activeCcItem?.type === "airing_today" && <Clock size={11} />}
                  <span>{activeCcItem?.reasonText}</span>
                </span>

                {/* Show countdown timer if airing soon */}
                {activeCcItem?.type === "airing_today" && item.next_airing?.airing_at && isAiringFuture && (
                  <span className="px-2 py-0.5 bg-black/40 text-amber-400 border border-amber-500/25 rounded-md text-[10px] font-black uppercase tracking-widest font-mono">
                    <AiringCountdown airingAt={item.next_airing.airing_at} />
                  </span>
                )}

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

            {/* Actions */}
            <div className="flex items-center space-x-2.5 pt-1">
              <button
                onClick={handlePlay}
                disabled={isAiringFuture || clicked}
                className="flex items-center space-x-2 bg-white text-black hover:bg-white/90 px-6 py-2.5 rounded-lg font-bold text-sm active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-all shadow-lg"
              >
                {clicked ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : isAiringFuture ? (
                  <Clock size={16} />
                ) : isManga ? (
                  <BookOpen size={16} />
                ) : (
                  <Play fill="currentColor" size={16} />
                )}
                <span>
                  {clicked
                    ? "Loading..."
                    : isAiringFuture
                      ? "Airing Soon"
                      : isFinished
                        ? (isManga ? "Read Again" : "Re-watch")
                        : isCaughtUp
                          ? "Caught Up"
                          : nextEpisodeToWatch
                            ? (isManga ? `Read Chapter ${nextEpisodeToWatch}` : `Watch Episode ${nextEpisodeToWatch}`)
                            : (isManga ? "Read Now" : "Play Now")
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

          {/* Right side: Watchlist Command Center Queue Shelf */}
          {queue.length > 1 && (
            <div className="hidden md:flex flex-col w-72 lg:w-80 shrink-0 bg-black/40 border border-white/5 backdrop-blur-md rounded-2xl p-4 space-y-3 self-center max-h-[320px] overflow-y-auto scrollbar-hide">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-wider text-gray-500">
                  Up Next
                </span>
                <span className="text-[10px] px-2 py-0.5 bg-accent/20 text-accent font-bold rounded-md">
                  {queue.length} items
                </span>
              </div>
              <div className="space-y-2">
                {queue.map((ccItem, index) => {
                  const isFocused = index === activeIndex;
                  const ccTitle = ccItem.item.title.english || ccItem.item.title.romaji || "Unknown";
                  const isAiring = ccItem.type === "airing_today";

                  return (
                    <button
                      key={ccItem.item.id}
                      onClick={() => setFocusedIndex(index)}
                      className={`w-full flex items-center gap-3 p-2 rounded-xl text-left border transition-all duration-300 group cursor-pointer ${
                        isFocused
                          ? "bg-accent/10 border-accent/30 shadow-[0_0_15px_rgba(0,0,0,0.1)] shadow-accent/25"
                          : "bg-white/[0.02] border-white/[0.04] hover:bg-white/[0.06] hover:border-white/10"
                      }`}
                    >
                      <div className="relative shrink-0 w-9 h-12 rounded-lg overflow-hidden border border-white/5 bg-neutral-900">
                        <img
                          src={ccItem.item.cover_image.large}
                          alt={ccTitle}
                          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                        />
                      </div>
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <h4 className={`text-xs font-bold truncate transition-colors ${isFocused ? "text-accent" : "text-white group-hover:text-accent-light"}`}>
                          {ccTitle}
                        </h4>
                        <p className="text-[10px] text-gray-500 truncate flex items-center gap-1">
                          {isAiring ? (
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                          ) : ccItem.type === "new_release" ? (
                            <span className="w-1.5 h-1.5 rounded-full bg-pink-500 animate-pulse" />
                          ) : (
                            <span className="w-1.5 h-1.5 rounded-full bg-accent/70" />
                          )}
                          <span>{ccItem.reasonText}</span>
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Right side: Portrait cover fallback (displayed if only 1 item in queue) */}
          {queue.length === 1 && !hasBanner && (
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

      {/* Mobile Queue Shelf */}
      {queue.length > 1 && (
        <div className="flex md:hidden overflow-x-auto w-full gap-2 px-6 pb-4 pt-1 scrollbar-hide select-none">
          {queue.map((ccItem, index) => {
            const isFocused = index === activeIndex;
            const ccTitle = ccItem.item.title.english || ccItem.item.title.romaji || "Unknown";
            return (
              <button
                key={ccItem.item.id}
                onClick={() => setFocusedIndex(index)}
                className={`shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all ${
                  isFocused
                    ? "bg-accent/15 border-accent/30 text-accent font-bold"
                    : "bg-white/[0.03] border-white/[0.05] text-gray-400 hover:text-white"
                }`}
              >
                <img
                  src={ccItem.item.cover_image.large}
                  alt={ccTitle}
                  className="w-5 h-7 rounded object-cover"
                />
                <span className="max-w-[80px] truncate">{ccTitle}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
});

export default Hero;
