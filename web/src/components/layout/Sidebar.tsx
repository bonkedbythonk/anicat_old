"use client";

import Image from "next/image";
import { 
  Home, 
  Search, 
  Download, 
  Library, 
  Settings, 
  Monitor,
  Heart,
  Cat
} from "lucide-react";

export type ViewName = "home" | "search" | "lists" | "downloads" | "library" | "settings";

const navItems: { icon: typeof Home; label: string; view: ViewName }[] = [
  { icon: Home, label: "Home", view: "home" },
  { icon: Search, label: "Search", view: "search" },
  { icon: Monitor, label: "My Lists", view: "lists" },
  { icon: Download, label: "Downloads", view: "downloads" },
  { icon: Library, label: "Library", view: "library" },
  { icon: Settings, label: "Settings", view: "settings" },
];

interface SidebarProps {
  activeView: ViewName;
  onNavigate: (view: ViewName) => void;
}

export default function Sidebar({ activeView, onNavigate }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[72px] lg:w-60 bg-black/60 backdrop-blur-xl border-r border-white/[0.04] z-50 flex flex-col py-6 transition-all duration-300">

      {/* Nav Items */}
      <nav className="flex-1 space-y-1 px-3">
        {navItems.map((item) => {
          const isActive = activeView === item.view;
          return (
            <button 
              key={item.view}
              onClick={() => onNavigate(item.view)}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl transition-all duration-200 group ${
                isActive 
                  ? "bg-accent/10 text-white" 
                  : "text-gray-500 hover:text-white hover:bg-white/[0.04]"
              }`}
            >
              <div className={`flex items-center justify-center w-9 h-9 rounded-lg transition-colors ${
                isActive ? "bg-accent text-white shadow-lg shadow-accent/25" : "group-hover:text-accent"
              }`}>
                <item.icon size={18} />
              </div>
              <span className="hidden lg:block text-[13px] font-semibold tracking-wide">{item.label}</span>
            </button>
          );
        })}
      </nav>
      
      {/* Footer */}
      <div className="px-5 py-3 mt-auto hidden lg:block">
        <p className="text-[10px] uppercase font-bold tracking-[0.15em] text-gray-700">Anicat Dashboard</p>
      </div>
    </aside>
  );
}
