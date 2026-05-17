"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Sidebar, { type ViewName } from "@/components/layout/Sidebar";
import NowPlaying from "@/components/layout/NowPlaying";
import MediaDetail from "@/components/media/MediaDetail";
import MangaReader from "@/components/media/MangaReader";
import AnimePlayer from "@/components/media/AnimePlayer";
import useKeyboardShortcuts from "@/lib/useKeyboardShortcuts";
import { mediaApi, type MediaItem, type HealthStatus, API_BASE_ORIGIN } from "@/lib/api";
import { dispatchRefresh } from "@/lib/events";
import Onboarding from "@/components/layout/Onboarding";
import { X, WifiOff, RotateCw } from "lucide-react";

// View Components
import HomeView from "@/components/views/HomeView";
import MangaView from "@/components/views/MangaView";
import SearchView from "@/components/views/SearchView";
import ListsView from "@/components/views/ListsView";
import DownloadsView from "@/components/views/DownloadsView";
import ScheduleView from "@/components/views/ScheduleView";
import LibraryView from "@/components/views/LibraryView";
import SettingsView from "@/components/views/SettingsView";
import NotificationsView from "@/components/views/NotificationsView";
import ProfileView from "@/components/views/ProfileView";
import HelpModal from "@/components/modals/HelpModal";

