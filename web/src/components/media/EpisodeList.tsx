"use client";

import { useState, useEffect, useRef } from "react";
import { Play, Download, Loader2, CheckCircle2, Clock, AlertCircle, BookOpen, XCircle } from "lucide-react";
import { mediaApi, type Episode } from "@/lib/api";
import { dispatchRefresh } from "@/lib/events";

interface EpisodeListProps {
  mediaId: number;
  episodes: Episode[];
  loading: boolean;
  progress?: number;
  isManga?: boolean;
  onRead?: (chapterNum: string) => void;
  onPlayEpisode?: (epNum: string) => void;
  playerType?: "embedded" | "external";
  onUnwatch?: (epNum: string) => void;
  nextAiringEpisode?: number;
}

export default function EpisodeList({
  mediaId,
  episodes,
  loading,
  progress = 0,
  isManga = false,
  onRead,
  onPlayEpisode,
  playerType = "external",
  onUnwatch,
  nextAiringEpisode
}: EpisodeListProps) {
  const [playingEp, setPlayingEp] = useState<string | null>(null);
  const [queueingEp, setQueueingEp] = useState<string | null>(null);
  const [batchStart, setBatchStart] = useState("");
  const [batchEnd, setBatchEnd] = useState("");
  const [batchQueuing, setBatchQueuing] = useState(false);

  // Removed automatic scrolling entirely to ensure UI stability.
  // The list will always start at the top (Episode 1).
  useEffect(() => {
    // Manual scroll only
  }, [mediaId]);

  const handlePlay = async (epNum: string) => {
    if (isManga && onRead) {
      onRead(epNum);
      return;
    }
    
    if (playerType === "embedded" && onPlayEpisode) {
      onPlayEpisode(epNum);
      return;
    }
    
    setPlayingEp(epNum);
    try {
      await mediaApi.play(mediaId, epNum);
      dispatchRefresh();
    } catch (error) {
      console.error("Failed to play:", error);
    } finally {
      setPlayingEp(null);
    }
  };

  const handleQueue = async (epNum: string) => {
    setQueueingEp(epNum);
    try {
      await mediaApi.addToQueue(mediaId, [epNum]);
    } catch (error) {
      console.error("Failed to queue:", error);
    } finally {
      setQueueingEp(null);
    }
  };

  const handleBatchQueue = async () => {
    const start = parseInt(batchStart);
    const end = parseInt(batchEnd);
    if (isNaN(start) || isNaN(end) || start > end) return;
    
    setBatchQueuing(true);
    const eps = [];
    for (let i = start; i <= end; i++) {
      eps.push(String(i));
    }
    try {
      await mediaApi.addToQueue(mediaId, eps);
      setBatchStart("");
      setBatchEnd("");
    } catch (error) {
      console.error("Failed to batch queue:", error);
    } finally {
      setBatchQueuing(false);
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "completed": return <CheckCircle2 size={14} className="text-green-400" />;
      case "downloading": return <Loader2 size={14} className="text-accent animate-spin" />;
      case "queued": return <Clock size={14} className="text-yellow-400" />;
      case "failed": return <AlertCircle size={14} className="text-red-400" />;
      default: return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="animate-spin text-accent" size={28} />
        <span className="ml-3 text-gray-500 text-sm font-medium">Fetching {isManga ? "chapters" : "episodes"} from provider...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Episode list */}
      {episodes.length === 0 ? (
        <div className="text-center py-12 text-gray-600 text-sm">
          No {isManga ? "chapters" : "episodes"} found from this provider.
        </div>
      ) : (
        <div className="space-y-1 max-h-[50vh] overflow-y-auto scrollbar-hide pr-1">
          {episodes.map((ep) => {
            const epNum = String(ep.number);
            const isWatched = Number(ep.number) <= progress;
            const isNext = Number(ep.number) === progress + 1;
            const isUnaired = !isManga && nextAiringEpisode !== undefined && Number(ep.number) >= nextAiringEpisode;
            
            return (
              <div
                key={epNum}
                onClick={() => !isUnaired && handlePlay(epNum)}
                className={`flex items-center justify-between px-4 py-2.5 rounded-lg transition-all group ${!isUnaired ? 'cursor-pointer' : ''} ${
                  isNext && !isUnaired ? 'bg-accent/10 border border-accent/20 shadow-lg shadow-accent/5' : 
                  isWatched ? 'opacity-50 hover:bg-white/[0.04] border border-transparent' : 
                  'bg-white/[0.02] border border-white/[0.02] hover:bg-white/[0.06] hover:border-white/[0.08]'
                }`}
              >
                <div className="flex items-center space-x-4 min-w-0">
                  {/* Clean Episode Badge */}
                  <div className={`w-11 h-11 shrink-0 flex items-center justify-center rounded-[14px] font-bold text-sm transition-all ${
                    isWatched ? "bg-white/5 text-gray-500" :
                    isUnaired ? "bg-white/5 text-gray-700" :
                    isNext ? "bg-accent text-white shadow-md shadow-accent/20" :
                    "bg-white/[0.06] text-white group-hover:bg-accent group-hover:text-white"
                  }`}>
                    {playingEp === epNum ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <div className="relative flex items-center justify-center w-full h-full">
                        <span className="group-hover:opacity-0 transition-opacity absolute">{epNum}</span>
                        <Play size={16} fill="currentColor" className="opacity-0 group-hover:opacity-100 transition-opacity absolute" />
                      </div>
                    )}
                  </div>
                  
                  <div className="flex flex-col min-w-0">
                    <span className={`text-sm font-medium truncate transition-colors ${
                      isWatched ? "text-gray-500" : 
                      isUnaired ? "text-gray-600" : 
                      "text-gray-200 group-hover:text-white"
                    }`}>
                      {ep.title.toLowerCase() === `episode ${epNum}` ? `Episode ${epNum}` : ep.title || `Episode ${epNum}`}
                    </span>
                  </div>
                  {statusIcon(ep.download_status)}
                </div>

                {!isUnaired ? (
                  <div className="flex items-center space-x-1.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleQueue(epNum);
                      }}
                      disabled={queueingEp === epNum || ep.download_status === "completed"}
                      title="Download"
                      className="flex items-center justify-center w-9 h-9 bg-white/[0.04] text-gray-300 rounded-xl hover:bg-white/10 hover:text-white transition-all disabled:opacity-30 active:scale-90"
                    >
                      {queueingEp === epNum ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Download size={16} />
                      )}
                    </button>
                    {isWatched && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onUnwatch) onUnwatch(epNum);
                        }}
                        title={isManga ? "Backtrack to before this chapter" : "Mark as unwatched"}
                        className="flex items-center justify-center w-9 h-9 bg-white/[0.04] text-gray-400 rounded-xl hover:bg-red-500/20 hover:text-red-400 transition-all active:scale-90"
                      >
                        <XCircle size={16} />
                      </button>
                    )}
                  </div>
                ) : (
                  <span className="text-[10px] font-black uppercase tracking-wider text-gray-400 px-3 py-1.5 bg-white/[0.04] border border-white/10 rounded-[10px] shrink-0">
                    Airing Soon
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
