"use client";

import { useState, useEffect } from "react";
import { Loader2, Globe, Monitor, Activity, Clock, Calendar } from "lucide-react";
import LazyCard from "@/components/media/LazyCard";
import { mediaApi, type MediaItem } from "@/lib/api";

interface ScheduleViewProps {
  onSelect: (item: MediaItem) => void;
}

export default function ScheduleView({ onSelect }: ScheduleViewProps) {
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [watchingOnly, setWatchingOnly] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("anicat_schedule_watching_only") === "true";
    }
    return false;
  });

  const handleToggleWatchingOnly = (value: boolean) => {
    setWatchingOnly(value);
    localStorage.setItem("anicat_schedule_watching_only", String(value));
  };

  const parseAiringAt = (airingAt?: string) => {
    if (!airingAt) return 0;
    return new Date(airingAt.endsWith("Z") ? airingAt : `${airingAt}Z`).getTime();
  };

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        let mediaIds: number[] | undefined = undefined;
        if (watchingOnly) {
          const watching = await mediaApi.getUserList("watching", "ANIME");
          mediaIds = (watching.media || []).map(m => m.id);
          if (mediaIds.length === 0) {
            setItems([]);
            setLoading(false);
            return;
          }
        }
        
        const data = await mediaApi.getSchedule(1, 3, 1, 50, mediaIds);
        setItems(data.media || []);
      } catch (err) {
        console.error("Failed to load schedule:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [watchingOnly]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-accent" size={36} />
      </div>
    );
  }

  // Sort globally by nearest airing first, then group by day in that order.
  const sortedItems = items
    .filter((item) => item.next_airing?.airing_at)
    .sort(
      (a, b) =>
        parseAiringAt(a.next_airing?.airing_at) -
        parseAiringAt(b.next_airing?.airing_at)
    );

  const groups = new Map<string, MediaItem[]>();
  sortedItems.forEach((item) => {
    const date = new Date(
      item.next_airing?.airing_at?.endsWith("Z")
        ? item.next_airing.airing_at
        : `${item.next_airing?.airing_at}Z`
    );
    const dateStr = date.toLocaleDateString(undefined, {
      weekday: "long",
      month: "long",
      day: "numeric",
    });
    if (!groups.has(dateStr)) groups.set(dateStr, []);
    groups.get(dateStr)!.push(item);
  });

  return (
    <div className="space-y-12 animate-fade-in pb-12">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6">
        <div className="flex flex-col space-y-2">
          <h1 className="text-4xl font-black text-white tracking-tight">Airing Schedule</h1>
          <p className="text-gray-500 font-medium text-lg">Keep track of the latest releases and upcoming episodes</p>
        </div>
        
        <div className="flex bg-white/[0.04] p-1 rounded-xl border border-white/[0.06] w-fit h-fit self-start sm:self-auto">
          <button
            onClick={() => handleToggleWatchingOnly(false)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
              !watchingOnly ? "bg-accent text-white shadow-lg shadow-accent/20" : "text-gray-500 hover:text-white"
            }`}
          >
            <Globe size={16} />
            <span>Global</span>
          </button>
          <button
            onClick={() => handleToggleWatchingOnly(true)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
              watchingOnly ? "bg-accent text-white shadow-lg shadow-accent/20" : "text-gray-500 hover:text-white"
            }`}
          >
            <Monitor size={16} />
            <span>Watching Only</span>
          </button>
        </div>
      </div>

      {Array.from(groups.entries()).map(([date, dayItems]) => (
        <div key={date} className="space-y-6">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-bold text-white px-4 py-2 bg-white/[0.03] border border-white/[0.06] rounded-xl inline-block">{date}</h2>
            <div className="h-px flex-1 bg-gradient-to-r from-white/[0.06] to-transparent" />
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
            {dayItems.map(item => (
              <div key={item.id} className="space-y-2">
                <LazyCard item={item} onSelect={onSelect} />
                <div className="flex items-center justify-between px-1">
                  <div className="flex items-center space-x-1.5 text-accent">
                    <Activity size={12} className="animate-pulse" />
                    <span className="text-[11px] font-black uppercase tracking-wider">Ep {item.next_airing?.episode}</span>
                  </div>
                  <div className="flex items-center space-x-1.5 text-gray-500">
                    <Clock size={12} />
                    <span className="text-[11px] font-bold">
                      {new Date(
                        item.next_airing!.airing_at!.endsWith("Z")
                          ? item.next_airing!.airing_at!
                          : `${item.next_airing!.airing_at!}Z`
                      ).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false })}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
          <div className="p-6 rounded-full bg-white/[0.02] border border-white/[0.04]">
            <Calendar size={48} className="text-gray-700" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-white">No episodes scheduled</h3>
            <p className="text-gray-500 max-w-xs">Check back later for updated airing times.</p>
          </div>
        </div>
      )}
    </div>
  );
}