export default function App() {
  const [activeView, setActiveView] = useState<ViewName>("home");
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null);
  const [initialAction, setInitialAction] = useState<"play" | null>(null);
  const [readingChapter, setReadingChapter] = useState<string | null>(null);
  const [playingEpisode, setPlayingEpisode] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [dismissedOffline, setDismissedOffline] = useState(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem("anicat_offline_dismissed") === "true";
    }
    return false;
  });

  const handleDismissOffline = () => {
    setDismissedOffline(true);
    sessionStorage.setItem("anicat_offline_dismissed", "true");
  };
  const [notificationCount, setNotificationCount] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState<"checking" | "connected" | "failed">("checking");
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [activeUpdateOverlay, setActiveUpdateOverlay] = useState<{ active: boolean; message: string; isNative: boolean } | null>(null);

  const lastDataVersion = useRef<number | null>(null);
  
  // Poll health for offline banner, notifications, and live sync
  useEffect(() => {
    let failedAttempts = 0;
    
    async function checkSystem() {
      try {
        const status = await mediaApi.getHealthStatus();
        setHealthStatus(status);
        setConnectionStatus("connected");
        setConnectionError(null);
        
        // 1. Live Sync Detection
        if (status.data_version !== undefined) {
          if (lastDataVersion.current !== null && status.data_version > lastDataVersion.current) {
            console.log("Live Sync: Data changed (version " + lastDataVersion.current + " -> " + status.data_version + "). Refreshing views...");
            dispatchRefresh();
          }
          lastDataVersion.current = status.data_version;
        }

        // 2. Offline Detection
        const shouldBeOffline = status.api_authenticated && (status.is_offline || !status.api_connected);
        setIsOffline(shouldBeOffline);
        
        if (!shouldBeOffline) setDismissedOffline(false);
        setNotificationCount(status.unread_notifications || 0);
      } catch (err: any) {
        failedAttempts++;
        console.error("Health check failed:", err);
        if (failedAttempts >= 3) {
          setConnectionStatus("failed");
          setConnectionError(err?.message || "Connection refused (backend sidecar unreachable on port 13370).");
        }
      }
    }
    
    checkSystem();
    const quickInterval = setInterval(() => {
      if (failedAttempts < 3) {
        checkSystem();
      }
    }, 1500);

    const normalInterval = setInterval(() => {
      if (failedAttempts >= 3) {
        checkSystem();
      }
    }, 5000);

    return () => {
      clearInterval(quickInterval);
      clearInterval(normalInterval);
    };
  }, []);

  // Check if onboarding should be shown
  useEffect(() => {
    // Only show onboarding if user hasn't seen it yet
    const hasSeenOnboarding = localStorage.getItem("anicat_onboarding_seen");
    // Show onboarding if user hasn't seen it yet regardless of healthStatus.
    // Health checks may be slow or fail on first startup; onboarding should still appear.
    if (!hasSeenOnboarding) {
      setShowOnboarding(true);
    } else {
      setShowOnboarding(false);
    }
  }, [healthStatus]);

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
    localStorage.setItem("anicat_onboarding_seen", "true");
    window.location.reload();
  };

  const handleOnboardingSkip = () => {
    setShowOnboarding(false);
    localStorage.setItem("anicat_onboarding_seen", "true");
  };

  useKeyboardShortcuts({
    onNavigate: setActiveView,
    onCloseDetail: () => setSelectedItem(null),
    onToggleHelp: () => setShowHelp(h => !h),
  });

  const handleSelect = (item: MediaItem, action?: "play") => {
    setSelectedItem(item);
    setInitialAction(action || null);
  };

  const renderView = () => {
    switch (activeView) {
      case "home":
        return <HomeView onSelect={handleSelect} />;
      case "manga":
        return <MangaView onSelect={handleSelect} />;
      case "search":
        return <SearchView onSelect={handleSelect} />;
      case "lists":
        return <ListsView onSelect={handleSelect} />;
      case "downloads":
        return <DownloadsView />;
      case "library":
        return <LibraryView onSelect={handleSelect} />;
      case "settings":
        return (
          <SettingsView
            health={healthStatus}
            onUpdateStarted={(msg) => {
              const message = msg || "Update in progress...";
              const isNative = message.toLowerCase().includes("restart") || message.toLowerCase().includes("native");
              setActiveUpdateOverlay({ active: true, message, isNative });
              
              if (!isNative) {
                // For git development builds, reload automatically after 7 seconds so the user does NOT have to do anything themselves!
                setTimeout(() => {
                  window.location.reload();
                }, 7000);
              }
            }}
          />
        );
      case "notifications":
        return <NotificationsView onSelect={handleSelect} />;
      case "schedule":
        return <ScheduleView onSelect={handleSelect} />;
      case "profile":
        return <ProfileView />;
    }
  };

  const handleCopyDiagnostics = async () => {
    try {
      const report = [
        `# AniCat Diagnostic Report`,
        `Generated: ${new Date().toISOString()}`,
        `Platform: ${typeof window !== "undefined" ? window.navigator.userAgent : "Server"}`,
        `Client Origin: ${typeof window !== "undefined" ? window.location.origin : "Unknown"}`,
        `API Target: ${API_BASE_ORIGIN}`,
        `Connection Status: FAILED`,
        `Connection Error: ${connectionError || "None"}`,
        `Onboarding Seen: ${localStorage.getItem("anicat_onboarding_seen") || "false"}`,
        `\n## Common Resolution Steps:`,
        `1. A port conflict on 13370 is the most common cause. Close any other running instances.`,
        `2. On macOS, ensure Gatekeeper didn't block the sidecar by checking: System Settings -> Privacy & Security.`,
        `3. Check the detailed backend logs inside the application cache log folder.`
      ].join("\n");
      await navigator.clipboard.writeText(report);
      alert("Diagnostics report copied to your clipboard! Please send this to the developer.");
    } catch (e) {
      alert("Failed to copy report: " + String(e));
    }
  };

  const handleOpenLogs = async () => {
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("open_logs_folder");
    } catch (err) {
      console.error("Failed to open logs:", err);
      alert("Could not open logs folder. Please look inside your user Library/Caches/anicat folder manually.");
    }
  };

  if (connectionStatus === "failed") {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#050505] text-white p-6 font-sans">
        <div className="max-w-md w-full bg-white/[0.02] border border-white/[0.08] backdrop-blur-xl rounded-3xl p-8 space-y-6 shadow-2xl shadow-black/80 animate-fade-in">
          {/* Header */}
          <div className="space-y-2 text-center">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 mb-2 animate-pulse">
              <WifiOff size={28} />
            </div>
            <h2 className="text-2xl font-black tracking-tight">Sidecar Connection Failed</h2>
            <p className="text-sm text-gray-400">
              The AniCat frontend could not establish a connection with the local Python API service.
            </p>
          </div>

          {/* Diagnostic Details */}
          <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/[0.05] space-y-3.5 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-gray-500 font-medium">Frontend Client</span>
              <span className="px-2 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/20 font-bold">Online</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500 font-medium">Backend Sidecar</span>
              <span className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 font-bold">Unreachable</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500 font-medium">API Endpoint</span>
              <span className="font-mono text-gray-400">{API_BASE_ORIGIN}</span>
            </div>
            <div className="pt-2 border-t border-white/5 text-[10px] text-red-300/80 leading-relaxed font-mono whitespace-pre-wrap break-all">
              Error: {connectionError || "Failed to fetch"}
            </div>
          </div>

          {/* Action Steps */}
          <div className="space-y-3">
            <button
              onClick={handleCopyDiagnostics}
              className="w-full py-3 bg-accent hover:bg-accent-light text-white font-bold rounded-xl text-sm transition-all shadow-lg shadow-accent/20 active:scale-95 flex items-center justify-center space-x-2"
            >
              <span>Copy Diagnostics Report</span>
            </button>
            
            <button
              onClick={handleOpenLogs}
              className="w-full py-3 bg-white/[0.04] hover:bg-white/[0.08] text-white/80 border border-white/10 font-bold rounded-xl text-sm transition-all active:scale-95 flex items-center justify-center space-x-2"
            >
              <span>Open Application Logs</span>
            </button>

            <button
              onClick={() => {
                setConnectionStatus("checking");
                window.location.reload();
              }}
              className="w-full py-2.5 text-xs font-semibold text-gray-500 hover:text-white transition-colors"
            >
              Retry Connection
            </button>
          </div>

          {/* Footer Info */}
          <p className="text-[10px] text-center text-gray-600 leading-normal">
            A port conflict (another process on port 13370) or Gatekeeper quarantine is the most common cause on macOS.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen relative">
      <Sidebar activeView={activeView} onNavigate={setActiveView} notificationCount={notificationCount} health={healthStatus} />

      {/* Main content */}
      <main className="flex-1 ml-[72px] lg:ml-60 overflow-y-auto scrollbar-hide relative">
        {/* Offline Banner */}
        {isOffline && !dismissedOffline && (
          <div className="absolute top-0 left-0 right-0 z-[300] animate-slide-down">
            <div className="mx-6 mt-6 lg:mx-10 bg-red-500/10 border border-red-500/20 backdrop-blur-md rounded-2xl p-4 flex items-center justify-between shadow-xl">
              <div className="flex items-center space-x-3 text-red-400">
                <WifiOff size={18} />
                <span className="text-sm font-bold">
                  AniList API unreachable. Browsing local library mode.
                </span>
              </div>
              <div className="flex items-center space-x-4">
                <button 
                  onClick={async () => {
                    try {
                      await mediaApi.reconnect();
                      window.location.reload();
                    } catch (err) {
                      console.error("Reconnection failed:", err);
                    }
                  }}
                  className="px-3 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 text-xs font-bold transition-all border border-red-500/20"
                >
                  Retry Connection
                </button>
                <button 
                  onClick={handleDismissOffline}
                  className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <X size={16} className="text-gray-400" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Full-Screen Update Overlay */}
        {activeUpdateOverlay && activeUpdateOverlay.active && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-xl z-[9999] flex flex-col items-center justify-center p-6">
            <style>{`
              @keyframes progress-fill {
                0% { width: 0%; }
                100% { width: 100%; }
              }
              .animate-spin-slow {
                animation: spin 3s linear infinite;
              }
            `}</style>
            <div className="max-w-md w-full text-center space-y-6">
              {/* Spinning Logo / Icon */}
              <div className="relative flex justify-center">
                <div className="absolute -inset-4 bg-accent/20 rounded-full blur-xl animate-pulse" />
                <div className="relative p-6 bg-white/[0.02] border border-white/[0.08] rounded-full shadow-2xl">
                  <RotateCw size={48} className="text-accent animate-spin-slow" />
                </div>
              </div>

              {/* Title & Description */}
              <div className="space-y-3">
                <h2 className="text-2xl font-black tracking-tight text-white animate-pulse">
                  {activeUpdateOverlay.isNative ? "Installing Application Update" : "Updating Local Environment"}
                </h2>
                <p className="text-sm text-gray-400 leading-relaxed px-4">
                  {activeUpdateOverlay.message}
                </p>
              </div>

              {/* Loader Bar */}
              <div className="w-48 mx-auto h-1.5 bg-white/[0.04] border border-white/[0.08] rounded-full overflow-hidden">
                <div className="h-full bg-accent rounded-full" style={{
                  animation: 'progress-fill 10s linear forwards'
                }} />
              </div>

              {/* Auto Action Text */}
              <p className="text-xs text-gray-500 font-medium">
                {activeUpdateOverlay.isNative 
                  ? "The application will close and restart automatically. Please do not close the app."
                  : "Refreshing view automatically in a few seconds..."}
              </p>
            </div>
          </div>
        )}

        <AnimatePresence mode="wait">
          <motion.div
            key={activeView}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className={`p-6 lg:p-10 max-w-[1600px] ${isOffline && !dismissedOffline ? 'pt-24 lg:pt-28' : ''}`}
          >
            {renderView()}
          </motion.div>
        </AnimatePresence>
      </main>

      <NowPlaying />

      {/* Media detail drawer */}
      <AnimatePresence>
        {selectedItem && (
          <MediaDetail 
            item={selectedItem} 
            initialAction={initialAction || undefined}
            onRead={(chapter) => setReadingChapter(chapter)}
            onPlayEpisode={(episode) => setPlayingEpisode(episode)}
            onClose={() => {
              setSelectedItem(null);
              setInitialAction(null);
            }} 
          />
        )}
      </AnimatePresence>

      {selectedItem && readingChapter && (
        <MangaReader
          mediaId={selectedItem.id}
          chapterNumber={readingChapter}
          onClose={() => {
            setReadingChapter(null);
            dispatchRefresh();
          }}
          onProgressUpdate={async (num) => {
            try {
              await mediaApi.updateStatus(selectedItem.id, undefined, undefined, parseInt(num));
              dispatchRefresh();
            } catch (error) {
              console.error("Failed to update manga progress:", error);
            }
          }}
        />
      )}

      {selectedItem && playingEpisode && (
        <AnimePlayer
          mediaId={selectedItem.id}
          episodeNumber={playingEpisode}
          onClose={() => {
            setPlayingEpisode(null);
            dispatchRefresh();
          }}
          onEpisodeCompleted={async (num) => {
            try {
              await mediaApi.updateStatus(selectedItem.id, undefined, undefined, parseInt(num));
              dispatchRefresh();
            } catch (error) {
              console.error("Failed to update watch progress:", error);
            }
          }}
          onPlayNextEpisode={() => {
            const nextEp = String(parseInt(playingEpisode) + 1);
            setPlayingEpisode(nextEp);
          }}
          hasNextEpisode={selectedItem.episodes ? parseInt(playingEpisode) < selectedItem.episodes : true}
        />
      )}

      {showHelp && <HelpModal onClose={() => setShowHelp(false)} />}

      {showOnboarding && (
        <Onboarding 
          onComplete={handleOnboardingComplete} 
          onSkip={handleOnboardingSkip} 
        />
      )}
    </div>
  );
}
