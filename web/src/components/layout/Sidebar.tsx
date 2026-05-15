"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Home,
  Search,
  Download,
  Library,
  Settings,
  Monitor,
  Bell,
  User,
  BookOpen,
} from "lucide-react";
import { mediaApi, type HealthStatus } from "@/lib/api";

export type ViewName = "home" | "manga" | "search" | "lists" | "downloads" | "library" | "settings" | "notifications" | "profile";

const navItems: { icon: typeof Home; label: string; view: ViewName }[] = [
  { icon: Home, label: "Home", view: "home" },
  { icon: BookOpen, label: "Manga", view: "manga" },
  { icon: Search, label: "Search", view: "search" },
  { icon: Monitor, label: "My Lists", view: "lists" },
  { icon: Download, label: "Downloads", view: "downloads" },
  { icon: Library, label: "Library", view: "library" },
];

const secondaryItems: { icon: typeof Home; label: string; view: ViewName }[] = [
  { icon: Bell, label: "Notifications", view: "notifications" },
  { icon: User, label: "Profile", view: "profile" },
  { icon: Settings, label: "Settings", view: "settings" },
];

interface SidebarProps {
  activeView: ViewName;
  onNavigate: (view: ViewName) => void;
  notificationCount?: number;
}

export default function Sidebar({ activeView, onNavigate, notificationCount = 0 }: SidebarProps) {
  const [health, setHealth] = useState<HealthStatus | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const status = await mediaApi.getHealthStatus();
      setHealth(status);
    } catch {
      setHealth({ api_connected: false, api_authenticated: false, worker_running: false, is_offline: true });
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[72px] lg:w-60 bg-black/60 backdrop-blur-xl border-r border-white/[0.04] z-50 flex flex-col py-6 transition-all duration-300">

      {/* Logo */}
      <div className="flex justify-center px-4 mb-10 pt-2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/anicat_logo.webp?v=2"
          alt="Anicat Logo"
          className="w-24 h-auto lg:w-32 opacity-95 hover:opacity-100 transition-opacity object-contain"
        />
      </div>

      {/* Primary Nav */}
      <nav className="flex-1 space-y-1 px-3">
        {navItems.map((item) => {
          const isActive = activeView === item.view;
          return (
            <button
              key={item.view}
              onClick={() => onNavigate(item.view)}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl transition-all duration-200 group ${isActive
                  ? "bg-accent/10 text-white"
                  : "text-gray-500 hover:text-white hover:bg-white/[0.04]"
                }`}
            >
              <div className={`flex items-center justify-center w-9 h-9 rounded-lg transition-colors ${isActive ? "bg-accent text-white shadow-lg shadow-accent/25" : "group-hover:text-accent"
                }`}>
                <item.icon size={18} />
              </div>
              <span className="hidden lg:block text-[13px] font-semibold tracking-wide">{item.label}</span>
            </button>
          );
        })}

        {/* Divider */}
        <div className="my-4 mx-3 border-t border-white/[0.04]" />

        {/* Secondary Nav */}
        {secondaryItems.map((item) => {
          const isActive = activeView === item.view;
          return (
            <button
              key={item.view}
              onClick={() => onNavigate(item.view)}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl transition-all duration-200 group relative ${isActive
                  ? "bg-accent/10 text-white"
                  : "text-gray-500 hover:text-white hover:bg-white/[0.04]"
                }`}
            >
              <div className={`flex items-center justify-center w-9 h-9 rounded-lg transition-colors relative ${isActive ? "bg-accent text-white shadow-lg shadow-accent/25" : "group-hover:text-accent"
                }`}>
                <item.icon size={18} />
                {/* Notification badge */}
                {item.view === "notifications" && notificationCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-[9px] font-bold text-white flex items-center justify-center animate-bounce-once">
                    {notificationCount > 9 ? "9+" : notificationCount}
                  </span>
                )}
              </div>
              <span className="hidden lg:block text-[13px] font-semibold tracking-wide">{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
