"use client";

import { useState, useEffect, useCallback } from "react";
import Sidebar, { type ViewName } from "@/components/layout/Sidebar";
import MediaCard from "@/components/media/MediaCard";
import MediaRow from "@/components/media/MediaRow";
import MediaDetail from "@/components/media/MediaDetail";
import Hero from "@/components/media/Hero";
import { mediaApi, type MediaItem, type QueueItem } from "@/lib/api";
import {
  Search,
  Loader2,
  Monitor,
  BookOpen,
  Download,
  X,
  RotateCcw,
  Clock,
  AlertCircle,
  CheckCircle2,
  Save,
  Cpu,
  PlayCircle,
  HardDrive,
  Globe,
  Library,
  Heart,
  Bookmark,
  Pause,
  XCircle,
} from "lucide-react";

// ─── Home View ────────────────────────────────────────
function HomeView({ onSelect }: { onSelect: (item: MediaItem) => void }) {
  const [watchingList, setWatchingList] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await mediaApi.getUserList("watching", "ANIME");
        setWatchingList(data.media || []);
      } catch (err) {
        console.error("Failed to load watching list:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-accent" size={36} />
      </div>
    );
  }

  const heroItem = watchingList[0];

  return (
    <div className="space-y-8 animate-fade-in">
      {heroItem && <Hero item={heroItem} onSelect={onSelect} />}
      <MediaRow title="Continue Watching" items={watchingList} onSelect={onSelect} />
    </div>
  );
}

