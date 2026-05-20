"use client";

import { useState, useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, X, CheckCircle2, Loader2, Music, ArrowRight } from "lucide-react";
import { mediaApi, type PlaybackStatus } from "@/lib/api";
import { dispatchRefresh } from "@/lib/events";

interface NowPlayingProps {
  onPlay?: (mediaId: number, episode: string) => void;
}

export default function NowPlaying({ onPlay }: NowPlayingProps) {
  const queryClient = useQueryClient();
  const [marking, setMarking] = useState(false);
  const [marked, setMarked] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  // Shared React Query key with HomeView — deduplicates the polling request
  const { data: playback } = useQuery<PlaybackStatus>({
    queryKey: ["playback-status"],
    queryFn: () => mediaApi.getPlaybackStatus().catch(() => null),
    refetchInterval: 5000,
    staleTime: 4000,
  });

  // Reset dismissed/marked state when a new playback session starts
  useEffect(() => {
    if (playback) {
      setDismissed(false);
      setMarked(false);
    }
  }, [playback]);

  const handleMarkWatched = async () => {
    if (!playback) return;
    setMarking(true);
    try {
      const epNum = parseInt(playback.episode);
      await mediaApi.updateStatus(playback.media_id, undefined, undefined, epNum);
      setMarked(true);
      dispatchRefresh();
      setTimeout(() => {
        setDismissed(true);
      }, 2000);
    } catch (err) {
      console.error("Failed to mark as watched:", err);
    } finally {
      setMarking(false);
    }
  };

  const handleDismiss = async () => {
    setDismissed(true);
    try {
      await mediaApi.clearPlaybackStatus();
      queryClient.invalidateQueries({ queryKey: ["playback-status"] });
    } catch {}
  };

  if (!playback || dismissed) return null;

  return (
    <div className="fixed bottom-0 left-[72px] lg:left-60 right-0 z-[90] animate-slide-up">
      <div className="mx-4 mb-4 bg-surface/95 backdrop-blur-xl border border-white/[0.08] rounded-2xl p-4 flex items-center justify-between shadow-2xl shadow-black/50">
        <div className="flex items-center space-x-4 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center shrink-0 animate-pulse-glow">
            <Music size={18} className="text-accent" />
          </div>
          <div className="min-w-0">
            <div className="text-[10px] font-bold text-accent uppercase tracking-widest">Now Playing</div>
            <div className="text-sm font-bold text-white truncate">
              {playback.media_title}
            </div>
            <div className="text-xs text-gray-500 font-medium">
              Episode {playback.episode}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          {onPlay && (
            <button
              onClick={() => onPlay(playback.media_id, playback.episode)}
              className="flex items-center space-x-2 px-4 py-2.5 rounded-xl font-bold text-sm bg-white/[0.04] hover:bg-accent hover:text-white border border-white/[0.06] transition-all active:scale-95"
              title="Jump to Player"
            >
              <ArrowRight size={14} />
              <span className="hidden sm:inline">Continue</span>
            </button>
          )}
          <button
            onClick={handleMarkWatched}
            disabled={marking || marked}
            className={`flex items-center space-x-2 px-5 py-2.5 rounded-xl font-bold text-sm transition-all active:scale-95 ${
              marked
                ? "bg-green-500 text-white"
                : "bg-accent text-white hover:bg-accent-light shadow-lg shadow-accent/20"
            }`}
          >
            {marking ? (
              <Loader2 size={14} className="animate-spin" />
            ) : marked ? (
              <CheckCircle2 size={14} />
            ) : (
              <CheckCircle2 size={14} />
            )}
            <span>{marked ? "Marked!" : "Mark Watched"}</span>
          </button>
          <button
            onClick={handleDismiss}
            className="p-2.5 rounded-xl text-gray-500 hover:text-white hover:bg-white/[0.06] transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
