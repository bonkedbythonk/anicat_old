"use client";

import { useEffect, useState } from "react";
import { X, Play, Loader2, Star, Users, Calendar, Clock, Building2, Monitor, CheckCircle2, Bookmark, Pause, XCircle, Download, BookOpen, RotateCcw } from "lucide-react";
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
  const [loadingEps, setLoadingEps] = useState(false);
  const [loadingChars, setLoadingChars] = useState(false);
  const [isPlayingNext, setIsPlayingNext] = useState(false);
  const [activeTab, setActiveTab] = useState<"episodes" | "characters" | "reviews" | "recommendations">("episodes");
  const [config, setConfig] = useState<any>(null);

  const isManga = item.type === "MANGA" || (item.format && ["MANGA", "ONE_SHOT", "NOVEL"].includes(item.format));

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

  const handlePlayNext = async () => {
    if (isPlayingNext) return;
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
    }
  };

  const handleUnwatch = async () => {
    if (confirm(`Are you sure you want to remove ${item.title.english || item.title.romaji} from your list?`)) {
      try {
        await mediaApi.updateStatus(item.id, "REPEATING", undefined, 0); // Hack to clear
        // Correct way would be a delete endpoint, but we can just set to planning/removed if supported
        // For now, let's just clear progress
        dispatchRefresh();
        onClose();
      } catch (error) {
        console.error("Failed to unwatch:", error);
      }
    }
  };

  const title = fullItem.title.english || fullItem.title.romaji;
  const banner = fullItem.banner_image || fullItem.cover_image.large;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 lg:p-8 animate-in fade-in zoom-in duration-300">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-md" onClick={onClose} />
      
      <div className="relative w-full max-w-5xl max-h-[90vh] bg-[#0c0c0c] border border-white/10 rounded-3xl overflow-hidden shadow-2xl flex flex-col lg:flex-row">
        {/* Close Button */}
        <button onClick={onClose} className="absolute top-6 right-6 z-10 p-2 bg-black/40 hover:bg-black/60 text-white/70 hover:text-white rounded-full backdrop-blur-sm transition-all border border-white/5">
          <X size={20} />
        </button>

        {/* Left: Media Poster & Meta (Desktop) / Header (Mobile) */}
        <div className="lg:w-80 flex-shrink-0 relative group">
          <div className="absolute inset-0 bg-gradient-to-t from-[#0c0c0c] via-transparent to-transparent z-[1]" />
          <img src={fullItem.cover_image.large} alt={title} className="w-full h-full object-cover" />
          
          <div className="absolute bottom-6 left-6 right-6 z-[2] space-y-4">
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
          </div>
        </div>

        {/* Right: Content Area */}
        <div className="flex-1 overflow-y-auto scrollbar-hide bg-gradient-to-br from-white/[0.02] to-transparent p-6 lg:p-10">
          <div className="max-w-3xl space-y-8">
            {/* Header */}
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center space-x-2 text-xs font-bold text-accent uppercase tracking-[0.2em]">
                  {fullItem.season && fullItem.seasonYear ? (
                    <span>{fullItem.season} {fullItem.seasonYear}</span>
                  ) : (
                    <span>{fullItem.status?.replace('_', ' ')}</span>
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
                {(() => {
                  const currentProgress = fullItem.user_status?.progress || 0;
                  const total = fullItem.episodes || fullItem.chapters || 0;
                  // If airing, we might not have all episodes yet. 
                  // Use the fetched episodes list as the source for 'available' episodes.
                  const latestAvailable = episodes.length > 0 ? Math.max(...episodes.map(e => Number(e.number))) : total;
                  const isFinished = total > 0 && currentProgress >= total;
                  const isCaughtUp = !isFinished && latestAvailable > 0 && currentProgress >= latestAvailable;

                  console.log(`[MediaDetail] ${title}: progress=${currentProgress}, total=${total}, latest=${latestAvailable}, finished=${isFinished}, caughtUp=${isCaughtUp}`);

                  return (
                    <button
                      onClick={handlePlayNext}
                      disabled={isPlayingNext || isCaughtUp}
                      className="flex-1 flex items-center justify-center space-x-2 py-2.5 bg-accent hover:bg-accent-light text-white font-extrabold text-sm rounded-xl transition-all shadow-lg shadow-accent/20 active:scale-95 disabled:opacity-50 disabled:bg-white/[0.05] disabled:text-gray-500 disabled:shadow-none"
                    >
                      {isPlayingNext ? (
                        <Loader2 className="animate-spin" size={18} />
                      ) : (
                        <>
                          {isManga ? <BookOpen size={18} /> : <Play size={18} fill="currentColor" />}
                          <span>
                            {isFinished ? "Completed" : isCaughtUp ? "Caught Up" : `Continue ${isManga ? 'Reading' : 'Watching'}`}
                          </span>
                        </>
                      )}
                    </button>
                  );
                })()}
                
                <button className="p-2.5 bg-white/[0.05] hover:bg-white/[0.1] text-white/70 hover:text-white rounded-xl transition-all border border-white/5 active:scale-95">
                  <Bookmark size={20} />
                </button>
              </div>

              <div className="flex items-center justify-between px-1">
                <div className="flex items-center space-x-4">
                  <div className="flex flex-col">
                    <span className="text-[9px] font-black text-gray-500 uppercase tracking-widest">Progress</span>
                    <span className="text-sm font-bold text-white">
                      {fullItem.user_status?.progress || 0} / {fullItem.episodes || fullItem.chapters || '?'}
                    </span>
                  </div>
                  <div className="h-6 w-px bg-white/10" />
                  <div className="flex flex-col">
                    <span className="text-[9px] font-black text-gray-500 uppercase tracking-widest">Score</span>
                    <span className="text-sm font-bold text-white">{fullItem.user_status?.score || '-'} / 10</span>
                  </div>
                </div>
                
                <div className="flex items-center space-x-1">
                   <div className={`w-1.5 h-1.5 rounded-full ${fullItem.status === 'RELEASING' ? 'bg-green-500 animate-pulse' : 'bg-gray-600'}`} />
                   <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">{fullItem.status?.replace('_', ' ')}</span>
                </div>
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
              {activeTab === "episodes" && <EpisodeList mediaId={item.id} episodes={episodes} loading={loadingEps} progress={fullItem.user_status?.progress} isManga={isManga} onRead={onRead} onUnwatch={handleUnwatch} />}
              {activeTab === "characters" && (
                <div className="grid grid-cols-2 gap-3">
                  {loadingChars ? (
                    <div className="col-span-2 py-20 flex justify-center">
                      <Loader2 className="animate-spin text-accent" size={24} />
                    </div>
                  ) : characters.length > 0 ? (
                    characters.map(char => (
                      <div key={char.id || char.name.full} className="flex items-center space-x-3 p-2 bg-white/[0.02] border border-white/[0.04] rounded-xl">
                        {char.image?.large && <img src={char.image.large} alt={char.name.full} className="w-12 h-12 rounded-lg object-cover" />}
                        <div className="min-w-0">
                          <div className="text-xs font-bold text-white truncate">{char.name.full}</div>
                          {char.description && <div className="text-[9px] text-gray-500 line-clamp-1">{char.description.replace(/<[^>]*>?/gm, '')}</div>}
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
                      <div key={idx} className="p-4 bg-white/[0.02] border border-white/[0.04] rounded-xl space-y-2">
                         {rev.summary && <div className="text-xs font-black text-gray-300 tracking-wide uppercase italic">"{rev.summary}"</div>}
                         <div className="text-[11px] text-gray-400 leading-relaxed" dangerouslySetInnerHTML={{ __html: rev.body.substring(0, 300) + '...' }} />
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
      </div>
    </div>
  );
}
