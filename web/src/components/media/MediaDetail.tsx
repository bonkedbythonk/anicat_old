"use client";

import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Play, Loader2, Star, Users, Calendar, Clock, Building2, Monitor, CheckCircle2, Bookmark, Pause, XCircle, Download, BookOpen, RotateCcw, ChevronDown, ChevronUp, MoreHorizontal } from "lucide-react";
import { mediaApi, type MediaItem, type Episode, type Character, type Review } from "@/lib/api";
import { dispatchRefresh, useRefreshTrigger } from "@/lib/events";
import { formatTime, formatRelativeTime } from "@/lib/date";
import EpisodeList from "./EpisodeList";

interface MediaDetailProps {
  item: MediaItem;
  onClose: () => void;
  initialAction?: "play";
  onRead?: (chapter: string) => void;
}

export default function MediaDetail({ item, onClose, initialAction, onRead }: MediaDetailProps) {
  const refreshKey = useRefreshTrigger();
  const [fullItem, setFullItem] = useState<MediaItem>(item);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [recommendations, setRecommendations] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);
  const [loadingEps, setLoadingEps] = useState(false);
  const [loadingChars, setLoadingChars] = useState(false);
  const [isPlayingNext, setIsPlayingNext] = useState(false);
  const [activeTab, setActiveTab] = useState<"episodes" | "characters" | "reviews" | "recommendations">("episodes");
  const [config, setConfig] = useState<any>(null);

  const isManga = item.type === "MANGA" || !!(item.format && ["MANGA", "ONE_SHOT", "NOVEL"].includes(item.format));

  useEffect(() => {
    async function loadDetails() {
      try {
        const [details, userConfig] = await Promise.all([
          mediaApi.getDetails(item.id),
          mediaApi.getConfig()
        ]);
        setFullItem(details);
        setConfig(userConfig);
      } catch (error) {
        console.error("Failed to load media details:", error);
      } finally {
        setLoading(false);
      }
    }
    loadDetails();
  }, [item.id, refreshKey]);

  useEffect(() => {
    if (activeTab === "episodes") {
      setLoadingEps(true);
      mediaApi.getEpisodes(item.id)
        .then(setEpisodes)
        .catch(err => console.error("Failed to load episodes:", err))
        .finally(() => setLoadingEps(false));
    } else if (activeTab === "characters" && characters.length === 0) {
      setLoadingChars(true);
      mediaApi.getCharacters(item.id)
        .then(res => setCharacters(res.characters))
        .catch(err => console.error("Failed to load characters:", err))
        .finally(() => setLoadingChars(false));
    } else if (activeTab === "reviews" && reviews.length === 0) {
      mediaApi.getReviews(item.id)
        .then(setReviews)
        .catch(err => console.error("Failed to load reviews:", err));
    } else if (activeTab === "recommendations" && recommendations.length === 0) {
      mediaApi.getRecommendations(item.id)
        .then(setRecommendations)
        .catch(err => console.error("Failed to load recommendations:", err));
    }
  }, [item.id, activeTab]);

  // Handle initial action (e.g. from Hero "Play Now" button)
  useEffect(() => {
    if (initialAction === "play") {
      handlePlayNext();
    }
  }, [initialAction, loading]);

  const isProcessingAction = useRef(false);

  const handlePlayNext = async () => {
    if (isPlayingNext || isProcessingAction.current) return;
    
    isProcessingAction.current = true;
    setIsPlayingNext(true);
    try {
      if (isManga) {
        // For manga, "Play Next" means read the next chapter
        const nextChapter = (fullItem.user_status?.progress || 0) + 1;
        if (onRead) onRead(nextChapter.toString());
      } else {
        await mediaApi.playNext(item.id);
        dispatchRefresh();
      }
    } catch (error) {
      console.error("Failed to play next:", error);
    } finally {
      setIsPlayingNext(false);
      // Keep locked for a short moment to prevent accidental double-clicks 
      // even after the request finished
      setTimeout(() => {
        isProcessingAction.current = false;
      }, 500);
    }
  };

  const handleUnwatch = async () => {
    if (confirm(`Are you sure you want to remove ${item.title.english || item.title.romaji} from your list?`)) {
      try {
        await mediaApi.updateStatus(item.id, "REPEATING", undefined, 0); // Hack to clear
        dispatchRefresh();
        onClose();
      } catch (error) {
        console.error("Failed to unwatch:", error);
      }
    }
  };

  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const handleToggleWatchlist = async () => {
    if (isUpdatingStatus) return;
    setIsUpdatingStatus(true);
    
    const isPlanning = fullItem.user_status?.status === 'PLANNING';
    const newStatus = isPlanning ? 'REPEATING' : 'PLANNING'; // REPEATING + 0 progress = hacky way to remove/reset
    
    try {
      await mediaApi.updateStatus(item.id, newStatus);
      dispatchRefresh();
    } catch (error) {
      console.error("Failed to toggle watchlist:", error);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const title = fullItem.title.english || fullItem.title.romaji;
  const banner = fullItem.banner_image || fullItem.cover_image.large;

  return (
    <div className="fixed inset-0 z-[150] flex justify-end overflow-hidden">
      {/* Backdrop */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose} 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm" 
      />
      
      {/* Sidebar Drawer */}
      <motion.div 
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ duration: 0.3, ease: [0.32, 0.72, 0, 1] }}
        style={{ willChange: "transform" }}
        className="relative w-full max-w-2xl h-full bg-[#0c0c0c] border-l border-white/10 shadow-[-20px_0_50px_rgba(0,0,0,0.5)] flex flex-col"
      >
        {/* Close Button */}
        <button 
          onClick={onClose} 
          className="absolute top-6 right-6 z-50 p-2 bg-black/40 hover:bg-black/60 text-white/70 hover:text-white rounded-full backdrop-blur-sm transition-all border border-white/5 active:scale-90"
        >
          <X size={20} />
        </button>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto scrollbar-hide">
          {/* Header Banner */}
          <div className="relative h-72 w-full flex-shrink-0">
             <div className="absolute inset-0 bg-gradient-to-t from-[#0c0c0c] via-transparent to-transparent z-[1]" />
             <img src={banner} alt={title} className="w-full h-full object-cover" />
             
             <div className="absolute bottom-6 left-8 right-8 z-[2] space-y-3">
                <div className="flex items-center space-x-2">
                  <div className="px-2 py-1 bg-accent rounded text-[10px] font-black uppercase tracking-widest text-white shadow-lg shadow-accent/20">
                    {fullItem.format || (isManga ? "MANGA" : "ANIME")}
                  </div>
                  {fullItem.average_score && (
                    <div className="flex items-center space-x-1 px-2 py-1 bg-black/40 backdrop-blur-md rounded text-[10px] font-bold text-yellow-400 border border-white/5">
                      <Star size={10} fill="currentColor" />
                      <span>{fullItem.average_score}%</span>
                    </div>
                  )}
                </div>
                <h2 className="text-3xl lg:text-4xl font-extrabold text-white leading-tight drop-shadow-lg">{title}</h2>
             </div>
          </div>

          <div className="p-8 lg:p-10 space-y-8">
            {/* Quick Actions & Meta */}
            <div className="flex flex-col space-y-4">
              <div className="flex items-center space-x-3">
                {(() => {
                  const currentProgress = fullItem.user_status?.progress || 0;
                  const total = fullItem.episodes || fullItem.chapters || 0;
                  const latestAvailable = episodes.length > 0 ? Math.max(...episodes.map(e => Number(e.number))) : total;
                  const nextEpisode = (fullItem.user_status?.progress || 0) + 1;
                  const isFinished = total > 0 && currentProgress >= total;
                  const isCaughtUp = !isFinished && latestAvailable > 0 && currentProgress >= latestAvailable;

                  return (
                    <button
                      onClick={handlePlayNext}
                      disabled={isPlayingNext || isCaughtUp}
                      className="flex-1 flex items-center justify-center space-x-3 py-3.5 bg-accent hover:bg-accent-light text-white font-extrabold text-sm rounded-2xl transition-all shadow-xl shadow-accent/20 active:scale-95 disabled:opacity-50 disabled:bg-white/[0.05] disabled:text-gray-500 disabled:shadow-none"
                    >
                      {isPlayingNext ? (
                        <Loader2 className="animate-spin" size={18} />
                      ) : (
                        <>
                          {isManga ? <BookOpen size={18} /> : <Play size={18} fill="currentColor" />}
                          <span>
                            {isFinished ? "Completed" : isCaughtUp ? "Caught Up" : `${isManga ? 'Read' : 'Continue'} Episode ${nextEpisode}`}
                          </span>
                        </>
                      )}
                    </button>
                  );
                })()}
                
                <button 
                  onClick={handleToggleWatchlist}
                  disabled={isUpdatingStatus}
                  title={fullItem.user_status?.status === 'PLANNING' ? "Remove from Watchlist" : "Add to Watchlist"}
                  className={`p-3.5 rounded-2xl transition-all border active:scale-95 ${
                    fullItem.user_status?.status === 'PLANNING' 
                    ? "bg-accent/20 border-accent/30 text-accent" 
                    : "bg-white/[0.05] border-white/5 text-white/70 hover:text-white hover:bg-white/[0.1]"
                  }`}
                >
                  {isUpdatingStatus ? <Loader2 size={22} className="animate-spin" /> : <Bookmark size={22} fill={fullItem.user_status?.status === 'PLANNING' ? "currentColor" : "none"} />}
                </button>

                <button 
                  title="More actions"
                  className="p-3.5 bg-white/[0.05] hover:bg-white/[0.1] text-white/70 hover:text-white rounded-2xl transition-all border border-white/5 active:scale-95"
                >
                  <MoreHorizontal size={22} />
                </button>
              </div>

              <div className="flex items-center justify-between px-2">
                <div className="flex items-center space-x-6">
                  <div className="flex flex-col">
                    <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Progress</span>
                    <span className="text-base font-bold text-white">
                      {fullItem.user_status?.progress || 0} <span className="text-gray-600 font-medium">/</span> {fullItem.episodes || fullItem.chapters || '?'}
                    </span>
                  </div>
                  <div className="h-8 w-px bg-white/10" />
                  <div className="flex flex-col">
                    <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Score</span>
                    <span className="text-base font-bold text-white">
                      {(fullItem.user_status?.score && fullItem.user_status.score > 0) ? fullItem.user_status.score : '-'} <span className={`text-gray-600 font-medium ${!(fullItem.user_status?.score && fullItem.user_status.score > 0) ? 'hidden' : ''}`}>/ 10</span>
                    </span>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                   <div className={`w-2 h-2 rounded-full ${fullItem.status === 'RELEASING' ? 'bg-green-500 animate-pulse' : 'bg-gray-600'}`} />
                   <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">{fullItem.status?.replace('_', ' ')}</span>
                </div>
              </div>
            </div>

            {/* Genres */}
            {fullItem.genres && (
              <div className="flex flex-wrap gap-2">
                {fullItem.genres.map(g => (
                  <span key={g} className="px-3 py-1 bg-white/[0.04] border border-white/5 rounded-lg text-[11px] font-bold text-gray-400">{g}</span>
                ))}
              </div>
            )}

            {/* Synopsis with Read More */}
            {fullItem.description && (
              <div className="space-y-3 p-6 rounded-2xl bg-white/[0.02] border border-white/[0.04]">
                <h3 className="text-[10px] font-black text-accent uppercase tracking-[0.2em]">Synopsis</h3>
                <div className="relative">
                  <p 
                    className={`text-sm text-gray-400 leading-relaxed transition-all duration-300 ${!isExpanded ? "line-clamp-4" : ""}`}
                    dangerouslySetInnerHTML={{ __html: fullItem.description }} 
                  />
                  {!isExpanded && fullItem.description.length > 200 && (
                    <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-[#121212] to-transparent pointer-events-none" />
                  )}
                </div>
                {fullItem.description.length > 200 && (
                  <button 
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="flex items-center space-x-1.5 text-[11px] font-bold text-white/50 hover:text-white transition-colors group"
                  >
                    <span>{isExpanded ? "Show Less" : "Read Full Synopsis"}</span>
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} className="group-hover:translate-y-0.5 transition-transform" />}
                  </button>
                )}
              </div>
            )}

            {/* Next Episode Banner */}
            {!isManga && fullItem.next_airing && (
              <div className="bg-accent/5 border border-accent/10 rounded-2xl p-5 flex items-center space-x-4">
                <div className="p-3 bg-accent/10 rounded-xl text-accent shadow-inner"><Calendar size={20} /></div>
                <div>
                  <div className="text-[10px] font-bold text-accent uppercase tracking-widest">Next Episode</div>
                  <div className="text-base text-gray-200 font-bold">
                    Episode {fullItem.next_airing.episode} <span className="text-gray-500 font-medium text-sm">airing {formatRelativeTime(new Date(fullItem.next_airing.airing_at + "Z"))}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Tabs */}
            <div className="space-y-6">
              <div className="flex space-x-1 p-1 bg-white/[0.03] border border-white/[0.06] rounded-2xl">
                {(["episodes", "characters", "reviews", "recommendations"] as const).map((tab) => (
                  <button 
                    key={tab} 
                    onClick={() => setActiveTab(tab)} 
                    className={`flex-1 py-2.5 text-[10px] font-bold uppercase tracking-wider rounded-xl transition-all ${activeTab === tab ? "bg-accent text-white shadow-lg" : "text-gray-500 hover:text-white"}`}
                  >
                    {tab === "episodes" ? (isManga ? "Chapters" : "Episodes") : tab}
                  </button>
                ))}
              </div>

              <div className="animate-fade-in min-h-[300px]">
                {activeTab === "episodes" && <EpisodeList mediaId={item.id} episodes={episodes} loading={loadingEps} progress={fullItem.user_status?.progress} isManga={isManga} onRead={onRead} onUnwatch={handleUnwatch} />}
                {activeTab === "characters" && (
                  <div className="grid grid-cols-2 gap-4">
                    {loadingChars ? (
                      <div className="col-span-2 py-20 flex justify-center">
                        <Loader2 className="animate-spin text-accent" size={24} />
                      </div>
                    ) : characters.length > 0 ? (
                      characters.map(char => (
                        <div key={char.id || char.name.full} className="flex items-center space-x-3 p-3 bg-white/[0.02] border border-white/[0.04] rounded-2xl hover:bg-white/[0.04] transition-colors group">
                          {char.image?.large && <img src={char.image.large} alt={char.name.full} className="w-14 h-14 rounded-xl object-cover shadow-lg" />}
                          <div className="min-w-0">
                            <div className="text-[13px] font-bold text-white group-hover:text-accent transition-colors truncate">{char.name.full}</div>
                            {char.description && <div className="text-[10px] text-gray-500 line-clamp-1">{char.description.replace(/<[^>]*>?/gm, '')}</div>}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="col-span-2 py-20 text-center text-gray-500 text-xs font-bold">No character data available.</div>
                    )}
                  </div>
                )}
                {activeTab === "reviews" && (
                  <div className="space-y-4">
                    {reviews.length > 0 ? (
                      reviews.map((rev, idx) => (
                        <div key={idx} className="p-5 bg-white/[0.02] border border-white/[0.04] rounded-2xl space-y-3">
                           {rev.summary && <div className="text-xs font-black text-gray-300 tracking-wide uppercase italic leading-snug">"{rev.summary}"</div>}
                           <div className="text-xs text-gray-400 leading-relaxed" dangerouslySetInnerHTML={{ __html: rev.body.substring(0, 300) + '...' }} />
                        </div>
                      ))
                    ) : (
                      <div className="py-20 text-center text-gray-500 text-xs font-bold">No reviews found.</div>
                    )}
                  </div>
                )}
                {activeTab === "recommendations" && (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    {recommendations.map(rec => (
                      <button key={rec.id} onClick={() => mediaApi.getDetails(rec.id).then(setFullItem)} className="group space-y-2 text-left">
                        <div className="aspect-[2/3] rounded-xl overflow-hidden border border-white/10 shadow-lg">
                          <img src={rec.cover_image.large} className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" />
                        </div>
                        <div className="text-[11px] font-bold text-gray-400 line-clamp-1 group-hover:text-white transition-colors">{rec.title.english || rec.title.romaji}</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
