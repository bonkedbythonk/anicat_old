"use client";

import { useRef, useState, useEffect, useCallback, memo } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import MediaCard from "./MediaCard";
import type { MediaItem } from "@/lib/api";

interface MediaRowProps {
  title: string;
  items: MediaItem[];
  onSelect?: (item: MediaItem) => void;
}

// Approximate card step (card width + gap). Measured at md breakpoint:
// w-[180px] + space-x-4 (16px) = 196px.  Slightly conservative.
const CARD_STEP = 194;
const BUFFER = 3; // extras rendered on each side of visible area

const MediaRow = memo(function MediaRow({ title, items, onSelect }: MediaRowProps) {
  const rowRef = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [visibleEnd, setVisibleEnd] = useState(Math.min(items.length, 10));

  // Recalculate visible range from scroll position
  const updateRange = useCallback(() => {
    const el = rowRef.current;
    if (!el) return;
    const visible = Math.ceil((el.scrollLeft + el.clientWidth) / CARD_STEP) + BUFFER;
    const clamped = Math.min(items.length, Math.max(10, visible));
    setVisibleEnd(prev => (prev !== clamped ? clamped : prev));
  }, [items.length]);

  useEffect(() => {
    const el = rowRef.current;
    if (!el) return;
    el.addEventListener("scroll", updateRange, { passive: true });
    updateRange();
    return () => el.removeEventListener("scroll", updateRange);
  }, [updateRange]);

  const scroll = (direction: "left" | "right") => {
    if (rowRef.current) {
      const { scrollLeft, clientWidth } = rowRef.current;
      const scrollTo = direction === "left"
        ? scrollLeft - clientWidth * 0.75
        : scrollLeft + clientWidth * 0.75;
      rowRef.current.scrollTo({ left: scrollTo, behavior: "smooth" });
    }
  };

  if (!items.length) return null;

  return (
    <div
      className="space-y-4 relative group/row"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <h2 className="text-lg font-bold text-white tracking-wide px-1">{title}</h2>

      <div className="relative">
        {/* Left arrow */}
        <div className={`absolute left-0 top-0 bottom-6 w-14 bg-gradient-to-r from-background to-transparent z-40 flex items-center justify-start transition-opacity duration-300 ${isHovered ? 'opacity-100' : 'opacity-0'} pointer-events-none`}>
          <button
            onClick={() => scroll("left")}
            className="p-2 ml-1 rounded-full bg-black/80 hover:bg-accent hover:text-white transition-colors pointer-events-auto border border-white/10"
          >
            <ChevronLeft size={20} />
          </button>
        </div>

        <div
          ref={rowRef}
          className="flex space-x-4 overflow-x-auto scrollbar-hide scroll-smooth pb-2"
        >
          {items.map((item, idx) => (
            <div
              key={`${item.id}-${idx}`}
              className="w-[150px] md:w-[180px] flex-none"
            >
              {idx < visibleEnd ? (
                <MediaCard item={item} onSelect={onSelect} />
              ) : (
                // Lightweight placeholder: just a coloured rectangle
                <div className="w-full rounded-lg bg-white/[0.03]" style={{ aspectRatio: '2/3' }} />
              )}
            </div>
          ))}
        </div>

        {/* Right arrow */}
        <div className={`absolute right-0 top-0 bottom-6 w-14 bg-gradient-to-l from-background to-transparent z-40 flex items-center justify-end transition-opacity duration-300 ${isHovered ? 'opacity-100' : 'opacity-0'} pointer-events-none`}>
          <button
            onClick={() => scroll("right")}
            className="p-2 mr-1 rounded-full bg-black/80 hover:bg-accent hover:text-white transition-colors pointer-events-auto border border-white/10"
          >
            <ChevronRight size={20} />
          </button>
        </div>
      </div>
    </div>
  );
});

export default MediaRow;
