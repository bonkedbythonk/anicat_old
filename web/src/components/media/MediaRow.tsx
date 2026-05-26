"use client";

import { useRef, useState, useEffect, useCallback, memo } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import MediaCard from "./MediaCard";
import type { MediaItem } from "@/lib/api";

interface MediaRowProps {
  title: string;
  items: MediaItem[];
  onSelect?: (item: MediaItem) => void;
  /** Optional secondary group rendered after a visual divider in the same scroll row */
  secondaryItems?: MediaItem[];
  /** Label shown on the divider pill */
  secondaryLabel?: string;
}

// Approximate card step (card width + gap). Measured at md breakpoint:
// w-[180px] + space-x-4 (16px) = 196px.  Slightly conservative.
const CARD_STEP = 194;
const BUFFER = 3; // extras rendered on each side of visible area

const MediaRow = memo(function MediaRow({
  title,
  items,
  onSelect,
  secondaryItems,
  secondaryLabel = "Smart Picks",
}: MediaRowProps) {
  const rowRef = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);
  const totalItems = items.length + (secondaryItems?.length ?? 0);
  const [visibleEnd, setVisibleEnd] = useState(Math.min(totalItems, 10));
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  // Recalculate visible range and scroll indicators from scroll position
  const updateRange = useCallback(() => {
    const el = rowRef.current;
    if (!el) return;
    const visible = Math.ceil((el.scrollLeft + el.clientWidth) / CARD_STEP) + BUFFER;
    const clamped = Math.min(totalItems, Math.max(10, visible));
    setVisibleEnd(prev => (prev !== clamped ? clamped : prev));

    setCanScrollLeft(el.scrollLeft > 2);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 2);
  }, [totalItems]);

  useEffect(() => {
    const el = rowRef.current;
    if (!el) return;

    const resizeObserver = new ResizeObserver(() => {
      updateRange();
    });
    resizeObserver.observe(el);

    el.addEventListener("scroll", updateRange, { passive: true });
    updateRange();

    return () => {
      resizeObserver.disconnect();
      el.removeEventListener("scroll", updateRange);
    };
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

  if (!items.length && !secondaryItems?.length) return null;

  const hasSecondary = secondaryItems && secondaryItems.length > 0;

  return (
    <div
      className="space-y-4 relative group/row"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <h2 className="text-lg font-bold text-white tracking-wide px-1">{title}</h2>

      <div className="relative">
        {/* Left arrow */}
        <div className={`absolute left-0 top-0 bottom-6 w-12 z-40 flex items-center justify-start transition-opacity duration-300 ${isHovered && canScrollLeft ? 'opacity-100' : 'opacity-0'} pointer-events-none`}>
          <button
            onClick={() => scroll("left")}
            className={`p-2 ml-1 rounded-full bg-black/80 text-white hover:bg-accent hover:text-white transition-colors border border-white/10 shadow-lg ${isHovered && canScrollLeft ? 'pointer-events-auto' : 'pointer-events-none'}`}
          >
            <ChevronLeft size={20} />
          </button>
        </div>

        <div
          ref={rowRef}
          className="flex space-x-4 overflow-x-auto scrollbar-hide scroll-smooth pb-2"
        >
          {/* Primary items */}
          {items.map((item, idx) => (
            <div
              key={`primary-${item.id}-${idx}`}
              className="w-[150px] md:w-[180px] flex-none"
            >
              {idx < visibleEnd ? (
                <MediaCard item={item} onSelect={onSelect} />
              ) : (
                <div className="w-full rounded-lg bg-white/[0.03]" style={{ aspectRatio: '2/3' }} />
              )}
            </div>
          ))}

          {/* Divider — only shown when there are secondary items */}
          {hasSecondary && (
            <div className="flex-none flex flex-col items-center justify-center gap-2 px-2 select-none">
              <div className="w-px flex-1 bg-white/[0.06]" />
              <span className="px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.07] text-[9px] font-bold text-white/40 uppercase tracking-widest whitespace-nowrap">
                {secondaryLabel}
              </span>
              <div className="w-px flex-1 bg-white/[0.06]" />
            </div>
          )}

          {/* Secondary items */}
          {hasSecondary && secondaryItems!.map((item, idx) => {
            const globalIdx = items.length + 1 + idx; // +1 for divider
            return (
              <div
                key={`secondary-${item.id}-${idx}`}
                className="w-[150px] md:w-[180px] flex-none opacity-80 hover:opacity-100 transition-opacity"
              >
                {globalIdx < visibleEnd + BUFFER ? (
                  <MediaCard item={item} onSelect={onSelect} />
                ) : (
                  <div className="w-full rounded-lg bg-white/[0.03]" style={{ aspectRatio: '2/3' }} />
                )}
              </div>
            );
          })}
        </div>

        {/* Right arrow */}
        <div className={`absolute right-0 top-0 bottom-6 w-12 z-40 flex items-center justify-end transition-opacity duration-300 ${isHovered && canScrollRight ? 'opacity-100' : 'opacity-0'} pointer-events-none`}>
          <button
            onClick={() => scroll("right")}
            className={`p-2 mr-1 rounded-full bg-black/80 text-white hover:bg-accent hover:text-white transition-colors border border-white/10 shadow-lg ${isHovered && canScrollRight ? 'pointer-events-auto' : 'pointer-events-none'}`}
          >
            <ChevronRight size={20} />
          </button>
        </div>
      </div>
    </div>
  );
});

export default MediaRow;