// ─── Search View ──────────────────────────────────────
function SearchView({ onSelect }: { onSelect: (item: MediaItem) => void }) {
  const [query, setQuery] = useState("");
  const [type, setType] = useState<"ANIME" | "MANGA">("ANIME");
  const [results, setResults] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await mediaApi.search(query, type, 1);
        setResults(data.media || []);
        setHasMore(data.page_info?.has_next_page || false);
        setPage(1);
      } catch {
        console.error("Search failed");
      } finally {
        setLoading(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [query, type]);

  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const loadMore = async () => {
    if (loadingMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const data = await mediaApi.search(query, type, nextPage);
      setResults(prev => [...prev, ...(data.media || [])]);
      setHasMore(data.page_info?.has_next_page || false);
      setPage(nextPage);
    } catch {
      console.error("Load more failed");
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Search header */}
      <div className="space-y-6">
        <div className="flex items-end justify-between">
          <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">Search</h1>
          <div className="flex bg-white/[0.04] p-1 rounded-xl border border-white/[0.06]">
            <button
              onClick={() => setType("ANIME")}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
                type === "ANIME" ? "bg-accent text-white shadow-lg shadow-accent/20" : "text-gray-500 hover:text-white"
              }`}
            >
              <Monitor size={16} />
              <span>Anime</span>
            </button>
            <button
              onClick={() => setType("MANGA")}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
                type === "MANGA" ? "bg-accent text-white shadow-lg shadow-accent/20" : "text-gray-500 hover:text-white"
              }`}
            >
              <BookOpen size={16} />
              <span>Manga</span>
            </button>
          </div>
        </div>

        <div className="relative group">
          <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-600 group-focus-within:text-accent transition-colors" size={22} />
          <input
            autoFocus
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Search for ${type.toLowerCase()}...`}
            className="w-full bg-white/[0.03] border border-white/[0.08] rounded-2xl py-4 pl-14 pr-6 text-lg font-medium focus:outline-none focus:border-accent/40 focus:bg-white/[0.04] transition-all placeholder:text-gray-700"
          />
          {loading && (
            <Loader2 className="absolute right-5 top-1/2 -translate-y-1/2 text-accent animate-spin" size={22} />
          )}
        </div>
      </div>

      {/* Results */}
      {results.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-5">
          {results.map((item) => (
            <MediaCard key={item.id} item={item} onSelect={onSelect} />
          ))}
        </div>
      ) : query && !loading ? (
        <div className="text-center py-24">
          <Search size={40} className="mx-auto text-gray-800 mb-4" />
          <p className="text-gray-600 font-semibold">No {type.toLowerCase()} found for &quot;{query}&quot;</p>
        </div>
      ) : null}

      {hasMore && (
        <div className="flex justify-center pt-8">
          <button
            onClick={loadMore}
            disabled={loadingMore}
            className="px-8 py-3 bg-white/[0.04] hover:bg-accent hover:text-white rounded-xl font-bold transition-all border border-white/[0.06] flex items-center space-x-3 group"
          >
            {loadingMore ? <Loader2 className="animate-spin" size={18} /> : <RotateCcw size={16} className="group-hover:rotate-180 transition-transform duration-500" />}
            <span>{loadingMore ? "Loading..." : "Load More"}</span>
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Lists View ───────────────────────────────────────
const LIST_TABS = [
  { key: "watching", label: "Watching", icon: Monitor },
  { key: "completed", label: "Completed", icon: CheckCircle2 },
  { key: "planning", label: "Planning", icon: Bookmark },
  { key: "paused", label: "Paused", icon: Pause },
  { key: "dropped", label: "Dropped", icon: XCircle },
];

function ListsView({ onSelect }: { onSelect: (item: MediaItem) => void }) {
  const [activeTab, setActiveTab] = useState("watching");
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    setLoading(true);
    mediaApi.getUserList(activeTab, "ANIME", 1)
      .then(data => {
        setItems(data.media || []);
        setHasMore(data.page_info?.has_next_page || false);
        setPage(1);
      })
      .catch(err => {
        console.error("Failed to load list:", err);
        setItems([]);
      })
      .finally(() => setLoading(false));
  }, [activeTab]);

  const loadMore = async () => {
    if (loadingMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const data = await mediaApi.getUserList(activeTab, "ANIME", nextPage);
      setItems(prev => [...prev, ...(data.media || [])]);
      setHasMore(data.page_info?.has_next_page || false);
      setPage(nextPage);
    } catch {
      console.error("Load more failed");
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-end justify-between">
        <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">My Lists</h1>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 bg-white/[0.02] p-1 rounded-xl border border-white/[0.06] overflow-x-auto scrollbar-hide">
        {LIST_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg font-semibold text-sm whitespace-nowrap transition-all ${
              activeTab === tab.key
                ? "bg-accent text-white shadow-lg shadow-accent/20"
                : "text-gray-500 hover:text-white"
            }`}
          >
            <tab.icon size={15} />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="animate-spin text-accent" size={36} />
        </div>
      ) : items.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-5">
          {items.map((item) => (
            <MediaCard key={item.id} item={item} onSelect={onSelect} />
          ))}
        </div>
      ) : (
        <div className="text-center py-24 border-2 border-dashed border-white/[0.04] rounded-2xl">
          <Heart size={40} className="mx-auto text-gray-800 mb-4" />
          <p className="text-gray-600 font-semibold">This list is empty</p>
          <p className="text-gray-700 text-sm mt-1">Search for anime and add them to your list.</p>
        </div>
      )}

      {hasMore && (
        <div className="flex justify-center pt-8">
          <button
            onClick={loadMore}
            disabled={loadingMore}
            className="px-8 py-3 bg-white/[0.04] hover:bg-accent hover:text-white rounded-xl font-bold transition-all border border-white/[0.06] flex items-center space-x-3 group"
          >
            {loadingMore ? <Loader2 className="animate-spin" size={18} /> : <RotateCcw size={16} className="group-hover:rotate-180 transition-transform duration-500" />}
            <span>{loadingMore ? "Loading..." : "Load More"}</span>
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Downloads View ───────────────────────────────────
function DownloadsView() {
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

// ─── Library View ─────────────────────────────────────
function LibraryView({ onSelect }: { onSelect: (item: MediaItem) => void }) {
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    mediaApi.getUserList("completed", "ANIME", 1)
      .then(data => {
        setItems(data.media || []);
        setHasMore(data.page_info?.has_next_page || false);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  const loadMore = async () => {
    if (loadingMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const data = await mediaApi.getUserList("completed", "ANIME", nextPage);
      setItems(prev => [...prev, ...(data.media || [])]);
      setHasMore(data.page_info?.has_next_page || false);
      setPage(nextPage);
    } catch {
      console.error("Load more failed");
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">Library</h1>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="animate-spin text-accent" size={36} />
        </div>
      ) : items.length > 0 ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-5">
            {items.map((item) => (
              <MediaCard key={item.id} item={item} onSelect={onSelect} />
            ))}
          </div>
          {hasMore && (
            <div className="flex justify-center pt-8">
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className="px-8 py-3 bg-white/[0.04] hover:bg-accent hover:text-white rounded-xl font-bold transition-all border border-white/[0.06] flex items-center space-x-3 group"
              >
                {loadingMore ? <Loader2 className="animate-spin" size={18} /> : <RotateCcw size={16} className="group-hover:rotate-180 transition-transform duration-500" />}
                <span>{loadingMore ? "Loading..." : "Load More"}</span>
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-24 border-2 border-dashed border-white/[0.04] rounded-2xl">
          <Library size={40} className="mx-auto text-gray-800 mb-4" />
          <p className="text-gray-600 font-semibold">Library is empty</p>
          <p className="text-gray-700 text-sm mt-1">Your completed anime will appear here.</p>
        </div>
      )}
    </div>
  );
}

// ─── Settings View ────────────────────────────────────
function SettingsView() {
  const [config, setConfig] = useState<Record<string, Record<string, unknown>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState("general");

  useEffect(() => {
    mediaApi.getConfig()
      .then(setConfig)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await mediaApi.updateConfig(config);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      console.error("Save failed");
    } finally {
      setSaving(false);
    }
  };

  const updateField = (section: string, field: string, value: unknown) => {
    setConfig(prev => prev ? {
      ...prev,
      [section]: { ...prev[section], [field]: value }
    } : null);
  };

  if (loading || !config) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-accent" size={36} />
      </div>
    );
  }

  const tabs = [
    { id: "general", label: "Core", icon: Cpu },
    { id: "stream", label: "Streaming", icon: PlayCircle },
    { id: "downloads", label: "Downloads", icon: HardDrive },
    { id: "anilist", label: "AniList", icon: Globe },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-end justify-between">
        <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">Settings</h1>
        <button
          onClick={handleSave}
          disabled={saving}
          className={`flex items-center space-x-2 px-6 py-3 rounded-xl font-bold text-sm transition-all active:scale-95 ${
            saved
              ? "bg-green-500 text-white"
              : "bg-accent text-white hover:bg-accent-light shadow-lg shadow-accent/20"
          }`}
        >
          {saving ? <Loader2 size={16} className="animate-spin" /> : saved ? <CheckCircle2 size={16} /> : <Save size={16} />}
          <span>{saved ? "Saved!" : "Save"}</span>
        </button>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Tab nav */}
        <div className="lg:w-52 flex lg:flex-col space-x-2 lg:space-x-0 lg:space-y-1 overflow-x-auto scrollbar-hide shrink-0">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-3 px-4 py-3 rounded-xl font-semibold text-sm whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? "bg-accent text-white shadow-lg"
                  : "text-gray-500 hover:text-white hover:bg-white/[0.04]"
              }`}
            >
              <tab.icon size={17} />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Settings form */}
        <div className="flex-1 space-y-6 max-w-2xl">
          {activeTab === "general" && (
            <div className="space-y-6 animate-fade-in">
              <SettingField
                label="Default Provider"
                description="Where to scrape video content from."
              >
                <select
                  value={String(config.general?.provider || "animepahe")}
                  onChange={(e) => updateField("general", "provider", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  <option value="animepahe">AnimePahe</option>
                  <option value="allmanga">AllManga</option>
                </select>
              </SettingField>

              <SettingField
                label="Media Tracker"
                description="The source for your list and metadata."
              >
                <select
                  value={String(config.general?.media_api || "anilist")}
                  onChange={(e) => updateField("general", "media_api", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  <option value="anilist">AniList</option>
                  <option value="jikan">Jikan / MyAnimeList</option>
                </select>
              </SettingField>
            </div>
          )}

          {activeTab === "stream" && (
            <div className="space-y-6 animate-fade-in">
              <SettingField label="Quality" description="Preferred playback quality.">
                <select
                  value={String(config.stream?.quality || "1080")}
                  onChange={(e) => updateField("stream", "quality", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  <option value="1080">1080p</option>
                  <option value="720">720p</option>
                  <option value="480">480p</option>
                  <option value="360">360p</option>
                </select>
              </SettingField>

              <SettingField label="Translation Type" description="Sub or dub.">
                <select
                  value={String(config.stream?.translation_type || "sub")}
                  onChange={(e) => updateField("stream", "translation_type", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  <option value="sub">Subtitled (JP)</option>
                  <option value="dub">Dubbed (EN)</option>
                </select>
              </SettingField>
            </div>
          )}

          {activeTab === "downloads" && (
            <div className="space-y-6 animate-fade-in">
              <SettingField label="Downloads Directory" description="Where downloaded media is stored on disk.">
                <div className="relative">
                  <HardDrive size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600" />
                  <input
                    type="text"
                    value={String(config.downloads?.downloads_dir || "")}
                    onChange={(e) => updateField("downloads", "downloads_dir", e.target.value)}
                    className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl py-3.5 pl-11 pr-4 text-sm font-medium focus:border-accent/40 outline-none transition-all"
                  />
                </div>
              </SettingField>
            </div>
          )}

          {activeTab === "anilist" && (
            <div className="space-y-6 animate-fade-in">
              <SettingField label="AniList Token" description="Your AniList API token for authentication.">
                <input
                  type="password"
                  value={String(config.anilist?.token || "")}
                  onChange={(e) => updateField("anilist", "token", e.target.value)}
                  placeholder="Paste your token here..."
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all placeholder:text-gray-700"
                />
              </SettingField>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SettingField({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2.5 p-5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
      <label className="text-xs font-bold text-accent uppercase tracking-wider">{label}</label>
      {children}
      {description && <p className="text-[11px] text-gray-600">{description}</p>}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────
export default function App() {
  const [activeView, setActiveView] = useState<ViewName>("home");
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null);

  const handleSelect = (item: MediaItem) => {
    setSelectedItem(item);
  };

  const renderView = () => {
    switch (activeView) {
      case "home":
        return <HomeView onSelect={handleSelect} />;
      case "search":
        return <SearchView onSelect={handleSelect} />;
      case "lists":
        return <ListsView onSelect={handleSelect} />;
      case "downloads":
        return <DownloadsView />;
      case "library":
        return <LibraryView onSelect={handleSelect} />;
      case "settings":
        return <SettingsView />;
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar activeView={activeView} onNavigate={setActiveView} />

      {/* Main content */}
      <main className="flex-1 ml-[72px] lg:ml-60 overflow-y-auto scrollbar-hide">
        <div className="p-6 lg:p-10 max-w-[1600px]">
          {renderView()}
        </div>
      </main>

      {/* Media detail panel */}
      {selectedItem && (
        <MediaDetail item={selectedItem} onClose={() => setSelectedItem(null)} />
      )}
    </div>
  );
}
