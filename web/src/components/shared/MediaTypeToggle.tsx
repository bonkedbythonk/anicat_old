"use client";

import { Monitor, BookOpen } from "lucide-react";

export type MediaTypeValue = "ANIME" | "MANGA";

interface MediaTypeToggleProps {
  value: MediaTypeValue;
  onChange: (value: MediaTypeValue) => void;
  className?: string;
}

/**
 * A reusable Anime/Manga toggle button group.
 *
 * Used across SearchView, LibraryView, and ListsView to avoid
 * duplicated Tailwind className strings and onClick handlers.
 */
export default function MediaTypeToggle({
  value,
  onChange,
  className = "",
}: MediaTypeToggleProps) {
  const activeClass =
    "bg-accent text-white shadow-lg shadow-accent/20";
  const inactiveClass = "text-gray-500 hover:text-white";

  return (
    <div
      className={`flex bg-white/[0.04] p-1 rounded-xl border border-white/[0.06] w-fit ${className}`}
    >
      <button
        onClick={() => onChange("ANIME")}
        className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
          value === "ANIME" ? activeClass : inactiveClass
        }`}
      >
        <Monitor size={16} />
        <span>Anime</span>
      </button>
      <button
        onClick={() => onChange("MANGA")}
        className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-semibold text-sm transition-all ${
          value === "MANGA" ? activeClass : inactiveClass
        }`}
      >
        <BookOpen size={16} />
        <span>Manga</span>
      </button>
    </div>
  );
}
