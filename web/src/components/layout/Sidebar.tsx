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
  Calendar,
} from "lucide-react";
import { mediaApi, type HealthStatus } from "@/lib/api";

// UX-11: Read offline pending changes from localStorage
function OfflinePendingCount() {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem("anicat_pending_offline_changes");
    if (!raw) return null;
    const changes = JSON.parse(raw);
    const count = Array.isArray(changes) ? changes.length : 0;
    return count > 0 ? <>{count > 9 ? "9+" : count}</> : null;
  } catch {
    return null;
  }
}

export type ViewName = "home" | "manga" | "search" | "lists" | "downloads" | "library" | "settings" | "notifications" | "profile" | "schedule";

type NavItem = { icon: typeof Home; label: string; view: ViewName; shortcut?: string };

const navItems: NavItem[] = [
  { icon: Home, label: "Home", view: "home", shortcut: "H" },
  { icon: BookOpen, label: "Manga", view: "manga" },
  { icon: Search, label: "Search", view: "search", shortcut: "/" },
  { icon: Monitor, label: "My Lists", view: "lists", shortcut: "L" },
  { icon: Download, label: "Downloads", view: "downloads", shortcut: "D" },
  { icon: Library, label: "Library", view: "library" },
  { icon: Calendar, label: "Schedule", view: "schedule" },
];

const secondaryItems: NavItem[] = [
  { icon: Bell, label: "Notifications", view: "notifications", shortcut: "N" },
  { icon: User, label: "Profile", view: "profile" },
  { icon: Settings, label: "Settings", view: "settings" },
];

interface SidebarProps {
  activeView: ViewName;
  onNavigate: (view: ViewName) => void;
  notificationCount?: number;
  health?: HealthStatus | null;
  isFullscreen?: boolean;
}
export default function Sidebar({ activeView, onNavigate, notificationCount = 0, health, isFullscreen = false }: SidebarProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <>
      {isFullscreen && (
        <div
          className="fixed left-0 top-0 bottom-0 w-3.5 z-45 bg-transparent"
          onMouseEnter={() => setIsHovered(true)}
        />
      )}
      <aside
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={
          isFullscreen
            ? `fixed left-0 top-0 bottom-0 w-60 glass-fixed z-50 flex flex-col py-6 transition-all duration-300 shadow-2xl shadow-black/85 ${
                isHovered ? "translate-x-0" : "-translate-x-full"
              }`
            : "fixed left-0 top-0 bottom-0 w-[72px] lg:w-60 z-50 flex flex-col py-6 transition-all duration-300"
        }
      >

        {/* Logo */}
        <div className="flex flex-col items-center justify-center px-4 mb-10 pt-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/anicat_logo.png"
            alt="Anicat Logo"
            className="w-24 h-auto lg:w-32 opacity-95 hover:opacity-100 transition-opacity object-contain dark:[filter:brightness(0)_invert(1)] [filter:invert(1)]"
          />
          {process.env.NODE_ENV === "development" && (
            <span className="mt-1.5 px-2 py-0.5 text-[9px] font-black uppercase tracking-widest bg-purple-500/10 text-purple-400 border border-purple-500/25 rounded-md select-none font-mono">
              Local Dev
            </span>
          )}
        </div>

        {/* Primary Nav */}
        <nav className="flex-1 space-y-1 px-3 overflow-y-auto scrollbar-hide">
          {navItems.map((item) => {
            const isActive = activeView === item.view;
            return (
              <button
                key={item.view}
                onClick={() => {
                  onNavigate(item.view);
                  setIsHovered(false);
                }}
                className={`w-full flex items-center justify-center lg:justify-start lg:space-x-3 px-3 py-2.5 rounded-xl transition-all duration-200 group ${isActive
                    ? "bg-accent/10 text-accent font-bold"
                    : "text-gray-500 dark:text-gray-400 hover:text-foreground hover:bg-foreground/[0.04]"
                  }`}
              >
                <item.icon size={20} className={`shrink-0 transition-colors ${isActive ? "text-accent" : "text-gray-500 dark:text-gray-400 group-hover:text-accent"}`} />
                <span className={`${isFullscreen ? "flex" : "hidden lg:flex"} items-center justify-between flex-1 text-[13px] font-semibold tracking-wide`}>
                  <span>{item.label}</span>
                  {item.shortcut && (
                    <kbd className="ml-auto text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-md bg-foreground/[0.06] text-muted-foreground border border-border/50 opacity-0 group-hover:opacity-100 transition-opacity">
                      {item.shortcut}
                    </kbd>
                  )}
                </span>
              </button>
            );
          })}

          {/* Divider */}
          <div className="my-4 mx-3 border-t border-border" />

          {/* Secondary Nav */}
          {secondaryItems.map((item) => {
            const isActive = activeView === item.view;
            const hasUpdate = item.view === "settings" && health?.update_available;
            
            return (
              <button
                key={item.view}
                onClick={() => {
                  onNavigate(item.view);
                  setIsHovered(false);
                }}
                className={`w-full flex items-center justify-center lg:justify-start lg:space-x-3 px-3 py-2.5 rounded-xl transition-all duration-200 group ${isActive
                    ? "bg-accent/10 text-accent font-bold"
                    : "text-gray-500 dark:text-gray-400 hover:text-foreground hover:bg-foreground/[0.04]"
                  }`}
              >
                <div className="relative shrink-0 flex items-center justify-center">
                  <item.icon size={20} className={`transition-colors ${isActive ? "text-accent" : "text-gray-500 dark:text-gray-400 group-hover:text-accent"}`} />
                   {hasUpdate && (
                    <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-amber-500 rounded-full border-2 border-background animate-pulse shadow-[0_0_12px_rgba(245,158,11,0.8)]" />
                  )}
                  {item.view === "notifications" && notificationCount > 0 && (
                    <span className="absolute -top-1 -right-1 min-w-[16px] h-[16px] bg-red-500 text-white text-[9px] font-bold flex items-center justify-center rounded-full border-2 border-background px-0.5">
                      {notificationCount > 9 ? "9+" : notificationCount}
                    </span>
                  )}
                </div>
                <span className={`${isFullscreen ? "flex" : "hidden lg:flex"} items-center justify-between flex-1 text-[13px] font-semibold tracking-wide`}>
                  <span>{item.label}</span>
                  {item.shortcut && (
                    <kbd className="ml-auto text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-md bg-foreground/[0.06] text-muted-foreground border border-border/50 opacity-0 group-hover:opacity-100 transition-opacity">
                      {item.shortcut}
                    </kbd>
                  )}
                </span>
              </button>
            );
          })}
        </nav>

      </aside>
    </>
  );
}
