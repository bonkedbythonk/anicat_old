"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2, RotateCcw, X, Clock, AlertCircle, CheckCircle2, Download } from "lucide-react";
import { mediaApi, type QueueItem } from "@/lib/api";

export default function DownloadsView() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchQueue = useCallback(async () => {
    try {
      const data = await mediaApi.getQueue();
      setQueue(data);
    } catch {
      console.error("Failed to fetch queue");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 5000);
    return () => clearInterval(interval);
  }, [fetchQueue]);

  const handleRetry = async () => {
    await mediaApi.retryQueue();
    fetchQueue();
  };

  const handleRemove = async (mediaId: number, ep: string) => {
    await mediaApi.removeFromQueue(mediaId, ep);
    fetchQueue();
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "downloading": return <Loader2 className="text-accent animate-spin" size={18} />;
      case "queued": return <Clock className="text-yellow-400" size={18} />;
      case "failed": return <AlertCircle className="text-red-400" size={18} />;
      case "completed": return <CheckCircle2 className="text-green-400" size={18} />;
      default: return <Download className="text-gray-500" size={18} />;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-end justify-between">
        <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">Downloads</h1>
        <button
          onClick={handleRetry}
          className="flex items-center space-x-2 bg-white/[0.04] hover:bg-accent hover:text-white transition-all px-5 py-2.5 rounded-xl font-semibold text-sm border border-white/[0.06] group"
        >
          <RotateCcw size={15} className="group-hover:rotate-180 transition-transform duration-500" />
          <span>Retry Failed</span>
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="animate-spin text-accent" size={36} />
        </div>
      ) : queue.length > 0 ? (
        <div className="space-y-2">
          {queue.map((item, idx) => (
            <div
              key={`${item.media_id}-${item.episode_number}-${idx}`}
              className="flex items-center justify-between p-5 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.03] transition-colors group relative overflow-hidden"
            >
              <div className="flex items-center space-x-5 min-w-0">
                <div className={`w-10 h-10 rounded-lg bg-white/[0.04] flex items-center justify-center shrink-0 ${
                  item.status === "downloading" ? "animate-pulse-glow" : ""
                }`}>
                  {statusIcon(item.status)}
                </div>
                <div className="min-w-0">
                  <h3 className="font-bold text-white truncate">{item.media_title}</h3>
                  <div className="flex items-center space-x-3 mt-0.5">
                    <span className="text-accent text-xs font-semibold">EP {item.episode_number}</span>
                    <span className="text-gray-600 text-xs font-medium uppercase">{item.status}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-3 shrink-0">
                {item.status === "failed" && item.error_message && (
                  <span className="text-xs text-red-400/70 max-w-[200px] truncate hidden lg:block" title={item.error_message}>
                    {item.error_message}
                  </span>
                )}
                <button
                  onClick={() => handleRemove(item.media_id, item.episode_number)}
                  className="p-2.5 rounded-lg bg-white/[0.04] text-gray-500 hover:bg-red-500/10 hover:text-red-400 transition-colors"
                >
                  <X size={16} />
                </button>
              </div>

              {item.status === "downloading" && (
                <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-white/[0.03]">
                  <div className="h-full bg-accent/60 animate-shimmer w-1/2" />
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-24 border-2 border-dashed border-white/[0.04] rounded-2xl">
          <Download size={40} className="mx-auto text-gray-800 mb-4" />
          <p className="text-gray-600 font-semibold">Queue is empty</p>
          <p className="text-gray-700 text-sm mt-1">Find anime and queue episodes for download.</p>
        </div>
      )}
    </div>
  );
}
