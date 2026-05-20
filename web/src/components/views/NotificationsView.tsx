"use client";

import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, CheckCircle2, Bell } from "lucide-react";
import { mediaApi, type MediaItem } from "@/lib/api";

interface NotificationsViewProps {
  onSelect: (item: MediaItem) => void;
}

export default function NotificationsView({ onSelect }: NotificationsViewProps) {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["notifications", "config"],
    queryFn: async () => {
      const [notifs, cfg] = await Promise.all([
        mediaApi.getNotifications(),
        mediaApi.getConfig(),
      ]);
      return { notifications: notifs || [], config: cfg };
    },
    staleTime: 30_000,
  });

  const notifications = data?.notifications ?? [];
  const config = data?.config ?? null;

  const handleMarkAllRead = useCallback(async () => {
    try {
      await mediaApi.markNotificationsAsRead();
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["health"] });
    } catch (err) {
      console.error("Failed to mark notifications as read:", err);
    }
  }, [queryClient]);

  if (isLoading) {
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
            onClick={handleMarkAllRead}
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
                  {notif.contexts?.[0] ?? ""}{notif.episode || ""}{notif.contexts?.[1] ?? ""}{notif.media?.title?.english || notif.media?.title?.romaji || ""}{notif.contexts?.[2] ?? ""}
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
