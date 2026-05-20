"use client";

import { useRef, useState, useEffect } from "react";
import MediaCard from "./MediaCard";
import type { MediaItem } from "@/lib/api";

interface LazyCardProps {
  item: MediaItem;
  onSelect?: (item: MediaItem) => void;
  /** Extra rootMargin for the IntersectionObserver, defaults to 200px */
  rootMargin?: string;
}

/**
 * LazyCard — renders a lightweight placeholder until the card is near
 * the viewport, then swaps in the real MediaCard.  Eliminates the cost
 * of rendering dozens of offscreen cards with images, overlays and
 * hover effects.
 */
export default function LazyCard({ item, onSelect, rootMargin = "200px" }: LazyCardProps) {
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [rootMargin]);

  if (visible) {
    return <MediaCard item={item} onSelect={onSelect} />;
  }

  return (
    <div
      ref={ref}
      className="w-full rounded-lg bg-white/[0.03]"
      style={{ aspectRatio: "2/3" }}
    />
  );
}
