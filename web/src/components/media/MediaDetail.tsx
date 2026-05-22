"use client";

import { useEffect, useState, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { X, Play, Loader2, Star, Users, Calendar, Clock, Building2, Monitor, CheckCircle2, Bookmark, Pause, XCircle, Download, BookOpen, RotateCcw, ChevronDown, ChevronUp, MoreHorizontal, Trash2, Edit2, Check } from "lucide-react";
import { mediaApi, type MediaItem, type Episode, type Character, type Review } from "@/lib/api";
import { dispatchRefresh } from "@/lib/events";
import { formatTime, formatRelativeTime } from "@/lib/date";
import { useAmbientColor } from "@/lib/useAmbientColor";
import { useProgressEditor } from "@/lib/useProgressEditor";
import { useAppState } from "@/lib/AppStateContext";
import EpisodeList from "./EpisodeList";

interface MediaDetailProps {
  item: MediaItem;
  onClose: () => void;
  initialAction?: "play";
  onRead?: (chapter: string) => void;
  onPlayEpisode?: (episodeNum: string) => void;
}

type DetailConfig = {
  stream?: {
    player_type?: "embedded" | "external";
  };
};

export default function MediaDetail({ item, onClose, initialAction, onRead, onPlayEpisode }: MediaDetailProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isPlayingNext, setIsPlayingNext] = useState(false);
  const [activeTab, setActiveTab] = useState<"episodes" | "characters" | "reviews" | "recommendations">("episodes");

  // Initial detail load via React Query
  const {
    data: fullItem = item,
    isLoading: loading,
  } = useQuery({
    queryKey: ["media-detail", item.id],
    queryFn: async () => {
      const details = await mediaApi.getDetails(item.id);
      return details;
    },
    staleTime: 60_000,
  });

  const { data: config = null } = useQuery<DetailConfig | null>({
    queryKey: ["media-config", item.id],
    queryFn: async () => {
      const userConfig = await mediaApi.getConfig();
      return userConfig;
    },
    staleTime: 60_000,
  });

  // Derived values (computed from state/props, must precede hooks that consume them)
  const isManga = item.type === "MANGA" || !!(item.format && ["MANGA", "ONE_SHOT", "NOVEL"].includes(item.format));
  const banner = fullItem.banner_image || fullItem.cover_image?.large || item.banner_image || item.cover_image?.large;
  const normalizedUserStatus = fullItem.user_status?.status?.toLowerCase() || item.user_status?.status?.toLowerCase();
  const isPlanning = normalizedUserStatus === "planning";

  // Extracted hooks
  const ambientColor = useAmbientColor(banner);
  const progressEditor = useProgressEditor();

  // Tab data loaded via React Query — cached, deduped, refetched on tab switch
  const {
    data: episodes = [],
    isLoading: loadingEps,
  } = useQuery({
    queryKey: ["media-episodes", item.id],
    queryFn: () => mediaApi.getEpisodes(item.id),
    staleTime: 60_000,
  });

  const {
    data: characters = [],
    isLoading: loadingChars,
  } = useQuery({
    queryKey: ["media-characters", item.id],
    queryFn: async () => {
      const res = await mediaApi.getCharacters(item.id);
      return res.characters ?? [];
    },
    staleTime: 60_000,
  });

  const {
    data: reviews = [],
  } = useQuery({
    queryKey: ["media-reviews", item.id],
    queryFn: () => mediaApi.getReviews(item.id),
    staleTime: 60_000,
  });

  const {
    data: recommendations = [],
  } = useQuery({
    queryKey: ["media-recommendations", item.id],
    queryFn: () => mediaApi.getRecommendations(item.id),
    staleTime: 60_000,
  });

  const [hasTriggeredInitial, setHasTriggeredInitial] = useState(false);

  // Handle initial action (e.g. from Hero "Play Now" button)
  useEffect(() => {
    if (initialAction === "play" && !loading && config && !hasTriggeredInitial) {
      setHasTriggeredInitial(true);
      handlePlayNext();
    }
  }, [initialAction, loading, config, hasTriggeredInitial]);

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
        const playerType = config?.stream?.player_type;
        if (playerType === "embedded" && onPlayEpisode) {
          const nextEpisode = (fullItem.user_status?.progress || 0) + 1;
          onPlayEpisode(nextEpisode.toString());
          onClose();
        } else {
          await mediaApi.playNext(item.id);
          dispatchRefresh();
        }
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

  const handleUpdateProgress = async (newProgress: number) => {
    await progressEditor.commitProgress(item.id, newProgress);
  };

  const handleRemoveFromList = async () => {
    if (confirm(`Are you sure you want to remove ${item.title.english || item.title.romaji} from your list?`)) {
      try {
        await mediaApi.deleteFromList(item.id);
        dispatchRefresh();
        onClose();
      } catch (error) {
        console.error("Failed to remove from list:", error);
      }
    }
  };

  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const queryClient = useQueryClient();
  const appState = useAppState();

  const handleToggleWatchlist = async () => {
    if (isUpdatingStatus) return;
    setIsUpdatingStatus(true);

    try {
      if (isPlanning) {
        await mediaApi.deleteFromList(item.id);
      } else {
        await mediaApi.updateStatus(item.id, "planning");
      }
      // Invalidate the detail query so it re-fetches with updated status
      queryClient.invalidateQueries({ queryKey: ["media-detail", item.id] });
      dispatchRefresh();
    } catch (error) {
      console.error("Failed to toggle watchlist:", error);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const title = fullItem.title.english || fullItem.title.romaji;

  return (
    <div className="fixed inset-0 z-[150] flex justify-end overflow-hidden">
      {/* Backdrop */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose} 
        className="absolute inset-0 bg-background/60 backdrop-blur-sm will-change-opacity transform-gpu" 
      />
      
      {/* Sidebar Drawer */}
      <motion.div 
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ duration: 0.3, ease: [0.32, 0.72, 0, 1] }}
        style={{ willChange: "transform" }}
        className="relative w-full max-w-2xl h-full bg-background/95 border-l border-border shadow-[-20px_0_50px_rgba(0,0,0,0.15)] dark:shadow-[-20px_0_50px_rgba(0,0,0,0.5)] flex flex-col transform-gpu overflow-hidden"
      >
        {/* Ambient Glow Backdrop Lighting */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
          <div 
            className="absolute -top-32 -left-32 w-[480px] h-[480px] rounded-full blur-[130px] transition-all duration-[1.5s] ease-out animate-pulse" 
            style={{ 
              backgroundColor: ambientColor,
              animationDuration: '9s',
              transition: 'background-color 1.2s ease-in-out, transform 1.2s ease-out'
            }} 
          />
          <div 
            className="absolute top-96 -right-32 w-[380px] h-[380px] rounded-full blur-[110px] transition-all duration-[1.5s] ease-out animate-pulse" 
            style={{ 
              backgroundColor: ambientColor.replace("0.18", "0.08"),
              animationDuration: '13s',
              transition: 'background-color 1.2s ease-in-out, transform 1.2s ease-out'
            }} 
          />
        </div>

        {/* Close Button */}
        <button 
          onClick={onClose} 
          className="absolute top-6 right-6 z-50 p-2 bg-foreground/10 hover:bg-foreground/20 text-foreground/70 hover:text-foreground rounded-full backdrop-blur-sm transition-all border border-border active:scale-90"
        >
          <X size={20} />
        </button>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto scrollbar-hide z-10 relative bg-transparent transform-gpu translate-z-0 will-change-scroll">
          {/* Header Banner */}
          <div className="relative h-72 w-full flex-shrink-0">
             <div className="absolute inset-0 bg-gradient-to-t from-background via-background/20 to-transparent z-[1]" />
             <img src={banner} alt={title} className="w-full h-full object-cover" />
             
             <div className="absolute bottom-6 left-8 right-8 z-[2] space-y-3">
                <div className="flex items-center space-x-2">
                  <div className="px-2 py-1 bg-accent rounded text-[10px] font-black uppercase tracking-widest text-white shadow-lg shadow-accent/20">
                    {fullItem.format || (isManga ? "MANGA" : "ANIME")}
                  </div>
                  {fullItem.average_score && (
                    <div className="flex items-center space-x-1 px-2 py-1 bg-background/65 backdrop-blur-md rounded text-[10px] font-bold text-amber-600 dark:text-yellow-400 border border-border">
                      <Star size={10} fill="currentColor" />
                      <span>{fullItem.average_score}%</span>
                    </div>
                  )}
                </div>
                <h2 className="text-3xl lg:text-4xl font-extrabold text-white leading-tight drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)]">{title}</h2>
             </div>
          </div>

          <div className="p-8 lg:p-10 space-y-8">
            {/* Quick Actions & Meta */}
            <div className="flex flex-col space-y-4">
              <div className="flex items-center space-x-3">
                {(() => {
                  const currentProgress = fullItem.user_status?.progress || 0;
                  const total = fullItem.episodes || fullItem.chapters || 0;
                  const nextAiringEp = fullItem.next_airing?.episode;
                  const latestAvailable = episodes.length > 0 
                    ? Math.max(...episodes.filter(e => !nextAiringEp || Number(e.number) < nextAiringEp).map(e => Number(e.number))) 
                    : total;
                  const nextEpisode = (fullItem.user_status?.progress || 0) + 1;
                  const isFinished = total > 0 && currentProgress >= total;
                  const isCaughtUp = !isFinished && latestAvailable > 0 && currentProgress >= latestAvailable;

                  return (
                    <button
                      onClick={handlePlayNext}
                      disabled={isPlayingNext || isCaughtUp}
                      className="flex-1 flex items-center justify-center space-x-3 py-3.5 bg-accent hover:bg-accent-light text-white font-extrabold text-sm rounded-2xl transition-all shadow-xl shadow-accent/20 active:scale-95 disabled:opacity-50 disabled:bg-foreground/[0.05] disabled:text-muted-foreground disabled:shadow-none"
                    >
                      {isPlayingNext ? (
                        <Loader2 className="animate-spin" size={18} />
                      ) : (
                        <>
                          {isManga ? <BookOpen size={18} /> : <Play size={18} fill="currentColor" />}
                          <span>
                            {isFinished ? "Completed" : isCaughtUp ? "Caught Up" : `${isManga ? 'Read' : 'Continue'} ${isManga ? 'Chapter' : 'Episode'} ${nextEpisode}`}
                          </span>
                        </>
                      )}
                    </button>
                  );
                })()}
                
                <button 
                  onClick={handleToggleWatchlist}
                  disabled={isUpdatingStatus}
                  title={isPlanning ? "Remove from Watchlist" : "Add to Watchlist"}
                  className={`p-3.5 rounded-2xl transition-all border active:scale-95 ${
                    isPlanning 
                    ? "bg-accent/20 border-accent/30 text-accent" 
                    : "bg-foreground/5 border-border text-foreground/70 hover:text-foreground hover:bg-foreground/10"
                  }`}
                >
                  {isUpdatingStatus ? <Loader2 size={22} className="animate-spin" /> : <Bookmark size={22} fill={isPlanning ? "currentColor" : "none"} />}
                </button>

                <button 
                  onClick={handleRemoveFromList}
                  title="Remove from List"
                  className="p-3.5 bg-red-500/10 hover:bg-red-500/20 text-red-500/70 hover:text-red-500 rounded-2xl transition-all border border-red-500/20 active:scale-95"
                >
                  <Trash2 size={22} />
                </button>
              </div>

              <div className="flex items-center justify-between px-2">
                <div className="flex items-center space-x-6">
                  <div>
                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em] mb-1">Progress</div>
                    {progressEditor.isEditing ? (
                      <div className="flex items-center space-x-2">
                        <input 
                          autoFocus
                          type="number" 
                          value={progressEditor.editValue}
                          onChange={(e) => progressEditor.setEditValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleUpdateProgress(parseInt(progressEditor.editValue) || 0);
                            if (e.key === 'Escape') progressEditor.cancelEditing();
                          }}
                          className="w-16 bg-foreground/5 border border-border rounded-lg px-2 py-1 text-sm font-bold text-foreground focus:outline-none focus:border-accent"
                        />
                        <button 
                          onClick={() => handleUpdateProgress(parseInt(progressEditor.editValue) || 0)}
                          className="p-1.5 bg-accent text-white rounded-lg hover:bg-accent-light transition-colors"
                        >
                          <Check size={14} />
                        </button>
                        <button 
                          onClick={() => progressEditor.cancelEditing()}
                          className="p-1.5 bg-foreground/5 text-muted-foreground rounded-lg hover:bg-foreground/10 transition-colors"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center space-x-3 group/progress">
                        <p className="text-xl font-black text-foreground tabular-nums">
                          {fullItem.user_status?.progress || 0}
                          <span className="text-muted-foreground/45 mx-1.5 font-medium">/</span>
                          <span className="text-muted-foreground">{fullItem.episodes || fullItem.chapters || "?"}</span>
                        </p>
                        <button 
                          onClick={() => progressEditor.startEditing(fullItem.user_status?.progress || 0)}
                          className="p-1.5 bg-foreground/5 text-muted-foreground hover:text-foreground hover:bg-foreground/10 rounded-lg transition-all opacity-0 group-hover/progress:opacity-100"
                        >
                          <Edit2 size={12} />
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="h-8 w-px bg-border" />
                  <div className="flex flex-col">
                    <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">
                      {fullItem.user_status?.score && fullItem.user_status.score > 0 ? "Your Score" : "Avg Score"}
                    </span>
                    <span className="text-base font-bold text-foreground">
                      {fullItem.user_status?.score && fullItem.user_status.score > 0 ? (
                        <>
                          {fullItem.user_status.score} <span className="text-muted-foreground/45 font-medium">/ 10</span>
                        </>
                      ) : (
                        <>
                          {fullItem.average_score ? `${fullItem.average_score}%` : '-'}
                        </>
                      )}
                    </span>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                   <div className={`w-2 h-2 rounded-full ${fullItem.status === 'RELEASING' ? 'bg-green-500 animate-pulse' : 'bg-gray-600'}`} />
                   <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">{fullItem.status?.replace('_', ' ')}</span>
                </div>
              </div>
            </div>

            {/* Genres */}
            {fullItem.genres && (
              <div className="flex flex-wrap gap-2">
                {fullItem.genres.map(g => (
                  <span key={g} className="px-3 py-1 bg-foreground/5 border border-border rounded-lg text-[11px] font-bold text-muted-foreground">{g}</span>
                ))}
              </div>
            )}

            {/* Synopsis with Read More */}
            {fullItem.description && (
              <div className="space-y-3 p-6 rounded-2xl bg-foreground/[0.02] border border-border">
                <h3 className="text-[10px] font-black text-accent uppercase tracking-[0.2em]">Synopsis</h3>
                <div className="relative">
                  <p 
                    className={`text-sm text-muted-foreground leading-relaxed transition-all duration-300 ${!isExpanded ? "line-clamp-4" : ""}`}
                    dangerouslySetInnerHTML={{ __html: fullItem.description }} 
                  />
                  {!isExpanded && fullItem.description.length > 200 && (
                    <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-background to-transparent pointer-events-none" />
                  )}
                </div>
                {fullItem.description.length > 200 && (
                  <button 
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="flex items-center space-x-1.5 text-[11px] font-bold text-foreground/50 hover:text-foreground transition-colors group"
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
                  <div className="text-base text-foreground font-bold">
                    Episode {fullItem.next_airing.episode} <span className="text-muted-foreground font-medium text-sm">airing {formatRelativeTime(new Date(fullItem.next_airing.airing_at + "Z"))}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Tabs */}
            <div className="space-y-6">
              <div className="flex space-x-1 p-1 bg-foreground/5 border border-border rounded-2xl">
                {(["episodes", "characters", "reviews", "recommendations"] as const).map((tab) => (
                  <button 
                    key={tab} 
                    onClick={() => setActiveTab(tab)} 
                    className={`flex-1 py-2.5 text-[10px] font-bold uppercase tracking-wider rounded-xl transition-all ${activeTab === tab ? "bg-accent text-white shadow-lg" : "text-muted-foreground hover:text-foreground"}`}
                  >
                    {tab === "episodes" ? (isManga ? "Chapters" : "Episodes") : tab}
                  </button>
                ))}
              </div>

              <div className="animate-fade-in min-h-[300px]">
                {activeTab === "episodes" && (
                  <EpisodeList 
                    mediaId={item.id} 
                    episodes={episodes} 
                    loading={loadingEps} 
                    progress={fullItem.user_status?.progress} 
                    isManga={isManga} 
                    onRead={onRead} 
                    onPlayEpisode={(epNum) => {
                      if (onPlayEpisode) onPlayEpisode(epNum);
                      onClose(); // Automatically close detail drawer upon playing
                    }}
                    playerType={config?.stream?.player_type}
                    onUnwatch={(num) => handleUpdateProgress(Number(num) - 1)} 
                    nextAiringEpisode={fullItem.next_airing?.episode}
                  />
                )}
                {activeTab === "characters" && (
                  <div className="grid grid-cols-2 gap-4">
                    {loadingChars ? (
                      <div className="col-span-2 py-20 flex justify-center">
                        <Loader2 className="animate-spin text-accent" size={24} />
                      </div>
                    ) : characters.length > 0 ? (
                      characters.map(char => (
                        <div key={char.id || char.name.full} className="flex items-center space-x-3 p-3 bg-foreground/[0.02] border border-border rounded-2xl hover:bg-foreground/[0.04] transition-colors group">
                          {char.image?.large && <img src={char.image.large} alt={char.name.full} className="w-14 h-14 rounded-xl object-cover shadow-lg" />}
                          <div className="min-w-0">
                            <div className="text-[13px] font-bold text-foreground group-hover:text-accent transition-colors truncate">{char.name.full}</div>
                            {char.description && <div className="text-[10px] text-muted-foreground line-clamp-1">{char.description.replace(/<[^>]*>?/gm, '')}</div>}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="col-span-2 py-20 text-center text-muted-foreground text-xs font-bold">No character data available.</div>
                    )}
                  </div>
                )}
                {activeTab === "reviews" && (
                  <div className="space-y-4">
                    {reviews.length > 0 ? (
                      reviews.map((rev, idx) => (
                        <div key={idx} className="p-5 bg-foreground/[0.02] border border-border rounded-2xl space-y-3">
                           {rev.summary && <div className="text-xs font-black text-foreground/90 tracking-wide uppercase italic leading-snug">"{rev.summary}"</div>}
                           <div className="text-xs text-muted-foreground leading-relaxed" dangerouslySetInnerHTML={{ __html: rev.body.substring(0, 300) + '...' }} />
                        </div>
                      ))
                    ) : (
                      <div className="py-20 text-center text-muted-foreground text-xs font-bold">No reviews found.</div>
                    )}
                  </div>
                )}
                {activeTab === "recommendations" && (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    {recommendations.map(rec => (
                      <button key={rec.id} onClick={() => appState.selectItem(rec)} className="group space-y-2 text-left">
                        <div className="aspect-[2/3] rounded-xl overflow-hidden border border-border shadow-lg">
                          <img src={rec.cover_image.large} className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" />
                        </div>
                        <div className="text-[11px] font-bold text-muted-foreground line-clamp-1 group-hover:text-foreground transition-colors">{rec.title.english || rec.title.romaji}</div>
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
