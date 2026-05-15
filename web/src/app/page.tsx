"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Sidebar, { type ViewName } from "@/components/layout/Sidebar";
import NowPlaying from "@/components/layout/NowPlaying";
import MediaCard from "@/components/media/MediaCard";
import MediaRow from "@/components/media/MediaRow";
import MediaDetail from "@/components/media/MediaDetail";
import Hero from "@/components/media/Hero";
import useKeyboardShortcuts from "@/lib/useKeyboardShortcuts";
import { mediaApi, type MediaItem, type QueueItem, type Notification, type UserProfile, type SearchFilters, type HealthStatus } from "@/lib/api";
import { useRefreshTrigger } from "@/lib/events";
import Onboarding from "@/components/layout/Onboarding";
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
  SlidersHorizontal,
  Bell,
  User,
  HelpCircle,
  ArrowRight,
  TrendingUp,
  Key,
  MessageSquare,
  Activity,
  WifiOff
} from "lucide-react";

// ─── Home View ────────────────────────────────────────
function HomeView({ onSelect }: { onSelect: (item: MediaItem) => void }) {
  const refreshKey = useRefreshTrigger();
  const [watchingList, setWatchingList] = useState<MediaItem[]>([]);
  const [trendingList, setTrendingList] = useState<MediaItem[]>([]);
  const [seasonalList, setSeasonalList] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [watching, trending, seasonal] = await Promise.all([
          mediaApi.getUserList("watching", "ANIME"),
          mediaApi.getTrending("ANIME"),
          mediaApi.getSeasonal("ANIME")
        ]);
        setWatchingList(watching.media || []);
        setTrendingList(trending.media || []);
        setSeasonalList(seasonal.media || []);
      } catch (err) {
        console.error("Failed to load home data:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [refreshKey]);

  const [heroItem, setHeroItem] = useState<MediaItem | null>(null);

  useEffect(() => {
    if (watchingList.length > 0) {
      // Pick a random item from the top 10 watching items for variety
      const randomIndex = Math.floor(Math.random() * Math.min(watchingList.length, 10));
      setHeroItem(watchingList[randomIndex]);
    } else if (trendingList.length > 0) {
      setHeroItem(trendingList[0]);
    }
  }, [watchingList, trendingList]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-accent" size={36} />
      </div>
    );
  }

  return (
    <div className="space-y-12 animate-fade-in pb-12">
      {heroItem && <Hero item={heroItem} onSelect={onSelect} />}
      
      {watchingList.length > 0 && (
        <MediaRow title="Continue Watching" items={watchingList} onSelect={onSelect} />
      )}
      
      <MediaRow title="Trending Now" items={trendingList} onSelect={onSelect} />
      
      <MediaRow title="Seasonal Highlights" items={seasonalList} onSelect={onSelect} />
    </div>
  );
}

// ─── Manga View ──────────────────────────────────────
function MangaView({ onSelect }: { onSelect: (item: MediaItem) => void }) {
  const refreshKey = useRefreshTrigger();
  const [trendingList, setTrendingList] = useState<MediaItem[]>([]);
  const [popularList, setPopularList] = useState<MediaItem[]>([]);
  const [readingList, setReadingList] = useState<MediaItem[]>([]);
  const [heroManga, setHeroManga] = useState<MediaItem | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadManga = async () => {
      try {
        const [trending, popular, reading] = await Promise.all([
          mediaApi.getTrending("MANGA"),
          mediaApi.search("", "MANGA", 1, { min_score: 70 }),
          mediaApi.getUserList("watching", "MANGA")
        ]);
        setTrendingList(trending.media || []);
        setPopularList(popular.media || []);
        setReadingList(reading.media || []);
        
        // Randomize hero from reading list or trending
        const pool = reading.media?.length ? reading.media.slice(0, 5) : trending.media?.slice(0, 5);
        if (pool?.length) {
          setHeroManga(pool[Math.floor(Math.random() * pool.length)]);
        }
      } catch (err) {
        console.error("Failed to load manga view:", err);
      } finally {
        setLoading(false);
      }
    };
    loadManga();
  }, [refreshKey]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="animate-spin text-accent" size={40} />
      </div>
    );
  }

  return (
    <div className="space-y-12 animate-fade-in pb-20">
      {heroManga && <Hero item={heroManga} onSelect={onSelect} />}

      {readingList.length > 0 && (
        <MediaRow title="Continue Reading" items={readingList} onSelect={onSelect} />
      )}
      
      <MediaRow title="Trending Manga" items={trendingList} onSelect={onSelect} />
      
      <MediaRow title="Highly Rated Manga" items={popularList} onSelect={onSelect} />
    </div>
  );
}

