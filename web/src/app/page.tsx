"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Sidebar, { type ViewName } from "@/components/layout/Sidebar";
import NowPlaying from "@/components/layout/NowPlaying";
import MediaDetail from "@/components/media/MediaDetail";
import MangaReader from "@/components/media/MangaReader";
import AnimePlayer from "@/components/media/AnimePlayer";
import useKeyboardShortcuts from "@/lib/useKeyboardShortcuts";
import { mediaApi, type MediaItem, type HealthStatus } from "@/lib/api";
import { dispatchRefresh } from "@/lib/events";
import Onboarding from "@/components/layout/Onboarding";
import { X, WifiOff, RotateCcw } from "lucide-react";

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
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [refreshNeeded, setRefreshNeeded] = useState(false);

  const lastDataVersion = useRef<number | null>(null);
  
  // Poll health for offline banner, notifications, and live sync
  useEffect(() => {
    async function checkSystem() {
      try {
        const status = await mediaApi.getHealthStatus();
        setHealthStatus(status);
        
        // 1. Live Sync Detection
        if (status.data_version !== undefined) {
          if (lastDataVersion.current !== null && status.data_version > lastDataVersion.current) {
            console.log("Live Sync: Data changed (version " + lastDataVersion.current + " -> " + status.data_version + "). Refreshing views...");
            dispatchRefresh();
          }
          lastDataVersion.current = status.data_version;
        }

        // 2. Offline Detection
        // Only show offline if explicitly told so by backend AND api is disconnected AND we are logged in
        const shouldBeOffline = status.api_authenticated && (status.is_offline || !status.api_connected);
        setIsOffline(shouldBeOffline);
        
        if (!shouldBeOffline) setDismissedOffline(false);
        setNotificationCount(status.unread_notifications || 0);
      } catch {
        // Silent fail on health poll
      }
    }
    checkSystem();
    const interval = setInterval(checkSystem, 10000); // Poll faster (10s) for snappier sync
    return () => clearInterval(interval);
  }, []);

  // Check if onboarding should be shown
  useEffect(() => {
    // Only show onboarding if user hasn't seen it yet
    const hasSeenOnboarding = localStorage.getItem("anicat_onboarding_seen");
    if (!hasSeenOnboarding && healthStatus) {
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
        return <SettingsView health={healthStatus} onUpdateStarted={() => setRefreshNeeded(true)} />;
      case "notifications":
        return <NotificationsView onSelect={handleSelect} />;
      case "schedule":
        return <ScheduleView onSelect={handleSelect} />;
      case "profile":
        return <ProfileView />;
    }
  };

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

        {/* Refresh Banner */}
        {refreshNeeded && (
          <div className={`absolute top-0 left-0 right-0 z-[300] animate-slide-down ${isOffline && !dismissedOffline ? 'mt-24' : ''}`}>
            <div className="mx-6 mt-6 lg:mx-10 bg-green-500/10 border border-green-500/20 backdrop-blur-md rounded-2xl p-4 flex items-center justify-between shadow-xl">
              <div className="flex items-center space-x-3 text-green-400">
                <RotateCcw size={18} className="animate-spin-slow" />
                <span className="text-sm font-bold">
                  Update in progress. Please refresh in about a minute to apply changes.
                </span>
              </div>
              <div className="flex items-center space-x-4">
                <button 
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 rounded-lg bg-green-500 hover:bg-green-400 text-white text-xs font-bold transition-all shadow-lg shadow-green-500/20"
                >
                  Refresh Now
                </button>
                <button 
                  onClick={() => setRefreshNeeded(false)}
                  className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <X size={16} className="text-gray-400" />
                </button>
              </div>
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
