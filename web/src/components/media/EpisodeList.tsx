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
  onUnwatch?: (epNum: string) => void;
}

export default function EpisodeList({ mediaId, episodes, loading, progress = 0, isManga = false, onRead, onUnwatch }: EpisodeListProps) {
  const [playingEp, setPlayingEp] = useState<string | null>(null);
  const [queueingEp, setQueueingEp] = useState<string | null>(null);
  const [batchStart, setBatchStart] = useState("");
  const [batchEnd, setBatchEnd] = useState("");
  const [batchQueuing, setBatchQueuing] = useState(false);
  const activeEpRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!loading && episodes.length > 0) {
      setTimeout(() => {
        activeEpRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 300);
    }
  }, [loading, episodes]);

  const handlePlay = async (epNum: string) => {
    if (isManga && onRead) {
      onRead(epNum);
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
            
            return (
              <div
                key={epNum}
                ref={isNext ? activeEpRef : null}
                className={`flex items-center justify-between px-4 py-3 rounded-xl transition-all group ${isNext ? 'bg-white/[0.04] border border-white/[0.05] shadow-lg' : 'hover:bg-white/[0.03]'}`}
              >
                <div className="flex items-center space-x-4 min-w-0">
                  <div className="flex items-center space-x-1 w-10 justify-end shrink-0">
                    {isWatched && (
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onUnwatch) onUnwatch(epNum);
                        }}
                        title={isManga ? "Mark as unread" : "Mark as unwatched"}
                        className="p-1 hover:bg-white/10 rounded-full transition-colors group/unwatch"
                      >
                        <CheckCircle2 size={16} className="text-green-500 fill-green-500/10 shrink-0 group-hover/unwatch:hidden" />
                        <XCircle size={16} className="text-red-500 hidden group-hover/unwatch:block" />
                      </button>
                    )}
                    <span className={`font-bold text-sm ${isWatched ? "text-green-500" : "text-accent"}`}>
                      {epNum}
                    </span>
                  </div>
                  <span className={`text-sm truncate group-hover:text-white transition-colors ${isWatched ? "text-gray-500" : "text-gray-300"}`}>
                    {ep.title}
                  </span>
                  {statusIcon(ep.download_status)}
                </div>

                <div className="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  <button
                    onClick={() => handlePlay(epNum)}
                    disabled={playingEp === epNum}
                    className="flex items-center space-x-1.5 bg-accent text-white px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-accent-light transition-colors active:scale-95"
                  >
                    {playingEp === epNum ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      isManga ? <BookOpen size={12} /> : <Play fill="currentColor" size={12} />
                    )}
                    <span>{isManga ? "Read" : "Play"}</span>
                  </button>
                  <button
                    onClick={() => handleQueue(epNum)}
                    disabled={queueingEp === epNum || ep.download_status === "completed"}
                    className="flex items-center space-x-1.5 bg-white/[0.06] text-gray-300 px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-white/10 transition-colors disabled:opacity-30 active:scale-95"
                  >
                    {queueingEp === epNum ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <Download size={12} />
                    )}
                    <span>DL</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
