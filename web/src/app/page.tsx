"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Sidebar, { type ViewName } from "@/components/layout/Sidebar";
import NowPlaying from "@/components/layout/NowPlaying";
import MediaDetail from "@/components/media/MediaDetail";
import MangaReader from "@/components/media/MangaReader";
import AnimePlayer from "@/components/media/AnimePlayer";
import useKeyboardShortcuts, { getPreviousView } from "@/lib/useKeyboardShortcuts";
import { useRemoteLogging } from "@/lib/useRemoteLogging";
import { useTheme } from "@/lib/useTheme";
import { useHealthPolling } from "@/lib/useHealthPolling";
import { useLiquidGlass } from "@/lib/useLiquidGlass";
import { AppStateProvider, useAppState } from "@/lib/AppStateContext";
import { mediaApi, API_BASE_ORIGIN, type PlaybackStatus } from "@/lib/api";
import { dispatchRefresh } from "@/lib/events";
import Onboarding from "@/components/layout/Onboarding";
import { X, WifiOff, RotateCw, Play } from "lucide-react";

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
import UpdateLogViewer from "@/components/modals/UpdateLogViewer";

export default function App() {
  // --- Extracted side-effect hooks (replace 2 large useEffect blocks) ---
  useRemoteLogging();
  useTheme();

  const {
    connectionStatus,
    connectionError,
    healthStatus,
    isOffline,
    dismissedOffline,
    notificationCount,
    dismissOffline,
  } = useHealthPolling();

  // Liquid Glass visual system
  const { enabled: liquidGlassEnabled } = useLiquidGlass();

  // --- App UI state ---
  const [activeView, setActiveView] = useState<ViewName>("home");
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Sync window fullscreen state (both Tauri window and HTML fullscreen)
  useEffect(() => {
    if (typeof window === "undefined") return;

    let unlisten: (() => void) | null = null;
    let active = true;

    async function setupFullscreenListener() {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        const appWindow = getCurrentWindow();
        
        // Initial check
        const initialFullscreen = await appWindow.isFullscreen();
        if (active) setIsFullscreen(initialFullscreen);

        // Resize triggers on entering/exiting fullscreen on macOS
        const unlistenFn = await appWindow.onResized(async () => {
          const fullscreen = await appWindow.isFullscreen();
          if (active) setIsFullscreen(fullscreen);
        });
        unlisten = unlistenFn;
      } catch (err) {
        console.warn("Failed to listen to Tauri window resize / fullscreen events:", err);
      }
    }

    setupFullscreenListener();

    const handleHtmlFullscreenChange = () => {
      const isHtmlFull = !!(
        document.fullscreenElement ||
        (document as any).webkitFullscreenElement ||
        (document as any).mozFullScreenElement ||
        (document as any).msFullscreenElement
      );
      setIsFullscreen(isHtmlFull);
    };

    document.addEventListener("fullscreenchange", handleHtmlFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleHtmlFullscreenChange);
    document.addEventListener("mozfullscreenchange", handleHtmlFullscreenChange);
    document.addEventListener("MSFullscreenChange", handleHtmlFullscreenChange);

    return () => {
      active = false;
      if (unlisten) {
        unlisten();
      }
      document.removeEventListener("fullscreenchange", handleHtmlFullscreenChange);
      document.removeEventListener("webkitfullscreenchange", handleHtmlFullscreenChange);
      document.removeEventListener("mozfullscreenchange", handleHtmlFullscreenChange);
      document.removeEventListener("MSFullscreenChange", handleHtmlFullscreenChange);
    };
  }, []);

  const [showHelp, setShowHelp] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(() => {
    if (typeof window === "undefined") return false;
    return !localStorage.getItem("anicat_onboarding_seen");
  });
  const [activeUpdateOverlay, setActiveUpdateOverlay] = useState<{
    active: boolean;
    message: string;
    isNative: boolean;
  } | null>(null);

  // Media item state lives in AppStateContext
  const appState = useAppState();

  const updateOverlayTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const updateStartedAtRef = useRef<number | null>(null);
  const updateDismissedRef = useRef(false);

  const clearUpdateOverlayTimeout = () => {
    if (updateOverlayTimeoutRef.current) {
      clearTimeout(updateOverlayTimeoutRef.current);
      updateOverlayTimeoutRef.current = null;
    }
  };

  // Reset the stale-update tracker when updating flag goes away
  useEffect(() => {
    if (healthStatus?.updating && !updateStartedAtRef.current && !updateDismissedRef.current) {
      updateStartedAtRef.current = Date.now();
    } else if (!healthStatus?.updating) {
      updateStartedAtRef.current = null;
      updateDismissedRef.current = false;
    }
  }, [healthStatus?.updating]);

  // Cleanup update overlay timeout on unmount
  useEffect(() => {
    return () => {
      clearUpdateOverlayTimeout();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    onCloseDetail: appState.closeDetail,
    onToggleHelp: () => setShowHelp(h => !h),
  });

  // UX-25: Pull-to-refresh — refresh all queries when scrolling to top
  const handleScroll = useCallback((e: React.UIEvent<HTMLElement>) => {
    const target = e.currentTarget;
    if (target.scrollTop === 0) {
      target.style.setProperty('--pull-indicator-opacity', '1');
    } else {
      target.style.setProperty('--pull-indicator-opacity', '0');
    }
  }, []);

  const renderView = () => {
    switch (activeView) {
      case "home":
        return <HomeView onSelect={appState.selectItem} />;
      case "manga":
        return <MangaView onSelect={appState.selectItem} />;
      case "search":
        return <SearchView onSelect={appState.selectItem} />;
      case "lists":
        return <ListsView onSelect={appState.selectItem} />;
      case "downloads":
        return <DownloadsView />;
      case "library":
        return <LibraryView onSelect={appState.selectItem} />;
      case "settings":
        return (
          <SettingsView
            health={healthStatus}
            onUpdateStarted={(msg) => {
              const message = msg || "Update in progress...";
              const isNative = message.toLowerCase().includes("restart") || message.toLowerCase().includes("native");
              clearUpdateOverlayTimeout();
              setActiveUpdateOverlay({ active: true, message, isNative });
              
              if (!isNative) {
                // For git development builds, reload automatically after 7 seconds so the user does NOT have to do anything themselves!
                setTimeout(() => {
                  window.location.reload();
                }, 7000);
              } else {
                updateOverlayTimeoutRef.current = setTimeout(() => {
                  setActiveUpdateOverlay(null);
                  updateOverlayTimeoutRef.current = null;
                }, 300000); // 5 min — matches backend stale-file cleanup
              }
            }}
          />
        );
      case "notifications":
        return <NotificationsView onSelect={appState.selectItem} />;
      case "schedule":
        return <ScheduleView onSelect={appState.selectItem} />;
      case "profile":
        return <ProfileView onSelect={appState.selectItem} />;
    }
  };

  const handleCopyDiagnostics = async () => {
    try {
      const report = [
        `# AniCat Diagnostic Report`,
        `Generated: ${new Date().toISOString()}`,
        `Platform: ${typeof window !== "undefined" ? window.navigator.userAgent : "Server"}`,
        `Client Origin: ${typeof window !== "undefined" ? window.location.origin : "Unknown"}`,
        `Server Address: ${API_BASE_ORIGIN}`,
        `Connection Status: FAILED`,
        `Connection Error: ${connectionError || "None"}`,
        `App Version: ${healthStatus?.current_version || "Unknown"}`,
        `Onboarding Seen: ${localStorage.getItem("anicat_onboarding_seen") || "false"}`,
        `\n## Common Fixes:`,
        `1. Restart the app from your Applications folder.`,
        `2. On macOS, go to System Settings > Privacy & Security and check for blocked apps.`,
        `3. If the issue persists, try restarting your Mac.`
      ].join("\n");
      await navigator.clipboard.writeText(report);
      alert("Diagnostic report copied to clipboard. Please send this to the developer for help.");
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

  // UX-05: During startup polling, check if there's a last playback to resume
  const [startupPlayback, setStartupPlayback] = useState<PlaybackStatus>(null);

  useEffect(() => {
    if (connectionStatus === "checking" && !healthStatus?.updating) {
      mediaApi.getPlaybackStatus()
        .then(data => setStartupPlayback(data))
        .catch(() => setStartupPlayback(null));
    }
  }, [connectionStatus, healthStatus?.updating]);

  if (connectionStatus === "checking" && !healthStatus?.updating) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#050505] text-white p-6 font-sans">
        <style>{`
          @keyframes progress-fill-startup {
            0% { width: 0%; }
            100% { width: 100%; }
          }
          .animate-spin-slow {
            animation: spin 3s linear infinite;
          }
        `}</style>
        <div className="max-w-md w-full text-center space-y-6">
          <div className="relative flex justify-center">
            <div className="absolute -inset-4 bg-accent/20 rounded-full blur-xl animate-pulse" />
            <div className="relative p-6 bg-white/[0.02] border border-white/[0.08] rounded-full shadow-2xl">
              <RotateCw size={48} className="text-accent animate-spin-slow" />
            </div>
          </div>

          <div className="space-y-3">
            <h2 className="text-2xl font-black tracking-tight text-white animate-pulse">
              Starting up...
            </h2>
            <p className="text-sm text-gray-400 leading-relaxed px-4">
              Anicat is preparing everything. This usually only takes a moment.
            </p>
          </div>

          {/* UX-05: Resume Last — skip straight to player from startup */}
          {startupPlayback && (
            <button
              onClick={() => {
                appState.startPlayback(
                  { id: startupPlayback.media_id, title: { english: startupPlayback.media_title, romaji: startupPlayback.media_title }, cover_image: { large: "" } } as any,
                  startupPlayback.episode
                );
              }}
              className="inline-flex items-center space-x-3 px-6 py-3 bg-accent/20 hover:bg-accent/30 border border-accent/30 text-accent font-bold rounded-xl text-sm transition-all active:scale-95"
            >
              <Play size={16} fill="currentColor" />
              <span>Resume {startupPlayback.media_title} Ep {startupPlayback.episode}</span>
            </button>
          )}

          <div className="w-48 mx-auto h-1.5 bg-white/[0.04] border border-white/[0.08] rounded-full overflow-hidden">
            <div className="h-full bg-accent rounded-full" style={{
              animation: 'progress-fill-startup 8s linear forwards'
            }} />
          </div>
        </div>
      </div>
    );
  }

  // Show a friendly "Updating..." screen when the background process restarts
  // during an update, instead of the scary "Connection Failed" error.
  // Auto-dismiss if the flag has been stuck for >5 minutes (backend cleans up
  // stale flags after 5 min).
  const UPDATING_STALE_TIMEOUT = 300000; // 5 minutes
  const isUpdatingStale = updateStartedAtRef.current && (Date.now() - updateStartedAtRef.current) > UPDATING_STALE_TIMEOUT;
  if (isUpdatingStale) {
    updateDismissedRef.current = true;
  }
  if (healthStatus?.updating && !isUpdatingStale && !updateDismissedRef.current) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#050505] text-white p-6 font-sans">
        <div className="max-w-md w-full text-center space-y-6 animate-fade-in">
          <div className="relative flex justify-center">
            <div className="absolute -inset-4 bg-accent/20 rounded-full blur-xl animate-pulse" />
            <div className="relative p-6 bg-white/[0.02] border border-white/[0.08] rounded-full shadow-2xl">
              <RotateCw size={48} className="text-accent animate-spin-slow" />
            </div>
          </div>
          <div className="space-y-3">
            <h2 className="text-2xl font-black tracking-tight text-white">
              Updating Anicat...
            </h2>
            <p className="text-sm text-gray-400 leading-relaxed px-4">
              Downloading the latest version. This may take a few minutes depending on your connection speed.
            </p>
          </div>
          <div className="w-48 mx-auto h-1.5 bg-white/[0.04] border border-white/[0.08] rounded-full overflow-hidden">
            <div className="h-full bg-accent rounded-full animate-pulse" style={{ width: '60%' }} />
          </div>
          <p className="text-[11px] text-gray-500 font-medium">
            The app will restart automatically when ready.
          </p>
        </div>
      </div>
    );
  }

  if (connectionStatus === "failed") {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#050505] text-white p-6 font-sans">
        <div className="max-w-md w-full bg-white/[0.02] border border-white/[0.08] backdrop-blur-xl rounded-3xl p-8 space-y-6 shadow-2xl shadow-black/80 animate-fade-in">
          <div className="space-y-2 text-center">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 mb-2 animate-pulse">
              <WifiOff size={28} />
            </div>
            <h2 className="text-2xl font-black tracking-tight">Connection Lost</h2>
            <p className="text-sm text-gray-400">
              Anicat couldn't reach its background service. This usually means the app needs to be restarted.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/[0.05] space-y-3.5 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-gray-500 font-medium">Anicat Window</span>
              <span className="px-2 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/20 font-bold">Ready</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500 font-medium">Background Service</span>
              <span className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 font-bold">Not Responding</span>
            </div>
            {healthStatus?.current_version && (
              <div className="flex justify-between items-center">
                <span className="text-gray-500 font-medium">Version</span>
                <span className="font-mono text-gray-400">{healthStatus.current_version}</span>
              </div>
            )}
            {connectionError && (
              <div className="pt-2 border-t border-white/5 text-[10px] text-red-300/80 leading-relaxed font-mono whitespace-pre-wrap break-all">
                Details: {connectionError}
              </div>
            )}
          </div>

          <div className="space-y-3">
            <button
              onClick={() => window.location.reload()}
              className="w-full py-3 bg-accent hover:bg-accent-light text-white font-bold rounded-xl text-sm transition-all shadow-lg shadow-accent/20 active:scale-95 flex items-center justify-center space-x-2"
            >
              <RotateCw size={16} />
              <span>Try Again</span>
            </button>

            <button
              onClick={handleCopyDiagnostics}
              className="w-full py-3 bg-white/[0.04] hover:bg-white/[0.08] text-white/80 border border-white/10 font-bold rounded-xl text-sm transition-all active:scale-95 flex items-center justify-center space-x-2"
            >
              <span>Copy Report for Support</span>
            </button>
          </div>

          <p className="text-[10px] text-center text-gray-600 leading-normal">
            Try restarting the app from your Applications folder. If the problem keeps happening, send the report above to the developer.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen relative">
      <Sidebar
        activeView={activeView}
        onNavigate={setActiveView}
        notificationCount={notificationCount}
        health={healthStatus}
      />

      {/* Liquid Glass — Native visionOS style doesn't use artificial cursor lights */}

      {/* Main content */}
      <main
        className="flex-1 ml-[72px] lg:ml-60 overflow-y-auto scrollbar-hide scroll-container relative z-10 transform-gpu translate-z-0 will-change-scroll"
        // UX-25: Pull-to-refresh — refresh all queries when scrolling to top
        onScroll={handleScroll}
      >
        {/* UX-25: Pull-to-refresh indicator bar */}
        <div className="sticky top-0 left-0 right-0 z-[200] h-0.5 bg-accent/0 transition-all duration-300"
          style={{ opacity: 'var(--pull-indicator-opacity, 0)', boxShadow: 'var(--pull-indicator-opacity, 0) === "1" ? "0 2px 20px rgba(236,72,153,0.3)" : "none"' }}
        />
        {/* Offline / Provider-Status Banner */}
        {isOffline && !dismissedOffline && (
          <div className="absolute top-0 left-0 right-0 z-[300] animate-slide-down">
            <div className="mx-6 mt-6 lg:mx-10 bg-amber-500/10 border border-amber-500/20 backdrop-blur-md rounded-2xl p-4 flex items-center justify-between shadow-xl">
              <div className="flex items-center space-x-3 text-amber-400 min-w-0">
                <WifiOff size={18} className="shrink-0" />
                <div className="min-w-0">
                  <span className="text-sm font-bold block truncate">
                    {healthStatus?.provider_status
                      ? healthStatus.provider_status
                      : "Could not connect to AniList. You can still browse your local library."}
                  </span>
                </div>
              </div>
              <div className="flex items-center space-x-4 shrink-0">
                <button 
                  onClick={async () => {
                    try {
                      await mediaApi.reconnect();
                      window.location.reload();
                    } catch (err) {
                      console.error("Reconnection failed:", err);
                    }
                  }}
                  className="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 text-xs font-bold transition-all border border-amber-500/20"
                >
                  Retry Connection
                </button>
                <button 
                  onClick={dismissOffline}
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

              {/* Update Logs: Show/Hide button + live feed */}
              <UpdateLogViewer />
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

      <NowPlaying
        onPlay={(mediaId, episode) => {
          // Find a matching media item from appState to open the player
          const item = appState.selectedItem;
          if (item && item.id === mediaId) {
            appState.startPlayback(item, episode);
          }
        }}
      />

      {/* Media detail drawer */}
      <AnimatePresence>
        {appState.selectedItem && (
          <MediaDetail 
            item={appState.selectedItem} 
            initialAction={appState.initialAction || undefined}
            onRead={(chapter) => {
              appState.startReading(appState.selectedItem!, chapter);
            }}
            onPlayEpisode={(episode) => {
              appState.startPlayback(appState.selectedItem!, episode);
            }}
            onClose={appState.closeDetail} 
          />
        )}
      </AnimatePresence>

      {appState.readingItem && appState.readingChapter && (
        <MangaReader
          mediaId={appState.readingItem.id}
          chapterNumber={appState.readingChapter}
          hasPrevChapter={parseInt(appState.readingChapter) > 1}
          hasNextChapter={appState.readingItem.chapters ? parseInt(appState.readingChapter) < appState.readingItem.chapters : true}
          onClose={() => {
            appState.closeReader();
            dispatchRefresh();
          }}
          onProgressUpdate={async (num) => {
            try {
              await mediaApi.updateStatus(appState.readingItem!.id, undefined, undefined, parseInt(num));
              dispatchRefresh();
            } catch (error) {
              console.error("Failed to update manga progress:", error);
            }
          }}
          onNavigateChapter={async (direction) => {
            const current = parseInt(appState.readingChapter!);
            const next = direction === "next" ? current + 1 : current - 1;
            if (next < 1) return;
            // Save progress on current chapter before navigating
            try {
              await mediaApi.updateStatus(appState.readingItem!.id, undefined, undefined, current);
            } catch {}
            appState.startReading(appState.readingItem!, String(next));
            dispatchRefresh();
          }}
        />
      )}

      {appState.playingItem && appState.playingEpisode && (
        <AnimePlayer
          mediaId={appState.playingItem.id}
          malId={appState.playingItem.id_mal}
          episodeNumber={appState.playingEpisode}
          totalEpisodes={appState.playingItem.episodes || undefined}
          onClose={() => {
            appState.closePlayback();
            // UX-28: Navigate back to the view that launched the player
            setActiveView(getPreviousView());
            dispatchRefresh();
          }}
          onEpisodeCompleted={async (num) => {
            try {
              await mediaApi.updateStatus(appState.playingItem!.id, undefined, undefined, parseInt(num));
              dispatchRefresh();
            } catch (error) {
              console.error("Failed to update watch progress:", error);
            }
          }}
          onPlayNextEpisode={() => {
            const nextEp = String(parseInt(appState.playingEpisode!) + 1);
            appState.setEpisode(nextEp);
          }}
          hasNextEpisode={appState.playingItem.episodes ? parseInt(appState.playingEpisode!) < appState.playingItem.episodes : true}
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
