"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, Loader2, SlidersHorizontal, Activity } from "lucide-react";
import MediaCard from "@/components/media/MediaCard";
import InfiniteScroll from "@/components/shared/InfiniteScroll";
import MediaTypeToggle from "@/components/shared/MediaTypeToggle";
import { mediaApi, type MediaItem, type SearchFilters } from "@/lib/api";

interface SearchViewProps {
  onSelect: (item: MediaItem) => void;
}

export default function SearchView({ onSelect }: SearchViewProps) {
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
  }, [query, type, filters, seedDiscovery, discovery.length]);

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
          <MediaTypeToggle value={type} onChange={setType} />
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
      {(() => {
        const hasFilters = Object.values(filters).some(Boolean);
        
        if (query.trim().length === 0 && !hasFilters) {
          return (
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
          );
        }

        if (results.length > 0) {
          return (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-5">
              {results.map((item) => (
                <MediaCard key={item.id} item={item} onSelect={onSelect} />
              ))}
            </div>
          );
        }

        if (query.trim().length > 0 && !loading) {
          return (
            <div className="text-center py-24">
              <Search size={40} className="mx-auto text-gray-800 mb-4" />
              <p className="text-gray-600 font-semibold">No {type.toLowerCase()} found for &quot;{query}&quot;</p>
            </div>
          );
        }

        if (hasFilters && !loading) {
          return (
            <div className="text-center py-24">
              <SlidersHorizontal size={40} className="mx-auto text-gray-800 mb-4" />
              <p className="text-gray-600 font-semibold">No {type.toLowerCase()} found matching these filters.</p>
            </div>
          );
        }

        return null;
      })()}

      <InfiniteScroll hasMore={hasMore} loading={loadingMore} onLoadMore={loadMore} />
    </div>
  );
}