// ─── Infinite Scroll Component ─────────────────────────
function InfiniteScroll({ hasMore, loading, onLoadMore }: { hasMore: boolean, loading: boolean, onLoadMore: () => void }) {
  const observerTarget = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          onLoadMore();
        }
      },
      { threshold: 1.0 }
    );

    if (observerTarget.current) {
      observer.observe(observerTarget.current);
    }

    return () => observer.disconnect();
  }, [hasMore, loading, onLoadMore]);

  if (!hasMore) return null;

  return (
    <div ref={observerTarget} className="flex justify-center py-10">
      <Loader2 className="animate-spin text-accent" size={24} />
    </div>
  );
}

// ─── Search View ──────────────────────────────────────
function SearchView({ onSelect }: { onSelect: (item: MediaItem) => void }) {
  const [query, setQuery] = useState("");
  const [type, setType] = useState<"ANIME" | "MANGA">("ANIME");
  const [results, setResults] = useState<MediaItem[]>([]);
  const [suggestions, setSuggestions] = useState<MediaItem[]>([]);
  const [discovery, setDiscovery] = useState<MediaItem[]>([]);
  const [randomList, setRandomList] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [loadingDiscovery, setLoadingDiscovery] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({});

  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const seedDiscovery = useCallback(async (active = true) => {
    setLoadingDiscovery(true);
    try {
      const [trending, seasonal, recent] = await Promise.all([
        mediaApi.getTrending(type),
        mediaApi.getSeasonal(type),
        mediaApi.getRecent(type, 12),
      ]);

      const pool = [...(trending.media || []), ...(seasonal.media || []), ...(recent.media || [])];
      const shuffled = pool
        .sort(() => Math.random() - 0.5)
        .filter((item, index, array) => array.findIndex(other => other.id === item.id) === index)
        .slice(0, 18);

      if (active) {
        setDiscovery(shuffled);
      }

      // Fetch truly random items by picking a random page (1-100)
      const randomPage = Math.floor(Math.random() * 100) + 1;
      const randomData = await mediaApi.search("", type, randomPage);
      if (active) {
        setRandomList(randomData.media || []);
      }
    } catch (err) {
      console.error("Discovery seeding failed:", err);
      if (active) {
        setDiscovery([]);
        setRandomList([]);
      }
    } finally {
      if (active) setLoadingDiscovery(false);
    }
  }, [type]);

  useEffect(() => {
    let active = true;
    seedDiscovery(active);
    return () => {
      active = false;
    };
  }, [seedDiscovery]);

  useEffect(() => {
    const trimmedQuery = query.trim();

    if (!trimmedQuery) {
      setResults([]);
      setHasMore(false);
      // Auto-reseed if empty
      if (discovery.length === 0) {
        seedDiscovery();
      }
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await mediaApi.search(trimmedQuery, type, 1, filters);
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
  }, [query, type, filters]);

  useEffect(() => {
    const trimmedQuery = query.trim();

    if (trimmedQuery.length < 2) {
      return;
    }

    const timer = setTimeout(async () => {
      setLoadingSuggestions(true);
      try {
        const data = await mediaApi.search(trimmedQuery, type, 1, filters);
        setSuggestions((data.media || []).slice(0, 6));
      } catch {
        setSuggestions([]);
      } finally {
        setLoadingSuggestions(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query, type, filters]);

  const loadMore = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const data = await mediaApi.search(query, type, nextPage, filters);
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
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">Search</h1>
          <div className="flex bg-white/[0.04] p-1 rounded-xl border border-white/[0.06] w-fit">
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

        {query.trim().length >= 2 && suggestions.length > 0 && (
          <div className="space-y-3 rounded-2xl border border-white/[0.06] bg-white/[0.03] p-4 shadow-2xl shadow-black/20">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-gray-500">Suggestions</p>
              {loadingSuggestions && <Loader2 className="animate-spin text-accent" size={14} />}
            </div>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {suggestions.map((item) => {
                const title = item.title.english || item.title.romaji || "Media";

                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setQuery(title);
                    }}
                    className="flex items-center gap-3 rounded-xl border border-white/[0.06] bg-black/20 p-2 text-left transition-colors hover:border-accent/30 hover:bg-white/[0.05]"
                  >
                    <img
                      src={item.cover_image.large}
                      alt={title}
                      className="h-14 w-10 rounded-lg object-cover"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-white">{title}</p>
                      <p className="truncate text-[11px] text-gray-500">
                        {item.season && item.seasonYear ? `${item.season.charAt(0) + item.season.slice(1).toLowerCase()} ${item.seasonYear}` : item.status || "Anime"}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Filter toggle */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all border ${
            showFilters || Object.values(filters).some(Boolean)
              ? "bg-accent/10 text-accent border-accent/20"
              : "bg-white/[0.03] text-gray-500 border-white/[0.06] hover:text-white"
          }`}
        >
          <SlidersHorizontal size={14} />
          <span>Filters{Object.values(filters).filter(Boolean).length > 0 ? ` (${Object.values(filters).filter(Boolean).length})` : ""}</span>
        </button>

        {/* Filter panel */}
        {showFilters && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 p-4 bg-white/[0.02] border border-white/[0.06] rounded-xl animate-fade-in">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Genre</label>
              <select
                value={filters.genre || ""}
                onChange={(e) => setFilters(f => ({ ...f, genre: e.target.value || undefined }))}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-lg p-2.5 text-xs font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
              >
                <option value="">Any Genre</option>
                {["Action","Adventure","Comedy","Drama","Fantasy","Horror","Mystery","Romance","Sci-Fi","Slice of Life","Sports","Supernatural","Thriller"].map(g => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Year</label>
              <select
                value={filters.year || ""}
                onChange={(e) => setFilters(f => ({ ...f, year: e.target.value ? Number(e.target.value) : undefined }))}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-lg p-2.5 text-xs font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
              >
                <option value="">Any Year</option>
                {Array.from({ length: 27 }, (_, i) => 2026 - i).map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Min Score</label>
              <select
                value={filters.min_score || ""}
                onChange={(e) => setFilters(f => ({ ...f, min_score: e.target.value ? Number(e.target.value) : undefined }))}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-lg p-2.5 text-xs font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
              >
                <option value="">Any Score</option>
                {[90, 80, 70, 60, 50].map(s => (
                  <option key={s} value={s}>{s}%+</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Status</label>
              <select
                value={filters.status || ""}
                onChange={(e) => setFilters(f => ({ ...f, status: e.target.value || undefined }))}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-lg p-2.5 text-xs font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
              >
                <option value="">Any Status</option>
                <option value="FINISHED">Finished</option>
                <option value="RELEASING">Releasing</option>
                <option value="NOT_YET_RELEASED">Not Yet Released</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {query.trim().length === 0 ? (
        <div className="space-y-12">
          {loadingDiscovery ? (
             <div className="flex flex-col items-center justify-center py-24 space-y-4">
               <Loader2 className="animate-spin text-accent" size={40} />
               <p className="text-gray-500 font-medium">Curating your discovery feed...</p>
             </div>
          ) : (
            <>
              {discovery.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h2 className="text-2xl font-extrabold tracking-tight text-white">Discover {type === "ANIME" ? "Anime" : "Manga"}</h2>
                      <p className="text-sm text-gray-500">A rotating mix of trending, seasonal, and recent picks.</p>
                    </div>
                    <button
                      onClick={() => setDiscovery([...discovery].sort(() => Math.random() - 0.5))}
                      className="rounded-xl border border-white/[0.06] bg-white/[0.03] px-4 py-2 text-sm font-semibold text-gray-300 transition-colors hover:border-accent/30 hover:text-white"
                    >
                      Shuffle
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
                    {discovery.map((item) => (
                      <MediaCard key={item.id} item={item} onSelect={onSelect} />
                    ))}
                  </div>
                </div>
              )}

              {randomList.length > 0 && (
                <div className="space-y-4 pt-12 border-t border-white/[0.04]">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h2 className="text-2xl font-extrabold tracking-tight text-white">Random Picks</h2>
                      <p className="text-sm text-gray-500">Completely random picks from across the database.</p>
                    </div>
                    <button
                      onClick={async () => {
                        setLoadingDiscovery(true);
                        const randomPage = Math.floor(Math.random() * 100) + 1;
                        try {
                          const data = await mediaApi.search("", type, randomPage);
                          setRandomList(data.media || []);
                        } finally {
                          setLoadingDiscovery(false);
                        }
                      }}
                      className="rounded-xl border border-white/[0.06] bg-white/[0.03] px-4 py-2 text-sm font-semibold text-gray-300 transition-colors hover:border-accent/30 hover:text-white"
                    >
                      New Random
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
                    {randomList.map((item) => (
                      <MediaCard key={item.id} item={item} onSelect={onSelect} />
                    ))}
                  </div>
                </div>
              )}

              {!loadingDiscovery && discovery.length === 0 && randomList.length === 0 && (
                <div className="text-center py-24 bg-white/[0.02] rounded-3xl border border-dashed border-white/[0.06]">
                  <Activity size={40} className="mx-auto text-gray-800 mb-4" />
                  <p className="text-gray-500 font-semibold">Unable to load discovery feed.</p>
                  <button 
                    onClick={() => window.location.reload()}
                    className="mt-4 text-accent text-sm font-bold hover:underline"
                  >
                    Try Refreshing
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      ) : results.length > 0 ? (
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

      <InfiniteScroll hasMore={hasMore} loading={loadingMore} onLoadMore={loadMore} />
    </div>
  );
}

// ─── Lists View ───────────────────────────────────────
const LIST_TABS = [
  { key: "watching", label: "Reading/Watching", icon: Monitor },
  { key: "completed", label: "Completed", icon: CheckCircle2 },
  { key: "planning", label: "Planning", icon: Bookmark },
  { key: "paused", label: "Paused", icon: Pause },
  { key: "dropped", label: "Dropped", icon: XCircle },
];

function ListsView({ onSelect }: { onSelect: (item: MediaItem) => void }) {
  const refreshKey = useRefreshTrigger();
  const [activeTab, setActiveTab] = useState("watching");
  const [type, setType] = useState<"ANIME" | "MANGA">("ANIME");
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    setLoading(true);
    mediaApi.getUserList(activeTab, type, 1)
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
  }, [activeTab, type, refreshKey]);

  const loadMore = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const data = await mediaApi.getUserList(activeTab, type, nextPage);
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
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">My Lists</h1>
        <div className="flex bg-white/[0.04] p-1 rounded-xl border border-white/[0.06] w-fit">
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
            <span>{tab.key === "watching" ? (type === "MANGA" ? "Reading" : "Watching") : tab.label}</span>
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
          <p className="text-gray-700 text-sm mt-1">Search for {type.toLowerCase()} and add them to your list.</p>
        </div>
      )}

      <InfiniteScroll hasMore={hasMore} loading={loadingMore} onLoadMore={loadMore} />
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
  const refreshKey = useRefreshTrigger();
  const [type, setType] = useState<"ANIME" | "MANGA">("ANIME");
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    setLoading(true);
    mediaApi.getUserList("completed", type, 1)
      .then(data => {
        setItems(data.media || []);
        setHasMore(data.page_info?.has_next_page || false);
        setPage(1);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [type, refreshKey]);

  const loadMore = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const data = await mediaApi.getUserList("completed", type, nextPage);
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
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">Library</h1>
        <div className="flex bg-white/[0.04] p-1 rounded-xl border border-white/[0.06] w-fit">
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
          <InfiniteScroll hasMore={hasMore} loading={loadingMore} onLoadMore={loadMore} />
        </>
      ) : (
        <div className="text-center py-24 border-2 border-dashed border-white/[0.04] rounded-2xl">
          <Library size={40} className="mx-auto text-gray-800 mb-4" />
          <p className="text-gray-600 font-semibold">Library is empty</p>
          <p className="text-gray-700 text-sm mt-1">Your completed {type.toLowerCase()} will appear here.</p>
        </div>
      )}
    </div>
  );
}

// ─── Settings View ────────────────────────────────────
function SettingsView({ health }: { health: HealthStatus | null }) {
  const [config, setConfig] = useState<Record<string, Record<string, unknown>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<"general" | "streaming" | "downloads" | "anilist" | "registry" | "maintenance" | "system">("general");
  const [refreshNeeded, setRefreshNeeded] = useState(false);
  const [registryStats, setRegistryStats] = useState<any>(null);
  const [backingUp, setBackingUp] = useState(false);
  const [backupUrl, setBackupUrl] = useState<string | null>(null);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [hasUpdate, setHasUpdate] = useState(health?.update_available || false);
  const [updateMessage, setUpdateMessage] = useState<{ text: string; type: "success" | "error" | null }>({ text: "", type: null });

  useEffect(() => {
    mediaApi.getConfig()
      .then(setConfig)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (health?.update_available) {
      setHasUpdate(true);
    }
  }, [health]);

  const handleUpdate = async () => {
    setCheckingUpdate(true);
    setUpdateMessage({ text: "", type: null });
    try {
      if (hasUpdate) {
        // Perform the actual update
        const res = await mediaApi.triggerUpdate();
        setUpdateMessage({ text: res.message, type: res.status === "success" ? "success" : "error" });
        if (res.status === "success" && (res.message.includes("Update") || res.message.includes("Updated"))) {
          setRefreshNeeded(true);
        }
      } else {
        // Just check for updates
        const res = await mediaApi.checkUpdate();
        setUpdateMessage({ text: res.message, type: res.status === "success" ? "success" : "error" });
        if (res.status === "success" && res.update_available) {
          setHasUpdate(true);
        }
      }
    } catch (err) {
      setUpdateMessage({ text: "Failed to connect to update server.", type: "error" });
    } finally {
      setCheckingUpdate(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await mediaApi.updateConfig(config);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err: any) {
      console.error("Save failed:", err);
      alert("Save failed: " + (err.message || "Unknown error"));
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

  useEffect(() => {
    if (activeTab === "registry" && !registryStats) {
      mediaApi.getRegistryStats().then(setRegistryStats).catch(console.error);
    }
  }, [activeTab, registryStats]);

  const handleBackup = async () => {
    setBackingUp(true);
    setBackupUrl(null);
    try {
      await mediaApi.triggerBackup();
      const origin = window.location.port === '3000' ? 'http://localhost:8000' : window.location.origin;
      setBackupUrl(`${origin}/api/registry/backup/download`);
    } finally {
      setBackingUp(false);
    }
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
    { id: "registry", label: "Registry", icon: Activity },
    { id: "maintenance", label: "Maintenance", icon: RotateCcw },
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
              onClick={() => setActiveTab(tab.id as any)}
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

              <SettingField
                label="Time Format"
                description="How dates and times should be displayed."
              >
                <select
                  value={String(config.general?.time_format || "12h")}
                  onChange={(e) => updateField("general", "time_format", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  <option value="12h">12-hour (AM/PM)</option>
                  <option value="24h">24-hour</option>
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

          {activeTab === "maintenance" && (
            <div className="space-y-8 animate-fade-in">
              {/* Onboarding Reset */}
              <div className="p-6 rounded-2xl bg-red-500/5 border border-red-500/10 space-y-4">
                <div className="flex items-start space-x-4">
                  <div className="p-2 rounded-lg bg-red-500/10 text-red-400">
                    <RotateCcw size={20} />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-sm font-bold text-white">Reset Onboarding</h3>
                    <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                      This will reset your "getting started" progress and re-run the welcome setup. 
                      Your account token and downloads will not be deleted.
                    </p>
                  </div>
                </div>
                <button 
                  onClick={() => {
                    if (confirm("Reset onboarding and restart setup?")) {
                      localStorage.removeItem("anicat_onboarding_seen");
                      window.location.reload();
                    }
                  }}
                  className="w-full py-3 px-4 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs font-bold transition-all border border-red-500/10 flex items-center justify-center space-x-2"
                >
                  <AlertCircle size={16} />
                  <span>Start Setup From Scratch</span>
                </button>
              </div>

              {/* Application Update */}
              <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-white">Application Update</h3>
                    <p className="text-sm text-gray-500 mt-1">Check for the latest features and bug fixes.</p>
                  </div>
                  <div className="px-3 py-1 bg-white/[0.04] rounded-lg border border-white/[0.1] text-[10px] font-mono text-gray-400">
                    {health?.current_version || "v1.2.4"}
                  </div>
                </div>
                <div className="flex flex-col space-y-3 pt-2">
                  <button
                    onClick={handleUpdate}
                    disabled={checkingUpdate}
                    className={`flex items-center justify-center space-x-2 py-3 rounded-xl font-bold transition-all shadow-lg shadow-accent/20 disabled:opacity-50 ${
                      hasUpdate ? "bg-green-600 hover:bg-green-500 text-white shadow-green-500/20" : "bg-accent text-white hover:bg-accent-light"
                    }`}
                  >
                    {checkingUpdate ? <Loader2 size={16} className="animate-spin" /> : hasUpdate ? <Download size={16} /> : <RotateCcw size={16} />}
                    <span>{checkingUpdate ? (hasUpdate ? "Updating..." : "Checking...") : hasUpdate ? "Install Update" : "Check for Updates"}</span>
                  </button>
                  {updateMessage.text && (
                    <div className={`p-3 rounded-xl text-xs font-semibold flex items-center space-x-2 animate-fade-in ${
                      updateMessage.type === "success" ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
                    }`}>
                      {updateMessage.type === "success" ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                      <span>{updateMessage.text}</span>
                    </div>
                  )}
                  <p className="text-[10px] text-center text-gray-600">Build: {new Date().toLocaleDateString()}</p>
                </div>
              </div>

              {/* Danger Zone */}
              <div className="p-6 rounded-2xl bg-red-500/5 border border-red-500/10 space-y-4">
                <h3 className="text-lg font-bold text-red-400/80">Danger Zone</h3>
                <button
                  onClick={() => {
                    if (confirm("Are you sure you want to clear your local cache? This cannot be undone.")) {
                      // Registry clear logic
                    }
                  }}
                  className="w-full py-3 border border-red-500/20 text-red-400/60 rounded-xl text-sm font-bold hover:bg-red-500/10 transition-all"
                >
                  Clear Local Registry
                </button>
              </div>
            </div>
          )}

          {activeTab === "registry" && (
            <div className="space-y-6 animate-fade-in">
              <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-4">
                <h2 className="text-lg font-bold text-white">Registry Management</h2>
                <p className="text-sm text-gray-400">
                  Your registry stores offline metadata, playback progress, and download tracking.
                </p>
                <div className="pt-4 border-t border-white/[0.04]">
                  <button
                    onClick={handleBackup}
                    disabled={backingUp}
                    className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-accent text-white hover:bg-accent-light transition-all font-bold text-sm disabled:opacity-50"
                  >
                    {backingUp ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                    <span>{backingUp ? "Creating Backup..." : "Backup Registry"}</span>
                  </button>
                  {backupUrl && (
                    <a
                      href={backupUrl}
                      download
                      className="inline-flex items-center space-x-2 mt-4 px-5 py-2.5 rounded-xl bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30 transition-all font-bold text-sm"
                    >
                      <Download size={16} />
                      <span>Download Latest Backup</span>
                    </a>
                  )}
                </div>
              </div>

              {registryStats && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
                    <div className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2">Total Media</div>
                    <div className="text-3xl font-extrabold text-white">
                      {registryStats.registry?.total_media_breakdown?.total || 0}
                    </div>
                  </div>
                  <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
                    <div className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2">Episodes Downloaded</div>
                    <div className="text-3xl font-extrabold text-white">
                      {registryStats.downloads?.downloaded || 0}
                    </div>
                  </div>
                </div>
              )}
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
// ─── Notifications View ─────────────────────────────────
function NotificationsView({ onSelect }: { onSelect: (item: MediaItem) => void }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState<any>(null);

  useEffect(() => {
    async function load() {
      try {
        const [notifs, cfg] = await Promise.all([
          mediaApi.getNotifications(),
          mediaApi.getConfig()
        ]);
        setNotifications(notifs || []);
        setConfig(cfg);
      } catch (err) {
        console.error("Failed to load notifications:", err);
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

  return (
    <div className="space-y-8 animate-fade-in max-w-3xl">
      <div className="flex items-center justify-between">
        <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">Notifications</h1>
        {notifications.length > 0 && (
          <button 
            onClick={async () => {
              await mediaApi.markNotificationsAsRead();
              window.location.reload();
            }}
            className="flex items-center space-x-2 px-4 py-2 bg-white/[0.04] hover:bg-accent hover:text-white border border-white/[0.06] rounded-xl text-sm font-bold transition-all"
          >
            <CheckCircle2 size={16} />
            <span>Mark all as read</span>
          </button>
        )}
      </div>
      
      {notifications.length === 0 ? (
        <div className="text-center py-20 bg-white/[0.02] border border-white/[0.04] rounded-3xl">
          <Bell size={48} className="mx-auto text-gray-600 mb-4" />
          <p className="text-gray-400 font-medium">You have no new notifications.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map((notif) => (
            <div 
              key={notif.id}
              onClick={() => onSelect(notif.media)}
              className="flex items-center space-x-4 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.1] transition-all cursor-pointer group"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img 
                src={notif.media.cover_image?.large} 
                alt="cover" 
                className="w-12 h-16 object-cover rounded-lg shrink-0 shadow-lg"
              />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-gray-300 group-hover:text-white transition-colors truncate">
                  {notif.contexts[0]}{notif.episode || ""}{notif.contexts[1] || ""}{notif.media?.title?.english || notif.media?.title?.romaji || ""}{notif.contexts[2] || ""}
                </div>
                <div className="text-xs text-accent font-bold mt-1">
                  {new Date(notif.created_at + "Z").toLocaleString([], { 
                    dateStyle: 'short', 
                    timeStyle: 'short',
                    hour12: config?.general?.time_format !== '24h'
                  })}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Profile View ─────────────────────────────────────
function ProfileView() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await mediaApi.getProfile();
        setProfile(data);
      } catch (err) {
        console.error("Failed to load profile:", err);
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

  if (!profile) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] space-y-4">
        <User size={48} className="text-gray-600" />
        <p className="text-gray-400 font-medium">Please login via the CLI to view your profile.</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in max-w-4xl">
      <div className="relative rounded-3xl overflow-hidden bg-surface border border-white/[0.06] shadow-2xl">
        {profile.banner_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={profile.banner_url} alt="Banner" className="w-full h-48 lg:h-64 object-cover brightness-[0.7]" />
        ) : (
          <div className="w-full h-48 lg:h-64 bg-gradient-to-r from-accent to-secondary opacity-30" />
        )}
        
        <div className="px-8 pb-8 relative -mt-16 lg:-mt-20">
          <div className="flex flex-col lg:flex-row lg:items-end space-y-4 lg:space-y-0 lg:space-x-6">
            {profile.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={profile.avatar_url} alt="Avatar" className="w-32 h-32 lg:w-40 lg:h-40 rounded-2xl object-cover border-4 border-surface shadow-2xl" />
            ) : (
              <div className="w-32 h-32 lg:w-40 lg:h-40 rounded-2xl bg-white/10 border-4 border-surface flex items-center justify-center backdrop-blur-md">
                <User size={48} className="text-white/50" />
              </div>
            )}
            
            <div className="pb-2">
              <h1 className="text-4xl lg:text-5xl font-extrabold text-white tracking-tight">{profile.name}</h1>
              <p className="text-accent font-semibold mt-1">AniList Connected</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


// ─── Help Modal ───────────────────────────────────────
function HelpModal({ onClose }: { onClose: () => void }) {
  const shortcuts = [
    { key: "/", desc: "Search" },
    { key: "Esc", desc: "Close detail panel" },
    { key: "h", desc: "Home" },
    { key: "n", desc: "Notifications" },
    { key: "l", desc: "My Lists" },
    { key: "d", desc: "Downloads" },
    { key: "?", desc: "Toggle this help menu" },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in" onClick={onClose}>
      <div className="bg-surface border border-white/[0.08] rounded-3xl p-8 max-w-md w-full shadow-2xl relative" onClick={e => e.stopPropagation()}>
        <button onClick={onClose} className="absolute top-6 right-6 text-gray-500 hover:text-white transition-colors">
          <X size={20} />
        </button>
        <h2 className="text-2xl font-extrabold text-white mb-6">Keyboard Shortcuts</h2>
        <div className="space-y-3">
          {shortcuts.map((s) => (
            <div key={s.key} className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-400">{s.desc}</span>
              <kbd className="px-3 py-1.5 bg-white/[0.05] border border-white/[0.1] rounded-lg text-xs font-bold text-white shadow-sm font-mono">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────
export default function App() {
  const [activeView, setActiveView] = useState<ViewName>("home");
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null);
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

  // Poll health for offline banner and notifications
  useEffect(() => {
    async function checkSystem() {
      try {
        const status = await mediaApi.getHealthStatus();
        setHealthStatus(status);
        
        // Only show offline if explicitly told so by backend AND api is disconnected AND we are logged in
        const shouldBeOffline = status.api_authenticated && (status.is_offline || !status.api_connected);
        setIsOffline(shouldBeOffline);
        
        if (!shouldBeOffline) setDismissedOffline(false);
        setNotificationCount(status.unread_notifications || 0);
      } catch {
        // If the health check fails, the backend might be down. 
        // We don't want to show the "Browsing local" banner immediately 
        // as it might just be a server restart.
      }
    }
    checkSystem();
    const interval = setInterval(checkSystem, 30000);
    return () => clearInterval(interval);
  }, []);

  // Check if onboarding should be shown
  useEffect(() => {
    if (healthStatus && !healthStatus.api_connected) {
      const hasSeenOnboarding = localStorage.getItem("anicat_onboarding_seen");
      if (!hasSeenOnboarding) {
        setShowOnboarding(true);
      }
    } else if (healthStatus?.api_connected) {
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

  const handleSelect = (item: MediaItem) => {
    setSelectedItem(item);
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
        return <SettingsView health={healthStatus} />;
      case "notifications":
        return <NotificationsView onSelect={handleSelect} />;
      case "profile":
        return <ProfileView />;
    }
  };

  return (
    <div className="flex h-screen relative">
      <Sidebar activeView={activeView} onNavigate={setActiveView} notificationCount={notificationCount} />

      {/* Main content */}
      <main className="flex-1 ml-[72px] lg:ml-60 overflow-y-auto scrollbar-hide relative">
        {/* Offline Banner */}
        {isOffline && !dismissedOffline && (
          <div className="absolute top-0 left-0 right-0 z-50 animate-slide-down">
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
          <div className={`absolute top-0 left-0 right-0 z-50 animate-slide-down ${isOffline && !dismissedOffline ? 'mt-24' : ''}`}>
            <div className="mx-6 mt-6 lg:mx-10 bg-green-500/10 border border-green-500/20 backdrop-blur-md rounded-2xl p-4 flex items-center justify-between shadow-xl">
              <div className="flex items-center space-x-3 text-green-400">
                <RotateCcw size={18} className="animate-spin-slow" />
                <span className="text-sm font-bold">
                  Update in progress. Please refresh in ~2 minutes to apply changes.
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

        <div className={`p-6 lg:p-10 max-w-[1600px] transition-all ${isOffline && !dismissedOffline ? 'pt-24 lg:pt-28' : ''}`}>
          {renderView()}
        </div>
      </main>

      <NowPlaying />

      {/* Media detail panel */}
      {selectedItem && (
        <MediaDetail item={selectedItem} onClose={() => setSelectedItem(null)} />
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
