"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Loader2, 
  RotateCcw, 
  X, 
  Clock, 
  AlertCircle, 
  CheckCircle2, 
  Download, 
  Play, 
  Trash2, 
  Film, 
  ChevronRight,
  FolderOpen,
  ArrowRight
} from "lucide-react";
import { mediaApi, type QueueItem } from "@/lib/api";

export default function DownloadsView() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"library" | "queue">("library");
  const [selectedMediaId, setSelectedMediaId] = useState<number | null>(null);
  const [playingItem, setPlayingItem] = useState<{ mediaId: number; ep: string } | null>(null);

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
    // Optimistically set all failed items to queued state in local UI
    setQueue(prev =>
      prev.map(item =>
        item.status === "failed" ? { ...item, status: "queued" } : item
      )
    );
    try {
      await mediaApi.retryQueue();
      fetchQueue();
    } catch (err) {
      console.error("Failed to retry queue:", err);
      fetchQueue();
    }
  };

  const handleRemove = async (mediaId: number, ep: string) => {
    // Optimistically remove the item from local UI state
    setQueue(prev =>
      prev.filter(item => !(item.media_id === mediaId && item.episode_number === ep))
    );
    try {
      await mediaApi.removeFromQueue(mediaId, ep);
      fetchQueue();
    } catch (err) {
      console.error("Failed to remove item:", err);
      fetchQueue();
    }
  };

  const handlePlay = async (mediaId: number, ep: string) => {
    setPlayingItem({ mediaId, ep });
    try {
      await mediaApi.play(mediaId, ep);
    } catch (error) {
      console.error("Failed to play:", error);
    } finally {
      setPlayingItem(null);
    }
  };

  const getStatusDetails = (status: string) => {
    switch (status) {
      case "downloading":
        return {
          icon: <Loader2 className="text-accent animate-spin" size={18} />,
          bg: "bg-accent/10 border-accent/20",
          text: "text-accent",
          label: "Downloading"
        };
      case "queued":
        return {
          icon: <Clock className="text-amber-400 animate-pulse" size={18} />,
          bg: "bg-amber-400/5 border-amber-400/10",
          text: "text-amber-400",
          label: "In Queue"
        };
      case "failed":
        return {
          icon: <AlertCircle className="text-rose-500" size={18} />,
          bg: "bg-rose-500/10 border-rose-500/20",
          text: "text-rose-400",
          label: "Failed"
        };
      case "completed":
        return {
          icon: <CheckCircle2 className="text-emerald-400" size={18} />,
          bg: "bg-emerald-400/10 border-emerald-400/20",
          text: "text-emerald-400",
          label: "Completed"
        };
      default:
        return {
          icon: <Download className="text-muted-foreground" size={18} />,
          bg: "bg-foreground/5 border-border",
          text: "text-muted-foreground",
          label: "Idle"
        };
    }
  };

  // Group completed items by media_id
  const completedGroups = queue
    .filter((item) => item.status === "completed")
    .reduce((groups: Record<number, { title: string; cover?: string; episodes: QueueItem[] }>, item) => {
      if (!groups[item.media_id]) {
        groups[item.media_id] = {
          title: item.media_title,
          cover: item.cover_image,
          episodes: [],
        };
      }
      groups[item.media_id].episodes.push(item);
      return groups;
    }, {});

  // Sort episodes in each group numerically
  Object.values(completedGroups).forEach((group) => {
    group.episodes.sort((a, b) => {
      const numA = parseFloat(a.episode_number);
      const numB = parseFloat(b.episode_number);
      return (isNaN(numA) ? 0 : numA) - (isNaN(numB) ? 0 : numB);
    });
  });

  const activeQueue = queue.filter((item) => item.status !== "completed");
  const selectedMedia = selectedMediaId !== null ? completedGroups[selectedMediaId] : null;

  return (
    <div className="space-y-8 pb-12">
      {/* Page Title & Glow Header */}
      <div className="relative flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="absolute -left-10 -top-10 w-72 h-72 bg-accent/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="space-y-1.5 relative z-10">
          <h1 className="text-4xl lg:text-5xl font-black tracking-tight text-white bg-gradient-to-r from-foreground via-foreground/90 to-muted-foreground bg-clip-text text-transparent">
            Offline Downloads
          </h1>
          <p className="text-sm text-muted-foreground max-w-xl font-medium">
            Manage your offline library, track active downloads, and play complete episodes without an active connection.
          </p>
        </div>
      </div>

      {/* Tabs bar */}
      <div className="flex items-center justify-between border-b border-border pb-0.5 relative z-10">
        <div className="flex space-x-6">
          <button
            onClick={() => setActiveTab("library")}
            className={`pb-4 text-sm font-bold tracking-wide transition-all relative cursor-pointer ${
              activeTab === "library" ? "text-foreground" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <span className="flex items-center gap-2">
              <FolderOpen size={16} />
              Offline Library ({Object.keys(completedGroups).length})
            </span>
            {activeTab === "library" && (
              <motion.div 
                layoutId="activeTabIndicator" 
                className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-accent rounded-full" 
                transition={{ type: "spring", stiffness: 350, damping: 30 }}
              />
            )}
          </button>
          
          <button
            onClick={() => setActiveTab("queue")}
            className={`pb-4 text-sm font-bold tracking-wide transition-all relative cursor-pointer ${
              activeTab === "queue" ? "text-foreground" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <span className="flex items-center gap-2">
              <Clock size={16} />
              Active Queue ({activeQueue.length})
            </span>
            {activeTab === "queue" && (
              <motion.div 
                layoutId="activeTabIndicator" 
                className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-accent rounded-full" 
                transition={{ type: "spring", stiffness: 350, damping: 30 }}
              />
            )}
          </button>
        </div>

        {activeTab === "queue" && activeQueue.some(item => item.status === "failed") && (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleRetry}
            className="flex items-center space-x-2 bg-accent hover:bg-accent-light text-white transition-all px-4.5 py-2 rounded-xl font-bold text-xs shadow-lg shadow-accent/15 cursor-pointer"
          >
            <RotateCcw size={13} className="animate-spin-slow" />
            <span>Retry All Failed</span>
          </motion.button>
        )}
      </div>

      {/* Main content frame */}
      <div className="relative min-h-[300px]">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="animate-spin text-accent" size={36} />
          </div>
        ) : (
          <AnimatePresence mode="wait">
            {activeTab === "library" ? (
              <motion.div
                key="library-tab"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.25 }}
              >
                {Object.keys(completedGroups).length > 0 ? (
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
                    {Object.entries(completedGroups).map(([mediaIdStr, group]) => {
                      const mediaId = parseInt(mediaIdStr);
                      return (
                        <motion.div
                          key={mediaId}
                          onClick={() => setSelectedMediaId(mediaId)}
                          whileHover={{ y: -6 }}
                          className="group cursor-pointer space-y-3"
                        >
                          <div className="relative aspect-[2/3] rounded-2xl overflow-hidden bg-card border border-border group-hover:border-accent/40 shadow-xl group-hover:shadow-accent/5 transition-all duration-300">
                            {group.cover ? (
                              <img
                                src={group.cover}
                                alt={group.title}
                                className="w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-105"
                              />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center bg-foreground/5 text-muted-foreground">
                                <Download size={32} />
                              </div>
                            )}
                            
                            {/* Frosted / dark gradient overlay */}
                            <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent opacity-80 group-hover:opacity-90 transition-opacity duration-300" />
                            
                            {/* Glowing background blur on hover */}
                            <div className="absolute inset-0 bg-accent/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-md pointer-events-none" />

                            {/* Floating EP Badge */}
                            <div className="absolute top-3 right-3 bg-accent text-white font-extrabold text-[10px] px-2.5 py-1 rounded-lg shadow-lg leading-none tracking-wider uppercase backdrop-blur-md">
                              {group.episodes.length} {group.episodes.length === 1 ? "EP" : "EPS"}
                            </div>

                            {/* Quick play overlay button on hover */}
                            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 bg-black/45 backdrop-blur-[2px]">
                              <div className="w-13 h-13 rounded-full bg-accent text-white flex items-center justify-center shadow-lg transform translate-y-3 group-hover:translate-y-0 transition-all duration-350 ease-out hover:scale-105 active:scale-95">
                                <Play size={20} fill="currentColor" className="ml-0.5 text-white" />
                              </div>
                            </div>
                          </div>
                          
                          <div className="px-1.5 space-y-1">
                            <h3 className="font-extrabold text-sm text-foreground/90 group-hover:text-foreground line-clamp-2 leading-snug transition-colors duration-200">
                              {group.title}
                            </h3>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-20 px-4 border border-dashed border-border bg-foreground/[0.01] rounded-3xl text-center space-y-4 max-w-xl mx-auto mt-6">
                    <div className="p-4 bg-foreground/5 border border-border text-muted-foreground rounded-2xl">
                      <Download size={32} />
                    </div>
                    <div className="space-y-1">
                      <p className="text-foreground font-extrabold text-base">Offline Library is Empty</p>
                      <p className="text-muted-foreground text-sm max-w-sm">
                        Episodes you download in AniCat will automatically download to your local drive and populate here.
                      </p>
                    </div>
                  </div>
                )}
              </motion.div>
            ) : (
              <motion.div
                key="queue-tab"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.25 }}
              >
                {activeQueue.length > 0 ? (
                  <div className="space-y-3.5">
                    {activeQueue.map((item, idx) => {
                      const statusInfo = getStatusDetails(item.status);
                      return (
                        <div
                          key={`${item.media_id}-${item.episode_number}-${idx}`}
                          className="flex items-center justify-between p-4.5 rounded-2xl bg-foreground/[0.02] border border-border hover:bg-foreground/[0.04] transition-all duration-300 group relative overflow-hidden"
                        >
                          <div className="flex items-center space-x-5 min-w-0 z-10">
                            {/* Status Icon Wrapper */}
                            <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 border transition-all ${statusInfo.bg} ${
                              item.status === "downloading" ? "shadow-md shadow-accent/10" : ""
                            }`}>
                              {statusInfo.icon}
                            </div>
                            
                            <div className="min-w-0 space-y-1">
                              <h3 className="font-extrabold text-sm text-foreground truncate max-w-[280px] sm:max-w-[400px]">
                                {item.media_title}
                              </h3>
                              <div className="flex items-center gap-2.5">
                                <span className="text-accent text-xs font-black bg-accent/10 px-2 py-0.5 rounded-md leading-none">
                                  EP {item.episode_number}
                                </span>
                                <span className={`text-[10px] font-black uppercase tracking-wider ${statusInfo.text}`}>
                                  {statusInfo.label}
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center space-x-4 shrink-0 z-10">
                            {item.status === "failed" && item.error_message && (
                              <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-500/5 border border-rose-500/10 text-rose-400 text-xs font-semibold max-w-[280px] truncate" title={item.error_message}>
                                <AlertCircle size={12} />
                                <span className="truncate">{item.error_message}</span>
                              </div>
                            )}
                            <button
                              onClick={() => handleRemove(item.media_id, item.episode_number)}
                              className="p-2.5 rounded-xl bg-foreground/5 text-muted-foreground hover:bg-rose-500/10 hover:text-rose-400 border border-border transition-all cursor-pointer hover:border-rose-500/20 active:scale-95"
                              title="Remove"
                            >
                              <X size={15} />
                            </button>
                          </div>

                          {/* Downloading bar shimmer */}
                          {item.status === "downloading" && (
                            <div className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-foreground/5">
                              <div className="h-full bg-accent/70 animate-shimmer w-[70%]" />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-20 px-4 border border-dashed border-border bg-foreground/[0.01] rounded-3xl text-center space-y-4 max-w-xl mx-auto mt-6">
                    <div className="p-4 bg-foreground/5 border border-border text-muted-foreground rounded-2xl">
                      <Clock size={32} />
                    </div>
                    <div className="space-y-1">
                      <p className="text-foreground font-extrabold text-base">Active Queue is Idle</p>
                      <p className="text-muted-foreground text-sm max-w-sm">
                        {"You don't have any in-progress, queued, or failed downloads right now."}
                      </p>
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </div>

      {/* Frosted Glass Detail Drawer Modal for Selected Media */}
      <AnimatePresence>
        {selectedMedia && (
          <div className="fixed inset-0 z-[999] flex items-center justify-center p-4">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedMediaId(null)}
              className="absolute inset-0 bg-background/80 backdrop-blur-md"
            />

            {/* Modal Body */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              transition={{ type: "spring", duration: 0.4 }}
              className="bg-card border border-border rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl relative z-10 flex flex-col max-h-[80vh]"
            >
              {/* Close Button */}
              <button
                onClick={() => setSelectedMediaId(null)}
                className="absolute top-5 right-5 p-2.5 rounded-full bg-foreground/5 text-muted-foreground hover:bg-foreground/10 hover:text-foreground border border-border transition-all z-10 cursor-pointer active:scale-95"
              >
                <X size={16} />
              </button>

              {/* Banner Area */}
              <div className="relative h-56 sm:h-64 bg-[#050505] overflow-hidden shrink-0 forced-dark-container">
                {/* Blurred background cover */}
                {selectedMedia.cover && (
                  <img
                    src={selectedMedia.cover}
                    alt=""
                    className="absolute inset-0 w-full h-full object-cover blur-2xl opacity-25 scale-110"
                  />
                )}
                
                <div className="absolute inset-0 bg-gradient-to-t from-[#050505] via-[#050505]/40 to-transparent" />
                
                {/* Content on Banner */}
                <div className="absolute bottom-6 left-6 right-6 flex items-end space-x-6">
                  {selectedMedia.cover && (
                    <img
                      src={selectedMedia.cover}
                      alt={selectedMedia.title}
                      className="w-20 sm:w-26 aspect-[2/3] rounded-2xl object-cover shadow-2xl border border-white/10 shrink-0"
                    />
                  )}
                  <div className="min-w-0 space-y-2 pb-1">
                    <span className="text-accent text-[9px] font-black uppercase tracking-widest bg-accent/15 border border-accent/25 px-2.5 py-1 rounded-md inline-block leading-none">
                      {selectedMedia.episodes.length} {selectedMedia.episodes.length === 1 ? "Episode Cached" : "Episodes Cached"}
                    </span>
                    <h2 className="text-xl sm:text-2xl font-black text-white truncate leading-tight">
                      {selectedMedia.title}
                    </h2>
                  </div>
                </div>
              </div>

              {/* Episode List Scroll Container */}
              <div className="p-6 overflow-y-auto space-y-3 flex-1 scrollbar-thin bg-foreground/[0.02]">
                {selectedMedia.episodes.map((ep) => {
                  const isCurrentPlaying = playingItem?.mediaId === ep.media_id && playingItem?.ep === ep.episode_number;
                  return (
                    <div
                      key={ep.episode_number}
                      className="flex items-center justify-between p-4 rounded-2xl bg-foreground/[0.02] border border-border hover:bg-foreground/[0.04] transition-all group"
                    >
                      <div className="flex items-center space-x-4 min-w-0">
                        <div className="w-11 h-11 rounded-xl bg-accent/10 border border-accent/15 flex items-center justify-center text-accent font-black text-sm shrink-0">
                          EP {ep.episode_number}
                        </div>
                        <div className="min-w-0">
                          <span className="font-extrabold text-sm text-foreground block truncate">
                            Episode {ep.episode_number}
                          </span>
                          <span className="text-[10px] text-muted-foreground font-extrabold tracking-wider uppercase block mt-0.5">
                            Ready Offline
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-3 shrink-0">
                        <button
                          onClick={() => handlePlay(ep.media_id, ep.episode_number)}
                          disabled={playingItem !== null}
                          className="flex items-center space-x-2 bg-accent hover:bg-accent-light text-white px-5 py-2.5 rounded-xl font-extrabold text-xs shadow-lg shadow-accent/10 transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
                        >
                          {isCurrentPlaying ? (
                            <Loader2 size={13} className="animate-spin" />
                          ) : (
                            <Play size={13} fill="currentColor" />
                          )}
                          <span>PLAY</span>
                        </button>
                        
                        <button
                          onClick={() => {
                            handleRemove(ep.media_id, ep.episode_number);
                            if (selectedMedia.episodes.length <= 1) {
                              setSelectedMediaId(null);
                            }
                          }}
                          className="p-2.5 rounded-xl bg-foreground/5 text-muted-foreground hover:bg-rose-500/10 hover:text-rose-400 border border-border transition-colors cursor-pointer active:scale-95"
                          title="Delete Cache"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
