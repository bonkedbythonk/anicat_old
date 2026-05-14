"use client";

import { useEffect, useState } from "react";
import { X, Play, Loader2, Star, Users, Calendar, Clock, Building2, Monitor, CheckCircle2, Bookmark, Pause, XCircle, Download, BookOpen, RotateCcw } from "lucide-react";
import { mediaApi, type MediaItem, type Episode, type Character, type Review } from "@/lib/api";
import { dispatchRefresh, useRefreshTrigger } from "@/lib/events";
import { formatTime, formatRelativeTime } from "@/lib/date";
import EpisodeList from "./EpisodeList";
import MangaReader from "./MangaReader";

interface MediaDetailProps {
  item: MediaItem;
  onClose: () => void;
}

export default function MediaDetail({ item, onClose }: MediaDetailProps) {
  const refreshKey = useRefreshTrigger();
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [recommendations, setRecommendations] = useState<MediaItem[]>([]);
  const [activeTab, setActiveTab] = useState<"episodes" | "characters" | "reviews" | "recommendations">("episodes");
  const isManga = item.type === "MANGA";
  const [loadingEps, setLoadingEps] = useState(true);
  const [loadingChars, setLoadingChars] = useState(false);
  const [loadingReviews, setLoadingReviews] = useState(false);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [fullItem, setFullItem] = useState<MediaItem>(item);
  const [rating, setRating] = useState(item.user_status?.score || 0);
  const [status, setStatus] = useState(item.user_status?.status || "");
  const [isUpdatingRating, setIsUpdatingRating] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [hasFetchedChars, setHasFetchedChars] = useState(false);
  const [hasFetchedReviews, setHasFetchedReviews] = useState(false);
  const [hasFetchedRecs, setHasFetchedRecs] = useState(false);
  const [config, setConfig] = useState<any>(null);
  const [isPlayingNext, setIsPlayingNext] = useState(false);
  const [isDownloadingRemaining, setIsDownloadingRemaining] = useState(false);
  const [readingChapter, setReadingChapter] = useState<string | null>(null);

  const title = fullItem.title.english || fullItem.title.romaji || "Unknown";

  useEffect(() => {
    mediaApi.getConfig().then(setConfig).catch(console.error);
  }, []);

  useEffect(() => {
    setFullItem(item);
    setEpisodes([]);
    setCharacters([]);
    setReviews([]);
    setRecommendations([]);
    setLoadingEps(true);
    setLoadingChars(false);
    setLoadingReviews(false);
    setLoadingRecs(false);
    setHasFetchedChars(false);
    setHasFetchedReviews(false);
    setHasFetchedRecs(false);
    setActiveTab("episodes");
    setRating(item.user_status?.score || 0);
    setStatus(item.user_status?.status || "");

    mediaApi.getDetails(item.id)
      .then(data => {
        setFullItem(data);
        if (data.user_status?.score !== undefined) setRating(data.user_status.score);
        if (data.user_status?.status) setStatus(data.user_status.status);
      })
      .catch(console.error);

    mediaApi.getEpisodes(item.id)
      .then(data => setEpisodes(data || []))
      .catch(err => {
        console.error("Failed to load episodes:", err);
        setEpisodes([]);
      })
      .finally(() => setLoadingEps(false));
  }, [item.id, refreshKey]);

  useEffect(() => {
    if (activeTab === "characters" && !hasFetchedChars) {
      setLoadingChars(true);
      setHasFetchedChars(true);
      mediaApi.getCharacters(item.id)
        .then(data => setCharacters(data.characters || []))
        .catch(console.error)
        .finally(() => setLoadingChars(false));
    } else if (activeTab === "reviews" && !hasFetchedReviews) {
      setLoadingReviews(true);
      setHasFetchedReviews(true);
      mediaApi.getReviews(item.id)
        .then(setReviews)
        .catch(console.error)
        .finally(() => setLoadingReviews(false));
    } else if (activeTab === "recommendations" && !hasFetchedRecs) {
      setLoadingRecs(true);
      setHasFetchedRecs(true);
      mediaApi.getRecommendations(item.id)
        .then(setRecommendations)
        .catch(console.error)
        .finally(() => setLoadingRecs(false));
    }
  }, [activeTab, item.id, characters.length, reviews.length, recommendations.length]);

  const handleRate = async (score: number) => {
    setIsUpdatingRating(true);
    try {
      await mediaApi.updateStatus(item.id, undefined, score);
      setRating(score);
      dispatchRefresh();
    } catch (err) {
      console.error("Failed to update rating:", err);
    } finally {
      setIsUpdatingRating(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    setIsUpdatingStatus(true);
    try {
      await mediaApi.updateStatus(item.id, newStatus);
      setStatus(newStatus);
      dispatchRefresh();
    } catch (err) {
      console.error("Failed to update status:", err);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handlePlayNext = async () => {
    const nextEp = (fullItem.user_status?.progress || 0) + 1;
    if (isManga) {
      setReadingChapter(String(nextEp));
      return;
    }

    // Optimistic Update
    setFullItem(prev => ({
      ...prev,
      user_status: prev.user_status ? {
        ...prev.user_status,
        progress: nextEp
      } : {
        status: "watching",
        progress: nextEp,
        score: 0
      }
    }));

    setIsPlayingNext(true);
    try {
      await mediaApi.play(item.id, String(nextEp));
      dispatchRefresh();
    } catch (error) {
      console.error("Failed to play:", error);
    } finally {
      setIsPlayingNext(false);
    }
  };

  const handleUnwatch = async (epNum: string) => {
    const num = parseInt(epNum);
    if (isNaN(num)) return;
    
    // Set progress to num - 1
    const newProgress = Math.max(0, num - 1);
    
    // Optimistic Update: Update the local state immediately
    setFullItem(prev => ({
      ...prev,
      user_status: prev.user_status ? {
        ...prev.user_status,
        progress: newProgress
      } : {
        status: "watching",
        progress: newProgress,
        score: 0
      }
    }));

    setIsUpdatingStatus(true);
    try {
      await mediaApi.updateStatus(item.id, undefined, undefined, newProgress);
      dispatchRefresh();
    } catch (error) {
      console.error("Failed to unwatch:", error);
      // Revert if it fails? (optional, usually not needed for simple progress)
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleDownloadRemaining = async () => {
    const remaining = episodes.filter(ep => ep.download_status === "not_downloaded");
    if (remaining.length === 0) return;
    setIsDownloadingRemaining(true);
    try {
      await mediaApi.addToQueue(item.id, remaining.map(ep => String(ep.number)));
    } catch (error) {
      console.error("Failed to queue remaining:", error);
    } finally {
      setIsDownloadingRemaining(false);
    }
  };

  const canDownload = fullItem.status && !fullItem.status.includes("AIRING") && !fullItem.status.includes("NOT_YET_AIRED");
  const remainingEpsCount = episodes.filter(ep => ep.download_status === "not_downloaded").length;

  const STATUS_OPTIONS = [
    { value: "watching", label: "Watching", icon: Monitor },
    { value: "completed", label: "Completed", icon: CheckCircle2 },
    { value: "planning", label: "Planning", icon: Bookmark },
    { value: "paused", label: "Paused", icon: Pause },
    { value: "dropped", label: "Dropped", icon: XCircle },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

      <div className="relative ml-auto w-full max-w-2xl bg-surface border-l border-white/[0.06] overflow-y-auto animate-slide-in-right">
        {/* Banner */}
        <div className="relative h-80 lg:h-96 overflow-hidden shrink-0">
          <img
            src={fullItem.banner_image || fullItem.cover_image.large}
            alt={title}
            className="absolute inset-0 w-full h-full object-cover brightness-[0.35]"
          />
          <div className="absolute inset-0 hero-gradient" />
          <div className="absolute inset-0 bg-gradient-to-r from-surface/60 to-transparent" />

          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 rounded-full bg-black/50 hover:bg-white/10 text-white transition-colors z-10"
          >
            <X size={20} />
          </button>

          <div className="absolute bottom-8 left-6 right-6 z-10 space-y-5">
            <div className="flex items-end space-x-5">
              <div className="w-28 h-40 rounded-lg overflow-hidden border border-white/10 shrink-0 shadow-2xl hidden sm:block">
                <img src={fullItem.cover_image.large} alt={title} className="w-full h-full object-cover" />
              </div>
              <div className="space-y-2 min-w-0 flex-1">
                <div className="flex items-center space-x-2 text-xs font-semibold text-gray-300">
                  <span className="text-accent">{fullItem.format || "TV"}</span>
                  <span className="text-gray-600">•</span>
                  <span>{fullItem.status}</span>
                  {fullItem.episodes && (
                    <><span className="text-gray-600">•</span><span>{fullItem.episodes} {isManga ? "chs" : "eps"}</span></>
                  )}
                  {isManga && fullItem.chapters && !fullItem.episodes && (
                    <><span className="text-gray-600">•</span><span>{fullItem.chapters} chs</span></>
                  )}
                  {fullItem.average_score && (
                    <><span className="text-gray-600">•</span><div className="flex items-center text-yellow-400"><Star size={10} fill="currentColor" className="mr-1" /><span>{fullItem.average_score}%</span></div></>
                  )}
                </div>
                <h2 className="text-2xl lg:text-3xl font-extrabold text-white leading-tight line-clamp-2">{title}</h2>
                {fullItem.genres && (
                  <div className="flex flex-wrap gap-1.5">
                    {fullItem.genres.slice(0, 4).map(g => (
                      <span key={g} className="px-2 py-0.5 bg-white/[0.06] rounded-md text-[10px] font-semibold text-gray-400">{g}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-col space-y-3">
              <div className="flex items-center space-x-2">
                <button
                  onClick={handlePlayNext}
                  disabled={isPlayingNext}
                  className="flex-1 flex items-center justify-center space-x-2 py-2.5 bg-accent hover:bg-accent-light text-white font-extrabold text-sm rounded-xl transition-all shadow-lg shadow-accent/20 active:scale-95 disabled:opacity-50"
                >
                  {isPlayingNext ? <Loader2 size={16} className="animate-spin" /> : (isManga ? <BookOpen size={16} /> : <Play size={16} fill="currentColor" />)}
                  <span>{isPlayingNext ? "Starting..." : fullItem.user_status?.progress ? `Continue ${isManga ? 'Chapter' : 'Episode'} ${fullItem.user_status.progress + 1}` : (isManga ? "Read Now" : "Play Now")}</span>
                </button>
                {canDownload && remainingEpsCount > 0 && (
                  <button
                    onClick={handleDownloadRemaining}
                    disabled={isDownloadingRemaining}
                    className="flex items-center justify-center space-x-2 px-4 py-2.5 bg-white/[0.1] hover:bg-white/[0.15] text-white font-bold text-sm rounded-xl transition-all active:scale-95 disabled:opacity-50"
                  >
                    {isDownloadingRemaining ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                    <span>Download {remainingEpsCount} {isManga ? "chs" : "eps"}</span>
                  </button>
                )}
              </div>

              <div className="flex items-center justify-between bg-black/40 backdrop-blur-md border border-white/10 rounded-xl p-2">
                <div className="flex items-center space-x-1">
                  {STATUS_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      disabled={isUpdatingStatus}
                      onClick={() => handleStatusChange(opt.value)}
                      title={opt.label}
                      className={`p-2 rounded-lg transition-all ${status === opt.value ? "bg-accent/20 text-accent" : "text-gray-500 hover:text-white hover:bg-white/5"}`}
                    >
                      {isUpdatingStatus && status === opt.value ? <Loader2 size={14} className="animate-spin" /> : <opt.icon size={14} />}
                    </button>
                  ))}
                </div>
                <div className="h-4 w-px bg-white/10 mx-2" />
                <div className="flex items-center space-x-1 group/rating">
                  {[...Array(5)].map((_, i) => (
                    <button key={i} disabled={isUpdatingRating} onClick={() => handleRate((i + 1) * 2)} className="transition-all hover:scale-110">
                      <Star size={14} fill={i < Math.floor((rating > 10 ? rating / 10 : rating) / 2) ? "#facc15" : "transparent"} className={i < Math.floor((rating > 10 ? rating / 10 : rating) / 2) ? "text-yellow-400" : "text-gray-600"} />
                    </button>
                  ))}
                  <span className="text-[10px] font-bold text-gray-400 ml-1 min-w-[2rem] text-center">{rating > 0 ? `${rating}/10` : "Rate"}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-4 border-y border-white/[0.06]">
            {!isManga && fullItem.studios?.[0] && (
              <div className="space-y-1">
                <div className="flex items-center text-gray-500 space-x-1.5"><Building2 size={12} /><span className="text-[10px] font-bold uppercase tracking-wider">Studio</span></div>
                <div className="text-xs text-gray-300 font-medium truncate">{fullItem.studios.find(s => s.isAnimationStudio)?.name || fullItem.studios[0].name}</div>
              </div>
            )}
            {!isManga && (
              <div className="space-y-1">
                <div className="flex items-center text-gray-500 space-x-1.5"><Calendar size={12} /><span className="text-[10px] font-bold uppercase tracking-wider">Season</span></div>
                <div className="text-xs text-gray-300 font-medium">{fullItem.season} {fullItem.seasonYear}</div>
              </div>
            )}
            <div className="space-y-1">
              <div className="flex items-center text-gray-500 space-x-1.5"><Users size={12} /><span className="text-[10px] font-bold uppercase tracking-wider">Popularity</span></div>
              <div className="text-xs text-gray-300 font-medium">{fullItem.popularity?.toLocaleString()}</div>
            </div>
            {!isManga && (
              <div className="space-y-1">
                <div className="flex items-center text-gray-500 space-x-1.5"><Clock size={12} /><span className="text-[10px] font-bold uppercase tracking-wider">Duration</span></div>
                <div className="text-xs text-gray-300 font-medium">{fullItem.duration}m</div>
              </div>
            )}
            <div className="space-y-1">
              <div className="flex items-center text-gray-500 space-x-1.5">
                <CheckCircle2 size={12} />
                <span className="text-[10px] font-bold uppercase tracking-wider">Progress</span>
                {fullItem.user_status?.progress ? (
                  <div className="flex items-center space-x-1">
                    <button 
                      onClick={() => handleUnwatch(String(fullItem.user_status?.progress))}
                      className="p-0.5 hover:bg-white/10 rounded text-gray-500 hover:text-red-500 transition-colors"
                      title={isManga ? "Undo last chapter" : "Undo last episode"}
                    >
                      <RotateCcw size={10} />
                    </button>
                    <button 
                      onClick={() => {
                        if (confirm(`Are you sure you want to reset all progress for ${title}?`)) {
                          handleUnwatch("1"); // Sets to 0
                        }
                      }}
                      className="p-0.5 hover:bg-white/10 rounded text-gray-500 hover:text-red-500 transition-colors"
                      title={isManga ? "Reset all chapters" : "Reset all episodes"}
                    >
                      <XCircle size={10} />
                    </button>
                  </div>
                ) : null}
              </div>
              <div className="text-xs text-gray-300 font-medium">{fullItem.user_status?.progress || 0} / {fullItem.episodes || fullItem.chapters || "?"}</div>
            </div>
          </div>

          {!isManga && fullItem.next_airing && (
            <div className="bg-accent/5 border border-accent/10 rounded-xl p-4 flex items-center space-x-3">
              <div className="p-2 bg-accent/10 rounded-lg text-accent"><Calendar size={18} /></div>
              <div>
                <div className="text-[10px] font-bold text-accent uppercase tracking-widest">Next Episode</div>
                <div className="text-sm text-gray-200 font-semibold">
                  Episode {fullItem.next_airing.episode} airing {formatRelativeTime(new Date(fullItem.next_airing.airing_at + "Z"))} 
                  <span className="text-gray-500 text-xs ml-2">
                    ({formatTime(new Date(fullItem.next_airing.airing_at + "Z"), config?.general?.time_format || '24h')})
                  </span>
                </div>
              </div>
            </div>
          )}

          {fullItem.description && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Synopsis</h3>
              <p className="text-sm text-gray-400 leading-relaxed max-h-48 overflow-y-auto scrollbar-hide" dangerouslySetInnerHTML={{ __html: fullItem.description }} />
            </div>
          )}

          <div className="flex space-x-1 p-1 bg-white/[0.03] border border-white/[0.06] rounded-xl">
            {(["episodes", "characters", "reviews", "recommendations"] as const).map((tab) => (
              <button 
                key={tab} 
                onClick={() => setActiveTab(tab)} 
                className={`flex-1 py-2 text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all ${activeTab === tab ? "bg-accent text-white shadow-lg" : "text-gray-500 hover:text-white"}`}
              >
                {tab === "episodes" ? (isManga ? "Chapters" : "Episodes") : tab}
              </button>
            ))}
          </div>

          <div className="animate-fade-in">
            {activeTab === "episodes" && <EpisodeList mediaId={item.id} episodes={episodes} loading={loadingEps} progress={fullItem.user_status?.progress} isManga={isManga} onRead={setReadingChapter} onUnwatch={handleUnwatch} />}
            {activeTab === "characters" && (
              <div className="grid grid-cols-2 gap-3">
                {characters.map(char => (
                  <div key={char.id} className="flex items-center space-x-3 p-2 bg-white/[0.02] border border-white/[0.04] rounded-xl">
                    {char.image?.large && <img src={char.image.large} alt={char.name.full} className="w-12 h-12 rounded-lg object-cover" />}
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-white truncate">{char.name.full}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {activeTab === "reviews" && (
              <div className="space-y-4">
                {reviews.map((rev, idx) => (
                  <div key={idx} className="p-4 bg-white/[0.02] border border-white/[0.04] rounded-xl space-y-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-accent">{rev.user.name}</span>
                    </div>
                    <p className="text-[11px] text-gray-500 line-clamp-4">{rev.body}</p>
                  </div>
                ))}
              </div>
            )}
            {activeTab === "recommendations" && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {recommendations.map(rec => (
                  <button key={rec.id} onClick={() => mediaApi.getDetails(rec.id).then(setFullItem)} className="group space-y-2 text-left">
                    <div className="aspect-[2/3] rounded-lg overflow-hidden border border-white/10">
                      <img src={rec.cover_image.large} className="w-full h-full object-cover transition-transform group-hover:scale-105" />
                    </div>
                    <div className="text-[10px] font-bold text-gray-400 line-clamp-1 group-hover:text-white">{rec.title.english || rec.title.romaji}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {readingChapter && (
        <MangaReader 
          mediaId={item.id} 
          chapterNumber={readingChapter} 
          onClose={() => {
            setReadingChapter(null);
            dispatchRefresh();
          }} 
          onProgressUpdate={async (num) => {
            try {
              await mediaApi.updateStatus(item.id, undefined, undefined, parseInt(num));
              dispatchRefresh();
            } catch (error) {
              console.error("Failed to update manga progress:", error);
            }
          }}
        />
      )}
    </div>
  );
}
